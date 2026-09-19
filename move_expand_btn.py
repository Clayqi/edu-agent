with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 改按钮位置：从左上角改到左下角
old_css = '''.expand-sidebar-btn{position:fixed;top:70px;left:12px;z-index:100;width:32px;height:32px;border-radius:8px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer}'''
new_css = '''.expand-sidebar-btn{position:fixed;bottom:20px;left:12px;z-index:100;width:32px;height:32px;border-radius:8px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer}'''

content = content.replace(old_css, new_css)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('按钮移到左下角了')
