with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复skill-card样式，用CSS变量，适配深色模式
old_card = '.skill-card{position:relative;background:#fff;border:.5px solid var(--line);border-radius:var(--r-md);padding:16px;cursor:pointer;text-align:left;transition:all .2s ease}'
new_card = '.skill-card{position:relative;background:var(--bg-soft);border:.5px solid var(--line);border-radius:var(--r-md);padding:14px 16px;cursor:pointer;text-align:left;transition:all .2s ease}'

content = content.replace(old_card, new_card)

# 2. 卡片描述文字调小
old_desc = '.skill-card .sc-desc{font-size:12.5px;color:var(--ink-500);margin-top:10px;line-height:1.55;text-align:left}'
new_desc = '.skill-card .sc-desc{font-size:12px;color:var(--ink-500);margin-top:8px;line-height:1.5;text-align:left}'

content = content.replace(old_desc, new_desc)

# 3. 卡片标题调小
old_title = '.skill-card .sc-title{font-size:14px;font-weight:600;text-align:left;line-height:1.3}'
new_title = '.skill-card .sc-title{font-size:13.5px;font-weight:600;text-align:left;line-height:1.3}'

content = content.replace(old_title, new_title)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('卡片样式优化完成')
