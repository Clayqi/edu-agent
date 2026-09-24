p = 'D:/edu-agent/static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old = """      nodeDimColor:'#94a0c2', nodeLabel:'#232a52', nodeDimLabel:'#5f6d92',
      labelShadow:'0 0 3px rgba(255,255,255,0.7) ', dimShadow:'0 1px 2px rgba(255,255,255,0.55)',
      tipBg:'rgba(255,255,255,0.96)', tipText:'#333', tipBorder:'rgba(90,110,180,0.3)',
      linkOn:'rgba(60,90,160,0.55)', linkOff:'rgba(150,160,200,0.45)',
      emLine:'rgba(50,80,150,0.85)',
      empty:'#8a90ab', loading:'#8a90ab', succBg:'rgba(22,160,90,0.12)', succText:'#0e8a4e', defColor:'#3d6ef2'"""

new = """      nodeDimColor:'#ccc', nodeLabel:'#1a1a1a', nodeDimLabel:'#999',
      labelShadow:'0 0 3px rgba(255,255,255,0.8) ', dimShadow:'none',
      tipBg:'rgba(255,255,255,0.98)', tipText:'#1a1a1a', tipBorder:'rgba(0,0,0,0.15)',
      linkOn:'rgba(0,0,0,0.5)', linkOff:'rgba(0,0,0,0.12)',
      emLine:'rgba(0,0,0,0.8)',
      empty:'#999', loading:'#999', succBg:'rgba(0,0,0,0.05)', succText:'#1a1a1a', defColor:'#1a1a1a'"""

c = c.replace(old, new)
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('日间调色板修正完成')
