with open('static/kg.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''      force: { 
        repulsion: 1500, 
        edgeLength: [200, 400],
        gravity: 0.01,
        friction: 0.1
      },'''

new = '''      force: { 
        repulsion: 600, 
        edgeLength: [120, 220],
        gravity: 0.08
      },'''

content = content.replace(old, new)

with open('static/kg.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('星图布局调整完成')
