/**
 * 滚到指定文本并截图（用于审查页面中段的组件）。
 *
 * 用法：node shot.js <url> <宽> <高> <锚点文本> <输出png> <1|0 明暗>
 */
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const [url, wArg, hArg, anchor, outPng, scheme] = process.argv.slice(2);
const W = Number(wArg || 1440);
const H = Number(hArg || 1000);
const PORT = 9228;

const args = [
  '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=' + path.join(__dirname, 'sc-' + W),
  '--window-size=' + W + ',' + H,
  '--force-prefers-reduced-motion',
  '--remote-debugging-port=' + PORT,
  'about:blank',
];
const child = spawn(EDGE, args, { stdio: 'ignore', windowsHide: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  let targets = null;
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch('http://127.0.0.1:' + PORT + '/json/list');
      targets = await r.json();
      if (targets && targets.length) break;
    } catch {}
    await sleep(500);
  }
  const page = targets.find((t) => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  const send = (method, params = {}) =>
    new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

  await new Promise((r) => ws.addEventListener('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  // 把 console 里的 error / warn 与未捕获异常抓回来 —— 截图看的是表象，
  // 报错文本才说明是"警告"还是"真崩"。
  const logs = [];
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
      logs.push('[console.' + m.params.type + '] ' + m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' ').slice(0, 300));
    }
    if (m.method === 'Runtime.exceptionThrown') {
      logs.push('[exception] ' + (m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 400));
    }
  });
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 600 });
  if (scheme) {
    await send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-color-scheme', value: scheme === '1' ? 'light' : 'dark' }],
    });
  }
  await send('Page.navigate', { url });
  await sleep(5000);

  if (anchor) {
    const r = await send('Runtime.evaluate', {
      returnByValue: true,
      expression: `(() => {
        const el = [...document.querySelectorAll('div')].find(d => (d.textContent || '').trim().startsWith(${JSON.stringify(anchor)}));
        if (!el) return 'anchor-not-found';
        el.scrollIntoView({ block: 'center' });
        const r = el.getBoundingClientRect();
        return JSON.stringify({ top: Math.round(r.top), left: Math.round(r.left), h: Math.round(r.height) });
      })()`,
    });
    console.log('锚点定位: ' + JSON.stringify(r.result && r.result.result && r.result.result.value));
    await sleep(900);
  }

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  const target = path.resolve(__dirname, outPng);
  fs.writeFileSync(target, Buffer.from(shot.result.data, 'base64'));
  console.log('已写: ' + target);

  if (logs.length) {
    console.log('--- 页面报错/警告 (' + logs.length + ') ---');
    [...new Set(logs)].slice(0, 12).forEach((l) => console.log('  ' + l));
  } else {
    console.log('--- 页面无 console 错误 ---');
  }

  ws.close();
  child.kill();
  process.exit(0);
})().catch((e) => { console.error(e.message); try { child.kill(); } catch {} process.exit(1); });
