with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <!-- ===== Sidebar ===== -->
    <aside class="sidebar">
      <div class="side-brand">
        <div class="name">教育 Agent</div>
        <div class="ver">v1.4.0</div>
      </div>
      <div class="side-actions">'''

new = '''    <!-- ===== Sidebar ===== -->
    <aside class="sidebar">
      <div class="side-actions" style="padding-top:12px">'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('左上角标题已删除')
