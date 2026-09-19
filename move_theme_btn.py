with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 删除顶部的主题切换按钮
old_topbar = '''        <div class="mh-right">
          <button class="wctl" id="themeToggle" title="切换主题" style="width:30px;height:30px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg></button>
          <button class="wctl" title="工具栏" style="width:30px;height:30px">'''

new_topbar = '''        <div class="mh-right">
          <button class="wctl" title="工具栏" style="width:30px;height:30px">'''

content = content.replace(old_topbar, new_topbar)

# 2. 在侧边栏底部加主题切换按钮
old_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>'''

new_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" id="themeToggleSide" title="切换主题">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>'''

content = content.replace(old_sidebottom, new_sidebottom)

# 3. 修改JS：绑定新的主题按钮
old_js = '''  document.getElementById('themeToggle').addEventListener('click', function(){
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });'''

new_js = '''  document.getElementById('themeToggleSide').addEventListener('click', function(){
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });'''

content = content.replace(old_js, new_js)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('主题按钮已移到侧边栏底部')
