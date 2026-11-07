# Werkzeug – so entsteht das Gesundheits-Lexikon

Dieser Ordner enthält alles, um die Webseite neu zu bauen oder mit neuen Inhalten aus den WhatsApp-Gruppen „Gesundheit“ und „Psychologie“ zu aktualisieren. Die Webseite selbst (`index.html`, `data.js`, `hilfe.js`, `bilder/`, `thumbs/`, `transkripte/`) liegt eine Ebene höher. Auf der Seite ist dieser Ordner nicht verlinkt.

## Wichtig: Seit 08.11.2026 keine Bilder/Transkripte mehr online

Aus urheberrechtlichen Gründen enthält die öffentliche Seite **keine** Bilder, Vorschaubilder und Transkripte mehr (auch nicht in der Git-Historie).
- `data.js` behält die Pfade (`im`, `big`, `tr`), damit die Offline-Versionen, die Verwandte vorher gespeichert haben, weiter funktionieren. Die App erkennt selbst, ob eine vollständige Offline-Version auf dem Gerät liegt; sonst blendet sie Bilder und Transkripte aus.
- `seite_bauen.py` schreibt Vorschaubilder und Transkripte nur noch nach `werkzeug/privat/offline_medien/` (nicht öffentlich).
- Sicherung aller entfernten Dateien: `Gesundheits-App\Lexikon-Privat\lexikon_medien_backup_2026-11-08.zip` auf Alex' PC.
- `bilder/`, `thumbs/`, `transkripte/`, `tsuche.js` sind per `.gitignore` gesperrt – nie wieder ins öffentliche Repo legen.
- Im Service Worker (`sw.js`) die Cache-Namen nie ändern, sonst löschen die Handys ihre Offline-Version.

## Ordner

| Ordner | Inhalt | Im Repo? |
|---|---|---|
| `skripte/` | Python-Skripte für die einzelnen Schritte | ja |
| `daten/` | Stammdaten: alle Einträge, manuelle Korrekturen, Bild-Einträge | ja |
| `sammler/` | Kopie des Windows-Sammlers (holt Titel, Vorschaubilder, Transkripte) | ja |
| `privat/` | Chat-Exporte, `links.json`, `ergebnis.json`, entpackte Sammler-ZIP | **nein** (per `.gitignore` gesperrt) |

**Datenschutz-Regel:** In `privat/` liegen Gesprächstexte aus den Gruppen. Davon kommt nichts ins Repo und nichts auf die Webseite – nur Links, Titel, Beschreibungen der Quellen und Transkripte öffentlicher Videos. Keine Namen von Gruppenmitgliedern, keine privaten Fotos.

## Update mit neuen Gruppeninhalten (alle 1–3 Monate)

Voraussetzung: Python 3 mit `pip install pillow`. Der Sammler richtet sich beim ersten Start selbst ein.

1. **Exportieren:** In WhatsApp beide Gruppen exportieren („Chat exportieren“, mit Medien, wenn neue Bilder/Infografiken dazukommen sollen). Immer den ganzen Chat – doppelte Links werden automatisch erkannt.
2. **Links auslesen:** Die zwei `.txt`-Dateien nach `werkzeug/privat/` legen, dann im Ordner `werkzeug/skripte/`:
   ```
   python chat_auslesen.py "../privat/WhatsApp-Chat mit Gesundheit.txt" "../privat/WhatsApp-Chat mit Psychologie.txt"
   ```
   Ergebnis: `privat/links.json`.
3. **Sammeln:** `links.json` in den Sammler-Ordner auf dem PC kopieren (`Lexikon-Sammler`) und `start.bat` starten. Schon erledigte Links werden übersprungen, solange der Ordner `ausgabe` dort erhalten bleibt. Am Ende entsteht `lexikon_daten_DATUM.zip`.
4. **ZIP entpacken** nach `werkzeug/privat/` (enthält `ergebnis.json`, `thumbs/`, `transkripte/`).
5. **Bauen** – im Ordner `werkzeug/skripte/` nacheinander:
   ```
   python klassifizieren.py          # ordnet Bereich + Kategorie zu  -> daten/eintraege.json
   python korrekturen_anwenden.py    # wendet manuelle Korrekturen an -> daten/eintraege_final.json
   python seite_bauen.py             # data.js, thumbs/, transkripte/ der Webseite (zählt auch die Version hoch)
   python hilfe_inhalt.py            # hilfe.js (Soforthilfe-Seiten)
   ```
