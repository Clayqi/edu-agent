with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 把主题按钮改成设置齿轮图标，删掉动态切换
old_btn = '''        <button class="sb-btn" id="themeToggleSide" title="设置">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>'''

new_btn = '''        <button class="sb-btn" id="btnSettings" title="设置">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>
        </button>'''

content = content.replace(old_btn, new_btn)

# 2. 删掉动态切换主题图标的JS
old_js = '''  function updateThemeIcon(){
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

new_js = '''  // 主题切换暂时用右上角按钮，后续移到设置弹窗
  document.getElementById('btnSettings').addEventListener('click', function(){
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });'''

content = content.replace(old_js, new_js)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('左下角按钮改成设置齿轮，月亮图标删掉')
