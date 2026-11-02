from bs4 import BeautifulSoup
import re

with open('detail_page.html', 'r', encoding='utf-8') as f:
    text = f.read()
    soup = BeautifulSoup(text, 'html.parser')

print("Mentions in raw text:")
for word in ['pdf', 'download', 'unduh', 'lampiran', 'salinan', 'berkas', 'file']:
    matches = len(re.findall(re.escape(word), text, re.IGNORECASE))
    print(f"  {word}: {matches}")

# Let's find context around 'pdf'
for m in re.finditer(r'pdf', text, re.IGNORECASE):
    start = max(0, m.start() - 100)
    end = min(len(text), m.end() + 100)
    print("--- Context ---")
    print(text[start:end])

# Check all iframes, embeds, objects, scripts
for tag in soup.find_all(['iframe', 'embed', 'object']):
    print("Tag:", tag)
