#!/usr/bin/env python3
"""Schritt 4: Baut aus eintraege_final.json das Datenpaket der Seite (data.js).

Seit 08.11.2026 werden Bilder, Vorschaubilder und Transkripte aus rechtlichen Gründen NICHT mehr veröffentlicht.
Sie landen in werkzeug/privat/offline_medien/ (thumbs/, transkripte/, bilder/) – nur für private Zwecke.
data.js behält die Pfade (im, big, tr), damit gespeicherte Offline-Versionen auf den Handys weiter funktionieren."""
import json, os, re, shutil
from datetime import date, datetime
from PIL import Image
from pfade import PRIVAT, DATEN, SEITE
import klassifizieren as k

SRC = str(PRIVAT)      # entpackte Sammler-ZIP (thumbs/, transkripte/) – fehlt etwas, wird das Vorhandene der Seite weiterverwendet
OUT = str(SEITE)
MED = str(PRIVAT / 'offline_medien')   # nicht öffentlich
for _d in ('thumbs', 'transkripte', 'bilder'): os.makedirs(f'{MED}/{_d}', exist_ok=True)


o = json.load(open(DATEN / 'eintraege_final.json', encoding='utf-8'))
tot = json.load(open(DATEN / 'tote_links.json', encoding='utf-8')) if (DATEN / 'tote_links.json').exists() else {}
if tot:
    vorher = len(o); o = [e for e in o if e['key'] not in tot]; print(vorher - len(o), 'tote Links weggelassen (siehe daten/tote_links.json)')
bad = re.compile(r'(\+?\d[\d /-]{6,}\d|telefon|tel\.|termin|whatsapp|e-?mail|kontaktier|buchen|gutschein|link in|beschreibung|abonn|newsletter|'
                 r'kostenlos(e|en)? (webinar|erstgespräch|gespräch|ebook|guide)|jetzt (anmelden|sichern|kaufen)|rabatt|code:?\s|sparen mit|%)', re.I)

def clean_desc(d):
    if not d: return None
    parts = re.split(r'(?<=[.!?…])\s+', d)
    nd = ' '.join(x for x in parts if not bad.search(x)).strip()
    nd = re.sub(r'[\U0001F300-\U0001FAFF☀-➿]+', '', nd).strip()
    return nd if len(nd) >= 25 else None

ents = []
for e in o:
    eid = e['id']
    # Vorschaubild
    im = None
    t = e.get('thumbnail') or e.get('thumb')
    tp = f'{SRC}/{t}' if t else None
    dst = f'{MED}/thumbs/{eid}.jpg'
    if os.path.exists(dst):
        im = f'thumbs/{eid}.jpg'
    elif tp and os.path.exists(tp):
        try:
            x = Image.open(tp).convert('RGB')
            if e['kind'] == 'youtube' and abs(x.size[0] / x.size[1] - 4 / 3) < 0.02 and not e.get('short'):
                w, h = x.size; ch = int(w * 9 / 16); top = (h - ch) // 2; x = x.crop((0, top, w, top + ch))
            x.thumbnail((480, 480)); x.save(dst, quality=72, optimize=True, progressive=True); im = f'thumbs/{eid}.jpg'
        except Exception:
            pass
    # Transkript
    tr = False; snip = ''
    trp = f"{SRC}/{e['transkript']}" if e.get('transkript') else None
    if trp and os.path.exists(trp):
        z = json.load(open(trp, encoding='utf-8'))
        rows = [[int(r['t']), r['text']] for r in z if r.get('text')]
        if rows:
            open(f'{MED}/transkripte/{eid}.js', 'w', encoding='utf-8').write(
                'LEX_T(' + json.dumps(eid) + ',' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ');')
            tr = True; snip = ' '.join(r[1] for r in rows)[:600]
    elif os.path.exists(f'{MED}/transkripte/{eid}.js'):
        js = open(f'{MED}/transkripte/{eid}.js', encoding='utf-8').read()
        rows = json.JSONDecoder().raw_decode(js, js.index(',') + 1)[0]   # LEX_T("id",[[t,"text"],...])
        tr = True; snip = ' '.join(r[1] for r in rows)[:600]
    kp = [[c['t'], c['titel']] for c in (e.get('kapitel') or []) if c.get('titel') and not re.match(r'<?untitled chapter', c['titel'], re.I)]
    x = {'id': eid, 't': e['typ'], 'a': e['area'], 'c': e['cats'], 'ti': e['titel'], 'd': clean_desc(e.get('beschreibung')),
         'u': e['url'], 'do': e['domain'], 'ch': e.get('kanal'), 'du': e.get('dauer'), 'l': e.get('lang'), 'im': im, 'tr': tr,
         'kp': kp if len(kp) >= 2 else None, 'dt': e.get('datum'), 'g': e.get('chats'), 'n': e.get('n', 1),
         'tg': [t for t in (e.get('yt_tags') or []) if len(t) < 30][:8], 'k': e['kind']}
    if e['kind'] == 'youtube':
        x['yt'] = e['key'].split(':', 1)[1]
    if e.get('short'): x['sh'] = True
    ents.append({kk: v for kk, v in x.items() if v not in (None, [], '', False) or kk == 'tr'})

# Bilder (bereits verarbeitet im ersten Durchlauf)
imgs = json.load(open(DATEN / 'bilder_eintraege.json', encoding='utf-8'))
for b in imgs:
    for f in (b['im'], b['big']):
        if not os.path.exists(f'{MED}/{f}'):
            print('Bild fehlt (nur privat relevant):', f)
ents += imgs

cats = [{'id': c[0], 'area': c[1], 'de': c[2]} for c in k.KAT] + [{'id': 'allgemein', 'area': 'health', 'de': 'Allgemeines'}]
data = {'stand': date.today().strftime('%d.%m.%Y'), 'entries': ents, 'cats': cats}
open(f'{OUT}/data.js', 'w', encoding='utf-8').write('window.LEX=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';')
# Version hochzählen, damit Handys und App (Service Worker) die neuen Daten laden
ver = datetime.now().strftime('%Y%m%d%H%M')
for f in ('index.html', 'sw.js'):
    p = SEITE / f
    if p.exists():
        p.write_text(re.sub(r'((?:data|hilfe)\.js\?v=)[\w.-]+', lambda m: m.group(1) + ver, p.read_text(encoding='utf-8')), encoding='utf-8')
print(len(ents), 'Einträge;', sum(1 for e in ents if e.get('tr')), 'Transkripte')
