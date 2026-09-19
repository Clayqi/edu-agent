with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 调整kg视图的样式，确保全屏铺满内容区
old_view = '''        <div class="view" id="view-kg" style="padding:0;overflow:hidden">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none"></iframe>
        </div>'''

new_view = '''        <div class="view" id="view-kg" style="padding:0;overflow:hidden;height:100%">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none;display:block"></iframe>
        </div>'''

content = content.replace(old_view, new_view)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('kg视图全屏样式已调整')
