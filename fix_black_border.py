with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片hover边框改成黑色
content = content.replace('.skill-card:hover{border-color:var(--blue);transform:translateY(-2px);box-shadow:var(--shadow-md)}',
'.skill-card:hover{border-color:#000;transform:translateY(-2px);box-shadow:var(--shadow-md)}')

# 2. 夜间模式hover边框改成浅灰
content = content.replace('body{transition:background 0.3s, color 0.3s}',
'''body{transition:background 0.3s, color 0.3s}
html.dark .skill-card:hover{border-color:rgba(255,255,255,0.25)}''')

# 3. 教师学生按钮文字水平不换行
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1}',
'.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('黑色边框+教师学生水平文字完成')
