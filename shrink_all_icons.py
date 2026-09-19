with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 左侧导航图标缩小
content = content.replace('.snav svg{width:16px;height:16px}', '.snav svg{width:15px;height:15px}')

# 新建任务图标
content = content.replace('.newtask svg{width:15px;height:15px}', '.newtask svg{width:14px;height:14px}')

# 底部按钮图标
content = content.replace('.sb-btn svg{width:17px;height:17px}', '.sb-btn svg{width:15px;height:15px}')

# 顶部工具栏按钮图标
content = content.replace('.wctl svg{width:16px;height:16px}', '.wctl svg{width:15px;height:15px}')

# 右侧面板图标再缩小
content = content.replace('.sp-ico{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:500}',
'.sp-ico{width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:500}')

# 项目折叠图标
content = content.replace('.proj .caret{width:12px;height:12px;flex:none;color:var(--ink-400);transition:transform .15s}',
'.proj .caret{width:11px;height:11px;flex:none;color:var(--ink-400);transition:transform .15s}')
content = content.replace('.proj .fold{width:15px;height:15px;color:var(--ink-500)}',
'.proj .fold{width:14px;height:14px;color:var(--ink-500)}')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全部图标缩小完成')
