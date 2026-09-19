with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复skill卡片文字，强制用ink-900，不要用变量导致看不见
content = content.replace('.skill-card .sc-title{font-size:13px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900)}',
'.skill-card .sc-title{font-size:13px;font-weight:600;text-align:left;line-height:1.3;color:var(--ink-900)}')
content = content.replace('.skill-card .sc-desc{font-size:12px;color:var(--ink-600);margin-top:8px;line-height:1.5;text-align:left}',
'.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.5;text-align:left}')

# 2. 调小右侧边栏图标
content = content.replace('.sp-ico{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500}',
'.sp-ico{width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:500}')

# 3. 教师/学生按钮容器加高，包住文字
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:24px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s}',
'.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('卡片文字+右侧图标+按钮容器调整完成')
