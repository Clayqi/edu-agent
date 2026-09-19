with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 改CSS：完全收起时宽度0
old_css = '''.sidebar.collapsed{width:48px}'''
new_css = '''.sidebar.collapsed{width:0;overflow:hidden;border:none}'''

content = content.replace(old_css, new_css)

# 2. 改按钮：直接控制style.width，不用class
old_btn = '''<button class="sb-btn" onclick="document.querySelector('.sidebar').classList.toggle('collapsed')" title="收起侧边栏">'''
new_btn = '''<button class="sb-btn" onclick="var s=document.querySelector('.sidebar'); if(s.style.width==='0px'){s.style.width='252px'}else{s.style.width='0px'}" title="收起侧边栏">'''

content = content.replace(old_btn, new_btn)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('改成完全收起0宽度了')
