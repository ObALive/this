import sys,re,html
p=sys.argv[1]
s=open(p,encoding='utf-8',errors='replace').read()
s=re.sub(r'(?is)<(script|style|head|nav)\b.*?</\1>',' ',s)
i=s.find('<div class="section">')
if i>0: s=s[i:]
j=s.find('<div class="footer-wrapper">')
if j>0: s=s[:j]
s=re.sub(r'(?is)<br\s*/?>','\n',s)
s=re.sub(r'(?is)</(p|div|li|tr|h1|h2|h3|h4|pre|table)>','\n',s)
s=re.sub(r'(?is)<(td|th)\b[^>]*>',' | ',s)
s=re.sub(r'(?s)<[^>]+>','',s)
s=html.unescape(s)
s=re.sub(r'[ \t]+',' ',s)
s=re.sub(r'\n\s*\n+','\n',s)
print(s.strip())
