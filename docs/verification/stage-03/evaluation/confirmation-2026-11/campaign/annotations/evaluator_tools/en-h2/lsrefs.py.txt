import sys, re
from lxml import html
d=sys.argv[1]
t=open(f'packets/{d}/render.html',encoding='utf-8').read()
doc=html.fromstring(t)
for s in doc.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
    dm=s.get('data-mw') or ''
    print('SUP',s.get('id'),dm[:110].replace('\n',' '))
for li in doc.xpath('//li[starts-with(@id,"cite_note")]'):
    print('LI',li.get('id'),' '.join(li.text_content().split())[:130])
