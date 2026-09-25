/* 侧边面板 UI 检查（jsdom 真 DOM，跑在本机 5174 上）
 *
 * 为什么放仓库里：以前这些脚本放临时目录，被清过两次，历史结论没法复跑。
 * 用法：
 *   cd tools/uicheck && npm i jsdom            # 只需一次
 *   node panel_check.js                        # 需要 5174 在跑（先「启动」）
 *
 * 覆盖：①「文档」入口与面板结构 ②文档可编辑 ③幻灯片 16:9 ④PPT 优化区（导入/体检/一键/下载）
 *      ⑤开关关掉时灰显并说明原因 ⑥会话里不再有「下一步」卡片 ⑦每条回答都有【生成文档】
 */
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const BASE = process.env.EDU_BASE || 'http://127.0.0.1:5174';
const ROOT = path.resolve(__dirname, '..', '..');
const HTML = fs.readFileSync(path.join(ROOT, 'static', 'index.html'), 'utf8')
  .replace('<head>', '<head><base href="' + BASE + '/">');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const txt = (el) => (el ? el.textContent.replace(/\s+/g, ' ').trim() : '(none)');
let pass = 0, fail = 0;
const check = (name, ok, extra) => {
  console.log((ok ? '  ✅ ' : '  ❌ ') + name + (extra ? '  ' + extra : ''));
  ok ? pass++ : fail++;
};

/* 桩数据：PPT 优化接口（真上传在 harness 里过不了 Node fetch 的 FormData 类型，这里只验接线） */
const REPORT = {
  ok: true, job_id: 'stub-job', file: '答辩稿.pptx', slides: 18,
  canvas: { width_px: 1280, height_px: 720 },
  theme: { title_font: '微软雅黑', body_font: '宋体', body_levels: [44, 32, 28, 24, 20] },
  totals: { tables: 3, charts: 2, diagrams: 1, images: 7, chars: 2456 },
  pages: [], flags: { dense_pages: [7], sparse_pages: [15], needs_confirmation: [9] },
};
const POLISH = {
  ok: true, pages: 18, file: 'x',
  applied: [{ action: 'font', label: '统一字体', runs: 128 },
            { action: 'strip-anim', label: '清理动画 / 转场', timing_removed: 42 }],
  verify: { ok: true, detail: '[VERIFY] passed' },
};

