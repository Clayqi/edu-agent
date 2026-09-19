with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 在</style>前加一段全局强制覆盖样式
old_style = '''body{transition:background 0.3s, color 0.3s}'''
new_style = '''body{transition:background 0.3s, color 0.3s}

/* 强制主题生效 */
html, body, .shell, .main, .scroll, .view, .sidepanel, .main-head, .side-brand, .side-nav, .side-bottom {
  background-color: var(--bg) !important;
  color: var(--ink-900) !important;
}
.sidebar {
  background-color: var(--bg-soft) !important;
}
.skill-card, .view-sec, .card {
  background-color: var(--bg) !important;
  color: var(--ink-900) !important;
}
button, .sb-btn, .wctl, .snav, .newtask, .proj, .proj-leaf, .sm-item, .pill-btn {
  color: var(--ink-700) !important;
}
.mh-spacer, .line, .divider, hr {
  background-color: var(--line) !important;
}'''

content = content.replace(old_style, new_style)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全局强制主题样式已加')
