with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 右侧边栏图标缩小
content = content.replace('.sp-ico{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600}', '.sp-ico{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500}')

# 右侧边栏字体对齐
content = content.replace('.sp-label{font-size:12px;color:var(--ink-500);margin-top:6px}', '.sp-label{font-size:12px;color:var(--ink-500);margin-top:5px}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('右侧边栏样式调整完成')
