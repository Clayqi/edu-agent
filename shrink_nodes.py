p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 节点整体缩小
c = c.replace("let baseSize = isLearned ? (10 + Math.min(degree * 2, 14)) : (5 + Math.min(degree, 6));",
              "let baseSize = isLearned ? (7 + Math.min(degree * 1.5, 10)) : (3 + Math.min(degree, 4));")

# scaling 范围缩小
c = c.replace("nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 5, max: 26 } },",
              "nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 3, max: 18 } },")

# 阴影缩小
c = c.replace("shadow: (!lowSpec && isLearned) ? { enabled: true, color: color, size: degree > 5 ? 14 : 8, x: 0, y: 0 } : { enabled: false },",
              "shadow: (!lowSpec && isLearned) ? { enabled: true, color: color, size: degree > 5 ? 10 : 6, x: 0, y: 0 } : { enabled: false },")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('节点缩小完成')
