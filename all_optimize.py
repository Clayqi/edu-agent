with open('D:/edu-agent/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 卡片描述2行截断，统一高度
content = content.replace('.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.5;text-align:left;opacity:0.8}',
'.skill-card .sc-desc{font-size:13px;color:var(--ink-600);line-height:1.5;text-align:left;opacity:0.8;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:39px}')

# 2. 字母前缀胶囊样式
content = content.replace('.skill-card .sc-ico{width:32px;height:32px;border-radius:6px;background:var(--bg-soft);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:var(--ink-700);flex:none}',
'.skill-card .sc-ico{width:32px;height:32px;border-radius:6px;background:var(--ink-900);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600;color:#fff;flex:none}')

# 3. 卡片布局
content = content.replace('.skill-card .sc-head{display:flex;align-items:center;gap:10px;margin-bottom:8px}',
'.skill-card .sc-head{display:flex;align-items:center;gap:10px;margin-bottom:8px;min-height:32px}')

# 4. 滚动条美化
old_style = 'body{font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink-900);overflow:hidden}'
new_style = '''body{font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink-900);overflow:hidden}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#999}'''
content = content.replace(old_style, new_style)

# 5. 计数数字胶囊
content = content.replace('.proj .cnt{font-size:11px;color:var(--ink-400);font-variant-numeric:tabular-nums}',
'.proj .cnt{font-size:11px;color:var(--ink-500);background:var(--bg-soft);padding:1px 6px;border-radius:10px;font-variant-numeric:tabular-nums}')

# 6. 分段控件hover
content = content.replace('.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:7px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}',
'.role-seg button{flex:1;border:none;background:transparent;height:20px;border-radius:6px;font-size:9px;color:var(--ink-600);transition:all .2s;display:flex;align-items:center;justify-content:center;line-height:1;white-space:nowrap;overflow:visible;letter-spacing:0;padding:0 2px}')

# 7. 标签hover
content = content.replace('.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer;margin-right:8px}',
'.drop-pill{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 14px;border:none;border-radius:20px;background:var(--bg-soft);font-size:13px;color:var(--ink-700);transition:all 0.2s;cursor:pointer;margin-right:8px} .drop-pill:hover{background:var(--line)}')

with open('D:/edu-agent/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('全部高优先级优化执行完成')
