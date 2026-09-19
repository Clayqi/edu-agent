const fs = require('fs');

function check(html, label) {
  let ok = true;
  console.log('===== ' + label + ' =====');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  if (scripts.length === 0) console.log('  (无内联 script)');
  scripts.forEach((m, i) => {
    try { new Function(m[1]); console.log('  script ' + (i + 1) + ' OK'); }
    catch (e) { ok = false; console.log('  script ' + (i + 1) + ' 错误: ' + e.message); }
  });
  const opens = (html.match(/<div[^>]*>/g) || []).length;
  const closes = (html.match(/<\/div>/g) || []).length;
  console.log('  div ' + opens + '/' + closes + (opens === closes ? ' OK' : ' FAIL'));
  if (opens !== closes) ok = false;
  console.log('  dragStart: ' + html.includes("on('dragStart'"));
  console.log('  dragEnd: ' + html.includes("on('dragEnd'"));
  console.log('  lockPhysics: ' + html.includes('lockPhysics'));
  console.log('  stabilizationIterationsDone: ' + html.includes('stabilizationIterationsDone'));
  console.log(ok ? '  == 通过 ==' : '  == 异常 ==');
  return ok;
}

let all = true;
all = check(fs.readFileSync('D:/edu-agent/static/index.html', 'utf-8'), 'index.html 主界面') && all;
all = check(fs.readFileSync('D:/edu-agent/static/kg.html', 'utf-8'), 'kg.html 独立页') && all;
console.log('\n' + (all ? '== 全部通过 ==' : '== 有异常 =='));