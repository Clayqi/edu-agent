with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        <div class="view" id="view-library">
          <div id="libBody" style="padding:20px 28px;max-width:920px"></div>
        </div>

        <!-- ===== Lesson / course (student) ===== -->'''

new = '''        <div class="view" id="view-library">
          <div id="libBody" style="padding:20px 28px;max-width:920px"></div>
        </div>

        <!-- 知识星图视图 -->
        <div class="view" id="view-kg" style="padding:0;overflow:hidden;width:100%;height:100%">
          <iframe src="/kg.html" style="width:100%;height:100%;border:none;display:block"></iframe>
        </div>

        <!-- ===== Lesson / course (student) ===== -->'''

content = content.replace(old, new)

# 确认views数组里有kg
if "'kg'" not in content:
    old_views = "var views = ['market','skill','chat','library','lesson','question','services'];"
    new_views = "var views = ['market','skill','chat','library','kg','lesson','question','services'];"
    content = content.replace(old_views, new_views)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('view-kg容器已加回')
