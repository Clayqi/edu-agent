with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 强制body和main用变量
old = '''body{font-family:var(--font);font-size:14px;color:var(--ink-900);background:var(--bg);-webkit-font-smoothing:antialiased;overflow:hidden}'''

new = '''body{font-family:var(--font);font-size:14px;color:var(--ink-900);background:var(--bg) !important;-webkit-font-smoothing:antialiased;overflow:hidden;transition:background 0.3s, color 0.3s}'''

content = content.replace(old, new)

# 强制main区域背景
old_main = '''.main{flex:1;display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg)}'''
if old_main in content:
    content = content.replace(old_main, '.main{flex:1;display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg) !important}')

# 强制滚动区域背景
old_scroll = '''.scroll{flex:1;overflow-y:auto;overflow-x:hidden;min-height:0}'''
if old_scroll in content:
    content = content.replace(old_scroll, '.scroll{flex:1;overflow-y:auto;overflow-x:hidden;min-height:0;background:var(--bg) !important}')

# 强制sidebar背景
old_sidebar = '''.sidebar{width:252px;flex:none;background:var(--bg);border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0;transition:width 0.2s}'''
new_sidebar = '''.sidebar{width:252px;flex:none;background:var(--bg-soft) !important;border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0;transition:width 0.2s, background 0.3s}'''
content = content.replace(old_sidebar, new_sidebar)

# 强制skill-card背景
content = content.replace('.skill-card{position:relative;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-sm);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}',
'.skill-card{position:relative;background:var(--bg) !important;border:.5px solid var(--line);border-radius:var(--r-sm);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('强制主题变量生效，界面颜色会跟着变了')
