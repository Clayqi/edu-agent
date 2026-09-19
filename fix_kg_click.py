with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 把左侧知识星图按钮改成内联onclick
old = '''<button class="snav" data-view="kg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>
          知识星图
        </button>'''

new = '''<button class="snav" onclick="switchView('kg')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M8 7l3 9M16 7l-3 9M9 6h6"/></svg>
          知识星图
        </button>'''

content = content.replace(old, new)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('按钮改成内联onclick了')
