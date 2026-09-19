with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在head最前面加防闪烁脚本
old_head = '''<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>教育 Agent · UnderstandAnything</title>'''

new_head = '''<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>教育 Agent · UnderstandAnything</title>
<script>
// 防闪烁：提前读取主题
(function(){
  var saved = localStorage.getItem('theme');
  if(saved === 'dark') document.documentElement.classList.add('dark');
})();
</script>'''

content = content.replace(old_head, new_head)

# 2. 统一所有颜色用变量，覆盖硬编码
# 把原来的变量保留，但是确保所有组件都用变量
# 加一段全局强制覆盖
old_end = '''<script>
function toggleThemeSimple(){
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
})();
</script>'''

new_end = '''<script>
function toggleThemeSimple(){
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
})();
</script>

<style>
/* 日夜模式强制覆盖 */
html.dark body, html.dark .main, html.dark .scroll, html.dark .view, html.dark .sidepanel, html.dark .main-head {
  background: #000 !important;
  color: #fff !important;
}
html.dark .sidebar {
  background: #111 !important;
  color: #fff !important;
}
html.dark .skill-card, html.dark .view-sec {
  background: #1a1a1a !important;
  border-color: #333 !important;
  color: #fff !important;
}
html.dark .sb-btn, html.dark .wctl, html.dark .snav, html.dark .newtask, html.dark .proj, html.dark .drop-pill {
  color: #ccc !important;
}
</style>'''

content = content.replace(old_end, new_end)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('完整日夜模式实现完成')
