"""删除教材库右上角重复的学习进度条和知识图谱按钮"""
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到右上角的进度条和知识图谱按钮，删掉
old_btns = """        '<div style="display:flex;align-items:center;gap:8px;margin-right:12px">' +
          '<span style="font-size:12px;color:var(--ink-600)">学习进度</span>' +
          '<div style="width:80px;height:6px;background:var(--line);border-radius:3px;overflow:hidden">' +
          '<div id="libProgressFill" style="height:100%;width:0%;background:linear-gradient(90deg,#409eff,#67c23a);transition:width 0.3s"></div>' +
          '</div>' +
          '<span id="libProgressText" style="font-size:12px;color:var(--ink-600)">0/0</span>' +
          '</div>' +
          '<button class="pill-btn" id="libKg" style="background:var(--blue-soft);color:var(--blue);margin-right:8px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px;vertical-align:-2px;margin-right:5px"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>知识图谱</button>' +
        '<button class="pill-btn dark" id="libUp">"""

new_btns = """        '<button class="pill-btn dark" id="libUp">"""

if old_btns in content:
    content = content.replace(old_btns, new_btns)
    
    with open('static/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('右上角重复的进度条和按钮已删除')
else:
    print('没找到要删除的内容，可能已经删过了')
