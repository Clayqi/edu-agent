with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <div class="wtab active"><span class="win-dot"><span>▤</span></span>主界面</div>
    <div class="wtab"><span class="win-dot"><span>◇</span></span>UnderstandAnything</div>
    <div class="wtab">Yan Work GUI</div>
    <div class="titlebar-spacer"></div>'''

new = '''    <div class="wtab active"><span class="win-dot"><span>▤</span></span>主界面</div>
    <div class="titlebar-spacer"></div>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('顶部多余标签页已删除')
