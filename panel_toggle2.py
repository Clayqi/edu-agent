with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 右侧边栏默认隐藏
content = content.replace('.sidepanel{width:300px;flex:none;border-left:.5px solid var(--line);background:var(--bg);display:flex;flex-direction:column;align-items:stretch;justify-content:flex-start;padding:18px 16px;min-height:0}',
'.sidepanel{width:300px;flex:none;border-left:.5px solid var(--line);background:var(--bg);display:none;flex-direction:column;align-items:stretch;justify-content:flex-start;padding:18px 16px;min-height:0}')

# 2. 直接在右上角停止按钮旁边加一个内联onclick按钮
old = '''<button class="wctl-btn" title="停止" onclick="stopGen()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></button>'''

new = '''<button class="wctl-btn" title="运行状态" onclick="var p=document.getElementById('sidePanel'); if(p.style.display==='flex'){p.style.display='none'}else{p.style.display='flex'}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg></button>
      <button class="wctl-btn" title="停止" onclick="stopGen()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="2"/></svg></button>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('右侧边栏默认关闭，内联按钮切换')
