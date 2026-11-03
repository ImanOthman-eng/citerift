import sys
d,a,b=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
t=open(f'../packets/{d}/source.wikitext',encoding='utf-8').read()
print(t[a:b])
