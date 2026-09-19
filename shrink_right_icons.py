with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 右侧边栏图标缩小
content = content.replace('.sp-ico{width:28px;height:28px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:500}',
'.sp-ico{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500}')

# 空状态文字居中加留白
content = content.replace('.sp-label{font-size:12px;color:var(--ink-500);margin-top:5px}',
'.sp-label{font-size:12px;color:var(--ink-500);margin-top:5px;text-align:center}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('右侧图标缩小完成')
