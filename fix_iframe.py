with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        <div class="view" id="view-kg">
          <iframe src="/kg.html" style="width:100%;height:calc(100vh - 60px);border:none;border-radius:0"></iframe>
        </div>'''

new = '''        <div class="view" id="view-kg" style="padding:0;overflow:hidden">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none"></iframe>
        </div>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('iframe样式已调整')
