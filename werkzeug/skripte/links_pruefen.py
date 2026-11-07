#!/usr/bin/env python3
"""Prüft alle Links im Lexikon und merkt sich tote in daten/tote_links.json.
seite_bauen.py lässt diese Einträge dann weg. Nur Python-Standardbibliothek nötig.

Als tot gilt nur, was eindeutig weg ist:
  YouTube: Video gelöscht, privat oder gesperrt
  Webseiten: 404/410 oder Domain existiert nicht mehr
Zeitüberschreitungen, 403, 429 oder Serverfehler zählen NICHT als tot (viele Seiten blocken Programme).

Aufruf:  python links_pruefen.py           (alle prüfen)
         python links_pruefen.py --nur-yt  (nur YouTube)
"""
import json, re, socket, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pfade import DATEN

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
HDR = {'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9', 'Cookie': 'SOCS=CAI; CONSENT=YES+'}

def hole(url, timeout=20):
    req = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(600_000).decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.gaierror): return 'dns', ''
        return 'netz', ''
    except Exception:
        return 'netz', ''

def pruefe_yt(vid):
    st, _ = hole(f'https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v={vid}')
    if st == 200: return None
    if st in (400, 404): return 'YouTube: Video existiert nicht mehr'
    if st == 401 or st == 403:          # privat ODER Einbetten verboten – Seite ansehen
        st2, html = hole(f'https://www.youtube.com/watch?v={vid}&hl=de')
        m = re.search(r'"playabilityStatus":\{"status":"(\w+)"', html)
        if m and m.group(1) in ('ERROR', 'LOGIN_REQUIRED', 'UNPLAYABLE'):
            if m.group(1) == 'LOGIN_REQUIRED' and re.search(r'Altersbeschränkung|age-restricted|confirm your age', html, re.I):
                return None                   # nur altersbeschränkt – bleibt drin
            return f'YouTube: {m.group(1).lower()}'
    return None

def pruefe_web(url):
    st, _ = hole(url)
    if st in (404, 410): return f'Webseite: {st}'
    if st == 'dns': return 'Webseite: Domain existiert nicht mehr'
    return None

def main():
    nur_yt = '--nur-yt' in sys.argv
    eintraege = json.load(open(DATEN / 'eintraege_final.json', encoding='utf-8'))
    pfad = DATEN / 'tote_links.json'
    tot = json.load(open(pfad, encoding='utf-8')) if pfad.exists() else {}
    jobs = []
    for e in eintraege:
        k = e['key']
        if k.startswith('yt:'): jobs.append((k, lambda v=k[3:]: pruefe_yt(v)))
        elif not nur_yt and e['kind'] == 'web': jobs.append((k, lambda u=e['url']: pruefe_web(u)))
    print(f'Prüfe {len(jobs)} Links …')
    neu_tot, wieder_da, n = 0, 0, 0
    def lauf(job):
        k, f = job; time.sleep(0.2); return k, f()
    with ThreadPoolExecutor(6) as ex:
        for k, grund in ex.map(lauf, jobs):
            n += 1
            if grund:
                if k not in tot: neu_tot += 1
                tot[k] = {'grund': grund, 'geprueft': date.today().isoformat()}
            elif k in tot:
                del tot[k]; wieder_da += 1
            if n % 100 == 0: print(f'  {n}/{len(jobs)} geprüft, bisher {len(tot)} tot')
    json.dump(tot, open(pfad, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Fertig: {len(tot)} tote Links ({neu_tot} neu, {wieder_da} wieder erreichbar) -> {pfad.name}')
    print('Danach: python seite_bauen.py')

if __name__ == '__main__':
    main()
