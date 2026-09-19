with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 改收起按钮：收起时显示展开按钮
old_collapse_btn = '''<button class="sb-btn" onclick="var s=document.querySelector('.sidebar'); var b=document.getElementById('expandSidebarBtn'); if(s.style.width==='0px'){s.style.width='252px'; b.style.display='none'}else{s.style.width='0px'; b.style.display='flex'}" title="收起侧边栏">'''
new_collapse_btn = '''<button class="sb-btn" onclick="toggleSidebar()" title="收起侧边栏">'''

content = content.replace(old_collapse_btn, new_collapse_btn)

# 加toggleSidebar函数
old_js_start = '''  // 侧边栏收起/展开
  var sidebar = document.querySelector('.sidebar');'''
new_js_start = '''  function toggleSidebar(){
    var s = document.querySelector('.sidebar');
    var b = document.getElementById('expandSidebarBtn');
    if(s.style.width === '0px' || s.style.width === ''){
      s.style.width = '0px';
      b.style.display = 'flex';
    } else {
      s.style.width = '';
      b.style.display = 'none';
    }
  }
  
  // 悬浮按钮展开
  document.getElementById('expandSidebarBtn').onclick = function(){
    var s = document.querySelector('.sidebar');
    s.style.width = '';
    this.style.display = 'none';
  };

  // 侧边栏收起/展开
  var sidebar = document.querySelector('.sidebar');'''

content = content.replace(old_js_start, new_js_start)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('侧边栏展开/收起逻辑修复完成')
