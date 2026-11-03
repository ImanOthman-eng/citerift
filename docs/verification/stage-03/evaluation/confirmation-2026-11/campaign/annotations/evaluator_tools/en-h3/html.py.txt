import sys
from lxml import html
d=sys.argv[1]
doc=html.parse(f'packets/{d}/render.html').getroot()
print("SUPS")
for s in doc.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
    print(s.get('id'),'|',(s.get('data-mw') or '')[:110].replace('\n',' '),'|',s.text_content())
print("LIS")
for l in doc.xpath('//li[starts-with(@id,"cite_note")]'):
    print(l.get('id'),'|',' '.join(l.text_content().split())[:230])
