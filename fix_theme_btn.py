with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 调整底部按钮顺序：主题按钮放收起按钮右边
old_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" id="themeToggleSide" title="切换主题">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>'''

new_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="themeToggleSide" title="切换主题">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>'''

content = content.replace(old_sidebottom, new_sidebottom)

# 2. 修改JS：切换主题时图标也变
old_js = '''  document.getElementById('themeToggleSide').addEventListener('click', function(){
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });'''

new_js = '''  function updateThemeIcon(){
    const isDark = document.documentElement.classList.contains('dark');
    const icon = document.getElementById('themeIcon');
    if(isDark){
      icon.innerHTML = '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>';
    } else {
      icon.innerHTML = '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>';
    }
  }
  updateThemeIcon();
  document.getElementById('themeToggleSide').addEventListener('click', function(){
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
  });'''

content = content.replace(old_js, new_js)

# 3. 删掉右侧边栏的月亮按钮
content = content.replace('''        <button class="sb-btn" id="btnDark" title="外观">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
        </button>
''', '')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('主题按钮+右侧按钮调整完成')
