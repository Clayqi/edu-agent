with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <!-- ===== Sidebar ===== -->
    <aside class="sidebar">
      <div class="side-actions" style="padding-top:12px">'''

new = '''    <!-- ===== Sidebar ===== -->
    <aside class="sidebar">
      <div class="side-brand">
        <div class="name">教育 Agent</div>
        <div class="ver">v1.4.0</div>
      </div>
      <div class="side-actions">'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('教育 Agent v1.4.0 已放回')
