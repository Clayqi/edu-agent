with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复展开按钮：改成内联onclick，最简单直接
old_html = '''<div class="expand-sidebar-btn" id="expandSidebarBtn" title="展开侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></div>'''
new_html = '''<div class="expand-sidebar-btn" onclick="document.querySelector('.sidebar').style.width='252px'; this.style.display='none'" title="展开侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></div>'''

content = content.replace(old_html, new_html)

# 2. 按钮大小缩小，跟sb-btn一样
old_css = '''.expand-sidebar-btn{position:fixed;bottom:20px;left:12px;z-index:100;width:32px;height:32px;border-radius:8px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer}
.expand-sidebar-btn:hover{background:var(--bg-hover)}'''
new_css = '''.expand-sidebar-btn{position:fixed;bottom:20px;left:12px;z-index:100;width:28px;height:28px;border-radius:6px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer;font-size:14px}
.expand-sidebar-btn svg{width:14px;height:14px}
.expand-sidebar-btn:hover{background:var(--bg-hover)}'''

content = content.replace(old_css, new_css)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('展开按钮修复+缩小完成')
