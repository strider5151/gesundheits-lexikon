#!/usr/bin/env python3
"""Schritt 3: Wendet die manuellen Korrekturen (korrekturen_nach_key.json) auf eintraege.json an -> eintraege_final.json.

Code-Bedeutung (Wert in korrekturen_nach_key.json):
  X = Eintrag weglassen (privat, Werbung, kaputt, themenfremd)
  sonst = Hauptkategorie setzen (siehe CODES)
"""
import json, sys
from pfade import DATEN

CODES = {
    'A': ('health', 'allgemein'), 'B': ('health', 'beziehung'), 'D': ('health', 'darm'), 'E': ('health', 'persoenlichkeit'),
    'G': ('health', 'gewicht'), 'K': ('health', 'koerper'), 'L': ('health', 'schlaf'), 'M': ('health', 'bewegung'),
    'N': ('health', 'ernaehrung'), 'P': ('health', 'psyche'), 'S': ('health', 'psychosomatik'), 'V': ('health', 'vitamine'),
    'n1': ('numer', 'numerologie'), 'n2': ('numer', 'astrologie'),
    's1': ('spirit', 'spirit_energie'), 's2': ('spirit', 'spirit_bewusstsein'), 's3': ('spirit', 'spirit_weisheit'),
}

def anwenden(eintraege, korr, kat_bereich):
    out = []
    for e in eintraege:
        code = korr.get(e['key'])
        if code == 'X':
            continue
        if code:
            area, cat = CODES[code]
            rest = [c for c in e['cats'] if c != cat and kat_bereich.get(c) == area]
            e = dict(e, area=area, cats=[cat] + rest[:1])
        out.append(e)
    return out

if __name__ == '__main__':
    import klassifizieren as k
    kat_bereich = {c[0]: c[1] for c in k.KAT}; kat_bereich['allgemein'] = 'health'
    eintraege = json.load(open(DATEN / 'eintraege.json', encoding='utf-8'))
    korr = json.load(open(DATEN / 'korrekturen_nach_key.json', encoding='utf-8'))
    out = anwenden(eintraege, korr, kat_bereich)
    json.dump(out, open(DATEN / 'eintraege_final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(len(eintraege), '->', len(out), 'Einträge')
