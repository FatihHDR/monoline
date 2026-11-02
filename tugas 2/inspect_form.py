from bs4 import BeautifulSoup

with open('search_page_dom.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

forms = soup.find_all('form')
print(f"Total forms: {len(forms)}")
for idx, form in enumerate(forms):
    print(f"\n--- Form {idx+1} ---")
    print("Action:", form.get('action'))
    print("Method:", form.get('method'))
    for inp in form.find_all(['input', 'select']):
        name = inp.get('name')
        inp_id = inp.get('id')
        val = inp.get('value')
        print(f"Field: name={name}, id={inp_id}, val={val}")
        if inp.name == 'select':
            options = inp.find_all('option')
            print(f"  Options count: {len(options)}")
            for opt in options[:10]:
                print(f"    value='{opt.get('value')}', text='{opt.get_text(strip=True)}'")