function makeDom(opts) {
  const o = opts || {};
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => { if (!/Could not load script/.test(e.message || '')) errors.push(e.message); });
  vc.on('error', (...a) => errors.push(a.join(' ')));
  vc.on('warn', () => {}); vc.on('log', () => {});
  const dom = new JSDOM(HTML, {
    url: BASE + '/', runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, resources: 'usable',
    beforeParse(window) {
      /* jsdom 缺一批浏览器 API：主脚本 init 时调用会抛未捕获错误 → 整个内联脚本当场中断，
         后面的绑定（圆钮点击、面板渲染）全挂不上，检查会误报"点不动"。
         这不是应用 bug（真浏览器都有），所以在检查脚本里补齐。 */
      if (!window.matchMedia) {
        window.matchMedia = (q) => ({ matches: false, media: q, onchange: null,
          addListener() {}, removeListener() {},
          addEventListener() {}, removeEventListener() {}, dispatchEvent() { return false; } });
      }
      if (!window.ResizeObserver) {
        window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
      }
      if (!window.IntersectionObserver) {
        window.IntersectionObserver = class {
          observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
        };
      }
      if (!window.requestIdleCallback) window.requestIdleCallback = (fn) => setTimeout(fn, 0);
      if (!window.scrollTo) window.scrollTo = () => {};
      if (window.Element && !window.Element.prototype.scrollIntoView) {
        window.Element.prototype.scrollIntoView = () => {};
      }

      const realFetch = fetch;
      window.fetch = async function (u, op) {
        const p = new URL(String(u), BASE).pathname;
        if (p === '/api/ppt/status') {
          return new Response(JSON.stringify(o.pptOff
            ? { ok: true, enabled: false, ready: false, install: { intake_ready: true, commit: 'stub' }, actions: [] }
            : { ok: true, enabled: true, ready: true, install: { intake_ready: true, installed: true, commit: 'stub' },
                actions: [{ id: 'font', label: '统一字体' }, { id: 'size', label: '统一字号层级' },
                          { id: 'strip-anim', label: '清理动画 / 转场' }] }),
            { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
        if (p === '/api/ppt/intake') return new Response(JSON.stringify(REPORT), { status: 200, headers: { 'Content-Type': 'application/json' } });
        if (p === '/api/ppt/polish') return new Response(JSON.stringify(POLISH), { status: 200, headers: { 'Content-Type': 'application/json' } });
        return realFetch(new URL(String(u), BASE).toString(), op);
      };
    },
  });
  return { w: dom.window, doc: dom.window.document, errors };
}

async function openDocPanel(doc) {
  doc.querySelector('#spQuad .qbtn[data-v="doc"]').click();
  await sleep(900);
}

(async () => {
  console.log('== 面板结构 / 入口 ==');
  {
    const { w, doc } = makeDom();
    await sleep(2500);
    const shell = Array.from(doc.querySelector('.shell').children).map((c) => c.id || c.tagName);
    check('右侧只有一块面板（.shell 子元素）', shell.join(',') === 'ASIDE,MAIN,sidePanel', shell.join(' | '));
    check('没有旧的独立面板 #docPanel', !doc.getElementById('docPanel'));
    check('「文档」入口在侧边面板里', !!doc.querySelector('#spQuad .qbtn[data-v="doc"]'));
    await openDocPanel(doc);
    check('点它进文档视图', doc.getElementById('sidePanel').classList.contains('sp-doc'));
    const ed = doc.querySelector('#spBody .dp-word[contenteditable="true"]');
    check('文档页签可直接编辑', !!ed);
    check('编辑工具栏显示', doc.getElementById('docPanelFmt').style.display === 'flex');
    doc.querySelector('#spBody .dp-tab[data-dp="slides"]').click(); await sleep(600);
    check('幻灯片页签有面板内 16:9 预览台', !!doc.querySelector('#spBody .dp-stage'));
    check('提示小字仍在', /右侧为内存预览效果/.test(txt(doc.querySelector('.dp-note'))));
    w.close();
  }

  console.log('== PPT 优化区（桩后端） ==');
  {
    const { w, doc } = makeDom();
    await sleep(2500);
    await openDocPanel(doc);
    doc.querySelector('#spBody .dp-tab[data-dp="slides"]').click(); await sleep(900);
    check('优化区存在', !!doc.querySelector('.ppt-box'));
    check('状态行报安装情况', /就绪/.test(txt(doc.querySelector('.ppt-state'))), txt(doc.querySelector('.ppt-state')));
    check('导入按钮可用', doc.getElementById('pptPick').disabled === false);
    const input = doc.getElementById('docPanelFile');
    const file = new w.File([new Uint8Array([1, 2, 3])], '答辩稿.pptx',
      { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    input.dispatchEvent(new w.Event('change', { bubbles: true }));
    for (let i = 0; i < 12 && !doc.querySelector('.ppt-rep'); i++) await sleep(400);
    check('体检报告出现', !!doc.querySelector('.ppt-rep'));
    check('报告含规模/字体/字号层级',
      /18 页/.test(txt(doc.querySelector('.ppt-rep'))) && /微软雅黑/.test(txt(doc.querySelector('.ppt-rep'))));
    const acts = Array.from(doc.querySelectorAll('.ppt-box input[data-act]'));
    check('动作默认只勾「统一字体」（保守）',
      acts.length === 3 && acts.filter((c) => c.checked).map((c) => c.dataset.act).join() === 'font',
      acts.map((c) => c.dataset.act + (c.checked ? '✓' : '')).join('/'));
    check('未优化时下载按钮灰着', doc.getElementById('pptGet').disabled === true);
    acts.forEach((c) => { if (c.dataset.act === 'strip-anim') c.checked = true; });
    doc.getElementById('pptRun').click();
    for (let i = 0; i < 12 && !/已优化|失败/.test(txt(doc.querySelector('.ppt-tip'))); i++) await sleep(400);
    check('一键优化给出结果与内容校验', /已优化/.test(txt(doc.querySelector('.ppt-tip'))) && /内容校验：✅/.test(txt(doc.querySelector('.ppt-tip'))),
      txt(doc.querySelector('.ppt-tip')).slice(0, 60));
    check('优化后下载可用', doc.getElementById('pptGet').disabled === false);
    w.close();
  }

  console.log('== 开关关掉时（桩：未开） ==');
  {
    const { w, doc } = makeDom({ pptOff: true });
    await sleep(2500);
    await openDocPanel(doc);
    doc.querySelector('#spBody .dp-tab[data-dp="slides"]').click(); await sleep(800);
    check('状态行说明为什么不可用', /已关闭/.test(txt(doc.querySelector('.ppt-state'))), txt(doc.querySelector('.ppt-state')));
    check('导入按钮灰显', doc.getElementById('pptPick').disabled === true);
    w.close();
  }

  console.log('== 会话侧：无「下一步」卡片 + 每条回答有【生成文档】 ==');
  {
    const { w, doc, errors } = makeDom();
    await sleep(3000);
    const vis = (() => { const c = doc.body.cloneNode(true); c.querySelectorAll('script,style').forEach((n) => n.remove()); return c.textContent.replace(/\s+/g, ' '); })();
    check('页面上没有「下一步」字样', !/下一步/.test(vis));
    check('计划卡片不渲染', doc.querySelectorAll('.plan-choice').length === 0);
    const btns = Array.from(doc.querySelectorAll('.pill-btn')).map(txt);
    check('历史回答带【生成文档】', btns.filter((x) => x === '生成文档').length > 0, btns.filter((x) => x === '生成文档').length + ' 个');
    check('无运行时错误', errors.length === 0, errors.slice(0, 2).join(' | '));
    w.close();
  }

  console.log('\n结果：' + pass + ' 通过 / ' + fail + ' 失败');
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('CHECK ERROR:', (e && e.stack) || e); process.exit(1); });
