/**
 * 带会话的页面实测：CDP 注入 localStorage 里的 JWT → 打开任意页面 → 量布局 + 全页截图。
 *
 * 为什么不用 measure.js：那个脚本的探测点写死给 workbench 了（找「不是正式页面」
 * 「平面 flat」这些锚点）。这个脚本面向接后端之后的产品页：量导航项、溢出、
 * 并回收 console 错误 —— 真后端 + 真实数据下最容易暴露问题的就是这三样。
 *
 * 用法：
 *   node app-shot.js <url> <宽> <高> <out.png> <scheme:1|0> [token]
 * 不给 token 就是未登录状态（应该看到登录页）。
 *
 * 注意：token 通过 `Page.addScriptToEvaluateOnNewDocument` 在**文档开始执行前**写入，
 * 所以第一次导航就能被 SessionProvider 的冷启动逻辑读到，不需要"先开首页再重载"。
 */
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const url = process.argv[2];
const W = Number(process.argv[3] || 390);
const H = Number(process.argv[4] || 844);
const png = process.argv[5];
const scheme = process.argv[6];
const token = process.argv[7];
const PORT = 9300 + (Number(process.env.CDP_OFFSET) || 0);

const args = [
  '--headless',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--user-data-dir=' + path.join(__dirname, 'cdp-app-' + W + '-' + Date.now()),
  '--window-size=' + W + ',' + H,
  '--force-prefers-reduced-motion',
];
if (scheme) args.push('--blink-settings=preferredColorScheme=' + scheme);
args.push('--remote-debugging-port=' + PORT, 'about:blank');

const child = spawn(EDGE, args, { stdio: 'ignore', windowsHide: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getJson(p) {
  const res = await fetch('http://127.0.0.1:' + PORT + p);
  return res.json();
}

async function main() {
  let targets = null;
  for (let i = 0; i < 60; i++) {
    try {
      targets = await getJson('/json/list');
      if (targets && targets.length) break;
    } catch {}
    await sleep(500);
  }
  if (!targets) throw new Error('CDP 没起来');

  const page = targets.find((t) => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const logs = [];

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
      return;
    }
    if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(msg.params.type)) {
      logs.push(
        msg.params.type + ': ' +
          (msg.params.args || []).map((a) => String(a.value ?? a.description ?? a.type)).join(' ').slice(0, 200),
      );
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails || {};
      logs.push('exception: ' + String((d.exception && (d.exception.description || d.exception.value)) || d.text).slice(0, 300));
    }
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
      logs.push('log: ' + String(msg.params.entry.text).slice(0, 200));
    }
  });

  const send = (method, params = {}) =>
    new Promise((resolve) => {
      const myId = ++id;
      pending.set(myId, resolve);
      ws.send(JSON.stringify({ id: myId, method, params }));
    });

  await new Promise((r) => ws.addEventListener('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');

  if (token) {
    await send('Page.addScriptToEvaluateOnNewDocument', {
      source: `try { localStorage.setItem('damn.auth.token', ${JSON.stringify(token)}); } catch (e) {}`,
    });
  }

  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: W < 600 });
  if (scheme) {
    await send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-color-scheme', value: scheme === '1' ? 'light' : 'dark' }],
    });
  }

  await send('Page.navigate', { url });
  await sleep(9000);

  const expr = `(() => {
    const de = document.documentElement;
    const over = [];
    document.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.right > window.innerWidth + 1) {
        over.push({
          tag: el.tagName.toLowerCase(),
          text: (el.textContent || '').trim().slice(0, 20),
          right: Math.round(r.right),
          w: Math.round(r.width),
        });
      }
    });
    const links = [...document.querySelectorAll('a')].map((a) => {
      const r = a.getBoundingClientRect();
      return {
        label: a.getAttribute('aria-label') || '',
        text: (a.textContent || '').trim(),
        left: Math.round(r.left),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    });
    const inputs = [...document.querySelectorAll('input')].map((i) => {
      const r = i.getBoundingClientRect();
      return { label: i.getAttribute('aria-label') || '', w: Math.round(r.width), h: Math.round(r.height) };
    });
    const buttons = [...document.querySelectorAll('[role="button"],button')].map((b) => {
      const r = b.getBoundingClientRect();
      return { text: (b.textContent || '').trim().slice(0, 28), w: Math.round(r.width), h: Math.round(r.height) };
    });
    return {
      viewport: window.innerWidth + 'x' + window.innerHeight,
      htmlScrollW: de.scrollWidth,
      bodyScrollW: document.body.scrollWidth,
      scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
      text: (document.body.innerText || '').replace(/\\n{2,}/g, '\\n').slice(0, 700),
      navLinks: links,
      inputs,
      buttons,
      overflowCount: over.length,
      overflowing: over.slice(0, 10),
    };
  })()`;

  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  const value = r.result && r.result.result ? r.result.result.value : null;
  console.log(JSON.stringify({ url, w: W, h: H, scheme, loggedIn: !!token, ...value, consoleLogs: logs.slice(0, 12) }, null, 2));

  if (png) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    if (shot.result && shot.result.data) {
      const target = path.resolve(__dirname, png);
      fs.writeFileSync(target, Buffer.from(shot.result.data, 'base64'));
      console.log('shot: ' + target);
    } else {
      console.log('shot failed: ' + JSON.stringify(shot).slice(0, 200));
    }
  }

  ws.close();
  child.kill();
  process.exit(0);
}

main().catch((e) => {
  console.error('error: ' + e.message);
  try { child.kill(); } catch {}
  process.exit(1);
});
