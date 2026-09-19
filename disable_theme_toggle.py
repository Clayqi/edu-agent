with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把按钮的onclick去掉，点了没反应，按钮留着
content = content.replace('onclick="toggleThemeSimple()"', '')

# 把初始化主题的JS删掉，永远是日间模式
content = content.replace('''// 初始化
(function(){
  var saved = localStorage.getItem('theme') || 'light';
  var isDark = saved === 'dark';
  if(isDark) document.documentElement.classList.add('dark');
  else document.documentElement.classList.remove('dark');
  var icon = document.getElementById('themeIcon');
  if(icon){
    if(isDark){
      icon.innerHTML = '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>';
    }
  }
})();''', '''// 主题切换已禁用，按钮保留''')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('日夜模式切换已禁用，按钮保留')
