with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 加悬浮展开按钮的CSS
old_css = '.sidebar-resizer{width:4px;flex:none;background:transparent;cursor:col-resize;position:relative}'
new_css = '''.sidebar-resizer{width:4px;flex:none;background:transparent;cursor:col-resize;position:relative}
.expand-sidebar-btn{position:fixed;top:70px;left:12px;z-index:100;width:32px;height:32px;border-radius:8px;background:var(--bg);border:.5px solid var(--line);box-shadow:0 2px 8px rgba(0,0,0,0.1);display:none;align-items:center;justify-content:center;cursor:pointer}
.expand-sidebar-btn:hover{background:var(--bg-hover)}'''

content = content.replace(old_css, new_css)

# 2. 加悬浮按钮的HTML
old_main = '''    <div class="sidebar-resizer" id="sidebarResizer"></div>

    <!-- ===== Main ===== -->'''
new_main = '''    <div class="sidebar-resizer" id="sidebarResizer"></div>
    <div class="expand-sidebar-btn" id="expandSidebarBtn" title="展开侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg></div>

    <!-- ===== Main ===== -->'''

content = content.replace(old_main, new_main)

# 3. 改按钮逻辑：收起时显示悬浮按钮，展开时隐藏
old_btn = '''onclick="var s=document.querySelector('.sidebar'); if(s.style.width==='0px'){s.style.width='252px'}else{s.style.width='0px'}"'''
new_btn = '''onclick="var s=document.querySelector('.sidebar'); var b=document.getElementById('expandSidebarBtn'); if(s.style.width==='0px'){s.style.width='252px'; b.style.display='none'}else{s.style.width='0px'; b.style.display='flex'}"'''

content = content.replace(old_btn, new_btn)

# 4. 悬浮按钮点击展开
old_resizer = '''  // 拖拽调整宽度
  var resizer = document.getElementById('sidebarResizer');'''
new_resizer = '''  // 悬浮按钮展开侧边栏
  document.getElementById('expandSidebarBtn').onclick = function(){
    document.querySelector('.sidebar').style.width = '252px';
    this.style.display = 'none';
  };

  // 拖拽调整宽度
  var resizer = document.getElementById('sidebarResizer');'''

content = content.replace(old_resizer, new_resizer)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('悬浮展开按钮已加')
