/**
 * dist 产物静态体检（临时脚本，用完可删）
 *
 * ## ⚠️ 这个脚本能查什么、不能查什么（我为此踩了四次坑，先读完再用）
 *
 * **能查**：`global.css` 这类**全局 CSS**（中文字换行修复、字体栈、滚动条），
 * 以及 HTML 里**内联写死**的几何值（固定宽度、max-width、gap…）。
 *
 * **不能查**：**组件级样式**（圆角、阴影、flex 组合）。原因：SSR 输出的
 * `<style id="react-native-stylesheet">` 只是 RNW 的**基础重置表**（约 19KB，
 * 实测里面一条 `border-radius` 都没有）；组件样式由 RNW 在**客户端水合时**
 * 通过 CSS-in-JS 注入，静态 HTML 里不存在。
 *
 * ## 我踩过的四个坑（都是脚本骗了我，不是代码有问题）
 *
 * 1. `.{90}xxx.{90}` 这类正则**不跨行**，命中不了就返回 0，看起来像"属性丢了"；
 * 2. 按第一个 `}` 切 CSS 规则，遇到 `@media` 的嵌套大括号会跑飞，只解析出 4 条规则；
 * 3. 只看 HTML 里的 `<style>`，漏掉 `expo export` 抽出来的**外链 CSS**；
 * 4. 产物是**压缩过的**：`white-space:normal!important` 冒号后没有空格，
 *    正则里写死空格就会误报"修复没进产物"。
 *
 * 结论：**要验组件级布局，必须渲染页面后读 `getComputedStyle`**，静态产物做不到。
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const file = process.argv[2] ?? 'dist/workbench.html';
const html = readFileSync(file, 'utf8');
const distDir = dirname(resolve(file));

/**
 * 只取 <head>：RNW 的样式表与跨端重置都在这里，body 里混着 hydration 脚本会干扰。
 *
 * ⚠️ 但**不能只看 head 里的 `<style>`** —— `expo export` 会把 `global.css` 抽成
 * 外链（`/_expo/static/css/global-*.css`），只扫内联块会漏掉它，
 * 于是把"中文换行修复没进产物"这类假警报报出来（我为此连踩三次）。
 */
const headEnd = html.indexOf('</head>');
const head = headEnd >= 0 ? html.slice(0, headEnd) : html;

/** 把 head 里外链的本地 CSS 也读进来（跳过 http(s) 外链） */
function linkedCss(headHtml) {
  const chunks = [];
  for (const m of headHtml.matchAll(/<link[^>]+rel="stylesheet"[^>]*>/g)) {
    const href = /href="([^"]+)"/.exec(m[0])?.[1];
    if (!href || /^https?:/.test(href)) continue;
    const rel = href.replace(/^\//, ''); // 导出产物里的路径是绝对路径，落到 dist 根
    try {
      chunks.push(readFileSync(resolve(distDir, rel), 'utf8'));
    } catch {
      // 拿不到就跳过，不影响其它检查
    }
  }
  return chunks.join('\n');
}

const styleBlocks = [...head.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]);
const sheetSource = [...styleBlocks, linkedCss(head)].join('\n');

/** 展开样式源里的所有 `selector{...}` 规则（要处理 @media 的嵌套大括号） */
function rulesFrom(source) {
  const rules = [];
  const css = source;
  let i = 0;
  let depth = 0;
  let selectorStart = 0;
  let bodyStart = -1;
  while (i < css.length) {
    const ch = css[i];
    if (ch === '{') {
      depth += 1;
      if (depth === 1) bodyStart = i + 1;
    } else if (ch === '}') {
      depth -= 1;
      if (depth === 0 && bodyStart >= 0) {
        rules.push({
          selector: css.slice(selectorStart, css.indexOf('{', selectorStart)).trim(),
          body: css.slice(bodyStart, i),
        });
        selectorStart = i + 1;
        bodyStart = -1;
      }
    }
    i += 1;
  }
  return rules;
}

const rules = rulesFrom(sheetSource);
const headText = rules.map((r) => r.body).join(';');

function collect(prop) {
  const out = [];
  const re = new RegExp(`(?:^|[;{\\s])${prop}\\s*:\\s*([^;]+)`, 'g');
  for (const m of headText.matchAll(re)) out.push(m[1].trim());
  return out;
}

function tally(label, values, isOk) {
  console.log(`\n=== ${label} ===`);
  const groups = new Map();
  for (const v of values) groups.set(v, (groups.get(v) ?? 0) + 1);
  if (groups.size === 0) {
    console.log('  （head 里一条都没有）');
    return;
  }
  for (const [v, n] of [...groups].sort()) {
    console.log(`  ${String(v).padEnd(14)} ×${String(n).padEnd(3)} ${isOk ? (isOk(v) ? '✅' : '❌') : ''}`);
  }
}

const tokens = [4, 8, 12, 16, 20, 999];
const radii = [...new Set(collect('border-radius'))];
console.log('\n⚠️ 静态产物里查不到**组件级**样式（圆角/阴影由 RNW 在客户端水合时注入）。');
console.log('   所以下面这一节为空是**预期结果**，不代表圆角没落地 —— 不要据此改代码。');
tally(
  '圆角（token 只允许 4/8/12/16/20/999）',
  radii,
  (v) => {
    if (v.endsWith('%')) return true; // 圆形由百分比表达的允许
    const n = Number.parseFloat(v);
    return tokens.includes(n);
  },
);

console.log('\n=== 非法值（出现即必然错位）===');
for (const bad of ['NaN', 'undefined', '\\[object']) {
  const n = (headText.match(new RegExp(bad, 'g')) ?? []).length;
  console.log(`  ${bad.replace('\\', '').padEnd(12)} ${n} 次 ${n === 0 ? '✅' : '❌'}`);
}

console.log('\n=== 中文换行修复是否进产物 ===');
// 注意：产物是**压缩过的**，`white-space:normal!important` 冒号后可能没有空格，
// 开头那个 `\s*` 不能省 —— 我第一版就是因为省了它，误报"修复没进产物"。
const preWrap = (headText.match(/white-space:\s*pre-wrap/g) ?? []).length;
const normalImp = (headText.match(/white-space:\s*normal\s*!\s*important/g) ?? []).length;
console.log(`  pre-wrap（RNW 默认，中文不断行的根因）: ${preWrap}`);
console.log(`  white-space:normal !important（我们的修复）: ${normalImp} ${normalImp > 0 ? '✅' : '❌'}`);
console.log(`  flex-wrap:wrap（能否换行）: ${(headText.match(/flex-wrap:\s*wrap/g) ?? []).length}`);

console.log('\n=== 固定宽 > 320px 且无 max-width 约束的元素（手机横向溢出风险）===');
const risky = [];
for (const r of rules) {
  if (!/width:\s*\d{3,}px/.test(r.body)) continue;
  if (/max-width/.test(r.body)) continue;
  const w = Number.parseInt(/width:\s*(\d+)px/.exec(r.body)[1], 10);
  if (w > 320) risky.push({ selector: r.selector, w, body: r.body.slice(0, 90) });
}
if (risky.length === 0) console.log('  无 ✅');
else for (const r of risky) console.log(`  ${r.selector}  width:${r.w}px  ${r.body}`);

console.log(`\n共解析 ${rules.length} 条规则，来自 ${file}`);
