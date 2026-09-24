p = 'D:/edu-agent/static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# ===== 日间模式：纯白底黑字，无彩色 =====
old_day = """#view-kg{position:relative;flex-direction:column;height:100%;min-height:0;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
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

new_day = """#view-kg{position:relative;flex-direction:column;height:100%;min-height:0;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
              --kg-bg:#ffffff;--kg-ink:#1a1a1a;--kg-ink2:#666;--kg-ink3:#999;
              --kg-stars-img:none;
              --kg-bar-bg:rgba(0,0,0,.08);--kg-fill:linear-gradient(90deg,#333,#000);
              --kg-panel:rgba(255,255,255,.98);--kg-panel-line:rgba(0,0,0,.12);--kg-panel-shadow:0 4px 24px rgba(0,0,0,.1);
              --kg-chip:rgba(0,0,0,.05);--kg-chip-hover:rgba(0,0,0,.1);--kg-chip-hover-sd:none;
              --kg-success:#1a1a1a;--kg-accent:#1a1a1a;
              --kg-head-line:rgba(0,0,0,.08);--kg-head-bg:rgba(255,255,255,.9);
              --kg-input-bg:#fff;--kg-input-bd:rgba(0,0,0,.15);--kg-input-ph:#999;
              background:var(--kg-bg);color:var(--kg-ink)}"""

c = c.replace(old_day, new_day)

# ===== 夜间模式：纯黑底白字 =====
old_night = """html.dark #view-kg{
              --kg-bg:#0a0a1a;--kg-ink:#e0e0ff;--kg-ink2:#aaa;--kg-ink3:#7a7aa8;
              --kg-stars-img:
                radial-gradient(2px 2px at 20px 30px,#fff,transparent),
                radial-gradient(2px 2px at 40px 70px,rgba(255,255,255,0.8),transparent),
                radial-gradient(1px 1px at 50px 160px,#fff,transparent),
                radial-gradient(2px 2px at 90px 40px,rgba(255,255,255,0.9),transparent),
                radial-gradient(1px 1px at 130px 80px,#fff,transparent),
                radial-gradient(2px 2px at 160px 120px,rgba(255,255,255,0.7),transparent),
                radial-gradient(1px 1px at 200px 50px,#fff,transparent),
                radial-gradient(2px 2px at 240px 180px,rgba(255,255,255,0.8),transparent);
              --kg-bar-bg:rgba(50,50,100,.5);--kg-fill:linear-gradient(90deg,#7ab8ff,#9dffb8);
              --kg-panel:rgba(15,15,50,.92);--kg-panel-line:rgba(100,150,255,.3);--kg-panel-shadow:0 4px 30px rgba(0,0,100,.5);
              --kg-chip:rgba(30,30,80,.6);--kg-chip-hover:rgba(50,50,120,.8);--kg-chip-hover-sd:0 0 10px rgba(100,150,255,.3);
              --kg-success:#9dffb8;--kg-accent:#8ab8ff;
              --kg-head-line:rgba(100,100,255,.2);--kg-head-bg:rgba(10,10,40,.8);
              --kg-input-bg:rgba(20,20,60,.6);--kg-input-bd:rgba(100,100,255,.3);--kg-input-ph:#7a7aa8;
              background:var(--kg-bg);color:var(--kg-ink)}"""

new_night = """html.dark #view-kg{
              --kg-bg:#0d0d0d;--kg-ink:#fff;--kg-ink2:#aaa;--kg-ink3:#777;
              --kg-stars-img:none;
              --kg-bar-bg:rgba(255,255,255,.12);--kg-fill:linear-gradient(90deg,#ccc,#fff);
              --kg-panel:rgba(20,20,20,.96);--kg-panel-line:rgba(255,255,255,.15);--kg-panel-shadow:0 4px 24px rgba(0,0,0,.5);
              --kg-chip:rgba(255,255,255,.08);--kg-chip-hover:rgba(255,255,255,.15);--kg-chip-hover-sd:none;
              --kg-success:#fff;--kg-accent:#fff;
              --kg-head-line:rgba(255,255,255,.1);--kg-head-bg:rgba(13,13,13,.9);
              --kg-input-bg:#1a1a1a;--kg-input-bd:rgba(255,255,255,.2);--kg-input-ph:#777;
              background:var(--kg-bg);color:var(--kg-ink)}"""

c = c.replace(old_night, new_night)

# ===== 按钮改黑白 =====
c = c.replace("#view-kg .kg-mark-btn{width:100%;padding:10px;border:none;border-radius:8px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;font-size:13px;cursor:pointer;margin-top:12px;transition:all 0.2s;font-family:inherit}",
"#view-kg .kg-mark-btn{width:100%;padding:10px;border:none;border-radius:8px;background:#1a1a1a;color:#fff;font-size:13px;cursor:pointer;margin-top:12px;transition:all 0.2s;font-family:inherit}")
c = c.replace("#view-kg .kg-mark-btn:hover{box-shadow:0 0 20px rgba(100,100,255,0.5)}",
"#view-kg .kg-mark-btn:hover{background:#333}")
c = c.replace("#view-kg .kg-mark-btn.learned{background:linear-gradient(135deg,#f093fb,#f5576c)}",
"#view-kg .kg-mark-btn.learned{background:#fff;color:#1a1a1a}")
c = c.replace("#view-kg .kg-progress .kg-fill{height:100%;background:var(--kg-fill);transition:width 0.3s;box-shadow:0 0 10px rgba(100,200,255,0.5);width:0%}",
"#view-kg .kg-progress .kg-fill{height:100%;background:var(--kg-fill);transition:width 0.3s;width:0%}")
c = c.replace("#view-kg .kg-search input:focus{border-color:#7ab8ff;box-shadow:0 0 10px rgba(100,150,255,0.3)}",
"#view-kg .kg-search input:focus{border-color:#333}")

# ===== 节点配色全部黑白 =====
c = c.replace("""  var constellationColorsDay = {
    '第一章': '#5b8def', '第二章': '#4caf7d', '第三章': '#e8b93c',
    '第四章': '#e86a9c', '初中衔接': '#9c6bd8'
  };
  var constellationColorsNight = {
    '第一章': '#7ab8ff', '第二章': '#98ff98', '第三章': '#ffd700',
    '第四章': '#ff6b9d', '初中衔接': '#c084fc'
  };""",
"""  var constellationColorsDay = {
    '第一章': '#1a1a1a', '第二章': '#333', '第三章': '#555',
    '第四章': '#777', '初中衔接': '#999'
  };
  var constellationColorsNight = {
    '第一章': '#ffffff', '第二章': '#ddd', '第三章': '#bbb',
    '第四章': '#999', '初中衔接': '#777'
  };""")

# ===== 调色板改黑白 =====
c = c.replace("""    } : {
      nodeDimColor:'#b0bcd4', nodeLabel:'#232a52', nodeDimLabel:'#5f6d92',
      labelShadow:'0 0 3px rgba(255,255,255,0.7) ', dimShadow:'0 1px 2px rgba(255,255,255,0.55)',
      tipBg:'rgba(255,255,255,0.96)', tipText:'#333', tipBorder:'rgba(90,110,180,0.3)',
      linkOn:'rgba(60,90,160,0.55)', linkOff:'rgba(150,160,200,0.35)',
      emLine:'rgba(50,80,150,0.85)',
      empty:'#8a90ab', loading:'#8a90ab', succBg:'rgba(22,160,90,0.12)', succText:'#0e8a4e', defColor:'#5b8def'
    };""",
"""    } : {
      nodeDimColor:'#ccc', nodeLabel:'#1a1a1a', nodeDimLabel:'#999',
      labelShadow:'0 0 3px rgba(255,255,255,0.8) ', dimShadow:'none',
      tipBg:'rgba(255,255,255,0.98)', tipText:'#1a1a1a', tipBorder:'rgba(0,0,0,0.15)',
      linkOn:'rgba(0,0,0,0.5)', linkOff:'rgba(0,0,0,0.12)',
      emLine:'rgba(0,0,0,0.8)',
      empty:'#999', loading:'#999', succBg:'rgba(0,0,0,0.05)', succText:'#1a1a1a', defColor:'#1a1a1a'
    };""")

# 夜间调色板改黑白
c = c.replace("""      nodeDimColor:'#666666', nodeLabel:'#ffffff', nodeDimLabel:'#888888',
      labelShadow:'0 0 6px ', dimShadow:'0 1px 2px rgba(0,0,0,0.8)',
      tipBg:'rgba(10, 10, 40, 0.9)', tipText:'#fff', tipBorder:'rgba(100, 150, 255, 0.3)',
      linkOn:'rgba(255,255,255,0.5)', linkOff:'rgba(150,150,200,0.3)',
      emLine:'rgba(255,255,255,0.8)',
      empty:'#555', loading:'#666', succBg:'rgba(100,200,150,0.2)', succText:'#98ff98', defColor:'#fff'""",
"""      nodeDimColor:'#444', nodeLabel:'#ffffff', nodeDimLabel:'#888',
      labelShadow:'0 0 6px rgba(255,255,255,0.3)', dimShadow:'none',
      tipBg:'rgba(20,20,20,0.95)', tipText:'#fff', tipBorder:'rgba(255,255,255,0.15)',
      linkOn:'rgba(255,255,255,0.6)', linkOff:'rgba(255,255,255,0.15)',
      emLine:'rgba(255,255,255,0.9)',
      empty:'#666', loading:'#777', succBg:'rgba(255,255,255,0.08)', succText:'#fff', defColor:'#fff'""")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('知识星图黑白简约配色完成')
