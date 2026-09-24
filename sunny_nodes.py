p = 'D:/edu-agent/static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 节点配色改暖色
c = c.replace("""  var constellationColors = {
    '第一章': '#7ab8ff', '第二章': '#98ff98', '第三章': '#ffd700',
    '第四章': '#ff6b9d', '初中衔接': '#c084fc'
  };""",
"""  var constellationColors = {
    '第一章': '#ff9a3c', '第二章': '#ffcc33', '第三章': '#ff6b6b',
    '第四章': '#ff8fab', '初中衔接': '#c084fc'
  };""")

# 日间模式调色板改暖色
c = c.replace("""    } : {
      nodeDimColor:'#94a0c2', nodeLabel:'#232a52', nodeDimLabel:'#5f6d92',
      labelShadow:'0 0 3px rgba(255,255,255,0.7) ', dimShadow:'0 1px 2px rgba(255,255,255,0.55)',
      tipBg:'rgba(255,255,255,0.96)', tipText:'#333', tipBorder:'rgba(90,110,180,0.3)',
      linkOn:'rgba(60,90,160,0.55)', linkOff:'rgba(150,160,200,0.45)',
      emLine:'rgba(50,80,150,0.85)',
      empty:'#8a90ab', loading:'#8a90ab', succBg:'rgba(22,160,90,0.12)', succText:'#0e8a4e', defColor:'#3d6ef2'
    };""",
"""    } : {
      nodeDimColor:'#d4c5a0', nodeLabel:'#5a3e00', nodeDimLabel:'#b09a6a',
      labelShadow:'0 0 3px rgba(255,240,200,0.8) ', dimShadow:'0 1px 2px rgba(255,220,150,0.5)',
      tipBg:'rgba(255,248,230,0.96)', tipText:'#5a3e00', tipBorder:'rgba(200,150,50,0.3)',
      linkOn:'rgba(255,150,50,0.6)', linkOff:'rgba(200,170,120,0.25)',
      emLine:'rgba(255,140,50,0.85)',
      empty:'#b09a6a', loading:'#b09a6a', succBg:'rgba(100,180,100,0.15)', succText:'#2d8a4e', defColor:'#ffb347'
    };""")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('主页面知识星图节点配色改暖色')
