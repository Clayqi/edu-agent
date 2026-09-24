p = 'D:/edu-agent/static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 日间模式CSS变量改回白底灰蓝，和主页面统一
old_vars = """#view-kg{position:relative;flex-direction:column;height:100%;min-height:0;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
              --kg-bg:linear-gradient(180deg,#fff8e7 0%,#ffe8c2 40%,#ffd489 100%);--kg-ink:#5a3e00;--kg-ink2:#8b6914;--kg-ink3:#b09a6a;
              --kg-stars-img:
                radial-gradient(80px 80px at 10% 20%,rgba(255,200,100,.15),transparent),
                radial-gradient(120px 120px at 90% 10%,rgba(255,220,150,.2),transparent),
                radial-gradient(60px 60px at 70% 80%,rgba(255,180,80,.12),transparent),
                radial-gradient(100px 100px at 20% 90%,rgba(255,200,120,.15),transparent),
                radial-gradient(150px 150px at 50% 0%,rgba(255,240,200,.4),transparent);
              --kg-bar-bg:rgba(200,160,80,.3);--kg-fill:linear-gradient(90deg,#ffb347,#ffcc33);
              --kg-panel:rgba(255,248,230,.95);--kg-panel-line:rgba(200,150,50,.3);--kg-panel-shadow:0 4px 30px rgba(200,150,50,.2);
              --kg-chip:rgba(255,220,150,.4);--kg-chip-hover:rgba(255,200,100,.6);--kg-chip-hover-sd:0 0 10px rgba(255,180,50,.3);
              --kg-success:#d4880f;--kg-accent:#ff8c42;
              --kg-head-line:rgba(200,150,50,.2);--kg-head-bg:rgba(255,248,230,.85);
              --kg-input-bg:#fff;--kg-input-bd:rgba(200,150,50,.4);--kg-input-ph:#b09a6a;
              background:var(--kg-bg);color:var(--kg-ink)}"""

new_vars = """#view-kg{position:relative;flex-direction:column;height:100%;min-height:0;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
              --kg-bg:#f5f7fd;--kg-ink:#1b1f36;--kg-ink2:#5c637d;--kg-ink3:#8a90ab;
              --kg-stars-img:
                radial-gradient(2px 2px at 20px 30px,rgba(96,120,190,.45),transparent),
                radial-gradient(2px 2px at 40px 70px,rgba(96,120,190,.35),transparent),
                radial-gradient(1px 1px at 50px 160px,rgba(96,120,190,.4),transparent),
                radial-gradient(2px 2px at 90px 40px,rgba(96,120,190,.45),transparent),
                radial-gradient(1px 1px at 130px 80px,rgba(96,120,190,.35),transparent),
                radial-gradient(2px 2px at 160px 120px,rgba(96,120,190,.4),transparent),
                radial-gradient(1px 1px at 200px 50px,rgba(96,120,190,.35),transparent),
                radial-gradient(2px 2px at 240px 180px,rgba(96,120,190,.45),transparent);
              --kg-bar-bg:rgba(110,130,190,.28);--kg-fill:linear-gradient(90deg,#4a7bff,#22c55e);
              --kg-panel:rgba(255,255,255,.96);--kg-panel-line:rgba(90,110,180,.28);--kg-panel-shadow:0 4px 30px rgba(60,80,150,.16);
              --kg-chip:rgba(237,241,252,.95);--kg-chip-hover:rgba(228,234,250,1);--kg-chip-hover-sd:0 0 10px rgba(90,115,190,.25);
              --kg-success:#15964a;--kg-accent:#3d6ef2;
              --kg-head-line:rgba(90,110,180,.18);--kg-head-bg:rgba(255,255,255,.72);
              --kg-input-bg:#fff;--kg-input-bd:rgba(110,130,190,.4);--kg-input-ph:#8a90ab;
              background:var(--kg-bg);color:var(--kg-ink)}"""

c = c.replace(old_vars, new_vars)

