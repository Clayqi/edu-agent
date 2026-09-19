with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 去掉绿色对勾
content = content.replace("'<span class=\"check-orb\">'+checkSvg+'</span>'+", "''")

# 2. 统一圆角：卡片改成8px
content = content.replace('.skill-card{position:relative;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-md);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}',
'.skill-card{position:relative;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-sm);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}')

# 3. 缩小侧边栏图标
content = content.replace('.snav svg{width:15px;height:15px}', '.snav svg{width:16px;height:16px}')

# 4. 教师/学生按钮字体改小，选中改黑色
old_role = '''.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-pill);padding:2px;margin:0 12px 10px}
.role-seg button{flex:1;border:none;background:transparent;height:28px;border-radius:var(--r-pill);font-size:13px;color:var(--ink-600);transition:all .2s}
.role-seg button:hover{background:var(--bg-hover)}
.role-seg button.active{background:var(--blue);color:#fff;box-shadow:0 2px 8px rgba(59,130,246,0.3)}'''

new_role = '''.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-sm);padding:2px;margin:0 12px 10px}
.role-seg button{flex:1;border:none;background:transparent;height:26px;border-radius:6px;font-size:12px;color:var(--ink-600);transition:all .2s}
.role-seg button:hover{background:var(--bg-hover)}
.role-seg button.active{background:#000;color:#fff}
html.dark .role-seg button.active{background:#fff;color:#000}'''

content = content.replace(old_role, new_role)

# 5. 收窄右侧面板
content = content.replace('.sidepanel{width:360px;flex:none;border-left:.5px solid var(--line);display:flex;flex-direction:column;min-height:0}',
'.sidepanel{width:320px;flex:none;border-left:.5px solid var(--line);display:flex;flex-direction:column;min-height:0}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全部优化完成')
