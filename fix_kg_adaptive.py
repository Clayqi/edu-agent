with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 调整kg视图样式，确保撑满
old_kg = '''        <div class="view" id="view-kg" style="padding:0;overflow:hidden;height:100%">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none;display:block"></iframe>
        </div>'''

new_kg = '''        <div class="view" id="view-kg" style="padding:0;overflow:hidden;width:100%;height:100%">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none;display:block"></iframe>
        </div>'''

content = content.replace(old_kg, new_kg)

# 切换到kg视图时自动收起右侧面板
old_switch = '''    if(v==='kg'){ document.getElementById('sidePanel').style.display = 'none'; }'''
if old_switch not in content:
    old_switch2 = '''    if(v==='library'){ libRender(); }'''
    new_switch2 = '''    if(v==='library'){ libRender(); }
    if(v==='kg'){ document.getElementById('sidePanel').style.display = 'none'; }'''
    content = content.replace(old_switch2, new_switch2)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('kg视图自适应调整完成')
