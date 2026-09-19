with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 在教育能力分组里加知识图谱菜单项
old = '''        <button class="snav" data-view="library" data-ro="teacher">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13z"/></svg>
          教材库
        </button>'''

new = '''        <button class="snav" data-view="library" data-ro="teacher">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13z"/></svg>
          教材库
        </button>
        <button class="snav" data-view="kg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>
          知识星图
        </button>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('左侧知识星图菜单项已加回')
