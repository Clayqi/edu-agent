with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 四个圆形大按钮缩小
content = content.replace('.qbtn{width:76px;height:76px;border-radius:var(--r-pill);border:.5px solid var(--line);background:transparent;color:var(--ink-800);display:flex;align-items:center;justify-content:center;position:relative}',
'.qbtn{width:48px;height:48px;border-radius:var(--r-pill);border:.5px solid var(--line);background:transparent;color:var(--ink-800);display:flex;align-items:center;justify-content:center;position:relative}')

# 里面的图标缩小
content = content.replace('.qbtn svg{width:22px;height:22px}', '.qbtn svg{width:16px;height:16px}')

# 标签位置调整
content = content.replace('.qbtn .qbl{position:absolute;bottom:-17px;left:0;right:0;font-size:11px;color:var(--ink-500);text-align:center;pointer-events:none}',
'.qbtn .qbl{position:absolute;bottom:-15px;left:0;right:0;font-size:10px;color:var(--ink-500);text-align:center;pointer-events:none}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('右侧四个圆形大按钮缩小完成')
