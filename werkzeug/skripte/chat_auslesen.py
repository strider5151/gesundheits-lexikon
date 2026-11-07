#!/usr/bin/env python3
"""Schritt 1: Liest die zwei WhatsApp-Exporte (.txt) und sammelt alle Links -> privat/links.json
Aufruf: python chat_auslesen.py "WhatsApp-Chat mit Gesundheit.txt" "WhatsApp-Chat mit Psychologie.txt"
links.json enthält Gesprächskontext und bleibt deshalb privat (nicht ins Repo!)."""
import json, re, sys, collections
from datetime import datetime, date
from pfade import PRIVAT
rx=re.compile(r'^(\d\d\.\d\d\.\d\d), (\d\d:\d\d) - ([^:]+?): (.*)$')
URL=re.compile(r'https?://[^\s<>"\)\]]+')
def parse(p):
    msgs=[]
    for line in open(p,encoding='utf-8'):
        line=line.rstrip('\n'); m=rx.match(line)
        if m: msgs.append(dict(dt=datetime.strptime(m[1]+' '+m[2],'%d.%m.%y %H:%M'),a=m[3],x=m[4]))
        elif msgs: msgs[-1]['x']+='\n'+line
    return msgs
def clean(t): 
    t=URL.sub('',t).replace('\u200e','').strip()
    if 'Datei angehängt' in t or 'Nachricht wurde gelöscht' in t or 'hast diese Nachricht gelöscht' in t or t=='<Medien ausgeschlossen>': return ''
    return re.sub(r'\s+',' ',t)[:400]
def key(u):
    u=u.rstrip('.,;!')
    m=re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/|embed/))([A-Za-z0-9_-]{11})',u)
    if m: return 'yt:'+m[1], 'youtube', 'https://www.youtube.com/watch?v='+m[1]
    if re.search(r'youtube\.com/(playlist|@|c/|channel/|user/)',u): return 'ytx:'+u.split('&si=')[0].split('?si=')[0], 'youtube_other', u
    if 'tiktok.com' in u: return 'tt:'+u.split('?')[0], 'tiktok', u.split('?')[0]
    return 'web:'+u, 'web', u
items={}
for chat,p in [('Gesundheit',sys.argv[1]),('Psychologie',sys.argv[2])]:
    ms=parse(p)
    for i,m in enumerate(ms):
        urls=URL.findall(m['x'])
        if not urls: continue
        ctx=[clean(m['x'])]
        for n in ms[i+1:i+4]:
            if (n['dt']-m['dt']).total_seconds()>1200: break
            if URL.search(n['x']): break
            c=clean(n['x'])
            if c: ctx.append(c)
        ctx=' | '.join(c for c in ctx if c)[:700]
        for u in urls:
            k,kind,norm=key(u)
            it=items.setdefault(k,dict(key=k,kind=kind,url=norm,original_url=u.rstrip('.,;!'),chats=[],dates=[],context=[]))
            if chat not in it['chats']: it['chats'].append(chat)
            it['dates'].append(m['dt'].strftime('%Y-%m-%d'))
            if ctx and ctx not in it['context']: it['context'].append(ctx)
out=list(items.values())
for it in out: it['first_shared']=min(it['dates']); it['times_shared']=len(it['dates']); del it['dates']; it['context']=it['context'][:3]
out.sort(key=lambda x:x['first_shared'])
json.dump(dict(version=1,created=date.today().isoformat(),count=len(out),items=out),open(PRIVAT/'links.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(len(out), collections.Counter(i['kind'] for i in out))
