with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 删掉左侧导航的知识星图按钮
old_nav = '''        <button class="snav" data-view="kg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>
          知识星图
        </button>'''

if old_nav in content:
    content = content.replace(old_nav, '')
    print('左侧导航按钮已删除')

# 2. 在顶部栏加知识星图按钮
old_topbar = '''        <div class="mh-right">
          <button class="wctl" title="工具栏" style="width:30px;height:30px">'''

new_topbar = '''        <div class="mh-right">
          <button class="wctl" title="知识星图" id="btnKgTop" style="width:30px;height:30px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg></button>
          <button class="wctl" title="工具栏" style="width:30px;height:30px">'''

if 'btnKgTop' not in content:
    content = content.replace(old_topbar, new_topbar)
    print('顶部栏按钮已加')

# 3. 给顶部栏按钮加点击事件
old_side_event = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });'''

new_side_event = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });
  document.getElementById('btnKgTop').addEventListener('click', function(){ switchView('kg'); });'''

content = content.replace(old_side_event, new_side_event)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全部完成！')
