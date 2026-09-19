with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片hover效果优化
content = content.replace('.skill-card:hover{border-color:#000;transform:translateY(-2px);box-shadow:var(--shadow-md)}',
'.skill-card:hover{border-color:var(--line-strong);transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.08)}')

# 2. 卡片标题和描述层级
content = content.replace('.skill-card .sc-title{font-size:13px;font-weight:600;text-align:left;line-height:1.3;color:var(--ink-900)}',
'.skill-card .sc-title{font-size:14px;font-weight:600;text-align:left;line-height:1.3;color:var(--ink-900);margin-bottom:6px}')
content = content.replace('.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.6;text-align:left}',
'.skill-card .sc-desc{font-size:12px;color:var(--ink-600);line-height:1.6;text-align:left;opacity:0.8}')

# 3. 分类标签改成胶囊样式
content = content.replace('.drop-pill{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;border:.5px solid var(--line);border-radius:var(--r-pill);background:var(--bg);font-size:13px;color:var(--ink-700)}',
'.drop-pill{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 14px;border:.5px solid var(--line);border-radius:var(--r-pill);background:var(--bg);font-size:13px;color:var(--ink-700);transition:all 0.2s}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('卡片+标签美化完成')
