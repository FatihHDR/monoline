import re

with open('detail_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('icon-files')
if pos != -1:
    print(text[pos-200:pos+800])
else:
    print("icon-files not found")
