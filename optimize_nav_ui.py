with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 优化sec-label样式
old_css = '.sec-label{padding:14px 14px 6px;font-size:11.5px;font-weight:600;color:var(--ink-500);letter-spacing:.01em}'
new_css = '.sec-label{padding:14px 14px 6px;font-size:11px;font-weight:500;color:var(--ink-400);letter-spacing:.02em;text-transform:uppercase}'

content = content.replace(old_css, new_css)

# 优化snav选中态
old_snav = '.snav.active{background:var(--bg-active);color:var(--ink-900);font-weight:500}'
new_snav = '.snav.active{background:var(--blue-soft);color:var(--blue);font-weight:500;border-radius:8px}'

content = content.replace(old_snav, new_snav)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('左侧导航样式优化完成')
