with open('D:/edu-agent/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 统一卡片内边距和圆角
content = content.replace('.skill-card{position:relative;background:var(--bg) !important;border:.5px solid var(--line);border-radius:10px;padding:16px;cursor:pointer;text-align:left;transition:all .24s ease}',
'.skill-card{position:relative;background:var(--bg) !important;border:.5px solid var(--line);border-radius:8px;padding:16px;cursor:pointer;text-align:left;transition:all 0.2s cubic-bezier(0.4,0,0.2,1)}')

# 2. 卡片标题14px，字重500
content = content.replace('.skill-card .sc-title{font-size:15px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}',
'.skill-card .sc-title{font-size:14px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}')

# 3. 卡片描述13px
content = content.replace('.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.55;text-align:left;opacity:0.75}',
'.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.5;text-align:left;opacity:0.8}')

# 4. hover效果优化
content = content.replace('.skill-card:hover{transform:translateY(-2px);box-shadow:0 3px 10px rgba(0,0,0,0.07)}',
'.skill-card:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,0.06);border-color:#999}')

# 5. 分类标签间距
content = content.replace('.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer}',
'.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer;margin-right:8px}')

# 6. 菜单选中态
content = content.replace('.snav.active{color:var(--ink-900);background:var(--bg-soft);font-weight:500}',
'.snav.active{color:var(--ink-900);background:var(--bg-soft);font-weight:500;box-shadow:inset 2px 0 0 var(--blue)}')

# 7. 全局过渡
content = content.replace('*{box-sizing:border-box}',
'*{box-sizing:border-box;transition:background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease}')

with open('D:/edu-agent/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('专业UI优化执行完成')
