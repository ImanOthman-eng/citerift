import sys,re
from lxml import html
h=html.parse(sys.argv[1]).getroot()
for s in h.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
    print('SUP',s.get('id'),(s.get('data-mw') or '')[:160].replace('\n',' '))
for l in h.xpath('//li[starts-with(@id,"cite_note")]'):
    print('LI',l.get('id'),' '.join(l.text_content().split())[:200])
