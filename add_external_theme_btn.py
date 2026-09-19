with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 在收起按钮和齿轮按钮之间加主题切换按钮
old = '''        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="btnSettings" title="设置" onclick="document.getElementById('settingsModal').style.display='flex'">'''

new = '''        <button class="sb-btn" onclick="document.querySelector('.sidebar').style.width='0px'; document.getElementById('expandBtn').style.display='flex'" title="收起侧边栏">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <button class="sb-btn" id="themeToggleBtn" title="切换主题" onclick="toggleTheme()">
          <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
        </button>
        <button class="sb-btn" id="btnSettings" title="设置" onclick="document.getElementById('settingsModal').style.display='flex'">'''

content = content.replace(old, new)

# 修改底部的主题切换JS
old_script = '''<script>
function setTheme(mode){
  if(mode==='dark'){
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('theme', mode);
  document.getElementById('settingsModal').style.display='none';
}
// 初始化主题
(function(){
  const saved = localStorage.getItem('theme') || 'light';
  if(saved==='dark') document.documentElement.classList.add('dark');
})();
</script>'''

new_script = '''<script>
function toggleTheme(){
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcon(isDark);
}
function updateThemeIcon(isDark){
  const icon = document.getElementById('themeIcon');
  if(isDark){
    icon.innerHTML = '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>';
  } else {
    icon.innerHTML = '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>';
  }
}
// 初始化主题
(function(){
  const saved = localStorage.getItem('theme') || 'light';
  const isDark = saved === 'dark';
  if(isDark) document.documentElement.classList.add('dark');
  updateThemeIcon(isDark);
})();
</script>'''

content = content.replace(old_script, new_script)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('外置主题切换按钮已加')
