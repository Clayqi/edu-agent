with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把教材库里的按钮onclick去掉，改成用id，然后JS绑定
old1 = """'<button class="pill-btn" style="background:#1890ff;color:#fff" onclick="switchView(\\'kg\\')">'"""
new1 = """'<button class="pill-btn" id="btnOpenKgTop" style="background:#1890ff;color:#fff">'"""

content = content.replace(old1, new1)

old2 = """'<button class="pill-btn" style="background:#e6f7ff;color:#1890ff;height:28px" onclick="switchView(\\'kg\\')">📊 本教材知识图谱</button>'"""
new2 = """'<button class="pill-btn" id="btnOpenKgBook" style="background:#e6f7ff;color:#1890ff;height:28px">📊 本教材知识图谱</button>'"""

content = content.replace(old2, new2)

# 在JS里加事件绑定
old_settimeout = """  // 学习进度更新
  setTimeout(function(){"""
new_settimeout = """  // 知识图谱按钮事件绑定
  setTimeout(function(){
    var btn1 = document.getElementById('btnOpenKgTop');
    if(btn1) btn1.onclick = function(){ switchView('kg'); };
    var btn2 = document.getElementById('btnOpenKgBook');
    if(btn2) btn2.onclick = function(){ switchView('kg'); };
  }, 200);
  
  // 学习进度更新
  setTimeout(function(){"""

content = content.replace(old_settimeout, new_settimeout)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('按钮事件绑定已修复')
