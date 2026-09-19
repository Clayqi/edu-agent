with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片hover效果优化
content = content.replace('.skill-card:hover{border-color:var(--line-strong);box-shadow:var(--shadow-sm)}',
'.skill-card:hover{border-color:var(--blue);transform:translateY(-2px);box-shadow:var(--shadow-md)}')

# 2. 卡片描述行高
content = content.replace('.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.5;text-align:left}',
'.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.6;text-align:left}')

# 3. 页面说明文字缩小
content = content.replace('.mk-sub{font-size:13.5px;color:var(--ink-500);margin-top:6px}',
'.mk-sub{font-size:12px;color:var(--ink-500);margin-top:4px}')

# 4. 教师学生按钮居中
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center}',
'.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('细节优化完成')
