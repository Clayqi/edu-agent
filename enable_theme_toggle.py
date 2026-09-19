with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把按钮的onclick加回去
content = content.replace('<button class="sb-btn" id="themeToggleBtn" title="切换主题" >',
'<button class="sb-btn" id="themeToggleBtn" title="切换主题" onclick="toggleThemeSimple()">')

# 把初始化和切换函数加回去
content = content.replace('''// 主题切换已禁用，按钮保留''', '''function toggleThemeSimple(){
  var h = document.documentElement;
  var isDark = h.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  var icon = document.getElementById('themeIcon');
  if(isDark){
    icon.innerHTML = '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>';
  } else {
    icon.innerHTML = '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>';
  }
}
// 初始化
(function(){
  var saved = localStorage.getItem('theme') || 'light';
  var isDark = saved === 'dark';
  if(isDark) document.documentElement.classList.add('dark');
  var icon = document.getElementById('themeIcon');
  if(icon && isDark){
    icon.innerHTML = '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>';
  }
})();''')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('日夜模式切换已启用')
