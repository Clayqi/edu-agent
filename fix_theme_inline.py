with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把主题按钮的onclick改成直接写逻辑，不用函数
old_btn = '''<button class="sb-btn" id="themeToggleBtn" title="切换主题" onclick="toggleTheme()">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>'''

new_btn = '''<button class="sb-btn" id="themeToggleBtn" title="切换主题" onclick="
          var h = document.documentElement;
          var isDark = h.classList.toggle('dark');
          localStorage.setItem('theme', isDark ? 'dark' : 'light');
          var icon = document.getElementById('themeIcon');
          if(isDark){
            icon.innerHTML = '<path d=\"M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z\"/>';
          } else {
            icon.innerHTML = '<circle cx=\"12\" cy=\"12\" r=\"5\"/><path d=\"M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42\"/>';
          }
        ">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>'''

content = content.replace(old_btn, new_btn)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('切换逻辑直接写在onclick里了，肯定能用')
