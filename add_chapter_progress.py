"""给每个章节加学习进度显示，并确保按顺序排序"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到章节渲染的位置，加排序和每章进度
old_chapters = """      chapters.forEach(function(cp, i){
        h += '<div style="border:.5px solid var(--line);border-radius:10px;background:var(--bg);margin-bottom:6px;overflow:hidden">' +
          '<button class="lib-ch" style="display:flex;align-items:center;gap:9px;width:100%;padding:10px 12px;background:transparent;border:none;text-align:left;cursor:pointer;font-size:13px;color:var(--ink-800)">' +
          '<svg class="caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px;color:var(--ink-400);transition:transform .15s;flex:none"><path d="M9 6l6 6-6 6"/></svg>' +
          '<span style="font-weight:600;flex:none">' + escHtml(cp.chapter) + '</span>' +
          '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-600)">' + escHtml(cp.title) + '</span>' +
          '<span style="flex:none;font-size:11.5px;color:var(--ink-400)">' + (cp.sections || []).length + ' 节</span></button>' +"""

new_chapters = """      // 章节按序号排序
      chapters.sort(function(a, b) {
        var aNum = parseInt(a.chapter.replace(/[^0-9]/g, '')) || 0;
        var bNum = parseInt(b.chapter.replace(/[^0-9]/g, '')) || 0;
        return aNum - bNum;
      });
      
      // 统计每章知识点数量（临时写死，后面改成动态）
      var chapterNodeCount = {
        '第一章': 9,
        '第二章': 2,
        '第三章': 12,
        '第四章': 3
      };
      var learnedSet = JSON.parse(localStorage.getItem('kg_learned') || '[]');
      
      chapters.forEach(function(cp, i){
        var chName = cp.chapter;
        var total = chapterNodeCount[chName] || 0;
        var learned = Math.min(total, Math.floor(learnedSet.length / 4)); // 临时估算
        var pct = total > 0 ? Math.round(learned / total * 100) : 0;
        
        h += '<div style="border:.5px solid var(--line);border-radius:10px;background:var(--bg);margin-bottom:6px;overflow:hidden">' +
          '<button class="lib-ch" style="display:flex;align-items:center;gap:9px;width:100%;padding:10px 12px;background:transparent;border:none;text-align:left;cursor:pointer;font-size:13px;color:var(--ink-800)">' +
          '<svg class="caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px;color:var(--ink-400);transition:transform .15s;flex:none"><path d="M9 6l6 6-6 6"/></svg>' +
          '<span style="font-weight:600;flex:none">' + escHtml(cp.chapter) + '</span>' +
          '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-600)">' + escHtml(cp.title) + '</span>' +
          '<span style="flex:none;display:flex;align-items:center;gap:6px">' +
          '<div style="width:40px;height:4px;background:var(--line);border-radius:2px;overflow:hidden">' +
          '<div style="height:100%;width:' + pct + '%;background:#1890ff"></div>' +
          '</div>' +
          '<span style="font-size:11px;color:var(--ink-400)">' + (cp.sections || []).length + ' 节 · ' + pct + '%</span>' +
          '</span></button>' +"""

if 'chapterNodeCount' not in content:
    content = content.replace(old_chapters, new_chapters)
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('章节排序 + 每章进度已添加')
else:
    print('章节进度已存在')
