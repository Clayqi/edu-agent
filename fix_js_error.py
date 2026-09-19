with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """      if(ub) ub.onclick = function(e){ e.stopPropagation(); curCorpus = 'textbook'; syncToolbars(); libRender(); showToast('知识范围：教材'); };
      var up = 
  // 知识图谱按钮跳转 + 学习进度更新
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

new = """      if(ub) ub.onclick = function(e){ e.stopPropagation(); curCorpus = 'textbook'; syncToolbars(); libRender(); showToast('知识范围：教材'); };
      
  // 学习进度更新
  setTimeout(function(){
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

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('语法错误已修复')
