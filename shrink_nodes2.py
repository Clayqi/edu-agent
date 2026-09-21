p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("let baseSize = isLearned ? (7 + Math.min(degree * 1.5, 10)) : (3 + Math.min(degree, 4));",
              "let baseSize = isLearned ? (5 + Math.min(degree * 1.2, 7)) : (2 + Math.min(degree * 0.8, 3));")

c = c.replace("nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 3, max: 18 } },",
              "nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 2, max: 12 } },")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('节点再缩小')
