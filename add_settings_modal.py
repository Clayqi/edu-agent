with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 把齿轮按钮点击改成打开设置弹窗
old_btn = '''        <button class="sb-btn" id="btnSettings" title="设置"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg></button>'''

new_btn = '''        <button class="sb-btn" id="btnSettings" title="设置" onclick="document.getElementById('settingsModal').style.display='flex'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg></button>'''

content = content.replace(old_btn, new_btn)

# 2. 加设置弹窗HTML
old_end = '''</body>
</html>'''
new_end = '''<!-- 设置弹窗 -->
<div id="settingsModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1000;align-items:center;justify-content:center" onclick="if(event.target===this)this.style.display='none'">
  <div style="background:var(--bg);border-radius:12px;padding:24px;width:320px;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <h3 style="font-size:16px;font-weight:600">设置</h3>
      <button onclick="document.getElementById('settingsModal').style.display='none'" style="border:none;background:none;font-size:20px;cursor:pointer;color:var(--ink-500)">×</button>
    </div>
    <div style="margin-bottom:16px">
      <div style="font-size:13px;color:var(--ink-500);margin-bottom:10px">外观主题</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <button onclick="setTheme('light')" id="themeLight" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg-soft);cursor:pointer;text-align:left">
          <span>☀️</span><span style="font-size:13px">日间模式</span>
        </button>
        <button onclick="setTheme('dark')" id="themeDark" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg-soft);cursor:pointer;text-align:left">
          <span>🌙</span><span style="font-size:13px">夜间模式</span>
        </button>
      </div>
    </div>
  </div>
</div>

<script>
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
</script>

</body>
</html>'''

content = content.replace(old_end, new_end)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('设置弹窗+主题切换完成')
