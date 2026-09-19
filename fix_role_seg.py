with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 优化role-seg样式，适配深色模式
old_css = '''.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-pill);padding:2px}
.role-seg button{border:none;background:transparent;height:26px;padding:0 14px;border-radius:var(--r-pill);font-size:12.5px;color:var(--ink-600)}
.role-seg button.active{background:var(--dark);color:#fff}'''

new_css = '''.role-seg{display:flex;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-pill);padding:2px;margin:0 12px 10px}
.role-seg button{flex:1;border:none;background:transparent;height:28px;border-radius:var(--r-pill);font-size:13px;color:var(--ink-600);transition:all .2s}
.role-seg button:hover{background:var(--bg-hover)}
.role-seg button.active{background:var(--blue);color:#fff;box-shadow:0 2px 8px rgba(59,130,246,0.3)}'''

content = content.replace(old_css, new_css)

# 把role-seg从side-bottom移到上面一点，更突出
old_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="btnSettings" title="设置">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M21 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>
        </button>
        <button class="sb-btn" id="btnDark" title="外观">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
        </button>
        <button class="sb-btn" title="帮助">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 4.9.7c0 1.5-2.4 2-2.4 3.3M12 17h.01"/></svg>
        </button>
        <div class="mh-spacer"></div>
        <div class="role-seg" id="roleSeg">
          <button class="active" data-role="teacher">教师</button>
          <button data-role="student">学生</button>
        </div>
      </div>'''

new_sidebottom = '''      <div style="padding:0 12px;margin-top:16px">
        <div class="role-seg" id="roleSeg">
          <button class="active" data-role="teacher">教师</button>
          <button data-role="student">学生</button>
        </div>
      </div>
      <div class="side-bottom">
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="btnSettings" title="设置">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M21 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>
        </button>
        <button class="sb-btn" id="btnDark" title="外观">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
        </button>
        <button class="sb-btn" title="帮助">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 4.9.7c0 1.5-2.4 2-2.4 3.3M12 17h.01"/></svg>
        </button>
      </div>'''

content = content.replace(old_sidebottom, new_sidebottom)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('教师/学生切换组件优化完成')
