with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 去掉绿色对勾
import re
# 删掉check-orb的HTML
content = re.sub(r"'<span class=\"check-orb\">'\+checkSvg\+'</span>'\+", "''", content)
# 删掉check-orb的CSS
content = re.sub(r'\.check-orb\{[^}]+\}', '', content)
content = re.sub(r'\.check-orb svg\{[^}]+\}', '', content)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('绿色对勾已删除')
