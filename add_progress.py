"""在教材库页面添加学习进度条"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到知识图谱按钮的位置，在前面加学习进度条
old_btn = """'<button class="pill-btn" id="libKg" style="background:var(--blue-soft);color:var(--blue);margin-right:8px">"""

new_btn = """'<div style="display:flex;align-items:center;gap:8px;margin-right:12px">' +
          '<span style="font-size:12px;color:var(--ink-600)">学习进度</span>' +
          '<div style="width:80px;height:6px;background:var(--line);border-radius:3px;overflow:hidden">' +
          '<div id="libProgressFill" style="height:100%;width:0%;background:linear-gradient(90deg,#409eff,#67c23a);transition:width 0.3s"></div>' +
          '</div>' +
          '<span id="libProgressText" style="font-size:12px;color:var(--ink-600)">0/0</span>' +
          '</div>' +
          '<button class="pill-btn" id="libKg" style="background:var(--blue-soft);color:var(--blue);margin-right:8px">"""

if 'id="libProgressFill"' not in content:
    content = content.replace(old_btn, new_btn)
    
    # 在libRender最后加更新进度的JS
    old_event = """  // 知识图谱按钮跳转
  setTimeout(function(){
    var kgBtn = document.getElementById('libKg');
    if(kgBtn) kgBtn.onclick = function(){ window.location.href = '/kg.html'; };
  }, 100);"""
    
    new_event = """  // 知识图谱按钮跳转 + 学习进度更新
  setTimeout(function(){
    var kgBtn = document.getElementById('libKg');
    if(kgBtn) kgBtn.onclick = function(){ window.location.href = '/kg.html'; };
    
    // 更新学习进度
    var learned = JSON.parse(localStorage.getItem('kg_learned') || '[]');
    fetch('/api/kg/graph')
      .then(r => r.json())
      .then(function(g) {
        var total = g.nodes.length;
        var pct = total > 0 ? Math.round(learned.length / total * 100) : 0;
        var fill = document.getElementById('libProgressFill');
        var text = document.getElementById('libProgressText');
        if(fill) fill.style.width = pct + '%';
        if(text) text.textContent = learned.length + '/' + total;
      });
  }, 100);"""
    
    content = content.replace(old_event, new_event)
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('学习进度条已添加到教材库')
else:
    print('进度条已存在')
