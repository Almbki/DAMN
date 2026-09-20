/**
 * 用 CDP 量真实布局 + 全页截图。
 *
 * 为什么需要它：截图只能看出"哪里被切了"，量 scrollWidth 才能确认是溢出还是裁切。
 * Node 24 自带 WebSocket，所以零依赖。
 *
 * 用法：node measure.js <url> <宽> <高> [输出png] [scheme:1|0|不传=跟随系统]
 */
const { spawn } = require('node:child_process');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const url = process.argv[2];
const W = Number(process.argv[3] || 390);
const H = Number(process.argv[4] || 844);
const png = process.argv[5];
const scheme = process.argv[6];
const PORT = 9224;

const args = [
  '--headless',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--user-data-dir=' + __dirname + '/cdp-profile-' + W,
  '--window-size=' + W + ',' + H,
  '--force-prefers-reduced-motion',
];
if (scheme) args.push('--blink-settings=preferredColorScheme=' + scheme);
args.push('--remote-debugging-port=' + PORT, 'about:blank');

const child = spawn(EDGE, args, { stdio: 'ignore', windowsHide: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getJson(path) {
  const res = await fetch('http://127.0.0.1:' + PORT + path);
  return res.json();
}

async function main() {
  // 等 CDP 起来
  let targets = null;
  for (let i = 0; i < 40; i++) {
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
  await send('Emulation.setDeviceMetricsOverride', {
    width: W,
    height: H,
    deviceScaleFactor: 1,
    mobile: W < 600,
  });
  if (scheme) {
    await send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-color-scheme', value: scheme === '1' ? 'light' : 'dark' }],
    });
  }

  await send('Page.navigate', { url });
  await sleep(5000);

  const expr = `(() => {
    const de = document.documentElement;
    const body = document.body;
    // 找出超出视口右边界的所有元素
    const over = [];
    document.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.right > window.innerWidth + 1) {
        over.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className || '').toString().slice(0, 40),
          left: Math.round(r.left),
          right: Math.round(r.right),
          w: Math.round(r.width),
          text: (el.textContent || '').trim().slice(0, 24),
        });
      }
    });
    // 底部导航：拿它的背景色与实际宽度
    const link = [...document.querySelectorAll('a')].find((a) => (a.getAttribute('aria-label') || '').includes('现在做什么'));
    const bar = link ? link.parentElement : null;
    const barStyle = bar ? getComputedStyle(bar) : null;

    // 精确量测：抬头段落 + 它的祖先链 + 四档卡片
    const paras = [...document.querySelectorAll('div,p')].filter((el) =>
      (el.textContent || '').startsWith('不是正式页面'));
    const p = paras.length ? paras[paras.length - 1] : null;
    const chain = [];
    let node = p;
    while (node && node !== document.body && chain.length < 8) {
      const r = node.getBoundingClientRect();
      const cs = getComputedStyle(node);
      chain.push({
        tag: node.tagName.toLowerCase(),
        left: Math.round(r.left),
        right: Math.round(r.right),
        w: Math.round(r.width),
        maxW: cs.maxWidth,
        pad: cs.paddingLeft + '/' + cs.paddingRight,
        whiteSpace: cs.whiteSpace,
        overflow: cs.overflowX,
      });
      node = node.parentElement;
    }

    const flat = [...document.querySelectorAll('div')].find((el) => (el.textContent || '').trim() === '平面 flat');

    // 玻璃审计：竖栏那层有没有真的应用 backdrop-filter
    const glassNodes = [...document.querySelectorAll('div')]
      .filter((d) => {
        const cs = getComputedStyle(d);
        return (cs.backdropFilter && cs.backdropFilter !== 'none') || (cs.webkitBackdropFilter && cs.webkitBackdropFilter !== 'none');
      })
      .slice(0, 4)
      .map((d) => {
        const cs = getComputedStyle(d);
        const r = d.getBoundingClientRect();
        return {
          w: Math.round(r.width),
          h: Math.round(r.height),
          bg: cs.backgroundColor,
          backdrop: cs.backdropFilter || cs.webkitBackdropFilter,
          border: cs.borderTopWidth + ' ' + cs.borderTopColor,
        };
      });

    let grid = null;
    if (flat) {
      // 往上找带 flexWrap 的那一层
      let n = flat;
      for (let i = 0; i < 5 && n; i++) {
        const cs = getComputedStyle(n);
        if (cs.flexWrap !== 'nowrap' || cs.display === 'flex') {
          const kids = [...n.children].map((c) => {
            const r = c.getBoundingClientRect();
            return { l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), h: Math.round(r.height), t: Math.round(r.top) };
          });
          const kr = n.getBoundingClientRect();
          grid = {
            level: i,
            display: cs.display,
            flexDirection: cs.flexDirection,
            flexWrap: cs.flexWrap,
            width: Math.round(kr.width),
            left: Math.round(kr.left),
            childCount: kids.length,
            children: kids,
          };
          if (kids.length > 1) break;
        }
        n = n.parentElement;
      }
    }

    return {
      viewport: window.innerWidth + 'x' + window.innerHeight,
      htmlScrollW: de.scrollWidth,
      bodyScrollW: body.scrollWidth,
      scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
      paraChain: chain,
      glassNodes,
      grid,
      bar: bar
        ? {
            width: Math.round(bar.getBoundingClientRect().width),
            bg: barStyle.backgroundColor,
            borderTop: barStyle.borderTopWidth + ' ' + barStyle.borderTopColor,
          }
        : null,
      overflowing: over.slice(0, 14),
      overflowCount: over.length,
    };
  })()`;

  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  console.log(JSON.stringify(r.result && r.result.result ? r.result.result.value : r, null, 2));

  if (png) {
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    if (shot.result && shot.result.data) {
      // 用 path.resolve 而不是直接写：Windows 盘符会被 Node 当成 URL scheme
      const target = require('node:path').resolve(__dirname, png);
      require('node:fs').writeFileSync(target, Buffer.from(shot.result.data, 'base64'));
      console.log('已写全页截图: ' + target);
    } else {
      console.log('截图失败: ' + JSON.stringify(shot).slice(0, 300));
    }
  }

  ws.close();
  child.kill();
  process.exit(0);
}

main().catch((e) => {
  console.error('出错: ' + e.message);
  try { child.kill(); } catch {}
  process.exit(1);
});
