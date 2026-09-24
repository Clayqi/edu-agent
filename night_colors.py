p = 'D:/edu-agent/static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 改成两套配色：日间暖色，夜间黄蓝经典
old_colors = """  var constellationColors = {
    '第一章': '#ff9a3c', '第二章': '#ffcc33', '第三章': '#ff6b6b',
    '第四章': '#ff8fab', '初中衔接': '#c084fc'
  };"""

new_colors = """  var constellationColorsDay = {
    '第一章': '#ff9a3c', '第二章': '#ffcc33', '第三章': '#ff6b6b',
    '第四章': '#ff8fab', '初中衔接': '#c084fc'
  };
  var constellationColorsNight = {
    '第一章': '#7ab8ff', '第二章': '#98ff98', '第三章': '#ffd700',
    '第四章': '#ff6b9d', '初中衔接': '#c084fc'
  };
  function getConstellationColors(){
    return document.documentElement.classList.contains('dark') ? constellationColorsNight : constellationColorsDay;
  }"""

c = c.replace(old_colors, new_colors)

# 替换所有取颜色的地方
c = c.replace("var color = constellationColors[n.category] || kr.defColor;",
              "var color = (getConstellationColors())[n.category] || kr.defColor;")
c = c.replace("var color = constellationColors[n._category] || kr.defColor;",
              "var color = (getConstellationColors())[n._category] || kr.defColor;")
c = c.replace("var col = constellationColors[c] || kr.defColor;",
              "var col = (getConstellationColors())[c] || kr.defColor;")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('夜间模式节点配色改回黄蓝经典')
