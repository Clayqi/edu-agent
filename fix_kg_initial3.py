p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. isBurst 条件：只小图（<=40节点）做星核弹开动画
old = "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 220;"
new = "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 40;"
c = c.replace(old, new); print('1 ok' if old not in c else '1 MISS')

# 2. stabilization 迭代 100->50
c = c.replace("stabilization: { iterations: 100, fit: true },",
              "stabilization: { iterations: 50, fit: true },")

# 3. 弹开兜底时间
c = c.replace("burstTimer = setTimeout(finishBurst, nodes.length > 120 ? 4200 : 3200);",
              "burstTimer = setTimeout(finishBurst, nodes.length > 60 ? 1500 : 2000);")

# 4. 首次加载 130 -> 40（只有第一处）
c = c.replace("renderGraph(graphData.nodes, graphData.links, null, 130);",
              "renderGraph(graphData.nodes, graphData.links, null, 40);", 1)

# 5. closeInfo 130 -> 30
c = c.replace("display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 40);",
              "display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 30);")

# 6. 搜索清空 130 -> 30
c = c.replace("renderGraph(graphData.nodes, graphData.links, null, 40);\n    return;",
              "renderGraph(graphData.nodes, graphData.links, null, 30);\n    return;")

# 7. 节点初始位置：大图散布
old_pos = """    if (burstCenter) {
      const ang = (i % 6) * (Math.PI / 3) + Math.random() * 0.4;
      const rad = 1 + Math.random() * 5;
      px = burstCenter.x + Math.cos(ang) * rad;
      py = burstCenter.y + Math.sin(ang) * rad;
    }"""
new_pos = """    if (burstCenter) {
      if (nodes.length <= 40) {
        const ang = (i % 6) * (Math.PI / 3) + Math.random() * 0.4;
        const rad = 1 + Math.random() * 5;
        px = burstCenter.x + Math.cos(ang) * rad;
        py = burstCenter.y + Math.sin(ang) * rad;
      } else {
        px = burstCenter.x + (Math.random() - 0.5) * 800;
        py = burstCenter.y + (Math.random() - 0.5) * 600;
      }
    }"""
c = c.replace(old_pos, new_pos)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

# 验证剩余 130 数量
print('剩余130:', c.count('null, 130'))
print('完成')
