with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 加CSS：展开按钮样式
old_css = '.sidebar{width:252px;flex:none;background:var(--bg);border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0}'
new_css = '''.sidebar{width:252px;flex:none;background:var(--bg);border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0;transition:width 0.2s}
.expand-btn{position:fixed;bottom:20px;left:12px;z-index:100;width:28px;height:28px;border-radius:6px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer}
.expand-btn:hover{background:var(--bg-hover)}
.expand-btn svg{width:14px;height:14px}'''

content = content.replace(old_css, new_css)

# 2. 在</aside>后面加展开按钮
old_aside = '''    </aside>

    <!-- ===== Main ===== -->'''
new_aside = '''    </aside>
    <div class="expand-btn" id="expandBtn" onclick="document.querySelector('.sidebar').style.width='252px'; this.style.display='none'" title="展开侧边栏">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
    </div>

    <!-- ===== Main ===== -->'''

content = content.replace(old_aside, new_aside)

# 3. 改侧边栏底部的收起按钮
old_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" id="btnSettings" title="设置">'''
new_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="btnSettings" title="设置">'''

content = content.replace(old_sidebottom, new_sidebottom)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('侧边栏收起/展开功能已修复')
