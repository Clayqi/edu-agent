with open('D:/edu-agent/static/kg.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 首次加载不做"星核弹开"动画，直接随机分布+快速稳定
# 原来的 isBurst 条件是 nodes.length >= 2 && nodes.length <= 220
# 改成 nodes.length <= 40 才弹开（小图才有动画感），大图直接稳定布局
old = "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 220;"
new = "const isBurst = its > 0 && !focusNode && nodes.length >= 2 && nodes.length <= 40;"
assert old in content
content = content.replace(old, new)

# 2. stabilization iterations 从 100 降到 50，快速收敛
old = "stabilization: { iterations: 100, fit: true },"
new = "stabilization: { iterations: 50, fit: true },"
assert old in content
content = content.replace(old, new)

# 3. 大图兜底时间从 4200ms 降到 1500ms
old = "burstTimer = setTimeout(finishBurst, nodes.length > 120 ? 4200 : 3200); // 兜底：动画期间一定收敛"
new = "burstTimer = setTimeout(finishBurst, nodes.length > 60 ? 1500 : 2000); // 兜底：动画期间一定收敛"
assert old in content
content = content.replace(old, new)

# 4. 节点初始位置：大图直接随机分布在整个画布，不堆中心
old = """    if (burstCenter) {
      const ang = (i % 6) * (Math.PI / 3) + Math.random() * 0.4;
      const rad = 1 + Math.random() * 5;
      px = burstCenter.x + Math.cos(ang) * rad;
      py = burstCenter.y + Math.sin(ang) * rad;
    }"""
new = """    if (burstCenter) {
      // 小图聚核弹开；大图直接散布整个画布，减少初始物理收敛时间
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
assert old in content
content = content.replace(old, new)

# 5. 首次加载 iters 从 130 降到 40
old = "renderGraph(graphData.nodes, graphData.links, null, 130);"
new = "renderGraph(graphData.nodes, graphData.links, null, 40);"
assert old in content
content = content.replace(old, new)

# 6. 关闭 info 关闭后的全量重渲染（130 iters）
old = """function closeInfo() {
  document.getElementById('infoPanel').style.display = 'none';
  renderGraph(graphData.nodes, graphData.links, null, 130);
}"""
new = """function closeInfo() {
  document.getElementById('infoPanel').style.display = 'none';
  renderGraph(graphData.nodes, graphData.links, null, 30);
}"""
assert old in content
content = content.replace(old, new)

# 7. 搜索框清空后重渲染 130 -> 30
old = """  if (!q) {
    renderGraph(graphData.nodes, graphData.links, null, 130);
    return;
  }"""
new = """  if (!q) {
    renderGraph(graphData.nodes, graphData.links, null, 30);
    return;
  }"""
assert old in content
content = content.replace(old, new)

with open('D:/edu-agent/static/kg.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('首次加载卡顿优化完成')
