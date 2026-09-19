with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 只删HTML里的绿色对勾span，不动其他
old = """          '<span class="check-orb">'+checkSvg+'</span>'+"""
new = """"""

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('只删了绿色对勾，卡片文字保留')
