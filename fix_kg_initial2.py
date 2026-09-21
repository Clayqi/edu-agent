import io
p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

def rep(old, new):
    global c
    if old in c:
        c = c.replace(old, new)
        print('OK:', old[:40].replace(chr(10),' '))
    else:
        print('MISS:', old[:40].replace(chr(10),' '))

rep("const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 220;",
    "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 40;")

rep("stabilization: { iterations: 100, fit: true },",
    "stabilization: { iterations: 50, fit: true },")

rep("burstTimer = setTimeout(finishBurst, nodes.length > 120 ? 4200 : 3200);",
    "burstTimer = setTimeout(finishBurst, nodes.length > 60 ? 1500 : 2000);")

rep("renderGraph(graphData.nodes, graphData.links, null, 130);",
    "renderGraph(graphData.nodes, graphData.links, null, 40);")

rep("renderGraph(graphData.nodes, graphData.links, null, 130);",
    "renderGraph(graphData.nodes, graphData.links, null, 30);")

# closeInfo 和搜索框清空两处的 130 都改成 30
c = c.replace(
    "document.getElementById('infoPanel').style.display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 130);",
    "document.getElementById('infoPanel').style.display = 'none';\n  renderGraph(graphData.nodes, graphData.links, null, 30);")

c = c.replace(
    "if (!q) {\n    renderGraph(graphData.nodes, graphData.links, null, 130);",
    "if (!q) {\n    renderGraph(graphData.nodes, graphData.links, null, 30);")

# 节点初始位置：大图直接散布，不堆中心
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
rep(old_pos, new_pos)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('写入完成')
