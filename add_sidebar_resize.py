with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 加CSS：侧边栏收起状态样式 + 拖拽条样式
old_css = '.sidebar{width:252px;flex:none;background:var(--bg);border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0}'
new_css = '''.sidebar{width:252px;flex:none;background:var(--bg);border-right:.5px solid var(--line);display:flex;flex-direction:column;min-height:0;transition:width 0.2s}
.sidebar.collapsed{width:48px}
.sidebar.collapsed .side-brand .name,
.sidebar.collapsed .side-brand .ver,
.sidebar.collapsed .snav span,
.sidebar.collapsed .sec-label,
.sidebar.collapsed .proj-leaf .ps-t,
.sidebar.collapsed .proj-leaf .ps-menu,
.sidebar.collapsed .sm-item span{display:none}
.sidebar.collapsed .snav{justify-content:center;padding:9px 0}
.sidebar.collapsed .sec-label{text-align:center;padding:10px 0;font-size:10px}
.sidebar-resizer{width:4px;flex:none;background:transparent;cursor:col-resize;position:relative}
.sidebar-resizer:hover{background:var(--blue)}'''

content = content.replace(old_css, new_css)

# 2. 在侧边栏后面加拖拽条
old_main_start = '''    </aside>

    <!-- ===== Main ===== -->'''
new_main_start = '''    </aside>
    <div class="sidebar-resizer" id="sidebarResizer"></div>

    <!-- ===== Main ===== -->'''

content = content.replace(old_main_start, new_main_start)

# 3. 在侧栏底部加收起按钮
old_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" id="btnSettings" title="设置">'''
new_sidebottom = '''      <div class="side-bottom">
        <button class="sb-btn" id="btnToggleSidebar" title="收起侧边栏"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg></button>
        <button class="sb-btn" id="btnSettings" title="设置">'''

content = content.replace(old_sidebottom, new_sidebottom)

# 4. 加JS：收起按钮 + 拖拽调整宽度
old_js = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });'''

new_js = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });
  
  // 侧边栏收起/展开
  var sidebar = document.querySelector('.sidebar');
  var btnToggle = document.getElementById('btnToggleSidebar');
  // 读取保存的宽度
  var savedWidth = localStorage.getItem('sidebarWidth');
  if(savedWidth) sidebar.style.width = savedWidth + 'px';
  // 读取收起状态
  var savedCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
  if(savedCollapsed) sidebar.classList.add('collapsed');
  
  btnToggle.addEventListener('click', function(){
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    var svg = btnToggle.querySelector('svg path');
    if(sidebar.classList.contains('collapsed')){
      svg.setAttribute('d', 'M9 18l6-6-6-6');
    } else {
      svg.setAttribute('d', 'M15 18l-6-6 6-6');
    }
  });
  
  // 拖拽调整宽度
  var resizer = document.getElementById('sidebarResizer');
  var isResizing = false;
  resizer.addEventListener('mousedown', function(e){
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function(e){
    if(!isResizing) return;
    var newWidth = e.clientX;
    if(newWidth < 180) {
      sidebar.classList.add('collapsed');
    } else {
      sidebar.classList.remove('collapsed');
      sidebar.style.width = newWidth + 'px';
    }
  });
  document.addEventListener('mouseup', function(){
    if(isResizing){
      isResizing = false;
      document.body.style.cursor = '';
      if(!sidebar.classList.contains('collapsed')){
        localStorage.setItem('sidebarWidth', sidebar.offsetWidth);
      }
    }
  });'''

content = content.replace(old_js, new_js)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('侧边栏收起+拖拽调整功能已加')