# 按钮改回蓝紫
c = c.replace("#view-kg .kg-mark-btn{width:100%;padding:10px;border:none;border-radius:8px;background:linear-gradient(135deg,#ffb347,#ff8c42);color:#fff;font-size:13px;cursor:pointer;margin-top:12px;transition:all 0.2s;font-family:inherit}",
              "#view-kg .kg-mark-btn{width:100%;padding:10px;border:none;border-radius:8px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;font-size:13px;cursor:pointer;margin-top:12px;transition:all 0.2s;font-family:inherit}")
c = c.replace("#view-kg .kg-mark-btn:hover{box-shadow:0 0 20px rgba(255,180,50,0.5)}",
              "#view-kg .kg-mark-btn:hover{box-shadow:0 0 20px rgba(100,100,255,0.5)}")
c = c.replace("#view-kg .kg-mark-btn.learned{background:linear-gradient(135deg,#ff6b6b,#ff8fab)}",
              "#view-kg .kg-mark-btn.learned{background:linear-gradient(135deg,#f093fb,#f5576c)}")
c = c.replace("#view-kg .kg-progress .kg-fill{height:100%;background:var(--kg-fill);transition:width 0.3s;box-shadow:0 0 10px rgba(255,180,50,0.5);width:0%}",
              "#view-kg .kg-progress .kg-fill{height:100%;background:var(--kg-fill);transition:width 0.3s;box-shadow:0 0 10px rgba(100,200,255,0.5);width:0%}")
c = c.replace("#view-kg .kg-search input:focus{border-color:#ffb347;box-shadow:0 0 10px rgba(255,180,50,0.3)}",
              "#view-kg .kg-search input:focus{border-color:#7ab8ff;box-shadow:0 0 10px rgba(100,150,255,0.3)}")

# 日间节点配色改回蓝白系
c = c.replace("""  var constellationColorsDay = {
    '第一章': '#ff9a3c', '第二章': '#ffcc33', '第三章': '#ff6b6b',
    '第四章': '#ff8fab', '初中衔接': '#c084fc'
  };""",
"""  var constellationColorsDay = {
    '第一章': '#5b8def', '第二章': '#4caf7d', '第三章': '#e8b93c',
    '第四章': '#e86a9c', '初中衔接': '#9c6bd8'
  };""")

# 日间调色板改回蓝白
c = c.replace("""    } : {
      nodeDimColor:'#d4c5a0', nodeLabel:'#5a3e00', nodeDimLabel:'#b09a6a',
      labelShadow:'0 0 3px rgba(255,240,200,0.8) ', dimShadow:'0 1px 2px rgba(255,220,150,0.5)',
      tipBg:'rgba(255,248,230,0.96)', tipText:'#5a3e00', tipBorder:'rgba(200,150,50,0.3)',
      linkOn:'rgba(255,150,50,0.6)', linkOff:'rgba(200,170,120,0.25)',
      emLine:'rgba(255,140,50,0.85)',
      empty:'#b09a6a', loading:'#b09a6a', succBg:'rgba(100,180,100,0.15)', succText:'#2d8a4e', defColor:'#ffb347'
    };""",
"""    } : {
      nodeDimColor:'#b0bcd4', nodeLabel:'#232a52', nodeDimLabel:'#5f6d92',
      labelShadow:'0 0 3px rgba(255,255,255,0.7) ', dimShadow:'0 1px 2px rgba(255,255,255,0.55)',
      tipBg:'rgba(255,255,255,0.96)', tipText:'#333', tipBorder:'rgba(90,110,180,0.3)',
      linkOn:'rgba(60,90,160,0.55)', linkOff:'rgba(150,160,200,0.35)',
      emLine:'rgba(50,80,150,0.85)',
      empty:'#8a90ab', loading:'#8a90ab', succBg:'rgba(22,160,90,0.12)', succText:'#0e8a4e', defColor:'#5b8def'
    };""")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('日间模式知识星图改回白底蓝白，和主页面统一')
