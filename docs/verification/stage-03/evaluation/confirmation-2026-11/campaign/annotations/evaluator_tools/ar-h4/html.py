import sys
from lxml import html
d=sys.argv[1]
doc=html.parse(f'packets/{d}/render.html').getroot()
for s in doc.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
    print('SUP',s.get('id'),s.get('data-mw','')[:int(sys.argv[2]) if len(sys.argv)>2 else 200])
for l in doc.xpath('//li[starts-with(@id,"cite_note")]'):
    print('LI',l.get('id'),' '.join(l.text_content().split())[:int(sys.argv[3]) if len(sys.argv)>3 else 120])
