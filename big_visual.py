with open('D:/edu-agent/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片间距加大
content = content.replace('.skill-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}',
'.skill-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}')

# 2. 卡片阴影明显
content = content.replace('.skill-card:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,0.06);border-color:#999}',
'.skill-card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.12);border-color:#666}')

# 3. 菜单选中态蓝色更明显
content = content.replace('.snav.active{color:var(--ink-900);background:var(--bg-soft);font-weight:500;box-shadow:inset 2px 0 0 var(--blue)}',
'.snav.active{color:var(--blue);background:#e8f0ff;font-weight:500;box-shadow:inset 3px 0 0 var(--blue)}')

# 4. 页面标题加大
content = content.replace('.view-title{font-size:20px;font-weight:600;margin-bottom:4px}',
'.view-title{font-size:22px;font-weight:700;margin-bottom:4px}')

# 5. 分类标题
content = content.replace('.sec-title{font-size:14px;font-weight:600;color:var(--ink-700);margin:20px 0 10px}',
'.sec-title{font-size:15px;font-weight:600;color:var(--ink-800);margin:24px 0 12px;border-left:3px solid var(--blue);padding-left:8px}')

with open('D:/edu-agent/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('大改动完成')
