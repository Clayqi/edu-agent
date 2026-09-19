with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 删掉月亮按钮
old = '''        <button class="sb-btn" id="btnSettings" title="设置"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg></button>
        <button class="sb-btn" id="btnDark" title="外观"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg></button>
        <button class="sb-btn" title="帮助">'''

new = '''        <button class="sb-btn" id="btnSettings" title="设置"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg></button>
        <button class="sb-btn" title="帮助">'''

content = content.replace(old, new)

# 给设置按钮加点击切换主题
old_js = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });'''

new_js = '''  document.getElementById('btnSidePanel').addEventListener('click', function(){
    document.getElementById('sidePanel').style.display = document.getElementById('sidePanel').style.display==='none'?'':'none';
  });
  document.getElementById('btnSettings').addEventListener('click', function(){
    document.documentElement.classList.toggle('dark');
  });'''

content = content.replace(old_js, new_js)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('月亮按钮已删除')
