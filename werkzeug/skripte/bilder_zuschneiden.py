#!/usr/bin/env python3
"""Schneidet Instagram-/App-Rahmen (Kopfzeile, Likes, Bildunterschrift) von Bildschirmfotos ab.

Schritt 1:  python bilder_zuschneiden.py
            -> sucht in allen noch nicht zugeschnittenen Bildern den eigentlichen Beitrag
            -> privat/zuschnitt_vorschau.jpg (rot = Vorschlag, darunter Ergebnis, mit Nummern)
Schritt 2:  Vorschau ansehen (am besten mit Claude), dann z. B.
            python bilder_zuschneiden.py --anwenden 2 3 4 7
            -> überschreibt bilder/<id>.jpg und thumbs/<id>.jpg, merkt sich die IDs in daten/zugeschnitten.json
Die Originale bleiben in der Git-Historie erhalten.
"""
import json, sys, numpy as np
from PIL import Image, ImageDraw
from pfade import SEITE, DATEN, PRIVAT
MED = PRIVAT / 'offline_medien'   # Bilder liegen seit 08.11.2026 nur noch privat

RATIOS = [1.0, 1.25, 4/3, 1.5, 0.75, 0.5625, 1.777]   # Höhe/Breite des Beitrags

def kante(a):
    # a: H x W x 3 float. Anteil der Spalten, die sich zwischen Zeile y-2 und y+2 deutlich ändern
    d = np.abs(a[4:] - a[:-4]).max(axis=2)          # (H-4) x W
    return np.concatenate([np.zeros(2), (d > 38).mean(axis=1), np.zeros(2)])

def gleichfoermig(a, y0, y1):
    """Anteil der Zeilen zwischen y0..y1, die (bis auf Text/Icons) einfarbig sind"""
    if y1 - y0 < 4: return 1.0
    blk = a[y0:y1]
    med = np.median(blk.reshape(-1, 3), axis=0)
    return float((np.abs(blk - med).max(axis=2) < 30).mean())

def finde(path):
    im = Image.open(path).convert('RGB'); W0, H0 = im.size
    if H0 / W0 < 1.6: return None
    sc = 400 / W0; im = im.resize((400, round(H0 * sc))); a = np.asarray(im).astype(np.float32); H, W = a.shape[:2]
    k = kante(a)
    best = None
    for y0 in range(int(H * 0.04), int(H * 0.5)):
        if k[y0] < 0.55: continue
        for r in RATIOS:
            h = W * r
            for y1 in range(int(y0 + h * 0.97), min(H - 1, int(y0 + h * 1.03)) + 1):
                if y1 >= H - 2 or k[y1] < 0.55: continue
                over = gleichfoermig(a, max(0, y0 - 30), y0 - 2)
                under = gleichfoermig(a, y1 + 2, min(H, y1 + 30))
                if over < 0.75 or under < 0.75: continue
                score = k[y0] + k[y1] + over + under
                if not best or score > best[0]: best = (score, y0, y1, r)
    if not best: return None
    _, y0, y1, r = best
    if (y1 - y0) / H > 0.93: return None
    return [0, round(y0 / sc), W0, round(y1 / sc), round(r, 3)]


def daten():
    d = (SEITE / 'data.js').read_text(encoding='utf-8')
    return json.loads(d[len('window.LEX='):-1])['entries']

def main():
    fertig_p = DATEN / 'zugeschnitten.json'
    fertig = set(json.load(open(fertig_p))) if fertig_p.exists() else set()
    boxen_p = PRIVAT / 'zuschnitt_boxen.json'
    by = {e['id']: e for e in daten()}
    if '--anwenden' in sys.argv:
        boxen = json.load(open(boxen_p))
        nr = [int(x) for x in sys.argv[sys.argv.index('--anwenden') + 1:]]
        for i in nr:
            id_, (x0, y0, x1, y1, r) = boxen[i]
            e = by[id_]
            c = Image.open(MED / e['big']).convert('RGB').crop((x0, y0, x1, y1))
            c.save(MED / e['big'], quality=85, optimize=True, progressive=True)
            t = c.copy(); t.thumbnail((480, 480)); t.save(MED / e['im'], quality=72, optimize=True, progressive=True)
            fertig.add(id_)
        json.dump(sorted(fertig), open(fertig_p, 'w'))
        print(len(nr), 'Bilder zugeschnitten')
        return
    boxen = []
    for e in by.values():
        if e['t'] != 'image' or e['id'] in fertig: continue
        b = finde(MED / e['big'])
        if b: boxen.append([e['id'], b])
    json.dump(boxen, open(boxen_p, 'w'))
    W, H = 110, 220
    sheet = Image.new('RGB', (12 * W, max(1, (len(boxen) + 11) // 12) * 2 * H), 'white'); d = ImageDraw.Draw(sheet)
    for i, (id_, (x0, y0, x1, y1, r)) in enumerate(boxen):
        im = Image.open(MED / by[id_]['big']).convert('RGB'); o = im.copy(); o.thumbnail((W - 6, H - 6)); s = o.size[0] / im.size[0]
        cx, cy = (i % 12) * W, (i // 12) * 2 * H
        sheet.paste(o, (cx + 3, cy + 3)); d.rectangle([cx + 3, cy + 3 + y0 * s, cx + 2 + o.size[0], cy + 3 + y1 * s], outline=(255, 0, 0), width=2)
        c = im.crop((x0, y0, x1, y1)); c.thumbnail((W - 6, H - 6)); sheet.paste(c, (cx + 3, cy + H + 3))
        d.text((cx + 4, cy + H - 14), str(i), fill=(200, 0, 0))
    sheet.save(PRIVAT / 'zuschnitt_vorschau.jpg', quality=80)
    print(len(boxen), 'Vorschläge -> privat/zuschnitt_vorschau.jpg')

if __name__ == '__main__':
    main()
