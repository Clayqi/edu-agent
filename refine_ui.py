with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片圆角改10px
content = content.replace('.skill-card{position:relative;background:var(--bg) !important;border:.5px solid var(--line);border-radius:var(--r-sm);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}',
'.skill-card{position:relative;background:var(--bg) !important;border:.5px solid var(--line);border-radius:10px;padding:16px;cursor:pointer;text-align:left;transition:all .24s ease}')

# 2. 卡片标题15px
content = content.replace('.skill-card .sc-title{font-size:14px;font-weight:600;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}',
'.skill-card .sc-title{font-size:15px;font-weight:500;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}')

# 3. 描述13px，行高1.55
content = content.replace('.skill-card .sc-desc{font-size:12px;color:var(--ink-600);line-height:1.6;text-align:left;opacity:0.8}',
'.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.55;text-align:left;opacity:0.75}')

# 4. hover阴影
content = content.replace('.skill-card:hover{border-color:var(--line-strong);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.08)}',
'.skill-card:hover{transform:translateY(-2px);box-shadow:0 3px 10px rgba(0,0,0,0.07)}')

# 5. 分类标签胶囊样式
content = content.replace('.drop-pill{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 14px;border:.5px solid var(--line);border-radius:var(--r-pill);background:var(--bg);font-size:13px;color:var(--ink-700);transition:all 0.2s}',
'.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('精致化UI完成')
