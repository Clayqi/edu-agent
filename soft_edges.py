with open('D:/edu-agent/static/kg.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 线更软，弯曲度更大
content = content.replace("smooth: { type: 'continuous', roundness: 0.2 }",
"smooth: { type: 'continuous', roundness: 0.5 }")

content = content.replace('const roundness = pairCount[k] > 1 ? 0.2 + i * 0.24 : 0.2;',
'const roundness = pairCount[k] > 1 ? 0.5 + i * 0.3 : 0.5;')

with open('D:/edu-agent/static/kg.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('线改软了，更弯曲')
