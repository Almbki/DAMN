/**
 * 真点一下：验证「点按钮 → 乐观更新 → PATCH 真后端 → 重新渲染」这条闭环。
 *
 * 静态截图证明不了这件事 —— 界面画得再对，点击没接上后端也看不出来。
 * 这里用 CDP 的 `Input.dispatchMouseEvent` 发**可信输入事件**（react-native-web 的
 * Pressable 认的是 pointer 事件，`element.click()` 不一定触发 onPress）。
 *
 * 用法：node app-click.js <url> <out.png> <token> [按钮文字|@primary] [点几次]
 *
 * `@primary` = 页面上**最高的那个按钮**（主操作）。用它而不是中文文案，是因为
 * Windows PowerShell 5.1 会按 ANSI 读无 BOM 的 UTF-8 脚本，把作为参数传进来的中文
 * 变成乱码，导致按文字匹配永远找不到按钮。
 */
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const url = process.argv[2];
const png = process.argv[3];
const token = process.argv[4];
const target = process.argv[5] || '开始';
const times = Number(process.argv[6] || 1);
const W = 1440;
const H = 1000;
const PORT = 9400 + (Number(process.env.CDP_OFFSET) || 0);

const args = [
  '--headless',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--user-data-dir=' + path.join(__dirname, 'cdp-click-' + Date.now()),
  '--window-size=' + W + ',' + H,
  '--force-prefers-reduced-motion',
  '--remote-debugging-port=' + PORT,
  'about:blank',
];

const child = spawn(EDGE, args, { stdio: 'ignore', windowsHide: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
  const logs = [];

  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
      return;
    }
    if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(msg.params.type)) {
      logs.push(msg.params.type + ': ' + (msg.params.args || []).map((a) => String(a.value ?? a.description ?? '')).join(' ').slice(0, 200));
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      logs.push('exception: ' + String(msg.params.exceptionDetails?.text).slice(0, 200));
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
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `try { localStorage.setItem('damn.auth.token', ${JSON.stringify(token)}); } catch (e) {}`,
  });
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });

  await send('Page.navigate', { url });
  await sleep(9000);

  const readText = async (label) => {
    const r = await send('Runtime.evaluate', {
      expression: `(document.body.innerText || '').replace(/\\n{2,}/g, '\\n').slice(0, 420)`,
      returnByValue: true,
    });
    console.log('\n--- ' + label + ' ---');
    console.log(r.result?.result?.value);
  };

  await readText('before');

  // 可选：先往第一个输入框里打字（环境变量传文本，避免 PS 5.1 把参数里的中文读坏）
  if (process.env.CLICK_TYPE_TEXT) {
    const box = await send('Runtime.evaluate', {
      expression: `(() => {
        const el = document.querySelector('textarea,input[type="text"],input:not([type])');
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
      })()`,
      returnByValue: true,
    });
    const point = box.result?.result?.value;
    if (!point) {
      console.log('\n!! no text input found');
    } else {
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
      await sleep(400);
      await send('Input.insertText', { text: process.env.CLICK_TYPE_TEXT });
      await sleep(800);
      console.log('\ntyped ' + process.env.CLICK_TYPE_TEXT.length + ' chars');
      await readText('after typing');
    }
  }

  for (let n = 1; n <= times; n++) {
    // 找到目标按钮的中心点（react-native-web 把 Pressable 渲染成 div[role=button]）
    const box = await send('Runtime.evaluate', {
      expression: `(() => {
        const want = ${JSON.stringify(target)};
        const candidates = [...document.querySelectorAll('[role="button"],button,[role="checkbox"]')];
        let el = null;
        if (want === '@primary') {
          // 主操作 = 全页最高的按钮（56px vs 次要动作的 44px）
          el = candidates
            .map((b) => ({ b, h: b.getBoundingClientRect().height }))
            .sort((a, b) => b.h - a.h)[0]?.b ?? null;
        } else {
          el = candidates.find((b) =>
            (b.textContent || b.getAttribute('aria-label') || '').trim().includes(want),
          ) ?? null;
        }
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), text: (el.textContent||'').trim().slice(0,30) };
      })()`,
      returnByValue: true,
    });
    const point = box.result?.result?.value;
    if (!point) {
      console.log('\n!! button not found: ' + target);
      break;
    }
    console.log(`\nclick #${n} on "${point.text}" at ${point.x},${point.y}`);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
    await sleep(3500);
    await readText(`after click #${n}`);
  }

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot.result?.data) {
    fs.writeFileSync(path.resolve(__dirname, png), Buffer.from(shot.result.data, 'base64'));
    console.log('\nshot: ' + path.resolve(__dirname, png));
  }
  console.log('console: ' + (logs.length ? JSON.stringify(logs.slice(0, 6)) : 'clean'));

  ws.close();
  child.kill();
  process.exit(0);
}

main().catch((e) => {
  console.error('error: ' + e.message);
  try { child.kill(); } catch {}
  process.exit(1);
});
