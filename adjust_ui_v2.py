with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 缩小主界面标题
content = content.replace('.mk-title{font-size:26px;font-weight:600;letter-spacing:-.02em}', '.mk-title{font-size:20px;font-weight:600;letter-spacing:-.02em}')
content = content.replace('.view-h1{font-size:22px;font-weight:600;letter-spacing:-.02em}', '.view-h1{font-size:18px;font-weight:600;letter-spacing:-.02em}')

# 2. 修复卡片文字对比度
content = content.replace('.skill-card .sc-title{font-size:13.5px;font-weight:600;text-align:left;line-height:1.3}', '.skill-card .sc-title{font-size:13px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900)}')
content = content.replace('.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.5;text-align:left}', '.skill-card .sc-desc{font-size:12px;color:var(--ink-600);margin-top:8px;line-height:1.5;text-align:left}')

# 3. 教师/学生按钮字体再变小
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:12px;color:var(--ink-600);transition:all .2s}', '.role-seg button{flex:1;border:none;background:transparent;height:24px;border-radius:6px;font-size:11px;color:var(--ink-600);transition:all .2s}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('前三项调整完成')
