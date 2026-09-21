p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. isBurst 只对小图(<40节点)启用星核弹开
c = c.replace("const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 220;",
              "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 40;")

# 2. stabilization 迭代 100->50
c = c.replace("stabilization: { iterations: 100, fit: true },",
              "stabilization: { iterations: 50, fit: true },")

# 3. 弹开兜底时间
c = c.replace("burstTimer = setTimeout(finishBurst, nodes.length > 120 ? 4200 : 3200);",
              "burstTimer = setTimeout(finishBurst, nodes.length > 60 ? 1500 : 2000);")

# 4. 所有三处 renderGraph(..., 130) 改成小迭代
#    首次加载40, closeInfo和搜索清空30
# 先把 closeInfo 那处改了（用上下文定位）
c = c.replace("document.getElementById('infoPanel').style.display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 130);",
              "document.getElementById('infoPanel').style.display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 30);")

c = c.replace("if (!q) {\n    renderGraph(graphData.nodes, graphData.links, null, 130);",
              "if (!q) {\n    renderGraph(graphData.nodes, graphData.links, null, 30);")

# 剩下那处（首次加载）改成40
c = c.replace("renderGraph(graphData.nodes, graphData.links, null, 130);",
              "renderGraph(graphData.nodes, graphData.links, null, 40);")

# 5. 节点初始位置：大图散布
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

print('剩余130:', c.count('null, 130'))
print('剩余40:', c.count('null, 40'))
print('剩余30:', c.count('null, 30'))
print('完成')
