p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. lockPhysics 改成"软锁定"：不真正关物理，只降低速度，让节点持续微动
old_lock = """function lockPhysics() {
  try {
    network.setOptions({ physics: { enabled: false } });
  } catch(e) {}
}"""
new_lock = """function lockPhysics() {
  // 不真正关闭物理引擎，让节点持续轻微浮动，像星空一样动态
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
}"""
c = c.replace(old_lock, new_lock)

# 2. 弹开完成后也调用 lockPhysics（已经会调），但现在 lockPhysics 不关物理了
# 3. dragStart 时恢复正常物理参数
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

# 4. dragEnd 后不 lockPhysics，回到微动模式
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
  try {
    // 拖完直接回到微动模式，不做额外稳定迭代
    lockPhysics();
  } catch(e) {}
});"""
c = c.replace(old_dragend, new_dragend)

# 5. 首次加载：不做 stabilization，直接物理引擎跑
#    把 renderGraph 里 its>0 的逻辑简化：直接 setData 后让物理引擎自己跑
#    找到 stabilizationIterationsDone 回调，改成直接 lockPhysics（微动）
old_stab = """      const opt = Object.assign({}, DEFAULT_VIS_OPTIONS);
      opt.physics.stabilization.iterations = adaptIts(nodes, its);
      opt.physics.stabilization.fit = true;
      network.setOptions(opt);
      network.once('stabilizationIterationsDone', () => {
        lockPhysics();
        settle();
      });"""
new_stab = """      const opt = Object.assign({}, DEFAULT_VIS_OPTIONS);
      opt.physics.stabilization.iterations = adaptIts(nodes, its);
      opt.physics.stabilization.fit = true;
      network.setOptions(opt);
      network.once('stabilizationIterationsDone', () => {
        lockPhysics(); // 切到微动模式，不关闭物理
        settle();
      });"""
c = c.replace(old_stab, new_stab)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('动态星空模式完成：物理引擎持续运行，节点微动')
