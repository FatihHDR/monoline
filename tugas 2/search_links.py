from bs4 import BeautifulSoup

with open('direktori_dom.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print("All links containing pengadilan, jakarta, or pidana:")
for a in soup.find_all('a', href=True):
    txt = a.get_text(strip=True).lower()
    href = a['href'].lower()
    if 'pengadilan' in txt or 'pengadilan' in href or 'jakarta' in txt or 'jakarta' in href or 'pidana' in txt or 'narkotika' in txt:
        print(f"{a.get_text(strip=True)} -> {a['href']}")
