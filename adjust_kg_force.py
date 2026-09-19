with open('D:/edu-agent/static/kg.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 调整力导向参数：线松一点，节点散开
old = '''    forceAtlas2Based: {
      gravitationalConstant: -60,
      centralGravity: 0.005,
      springLength: 120,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 0.8
    }'''

new = '''    forceAtlas2Based: {
      gravitationalConstant: -120,
      centralGravity: 0.002,
      springLength: 160,
      springConstant: 0.04,
      damping: 0.4,
      avoidOverlap: 0.8
    }'''

content = content.replace(old, new)

# 还有另外两处配置也一起改
content = content.replace('''      forceAtlas2Based: {
        gravitationalConstant: -60,
        centralGravity: 0.005,
        springLength: 120,
        springConstant: 0.08,
        damping: 0.4,
        avoidOverlap: 0.8
      }''', '''      forceAtlas2Based: {
        gravitationalConstant: -120,
        centralGravity: 0.002,
        springLength: 160,
        springConstant: 0.04,
        damping: 0.4,
        avoidOverlap: 0.8
      }''')

content = content.replace('''      forceAtlas2Based: {
        gravitationalConstant: -60,
        centralGravity: 0.005,
        springLength: 120,
        springConstant: 0.08,
        damping: 0.4,
        avoidOverlap: 0.8
      }''', '''      forceAtlas2Based: {
        gravitationalConstant: -120,
        centralGravity: 0.002,
        springLength: 160,
        springConstant: 0.04,
        damping: 0.4,
        avoidOverlap: 0.8
      }''')

with open('D:/edu-agent/static/kg.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('知识星图牵引力调松完成')
