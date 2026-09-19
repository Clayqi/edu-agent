with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 改成一行四个并排
content = content.replace('.quad{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:18px}',
'.quad{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:18px;justify-items:center}')

# 按钮再调小一点，适合并排
content = content.replace('.qbtn{width:48px;height:48px;border-radius:var(--r-pill);border:.5px solid var(--line);background:transparent;color:var(--ink-800);display:flex;align-items:center;justify-content:center;position:relative}',
'.qbtn{width:40px;height:40px;border-radius:var(--r-pill);border:.5px solid var(--line);background:transparent;color:var(--ink-800);display:flex;align-items:center;justify-content:center;position:relative}')

# 标签位置调整
content = content.replace('.qbtn .qbl{position:absolute;bottom:-15px;left:0;right:0;font-size:10px;color:var(--ink-500);text-align:center;pointer-events:none}',
'.qbtn .qbl{position:absolute;bottom:-14px;left:0;right:0;font-size:9px;color:var(--ink-500);text-align:center;pointer-events:none;white-space:nowrap}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('四个图标并排完成')
