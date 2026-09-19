with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 教师/学生按钮9px
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:7px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}',
'.role-seg button{flex:1;border:none;background:transparent;height:22px;border-radius:6px;font-size:9px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 4px}')

# 2. 卡片标题15px，描述13px
content = content.replace('.skill-card .sc-title{font-size:15px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}',
'.skill-card .sc-title{font-size:15px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}')
content = content.replace('.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.55;text-align:left;opacity:0.75}',
'.skill-card .sc-desc{font-size:12px;color:var(--ink-500);line-height:1.55;text-align:left;opacity:0.8}')

# 3. 分类标签选中态
content = content.replace('.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer}',
'.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer;margin-right:8px}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('UI优化执行完成')
