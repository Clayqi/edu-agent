p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. lockPhysics：不关闭物理，改成持续微动模式
old_lock = """function lockPhysics() {
  try {
    network.setOptions({ physics: { enabled: false } });
  } catch(e) {}
}"""
new_lock = """function lockPhysics() {
  // 不关闭物理引擎，让节点持续轻微浮动
  try {
    network.setOptions({
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -80,
          centralGravity: 0.001,
          springLength: 160,
          springConstant: 0.02,
          damping: 0.9,
          avoidOverlap: 0.8
        },
        stabilization: { enabled: false },
        maxVelocity: 8,
        minVelocity: 0.01
      }
    });
  } catch(e) {}
  // 持续注入能量，让节点永远飘着
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
  }, 2500);
}"""
c = c.replace(old_lock, new_lock)

# 2. dragStart 恢复正常物理参数
old_drag = """network.on('dragStart', () => {
  draggingNow = true;
  try {
    network.setOptions({ physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -60, centralGravity: 0.005,
        springLength: 120, springConstant: 0.08,
        damping: 0.5, avoidOverlap: 0.8
      },
      stabilization: { enabled: false },
      timestep: 0.5, adaptiveTimestep: true,
      maxVelocity: 90, minVelocity: 0.05
    } });
  } catch(e) {}
});"""
new_drag = """network.on('dragStart', () => {
  draggingNow = true;
  try {
    network.setOptions({ physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -120, centralGravity: 0.002,
        springLength: 160, springConstant: 0.04,
        damping: 0.4, avoidOverlap: 0.8
      },
      stabilization: { enabled: false },
      timestep: 0.5, adaptiveTimestep: true,
      maxVelocity: 60, minVelocity: 0.12
    } });
  } catch(e) {}
});"""
c = c.replace(old_drag, new_drag)

# 3. dragEnd 直接回到微动模式
old_dragend = """network.on('dragEnd', () => {
  draggingNow = false;
  try {
    // 大图更少迭代，避免拖完卡顿
    const n = (nodesDS && nodesDS.length) || 0;
    const its = n > 150 ? 8 : (n > 80 ? 12 : 15);
    network.stabilize(its, () => lockPhysics());
  } catch(e) {}
});"""
new_dragend = """network.on('dragEnd', () => {
  draggingNow = false;
  try { lockPhysics(); } catch(e) {}
});"""
c = c.replace(old_dragend, new_dragend)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('动态星空完成')
