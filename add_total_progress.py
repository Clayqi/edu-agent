"""在教材库顶部加总学习进度 + 总图谱入口"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到教材库头部的位置，在最前面加总进度卡片
old_lib_header = """      var h = '<div style="display:flex;align-items:center;gap:10px;margin:2px 2px 14px">' +
        '<div style="font-size:17px;font-weight:600">教材库</div>' +
        '<span style="font-size:11.5px;color:var(--ink-400)">教材与资料 · 点击行展开</span>' +
        '<div style="flex:1"></div>'"""

new_lib_header = """      // 总学习进度卡片
      var learnedTotal = JSON.parse(localStorage.getItem('kg_learned') || '[]').length;
      var totalNodes = 28; // 先写死，后面改成从API获取
      var totalPct = totalNodes > 0 ? Math.round(learnedTotal / totalNodes * 100) : 0;
      
      var h = '<div style="background:linear-gradient(135deg,#f0f5ff,#e6f7ff);border-radius:12px;padding:16px 20px;margin-bottom:16px;border:.5px solid #91d5ff">' +
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">' +
        '<div style="font-size:15px;font-weight:600;color:#1890ff">📚 总学习进度</div>' +
        '<div style="font-size:13px;color:#666">已点亮 ' + learnedTotal + ' / ' + totalNodes + ' 个知识点 (' + totalPct + '%)</div>' +
        '</div>' +
        '<div style="width:100%;height:10px;background:#e6f7ff;border-radius:5px;overflow:hidden;margin-bottom:12px">' +
        '<div style="height:100%;width:' + totalPct + '%;background:linear-gradient(90deg,#1890ff,#52c41a);border-radius:5px;transition:width 0.3s"></div>' +
        '</div>' +
        '<div style="display:flex;gap:10px">' +
        '<button class="pill-btn" style="background:#1890ff;color:#fff" onclick="window.location.href=\\'/kg.html\\'">' +
        '<svg viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'2\\' style=\\'width:13px;height:13px;vertical-align:-2px;margin-right:5px\\'><circle cx=\\'6\\' cy=\\'6\\' r=\\'3\\'/><circle cx=\\'18\\' cy=\\'6\\' r=\\'3\\'/><circle cx=\\'12\\' cy=\\'18\\' r=\\'3\\'/><path d=\\'M8 7l3 9M16 7l-3 9M9 6h6\\'/></svg>打开总知识图谱星图</button>' +
        '</div></div>';
      
      h += '<div style="display:flex;align-items:center;gap:10px;margin:2px 2px 14px">' +
        '<div style="font-size:17px;font-weight:600">教材列表</div>' +
        '<span style="font-size:11.5px;color:var(--ink-400)">点击展开教材详情</span>' +
        '<div style="flex:1"></div>'"""

if '总学习进度' not in content:
    content = content.replace(old_lib_header, new_lib_header)
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('教材库顶部总进度卡片已添加')
else:
    print('总进度卡片已存在')
