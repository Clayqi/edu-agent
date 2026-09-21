with open('D:/edu-agent/static/kg.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 默认配置降负载 ==========
old = """  physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -120,
      centralGravity: 0.002,
      springLength: 160,
      springConstant: 0.04,
      damping: 0.4,
      avoidOverlap: 0.8
    },
    stabilization: { iterations: 200, fit: true },
    maxVelocity: 60,
    minVelocity: 0.12
  },
  interaction: {
    hover: true,
    tooltipDelay: 80,
    navigationButtons: false,
    keyboard: false,
    dragNodes: true,
    zoomView: true,
    dragView: true,
    hoverConnectedEdges: true,
    selectConnectedEdges: true
  },
  nodes: { shape: 'dot', borderWidth: 1.2, scaling: { min: 10, max: 30 } },
  edges: {
    smooth: { type: 'continuous', roundness: 0.8 },
    selectionWidth: 2.5,
    hoverWidth: 2.2,
    arrows: { to: { enabled: true, scaleFactor: 0.4 } }
  }
};"""

new = """  physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -120,
      centralGravity: 0.002,
      springLength: 160,
      springConstant: 0.04,
      damping: 0.5,
      avoidOverlap: 0.8
    },
    stabilization: { iterations: 100, fit: true },
    maxVelocity: 30,
    minVelocity: 0.15
  },
  interaction: {
    hover: true,
    tooltipDelay: 300,
    navigationButtons: false,
    keyboard: false,
    dragNodes: true,
    zoomView: true,
    dragView: true,
    hoverConnectedEdges: false,
    selectConnectedEdges: false
  },
  nodes: { shape: 'dot', borderWidth: 1, scaling: { min: 10, max: 26 } },
  edges: {
    smooth: { type: 'continuous', roundness: 0.4 },
    selectionWidth: 2,
    hoverWidth: 1.8,
    arrows: { to: { enabled: true, scaleFactor: 0.3 } }
  }
};"""

assert old in content, "默认配置未匹配"
content = content.replace(old, new)

# ========== 2. 呼吸动画降频 + 大图自动休眠 ==========
old = """function startBreathe() {
  if (breatheTimer) return;
  let t = 0;
  breatheTimer = setInterval(() => {
    t++;
    if (!network || !nodesDS || draggingNow) return;
    const all = nodesDS.get();
    if (!all.length || all.length > 120) return;
    const upd = [];
    for (let i = 0; i < all.length; i++) {
      const n = all[i];
      if (!learnedSet.has(n.id)) continue;
      let base = (typeof n._shadowBase === 'number') ? n._shadowBase : 10;
      let s = base + Math.sin(t * 0.5) * 2;
      if (s < 4) s = 4;
      upd.push({ id: n.id, shadow: { enabled: true, color: n._catColor || '#888', size: s, x: 0, y: 0 } });
    }
    if (upd.length) {
      try { nodesDS.update(upd); network.redraw(); } catch(e) {}
    }
  }, 1500);
}"""

new = """function startBreathe() {
  if (breatheTimer) return;
  let t = 0;
  breatheTimer = setInterval(() => {
    t++;
    if (!network || !nodesDS || draggingNow) return;
    const all = nodesDS.get();
    // 大图（>60）自动休眠呼吸动画，避免持续重绘卡顿
    if (!all.length || all.length > 60) return;
    const upd = [];
    for (let i = 0; i < all.length; i++) {
      const n = all[i];
      if (!learnedSet.has(n.id)) continue;
      let base = (typeof n._shadowBase === 'number') ? n._shadowBase : 10;
      let s = base + Math.sin(t * 0.4) * 1.5;
      if (s < 3) s = 3;
      upd.push({ id: n.id, shadow: { enabled: true, color: n._catColor || '#888', size: s, x: 0, y: 0 } });
    }
    if (upd.length) {
      try { nodesDS.update(upd); } catch(e) {}
      // 用 requestAnimationFrame 节流重绘，避免 setInterval 满负荷 redraw
      if (!window._kgRedrawPending) {
        window._kgRedrawPending = true;
        requestAnimationFrame(() => {
          window._kgRedrawPending = false;
          try { network.redraw(); } catch(e) {}
        });
      }
    }
  }, 2600);
}"""

assert old in content, "呼吸动画未匹配"
content = content.replace(old, new)

# ========== 3. 拖拽结束：稳定迭代 60 -> 15，大图更低 ==========
old = """network.on('dragEnd', () => {
  draggingNow = false;
  try {
    network.stabilize(60, () => lockPhysics());
  } catch(e) {}
});"""

new = """network.on('dragEnd', () => {
  draggingNow = false;
  try {
    // 大图更少迭代，避免拖完卡顿
    const n = (nodesDS && nodesDS.length) || 0;
    const its = n > 150 ? 8 : (n > 80 ? 12 : 15);
    network.stabilize(its, () => lockPhysics());
  } catch(e) {}
});"""

assert old in content, "dragEnd 未匹配"
content = content.replace(old, new)

# ========== 4. 大图自动低配：节点>80 关闭阴影与高曲线 ==========
old = """    const item = {
      id: n.id,
      label: String(n.name || n.id),
      title: `<b>${escHtml(n.name)}</b><br>${isLearned ? '✨ 已点亮' : '⭕ 未点亮'}<br>章节：${escHtml(n.category || '-')}<br>${degree} 个连接`,
      shape: 'dot',
      size: baseSize,
      color: {
        background: isLearned ? color : KG_DARK.nodeDimColor,
        border: isLearned ? color : KG_DARK.nodeDimColor,
        highlight: { background: '#fff', border: color },
        hover: { background: '#fff', border: color }
      },
      font: { size: 11, color: isLearned ? KG_DARK.nodeLabel : KG_DARK.nodeDimLabel, face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' },
      shadow: isLearned ? { enabled: true, color: color, size: degree > 5 ? 18 : 10, x: 0, y: 0 } : { enabled: false },
      _degree: degree,
      _category: n.category || '',
      _shadowBase: isLearned ? (degree > 5 ? 18 : 10) : 0,
      _catColor: color
    };"""

new = """    const lowSpec = nodes.length > 80; // 大图低配：关阴影
    const item = {
      id: n.id,
      label: String(n.name || n.id),
      title: `<b>${escHtml(n.name)}</b><br>${isLearned ? '✨ 已点亮' : '⭕ 未点亮'}<br>章节：${escHtml(n.category || '-')}<br>${degree} 个连接`,
      shape: 'dot',
      size: baseSize,
      color: {
        background: isLearned ? color : KG_DARK.nodeDimColor,
        border: isLearned ? color : KG_DARK.nodeDimColor,
        highlight: { background: '#fff', border: color },
        hover: { background: '#fff', border: color }
      },
      font: { size: 11, color: isLearned ? KG_DARK.nodeLabel : KG_DARK.nodeDimLabel, face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' },
      shadow: (!lowSpec && isLearned) ? { enabled: true, color: color, size: degree > 5 ? 14 : 8, x: 0, y: 0 } : { enabled: false },
      _degree: degree,
      _category: n.category || '',
      _shadowBase: (!lowSpec && isLearned) ? (degree > 5 ? 14 : 8) : 0,
      _catColor: color
    };"""

assert old in content, "节点构建未匹配"
content = content.replace(old, new)

# ========== 5. 大图边低配：直线（禁用smooth） ==========
old = """  const pairIdx = {};
  const edgeItems = links.map((l, idx) => {
    const bothLearned = learnedSet.has(l.source) && learnedSet.has(l.target);
    const k = l.source < l.target ? l.source + '~' + l.target : l.target + '~' + l.source;
    const i = pairIdx[k] || 0;
    pairIdx[k] = i + 1;
    const roundness = pairCount[k] > 1 ? 0.8 + i * 0.3 : 0.8;
    const rel = l.relation || '关联';
    return {
      id: 'e' + idx,
      from: l.source,
      to: l.target,
      title: escHtml(rel) + (bothLearned ? '（已点亮）' : '未点亮'),
      width: bothLearned ? 1.8 : 1.2,
      color: bothLearned ? { color: KG_DARK.linkOn, highlight: KG_DARK.emLine, hover: KG_DARK.emLine }
                         : { color: KG_DARK.linkOff, highlight: KG_DARK.emLine, hover: KG_DARK.emLine },
      dashes: rel === '前置知识点' ? [6, 4] : (rel === '可推导' ? [2, 3] : false),
      smooth: { type: 'continuous', roundness: roundness, forceDirection: 'none' }
    };
  });"""

new = """  const pairIdx = {};
  const lowSpecEdge = links.length > 150; // 大图低配：直线渲染
  const edgeItems = links.map((l, idx) => {
    const bothLearned = learnedSet.has(l.source) && learnedSet.has(l.target);
    const k = l.source < l.target ? l.source + '~' + l.target : l.target + '~' + l.source;
    const i = pairIdx[k] || 0;
    pairIdx[k] = i + 1;
    const roundness = pairCount[k] > 1 ? 0.8 + i * 0.3 : 0.8;
    const rel = l.relation || '关联';
    return {
      id: 'e' + idx,
      from: l.source,
      to: l.target,
      title: escHtml(rel) + (bothLearned ? '（已点亮）' : '未点亮'),
      width: bothLearned ? 1.8 : 1.2,
      color: bothLearned ? { color: KG_DARK.linkOn, highlight: KG_DARK.emLine, hover: KG_DARK.emLine }
                         : { color: KG_DARK.linkOff, highlight: KG_DARK.emLine, hover: KG_DARK.emLine },
      dashes: rel === '前置知识点' ? [6, 4] : (rel === '可推导' ? [2, 3] : false),
      smooth: lowSpecEdge ? false : { type: 'continuous', roundness: roundness, forceDirection: 'none' }
    };
  });"""

assert old in content, "边构建未匹配"
content = content.replace(old, new)

# ========== 6. 弹开模式降低 maxVelocity 和引力，减少动画期卡顿 ==========
old = """    optB.physics.forceAtlas2Based.gravitationalConstant = -130; // 更强的互相排斥 → 弹开更明显
    optB.physics.forceAtlas2Based.centralGravity = 0.002;
    optB.physics.maxVelocity = 140;
    optB.physics.minVelocity = 0.08;"""

new = """    optB.physics.forceAtlas2Based.gravitationalConstant = -110; // 更强的互相排斥 → 弹开更明显
    optB.physics.forceAtlas2Based.centralGravity = 0.002;
    optB.physics.maxVelocity = 80;
    optB.physics.minVelocity = 0.1;"""

assert old in content, "弹开模式未匹配"
content = content.replace(old, new)

# ========== 7. updateNodeColors 大图跳过阴影 ==========
old = """      font: { size: 11, color: isLearned ? KG_DARK.nodeLabel : KG_DARK.nodeDimLabel, face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' },
      shadow: isLearned ? { enabled: true, color: color, size: (n._degree && n._degree > 5) ? 18 : 10, x: 0, y: 0 } : { enabled: false },
      _shadowBase: isLearned ? ((n._degree && n._degree > 5) ? 18 : 10) : 0,
      _catColor: color
    });
  });
  nodesDS.update(upd);"""

new = """      font: { size: 11, color: isLearned ? KG_DARK.nodeLabel : KG_DARK.nodeDimLabel, face: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' },
      shadow: isLearned ? { enabled: true, color: color, size: (n._degree && n._degree > 5) ? 14 : 8, x: 0, y: 0 } : { enabled: false },
      _shadowBase: isLearned ? ((n._degree && n._degree > 5) ? 14 : 8) : 0,
      _catColor: color
    });
  });
  nodesDS.update(upd);"""

assert old in content, "updateNodeColors 未匹配"
content = content.replace(old, new)

with open('D:/edu-agent/static/kg.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('知识星图性能优化完成：7项降载')
