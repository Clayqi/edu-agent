with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 删掉主题切换按钮
import re
content = re.sub(r'<button class="sb-btn" id="themeToggleBtn".*?</button>', '', content, flags=re.DOTALL)

# 删掉主题切换JS和强制样式
content = re.sub(r'<script>\s*function toggleThemeSimple.*?</script>', '', content, flags=re.DOTALL)
content = re.sub(r'<style>\s*/\* 日夜模式强制覆盖 \*/.*?</style>', '', content, flags=re.DOTALL)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('日夜模式及按钮已删除')
