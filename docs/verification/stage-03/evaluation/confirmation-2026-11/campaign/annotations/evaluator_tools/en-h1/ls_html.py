import sys, lxml.html, json
p=sys.argv[1]
d=lxml.html.parse(p).getroot()
for s in d.xpath('//sup[contains(@typeof,"mw:Extension/ref")]'):
    dm=s.get('data-mw','')
    print('SUP',s.get('id'),dm[:230].replace('\n',' '))
for l in d.xpath('//li[starts-with(@id,"cite_note")]'):
    print('LI',l.get('id'),' '.join(l.text_content().split())[:260])
