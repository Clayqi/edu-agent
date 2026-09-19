"""在每本教材详情里加独立进度 + 单独图谱按钮"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到教材详情头部的位置，加这本教材的进度
old_detail_header = """          '<div style="padding:12px 18px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">' +
            '<button class="pill-btn' + (curCorpus === 'textbook' ? ' dark' : '') + '" id="libUseTextbook" style="height:28px">' + (curCorpus === 'textbook' ? '✓ 当前知识源' : '设为知识源') + '</button>' +
            '<span style="font-size:11.5px;color:var(--ink-400)">章节（点击展开小节）</span></div>'"""

new_detail_header = """          '<div style="padding:12px 18px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:.5px solid var(--line);padding-bottom:10px;margin-bottom:8px">' +
            '<button class="pill-btn' + (curCorpus === 'textbook' ? ' dark' : '') + '" id="libUseTextbook" style="height:28px">' + (curCorpus === 'textbook' ? '✓ 当前知识源' : '设为知识源') + '</button>' +
            '<button class="pill-btn" style="background:#e6f7ff;color:#1890ff;height:28px" onclick="window.location.href=\\'/kg.html?book=必修一\\'">📊 本教材知识图谱</button>' +
            '<div style="flex:1"></div>' +
            '<div style="display:flex;align-items:center;gap:6px">' +
            '<span style="font-size:11px;color:var(--ink-400)">本教材进度</span>' +
            '<div style="width:60px;height:5px;background:var(--line);border-radius:3px;overflow:hidden">' +
            '<div style="height:100%;width:0%;background:#1890ff" class="book-progress-fill"></div>' +
            '</div>' +
            '<span style="font-size:11px;color:var(--ink-400)" class="book-progress-text">0/0</span>' +
            '</div></div>' +
          '<div style="padding:0 18px 8px;font-size:11.5px;color:var(--ink-400)">章节（按顺序排序 · 点击展开小节）</div>'"""

if '本教材知识图谱' not in content:
    content = content.replace(old_detail_header, new_detail_header)
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('每本教材独立进度 + 图谱按钮已添加')
else:
    print('教材详情进度已存在')
