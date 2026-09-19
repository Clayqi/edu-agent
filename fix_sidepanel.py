with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    if(v==='chat'){ updateGreeting(); }
    if(v==='library'){ libRender(); }
  }"""

new = """    if(v==='chat'){ updateGreeting(); }
    if(v==='library'){ libRender(); }
    if(v==='kg'){ document.getElementById('sidePanel').style.display = 'none'; }
  }"""

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('切换kg视图自动收起侧边栏已加')
