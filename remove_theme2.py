with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到主题按钮删掉
import re
content = re.sub(r'<button class="sb-btn"[^>]*id="themeToggleBtn"[^>]*>.*?</button>', '', content, flags=re.DOTALL)

# 删掉toggleThemeSimple函数和初始化
content = re.sub(r'<script>\s*function toggleThemeSimple.*?</script>', '', content, flags=re.DOTALL)

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('日夜模式及按钮已删除')
