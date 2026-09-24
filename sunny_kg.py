p = 'D:/edu-agent/static/kg.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. 背景改成阳光渐变
c = c.replace("background: #0a0a1a;",
              "background: linear-gradient(180deg, #fff8e7 0%, #ffe8c2 40%, #ffd489 100%);")

# 2. 星星背景改成阳光光斑（不是白色星星，是暖光晕）
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
      radial-gradient(2px 2px at 240px 180px, rgba(255,255,255,0.8), transparent),
      radial-gradient(1px 1px at 70px 200px, rgba(255,255,255,0.6), transparent),
      radial-gradient(1px 1px at 180px 220px, #fff, transparent),
      radial-gradient(2px 2px at 280px 90px, rgba(255,255,255,0.7), transparent),
      radial-gradient(1px 1px at 320px 150px, #fff, transparent);
    background-size: 350px 350px;
    animation: twinkle 4s ease-in-out infinite;
  }
  .stars::after {
    background-size: 200px 200px;
    background-position: 100px 50px;
    opacity: 0.5;
    animation-delay: 2.5s;
  }"""

new_stars = """  .stars::before, .stars::after {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
      radial-gradient(circle at 50% 0%, rgba(255, 220, 150, 0.4) 0%, transparent 50%),
      radial-gradient(80px 80px at 10% 20%, rgba(255, 200, 100, 0.15), transparent),
      radial-gradient(120px 120px at 90% 10%, rgba(255, 220, 150, 0.2), transparent),
      radial-gradient(60px 60px at 70% 80%, rgba(255, 180, 80, 0.12), transparent),
      radial-gradient(100px 100px at 20% 90%, rgba(255, 200, 120, 0.15), transparent);
    background-size: 100% 100%;
    animation: sunGlow 6s ease-in-out infinite;
  }
  .stars::after {
    background-image: 
      radial-gradient(circle at 50% -10%, rgba(255, 240, 200, 0.6) 0%, transparent 40%);
    opacity: 0.7;
    animation-delay: 1s;
  }
  @keyframes sunGlow {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
  }"""

c = c.replace(old_stars, new_stars)

# 3. header 改成暖色
c = c.replace("background: rgba(10, 10, 40, 0.8);",
              "background: rgba(255, 248, 230, 0.85);")
c = c.replace("border-bottom: 1px solid rgba(100, 100, 255, 0.2);",
              "border-bottom: 1px solid rgba(200, 150, 50, 0.2);")
c = c.replace(".header h1 { font-size: 18px; color: #fff; text-shadow: 0 0 20px rgba(100, 150, 255, 0.5); }",
              ".header h1 { font-size: 18px; color: #8b5a00; text-shadow: 0 0 20px rgba(255, 180, 50, 0.3); }")
c = c.replace(".header .back { color: #7ab8ff; text-decoration: none; font-size: 14px; }",
              ".header .back { color: #d4880f; text-decoration: none; font-size: 14px; }")

# 4. 进度条改成暖色
c = c.replace(".progress-bar .bar { width: 160px; height: 8px; background: rgba(50, 50, 100, 0.5); border-radius: 4px; overflow: hidden; }",
              ".progress-bar .bar { width: 160px; height: 8px; background: rgba(200, 160, 80, 0.3); border-radius: 4px; overflow: hidden; }")
c = c.replace(".progress-bar .fill { height: 100%; background: linear-gradient(90deg, #7ab8ff, #9dffb8); transition: width 0.3s; box-shadow: 0 0 10px rgba(100, 200, 255, 0.5); }",
              ".progress-bar .fill { height: 100%; background: linear-gradient(90deg, #ffb347, #ffcc33); transition: width 0.3s; box-shadow: 0 0 10px rgba(255, 180, 50, 0.5); }")
c = c.replace(".progress-bar .percent { font-size: 13px; color: #9dffb8; font-weight: 600; }",
              ".progress-bar .percent { font-size: 13px; color: #d4880f; font-weight: 600; }")
c = c.replace(".progress-bar .label { font-size: 13px; color: #aaa; }",
              ".progress-bar .label { font-size: 13px; color: #8b6914; }")

# 5. 搜索框改成暖色
c = c.replace("background: rgba(10, 10, 40, 0.6);",
              "background: rgba(255, 248, 230, 0.7);")
c = c.replace("border-bottom: 1px solid rgba(100, 100, 255, 0.2);",
              "border-bottom: 1px solid rgba(200, 150, 50, 0.2);")
c = c.replace("border: 1px solid rgba(100, 100, 255, 0.3);",
              "border: 1px solid rgba(200, 150, 50, 0.3);")
c = c.replace("background: rgba(20, 20, 60, 0.6);",
              "background: rgba(255, 255, 255, 0.8);")
c = c.replace("color: #fff;",
              "color: #5a3e00;")
c = c.replace(".search-box input:focus { border-color: #7ab8ff; box-shadow: 0 0 10px rgba(100, 150, 255, 0.3); }",
              ".search-box input:focus { border-color: #ffb347; box-shadow: 0 0 10px rgba(255, 180, 50, 0.3); }")

# 6. 节点配色改成暖色
c = c.replace("const constellationColors = {\n  '第一章': '#7ab8ff',\n  '第二章': '#98ff98',\n  '第三章': '#ffd700',\n  '第四章': '#ff6b9d',\n  '初中衔接': '#c084fc'\n};",
"""const constellationColors = {
  '第一章': '#ff9a3c',
  '第二章': '#ffcc33',
  '第三章': '#ff6b6b',
  '第四章': '#ff8fab',
  '初中衔接': '#c084fc'
};""")

# 7. 深色主题配色改成浅色
c = c.replace("""const KG_DARK = {
  nodeDimColor: '#5a628a',
  nodeLabel: '#ffffff',
  nodeDimLabel: '#aab2d8',
  linkOn: 'rgba(255, 255, 255, 0.55)',
  linkOff: 'rgba(160, 170, 220, 0.18)',
  emLine: '#ffffff',
  defColor: '#c9a3ff',
  succBg: 'rgba(100,200,150,0.2)',
  succText: '#98ff98',
  empty: '#666',
  loading: '#888'
};""",
"""const KG_DARK = {
  nodeDimColor: '#d4c5a0',
  nodeLabel: '#5a3e00',
  nodeDimLabel: '#b09a6a',
  linkOn: 'rgba(255, 150, 50, 0.6)',
  linkOff: 'rgba(180, 150, 100, 0.2)',
  emLine: '#ff9a3c',
  defColor: '#ffb347',
  succBg: 'rgba(100,200,150,0.2)',
  succText: '#2d8a4e',
  empty: '#999',
  loading: '#888'
};""")

# 8. 信息面板改成暖色
c = c.replace("background: rgba(15, 15, 50, 0.9);",
              "background: rgba(255, 248, 230, 0.95);")
c = c.replace("box-shadow: 0 4px 30px rgba(0, 0, 100, 0.5);",
              "box-shadow: 0 4px 30px rgba(200, 150, 50, 0.3);")
c = c.replace("border: 1px solid rgba(100, 150, 255, 0.3);",
              "border: 1px solid rgba(200, 150, 50, 0.3);")
c = c.replace(".info-panel h3 { font-size: 16px; margin-bottom: 12px; color: #fff; text-shadow: 0 0 10px rgba(100, 150, 255, 0.5); }",
              ".info-panel h3 { font-size: 16px; margin-bottom: 12px; color: #8b5a00; text-shadow: 0 0 10px rgba(255, 180, 50, 0.3); }")
c = c.replace(".info-panel .prereq-item { \n    padding: 6px 8px; \n    background: rgba(30, 30, 80, 0.6); \n    border-radius: 6px; \n    margin: 4px 0; \n    font-size: 13px; \n    color: #7ab8ff; \n    cursor: pointer; \n    transition: all 0.2s;\n  }",
              ".info-panel .prereq-item { \n    padding: 6px 8px; \n    background: rgba(255, 220, 150, 0.4); \n    border-radius: 6px; \n    margin: 4px 0; \n    font-size: 13px; \n    color: #8b5a00; \n    cursor: pointer; \n    transition: all 0.2s;\n  }")
c = c.replace(".info-panel .prereq-item:hover { background: rgba(50, 50, 120, 0.8); box-shadow: 0 0 10px rgba(100, 150, 255, 0.3); }",
              ".info-panel .prereq-item:hover { background: rgba(255, 200, 100, 0.6); box-shadow: 0 0 10px rgba(255, 180, 50, 0.3); }")
c = c.replace(".info-panel .close { position: absolute; top: 8px; right: 12px; cursor: pointer; color: #888; font-size: 18px; }",
              ".info-panel .close { position: absolute; top: 8px; right: 12px; cursor: pointer; color: #999; font-size: 18px; }")
c = c.replace("background: linear-gradient(135deg, #667eea, #764ba2);",
              "background: linear-gradient(135deg, #ffb347, #ff8c42);")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('阳光照耀风格完成')
