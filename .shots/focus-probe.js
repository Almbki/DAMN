/**
 * 焦点态实测：登录页输入框在**聚焦前/后**的 computed style 差在哪。
 *
 * 要证伪的是"那圈黑框是浏览器 UA 的 outline，而不是我们画的"：
 *   - 聚焦前 outline 应该已经是 none（说明我们没画外框）
 *   - 聚焦后 outline 仍然是 none，而 border-bottom-color 变成强调色（说明焦点指示是我们自己画的）
 *
 * 用法：node focus-probe.js <url> <out.png>
 */
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const url = process.argv[2] || 'http://localhost:8081/';
const png = process.argv[3] || 'focus-after.png';
const W = 1440;
const H = 1000;
const PORT = 9500 + (Number(process.env.CDP_OFFSET) || 0);

const args = [
  '--headless',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--user-data-dir=' + path.join(__dirname, 'cdp-focus-' + Date.now()),
  '--window-size=' + W + ',' + H,
  '--remote-debugging-port=' + PORT,
  'about:blank',
];

const child = spawn(EDGE, args, { stdio: 'ignore', windowsHide: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const PROBE = `(() => {
  const inputs = [...document.querySelectorAll('input, textarea')];
  const active = document.activeElement;
  return {
    focusedLabel: active && active.getAttribute ? (active.getAttribute('aria-label') || null) : null,
    inputs: inputs.map((el) => {
      const cs = getComputedStyle(el);
      return {
        label: el.getAttribute('aria-label') || el.tagName.toLowerCase(),
        isFocused: el === active,
        outlineStyle: cs.outlineStyle,
        outlineWidth: cs.outlineWidth,
        outlineColor: cs.outlineColor,
        borderBottomColor: cs.borderBottomColor,
        borderBottomWidth: cs.borderBottomWidth,
        boxShadow: cs.boxShadow,
      };
    }),
  };
})()`;

async function main() {
  let targets = null;
  for (let i = 0; i < 60; i++) {
    try {
      targets = await (await fetch('http://127.0.0.1:' + PORT + '/json/list')).json();
      if (targets && targets.length) break;
    } catch {}
    await sleep(500);
  }
  if (!targets) throw new Error('CDP did not start');

  const page = targets.find((t) => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
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
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });

  await send('Page.navigate', { url });
  await sleep(9000);

  const read = async (label) => {
    const r = await send('Runtime.evaluate', { expression: PROBE, returnByValue: true });
    console.log('\n=== ' + label + ' ===');
    console.log(JSON.stringify(r.result?.result?.value, null, 2));
    return r.result?.result?.value;
  };

  await read('BEFORE focus');

  // 点进密码框（真鼠标事件，和用户操作一致）
  const box = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = [...document.querySelectorAll('input')].find((i) => i.getAttribute('aria-label') === '密码');
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
    })()`,
    returnByValue: true,
  });
  const point = box.result?.result?.value;
  if (!point) throw new Error('password input not found');
  console.log('\nclicking password input at ' + point.x + ',' + point.y);
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await sleep(1200);

  await read('AFTER focus (password)');

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot.result?.data) {
    fs.writeFileSync(path.resolve(__dirname, png), Buffer.from(shot.result.data, 'base64'));
    console.log('\nshot: ' + path.resolve(__dirname, png));
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