6. **Tote Links aussortieren:** `links_pruefen.bat` (Doppelklick, im Ordner `werkzeug`) prüft alle YouTube-Videos und Webseiten. Gelöschte, private oder verschwundene landen in `daten/tote_links.json` und werden beim nächsten `seite_bauen.py` weggelassen. Kommt ein Link zurück, wird er beim nächsten Prüfen wieder aufgenommen. Dauert ca. 10–15 Minuten. Nur auf dem PC ausführen (braucht normales Internet).
7. **Prüfen** (am besten mit Claude): Neue Einträge durchsehen, falsch einsortierte oder private Links in `daten/korrekturen_nach_key.json` eintragen (Codes siehe unten), Schritt 5 ab `korrekturen_anwenden.py` wiederholen.
8. **Veröffentlichen:** committen und pushen. GitHub Pages aktualisiert die Seite nach etwa 1–2 Minuten. Hängt es länger, unter *Actions* im Repo nachsehen – ein fehlgeschlagener Lauf lässt sich dort neu starten oder durch einen weiteren Push auslösen.

## Korrektur-Codes (`daten/korrekturen_nach_key.json`)

Schlüssel ist der `key` des Eintrags (z. B. `yt:VIDEOID` oder `web:URL`), Wert ein Code:

| Code | Bereich / Kategorie | Code | Bereich / Kategorie |
|---|---|---|---|
| `X` | Eintrag weglassen | `N` | Ernährung |
| `A` | Allgemeines | `P` | Psyche |
| `B` | Beziehung | `S` | Psychosomatik |
| `D` | Darm | `V` | Vitamine |
| `E` | Persönlichkeit | `n1` | Numerologie |
| `G` | Gewicht | `n2` | Astrologie |
| `K` | Körper | `s1` | Spirituell: Energie |
| `L` | Schlaf | `s2` | Spirituell: Bewusstsein |
| `M` | Bewegung | `s3` | Spirituell: Weisheit |

## Bilder und Infografiken

Bilder kommen aus dem Medien-Teil des Exports. Sie wurden per Texterkennung (OCR) gelesen, private Fotos aussortiert und Titel/Kategorie von Claude vergeben. Das ist ein betreuter Schritt, kein Skript: neue Bilder als Einträge in `daten/bilder_eintraege.json` ergänzen, die Dateien nach `bilder/` (groß, max. 1600 px) und `thumbs/` (klein, max. 480 px) legen.

### Instagram-Rahmen abschneiden

`python bilder_zuschneiden.py` sucht in neuen Bildschirmfotos den eigentlichen Beitrag und legt eine Vorschau nach `privat/zuschnitt_vorschau.jpg`. Nach Durchsicht nur die guten Vorschläge übernehmen: `python bilder_zuschneiden.py --anwenden 2 3 7 …` (Nummern aus der Vorschau). Bereits zugeschnittene stehen in `daten/zugeschnitten.json`.

## App (PWA) und Offline

- `manifest.webmanifest` + `icons/` machen die Seite installierbar (grünes Herz mit Lupe). Quelle des Symbols: `icons/icon.svg`.
- `sw.js` (Service Worker) speichert Seite, Daten und Soforthilfe für offline; Bilder, Vorschaubilder und Transkripte werden beim Ansehen gespeichert (max. ca. 900 Bilder). Favoriten-Bilder werden automatisch vorgeladen.
- Online wird immer zuerst die neue Version geladen (nach 4 s Wartezeit notfalls die gespeicherte). `seite_bauen.py` zählt die Version in `index.html` und `sw.js` hoch, damit Handys die neuen Daten sicher holen.
- Wird `sw.js` grundlegend geändert, die Cache-Namen oben in der Datei (`lex-core-v1` usw.) hochzählen.

## Soforthilfe

Alle 44 Themen stehen in `skripte/hilfe_inhalt.py` (ein Block pro Beschwerde). Text ändern, `python hilfe_inhalt.py` ausführen, pushen.

## Hinweise für Claude

- `index.html` ist handgeschrieben (Vanilla-JS, Hash-Routing); `data.js` und `hilfe.js` werden erzeugt.
- Einträge in `data.js`: `id, t` (video/article/book/image), `a` (health/spirit/numer), `c` (Kategorien), `ti, d, u, do, ch, du, l, im, tr, kp, dt, g, n, tg, s, k, yt, sh`.
- Transkripte: `transkripte/<id>.js` ruft `LEX_T(id, [[sekunde, "text"], …])` auf. Fehlen die Rohdaten in `privat/`, nutzt `seite_bauen.py` die vorhandenen Dateien weiter.
- Geplant: russische Ansicht für Alex’ Eltern (ganz am Ende).
