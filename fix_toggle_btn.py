with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把按钮改成内联onclick，最简单直接
old_btn = '''<button class="sb-btn" id="btnToggleSidebar" title="收起侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg></button>'''
new_btn = '''<button class="sb-btn" onclick="document.querySelector('.sidebar').classList.toggle('collapsed')" title="收起侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg></button>'''

content = content.replace(old_btn, new_btn)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('按钮改成内联onclick了')
