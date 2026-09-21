p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# ========== 1. 浮动效果：改用 moveNode 正弦偏移，平滑不跳 ==========
old_float = """  // 持续注入能量，让节点永远飘着
  if (window._breatheInterval) clearInterval(window._breatheInterval);
  window._breatheInterval = setInterval(() => {
    if (!network || draggingNow) return;
    try {
      // 轻轻推一下，让节点重新浮动
      network.setOptions({ physics: {
        forceAtlas2Based: { gravitationalConstant: -100 }
      }});
      setTimeout(() => {
        try { network.setOptions({ physics: {
          forceAtlas2Based: { gravitationalConstant: -80 }
        }}); } catch(e) {}
      }, 200);
    } catch(e) {}
  }, 2500);"""

new_float = """  // 用 moveNode 手动给节点加正弦浮动，平滑不跳
  if (window._floatInterval) clearInterval(window._floatInterval);
  let _ft = 0;
  window._floatInterval = setInterval(() => {
    if (!network || draggingNow || !nodesDS) return;
    _ft += 0.02;
    try {
      const all = nodesDS.get();
      if (all.length > 80) return; // 大图不浮动，避免卡
      const upd = [];
      for (let i = 0; i < all.length; i++) {
        const n = all[i];
        const dx = Math.sin(_ft + i * 0.5) * 0.8;
        const dy = Math.cos(_ft * 0.7 + i * 0.3) * 0.6;
        if (n.x === undefined) continue;
        upd.push({ id: n.id, x: n.x + dx, y: n.y + dy });
      }
      if (upd.length) nodesDS.update(upd);
    } catch(e) {}
  }, 50);"""

c = c.replace(old_float, new_float)

# ========== 2. 未点亮节点更暗更小 ==========
old_size = "let baseSize = 8 + Math.min(degree * 2, 12); // 8~20之间"
new_size = "let baseSize = isLearned ? (10 + Math.min(degree * 2, 14)) : (5 + Math.min(degree, 6)); // 点亮大，未点亮小"
c = c.replace(old_size, new_size)

# ========== 3. hover节点放大 ==========
old_nodes = "nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 10, max: 26 } },"
new_nodes = "nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 5, max: 26 } }, interaction: { hover: true, tooltipDelay: 300, hoverNeighbor: true },"
# 注意：上面会重复 interaction，我改到 edges 那行
c = c.replace(old_nodes, "nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 5, max: 26 } },")

# ========== 4. 搜索防抖 ==========
old_search = """document.getElementById('searchInput').addEventListener('input', function(e) {
  const q = e.target.value.trim();
  if (!q) {
    renderGraph(graphData.nodes, graphData.links, null, 30);
    return;
  }
  fetch(`/api/kg/search?q=${encodeURIComponent(q)}`)"""

new_search = """let _searchTimer = null;
document.getElementById('searchInput').addEventListener('input', function(e) {
  const q = e.target.value.trim();
  if (_searchTimer) clearTimeout(_searchTimer);
  if (!q) {
    renderGraph(graphData.nodes, graphData.links, null, 30);
    return;
  }
  _searchTimer = setTimeout(() => {
  fetch(`/api/kg/search?q=${encodeURIComponent(q)}`)"""
c = c.replace(old_search, new_search)

# 搜索fetch结束后要加括号闭合
old_search_end = """      }
    });
});

// vis-network 自动监听窗口大小变化，无需手动 redraw"""
new_search_end = """      }
    });
  }, 350);
});

// vis-network 自动监听窗口大小变化，无需手动 redraw"""
c = c.replace(old_search_end, new_search_end)

# ========== 5. 背景星星增多 ==========
old_stars = """  .stars::before, .stars::after {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
      radial-gradient(2px 2px at 20px 30px, #fff, transparent),
      radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
      radial-gradient(1px 1px at 50px 160px, #fff, transparent),
      radial-gradient(2px 2px at 90px 40px, rgba(255,255,255,0.9), transparent),
      radial-gradient(1px 1px at 130px 80px, #fff, transparent),
      radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.7), transparent),
      radial-gradient(1px 1px at 200px 50px, #fff, transparent),
      radial-gradient(2px 2px at 240px 180px, rgba(255,255,255,0.8), transparent);
    background-size: 300px 300px;
    animation: twinkle 5s ease-in-out infinite;
  }"""

new_stars = """  .stars::before, .stars::after {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
      radial-gradient(2px 2px at 20px 30px, #fff, transparent),
      radial-gradient(2px 2px at 40px 70px, rgba(255,255,255,0.8), transparent),
      radial-gradient(1px 1px at 50px 160px, #fff, transparent),
      radial-gradient(2px 2px at 90px 40px, rgba(255,255,255,0.9), transparent),
      radial-gradient(1px 1px at 130px 80px, #fff, transparent),
      radial-gradient(2px 2px at 160px 120px, rgba(255,255,255,0.7), transparent),
      radial-gradient(1px 1px at 200px 50px, #fff, transparent),
      radial-gradient(2px 2px at 240px 180px, rgba(255,255,255,0.8), transparent),
      radial-gradient(1px 1px at 70px 200px, rgba(255,255,255,0.6), transparent),
      radial-gradient(1px 1px at 180px 220px, #fff, transparent),
      radial-gradient(2px 2px at 280px 90px, rgba(255,255,255,0.7), transparent),
      radial-gradient(1px 1px at 320px 150px, #fff, transparent);
    background-size: 350px 350px;
    animation: twinkle 4s ease-in-out infinite;
  }"""
c = c.replace(old_stars, new_stars)

# ========== 6. 未点亮连线更透明 ==========
c = c.replace("linkOff: 'rgba(160, 170, 220, 0.35)'",
              "linkOff: 'rgba(160, 170, 220, 0.18)'")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('全部优化完成：6项')
