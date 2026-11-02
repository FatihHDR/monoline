from bs4 import BeautifulSoup

with open('download_page.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

print("Title:", soup.title.string if soup.title else "None")

# Check forms, buttons, links
forms = soup.find_all('form')
print("Forms:", len(forms))
for f in forms:
    print("Form action:", f.get('action'), "method:", f.get('method'))
    for inp in f.find_all(['input', 'button', 'select']):
        print("  Input:", inp.get('name'), inp.get('id'), inp.get('type'), inp.get('value'))

# Check links
for a in soup.find_all('a', href=True):
    txt = a.get_text(strip=True)
    href = a['href']
    if any(w in txt.lower() or w in href.lower() for w in ['download', 'unduh', 'pdf', 'zip', 'klik']):
        print(f"Link: '{txt}' -> {href}")

# Check any script or text mentioning robot/captcha
for s in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'div']):
    t = s.get_text(strip=True)
    if any(w in t.lower() for w in ['captcha', 'robot', 'centang', 'keamanan', 'download']):
        if len(t) < 150:
            print("Notice:", t)
