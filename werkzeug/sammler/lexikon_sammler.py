#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lexikon-Sammler
================
Holt zu allen Links aus links.json die Daten fürs Gesundheits-Lexikon:

  * YouTube / TikTok: Titel, Kanal, Dauer, Sprache, Beschreibung, Kapitel,
    Vorschaubild und Untertitel (als Transkript mit Zeitmarken)
  * Webseiten: Titel, Beschreibung, Vorschaubild (og:image)
  * optional: Transkript per Spracherkennung (faster-whisper), wenn ein
    Video keine Untertitel hat

Alles landet im Ordner "ausgabe". Bereits erledigte Links werden beim
nächsten Start übersprungen – man kann also jederzeit abbrechen (Strg+C)
und später weitermachen.

Aufruf (am einfachsten über start.bat):
    python lexikon_sammler.py                 # alles
    python lexikon_sammler.py --nur youtube   # nur YouTube
    python lexikon_sammler.py --limit 20      # zum Testen nur 20 Links
    python lexikon_sammler.py --whisper       # fehlende Transkripte per KI
    python lexikon_sammler.py --cookies chrome  # falls YouTube blockiert
    python lexikon_sammler.py --zip           # nur ZIP zum Hochladen bauen
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

BASIS = Path(__file__).resolve().parent
AUSGABE = BASIS / "ausgabe"
CACHE = AUSGABE / "cache"
THUMBS = AUSGABE / "thumbs"
TRANS = AUSGABE / "transkripte"
LOG = AUSGABE / "fehler.log"

SPRACH_REIHENFOLGE = ["de", "ru", "en"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


# ---------------------------------------------------------------- Helfer
def log(msg):
    zeit = datetime.now().strftime("%H:%M:%S")
    print(f"[{zeit}] {msg}", flush=True)


def fehler(key, msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{key}\t{msg}\n")


def dateiname(key):
    sauber = re.sub(r"[^A-Za-z0-9_-]", "_", key)[:60]
    return sauber + "_" + hashlib.sha1(key.encode()).hexdigest()[:8]


def cache_lesen(key):
    p = CACHE / (dateiname(key) + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def cache_schreiben(key, daten):
    p = CACHE / (dateiname(key) + ".json")
    p.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")


def zeit_fmt(sek):
    sek = int(sek or 0)
    h, r = divmod(sek, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ---------------------------------------------------------- Untertitel
def json3_zu_zeilen(roh):
    """YouTube-Untertitel (json3) -> [{t: Sekunden, text}] in ~Satzblöcken."""
    daten = json.loads(roh)
    zeilen = []
    for ev in daten.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        zeilen.append({"t": round(ev.get("tStartMs", 0) / 1000, 1), "text": text})
    # kleine Auto-Untertitel-Schnipsel zu Blöcken von ~15 s zusammenfassen
    bloecke, akt = [], None
    for z in zeilen:
        if akt and z["t"] - akt["t"] < 15 and len(akt["text"]) < 400:
            akt["text"] += " " + z["text"]
        else:
            akt = dict(z)
            bloecke.append(akt)
    for b in bloecke:
        b["text"] = re.sub(r"\s+", " ", b["text"]).strip()
    return bloecke


def vtt_zu_zeilen(roh):
    zeilen, t = [], 0.0
    for block in roh.split("\n\n"):
        m = re.search(r"(\d+):(\d\d):(\d\d)[.,](\d+)\s+-->", block)
        if not m:
            m2 = re.search(r"(\d\d):(\d\d)[.,](\d+)\s+-->", block)
            if not m2:
                continue
            t = int(m2[1]) * 60 + int(m2[2])
        else:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
        text = " ".join(l for l in block.splitlines()[1:] if "-->" not in l)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text and (not zeilen or zeilen[-1]["text"] != text):
            zeilen.append({"t": t, "text": text})
    return zeilen


def untertitel_waehlen(info):
    """Beste Spur: Originalsprache > de > ru > en; manuell vor automatisch."""
    original = (info.get("language") or "").split("-")[0] or None
    reihenfolge = ([original] if original else []) + [s for s in SPRACH_REIHENFOLGE if s != original]
    for quelle, art in ((info.get("subtitles") or {}, "manuell"), (info.get("automatic_captions") or {}, "automatisch")):
        for lang in reihenfolge:
            for code, spuren in quelle.items():
                if code.split("-")[0] != lang:
                    continue
                # automatische Übersetzungen ("de-en" o. ä.) überspringen, wenn Original da ist
                if art == "automatisch" and "-" in code and code.split("-")[0] != original:
                    continue
                for ext in ("json3", "vtt"):
                    for s in spuren:
                        if s.get("ext") == ext and s.get("url"):
                            return {"lang": code, "art": art, "ext": ext, "url": s["url"]}
    return None



# ------------------------------------------------- Fehler einordnen
def ist_gesperrt(msg):
    m = msg.lower()
    # private/gelöschte Videos sind keine Sperre, auch wenn YouTube "sign in" dazuschreibt
    if any(s in m for s in ("private video", "helps protect our community", "age-restricted", "inappropriate", "terminated", "has been removed", "no longer available",
                            "this video is unavailable", "this video is not available")):
        return False
    return any(s in m for s in ("rate-limited", "try again later", "http error 429", "too many requests",
                                "confirm you're not a bot", "confirm you’re not a bot"))


def ist_dauerhaft(msg):
    m = msg.lower()
    if ist_gesperrt(msg):
        return False
    return any(s in m for s in ("terminated", "private video", "helps protect our community", "age-restricted", "inappropriate", "video unavailable", "this video is unavailable",
                                "this video is not available", "has been removed", "no longer available",
                                "copyright", "404", "410"))


# --------------------------------------------------------------- TikTok
def tiktok_holen(ydl, session, item, args):
    """vm.tiktok.com-Kurzlinks erst auflösen, dann mit yt-dlp lesen."""
    url = item["url"]
    if "vm.tiktok.com" in url or "vt.tiktok.com" in url or "/t/" in url:
        mobil = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S916B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"}
        ziel = None
        for kopf in (mobil, {"User-Agent": UA}):
            try:
                r = session.get(url, headers=kopf, timeout=20, allow_redirects=True)
                kandidaten = [h.headers.get("location", "") for h in r.history] + [r.url]
                for k in kandidaten:
                    if re.search(r"/(video|photo)/\d+", k):
                        ziel = k.split("?")[0]
                        break
                if not ziel:
                    m = re.search(r"https://www\.tiktok\.com/@[^\"'\s]+/(?:video|photo)/\d+", r.text)
                    if m:
                        ziel = m.group(0)
            except Exception:
                pass
            if ziel:
                break
        if not ziel:
            # nicht auflösbar (Video gelöscht oder TikTok blockt) -> als einfacher Link behalten
            return {"key": item["key"], "kind": "tiktok", "url": url, "titel": None,
                    "_hinweis": "TikTok-Kurzlink nicht auflösbar – bleibt als Link im Lexikon"}
        item = dict(item, url=ziel)
    return video_holen(ydl, item, args)

# ------------------------------------------------------------- Videos
def video_holen(ydl, item, args):
    info = ydl.extract_info(item["url"], download=False)
    if info.get("_type") == "playlist" and info.get("entries"):
        info = next(iter(info["entries"]))

    vid = info.get("id")
    daten = {
        "key": item["key"],
        "kind": item["kind"],
        "url": info.get("webpage_url") or item["url"],
        "id": vid,
        "titel": info.get("title"),
        "kanal": info.get("channel") or info.get("uploader"),
        "kanal_url": info.get("channel_url") or info.get("uploader_url"),
        "hochgeladen": info.get("upload_date"),
        "dauer_s": info.get("duration"),
        "dauer": zeit_fmt(info.get("duration")) if info.get("duration") else None,
        "sprache": info.get("language"),
        "beschreibung": (info.get("description") or "")[:3000],
        "tags": (info.get("tags") or [])[:25],
        "kategorien": info.get("categories"),
        "aufrufe": info.get("view_count"),
        "ist_short": "/shorts/" in (item.get("original_url") or "") or (info.get("duration") or 999) <= 70,
        "kapitel": [{"t": round(c.get("start_time", 0)), "zeit": zeit_fmt(c.get("start_time")), "titel": c.get("title")}
                    for c in (info.get("chapters") or [])],
        "thumbnail": None,
        "transkript": None,
        "transkript_quelle": None,
        "transkript_sprache": None,
    }

    # Vorschaubild
    thumb_url = None
    if item["kind"] == "youtube" and vid:
        thumb_url = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    elif info.get("thumbnail"):
        thumb_url = info["thumbnail"]
    if thumb_url:
        try:
            roh = ydl.urlopen(thumb_url).read()
            endung = ".jpg" if roh[:3] == b"\xff\xd8\xff" else (".webp" if roh[8:12] == b"WEBP" else ".png" if roh[:4] == b"\x89PNG" else ".jpg")
            name = dateiname(item["key"]) + endung
            (THUMBS / name).write_bytes(roh)
            daten["thumbnail"] = "thumbs/" + name
        except Exception as e:
            fehler(item["key"], f"Thumbnail: {e}")

    # Untertitel -> Transkript
    spur = untertitel_waehlen(info)
    if spur:
        try:
            roh = ydl.urlopen(spur["url"]).read().decode("utf-8", "replace")
            zeilen = json3_zu_zeilen(roh) if spur["ext"] == "json3" else vtt_zu_zeilen(roh)
            if zeilen:
                name = dateiname(item["key"]) + ".json"
                (TRANS / name).write_text(json.dumps(zeilen, ensure_ascii=False, indent=0), encoding="utf-8")
                daten["transkript"] = "transkripte/" + name
                daten["transkript_quelle"] = "untertitel_" + spur["art"]
                daten["transkript_sprache"] = spur["lang"]
        except Exception as e:
            fehler(item["key"], f"Untertitel: {e}")

    if not daten["transkript"] and args.whisper:
        whisper_transkript(item, daten, args)

    return daten


_WHISPER = None


def whisper_transkript(item, daten, args):
    global _WHISPER
    if (daten.get("dauer_s") or 0) > args.whisper_max_min * 60:
        daten["transkript_quelle"] = f"zu_lang_für_whisper (> {args.whisper_max_min} min)"
        return
    try:
        from faster_whisper import WhisperModel
        import yt_dlp
    except ImportError:
        log("  faster-whisper fehlt – bitte whisper_installieren.bat ausführen")
        args.whisper = False
        return
    tmp = AUSGABE / "tmp_audio"
    tmp.mkdir(exist_ok=True)
    ziel = str(tmp / (dateiname(item["key"]) + ".%(ext)s"))
    opts = {"format": "bestaudio/best", "outtmpl": ziel, "quiet": True, "no_warnings": True}
    if args.cookies:
        opts["cookiesfrombrowser"] = (args.cookies,)
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([daten["url"]])
        dateien = list(tmp.glob(dateiname(item["key"]) + ".*"))
        if not dateien:
            return
        if _WHISPER is None:
            log(f"  lade Whisper-Modell '{args.whisper_modell}' (einmalig) …")
            _WHISPER = WhisperModel(args.whisper_modell, device="auto", compute_type="int8")
        segs, info = _WHISPER.transcribe(str(dateien[0]), vad_filter=True)
        zeilen = [{"t": round(s.start, 1), "text": s.text.strip()} for s in segs]
        if zeilen:
            name = dateiname(item["key"]) + ".json"
            (TRANS / name).write_text(json.dumps(zeilen, ensure_ascii=False, indent=0), encoding="utf-8")
            daten["transkript"] = "transkripte/" + name
            daten["transkript_quelle"] = "whisper_" + args.whisper_modell
            daten["transkript_sprache"] = info.language
    except Exception as e:
        fehler(item["key"], f"Whisper: {e}")
    finally:
        for f in tmp.glob(dateiname(item["key"]) + ".*"):
            try:
                f.unlink()
            except Exception:
                pass


# ----------------------------------------------------------- Webseiten
def web_holen(session, item):
    from bs4 import BeautifulSoup
    r = session.get(item["url"], timeout=20, allow_redirects=True)
    daten = {"key": item["key"], "kind": "web", "url": item["url"], "endgueltige_url": r.url,
             "status": r.status_code, "domain": re.sub(r"^www\.", "", r.url.split("/")[2]) if "//" in r.url else None,
             "titel": None, "beschreibung": None, "seitenname": None, "thumbnail": None, "text_auszug": None}
    if "text/html" not in r.headers.get("content-type", ""):
        daten["typ"] = r.headers.get("content-type")
        return daten
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")

    def meta(*namen):
        for n in namen:
            t = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
            if t and t.get("content"):
                return t["content"].strip()
        return None

    daten["titel"] = meta("og:title", "twitter:title") or (soup.title.string.strip() if soup.title and soup.title.string else None)
    if daten["titel"] and any(s in daten["titel"].lower() for s in ("not a bot", "just a moment", "attention required",
                                                                   "access denied", "zugriff verweigert", "are you a robot")):
        daten["titel"] = None
        daten["_schutzseite"] = True   # Bot-Schutz statt Inhalt
    daten["beschreibung"] = meta("og:description", "description", "twitter:description")
    daten["seitenname"] = meta("og:site_name")
    # kurzer Textauszug (erste Absätze) – hilft später beim Zusammenfassen
    absaetze = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    absaetze = [a for a in absaetze if len(a) > 60][:8]
    daten["text_auszug"] = "\n".join(absaetze)[:2500] or None

    bild = meta("og:image", "twitter:image")
    if bild:
        if bild.startswith("//"):
            bild = "https:" + bild
        elif bild.startswith("/"):
            bild = "/".join(r.url.split("/")[:3]) + bild
        try:
            b = session.get(bild, timeout=20)
            if b.ok and len(b.content) > 1500:
                roh = b.content
                endung = ".jpg" if roh[:3] == b"\xff\xd8\xff" else (".webp" if roh[8:12] == b"WEBP" else ".png" if roh[:4] == b"\x89PNG" else ".jpg")
                name = dateiname(item["key"]) + endung
                (THUMBS / name).write_bytes(roh)
                daten["thumbnail"] = "thumbs/" + name
        except Exception as e:
            fehler(item["key"], f"Bild: {e}")
    return daten


# ------------------------------------------------------------- Ablauf
def zip_bauen():
    ziel = BASIS / f"lexikon_daten_{datetime.now():%Y%m%d_%H%M}.zip"
    log(f"Baue {ziel.name} …")
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        for p in AUSGABE.rglob("*"):
            if p.is_file() and "tmp_audio" not in p.parts and "cache" not in p.parts:
                z.write(p, p.relative_to(AUSGABE))
    groesse = ziel.stat().st_size / 1024 / 1024
    log(f"Fertig: {ziel}  ({groesse:.1f} MB) – diese Datei an Claude hochladen.")


def ergebnis_schreiben(items):
    alle = []
    for it in items:
        d = cache_lesen(it["key"])
        if d:
            d["chats"] = it.get("chats")
            d["zuerst_geteilt"] = it.get("first_shared")
            d["mal_geteilt"] = it.get("times_shared")
            d["chat_kontext"] = it.get("context")
            alle.append(d)
    (AUSGABE / "ergebnis.json").write_text(json.dumps({"erstellt": datetime.now().isoformat(timespec="seconds"),
                                                       "anzahl": len(alle), "eintraege": alle},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    return len(alle)


def main():
    ap = argparse.ArgumentParser(description="Sammelt Metadaten, Vorschaubilder und Transkripte fürs Lexikon.")
    ap.add_argument("--nur", choices=["youtube", "tiktok", "web", "videos"], help="nur diese Art von Links")
    ap.add_argument("--limit", type=int, default=0, help="höchstens so viele (neue) Links bearbeiten")
    ap.add_argument("--pause", type=float, default=1.0, help="Sekunden Pause zwischen Webseiten (Standard 1)")
    ap.add_argument("--pause-yt", type=float, default=4.0, help="Sekunden Pause zwischen YouTube-Abrufen (Standard 4)")
    ap.add_argument("--sperre-min", type=int, default=20, help="Minuten warten, wenn YouTube sperrt (Standard 20)")
    ap.add_argument("--neu", action="store_true", help="Fehlgeschlagene Links erneut versuchen")
    ap.add_argument("--cookies", metavar="BROWSER", help="Cookies aus Browser nutzen (chrome, edge, firefox), falls YouTube blockiert")
    ap.add_argument("--whisper", action="store_true", help="Videos ohne Untertitel per faster-whisper transkribieren")
    ap.add_argument("--whisper-modell", default="small", help="tiny, base, small, medium, large-v3 (Standard: small)")
    ap.add_argument("--whisper-max-min", type=int, default=60, help="längere Videos nicht per Whisper (Standard 60 min)")
    ap.add_argument("--zip", action="store_true", help="nur ergebnis.json + ZIP zum Hochladen bauen")
    args = ap.parse_args()

    for p in (AUSGABE, CACHE, THUMBS, TRANS):
        p.mkdir(parents=True, exist_ok=True)

    items = json.loads((BASIS / "links.json").read_text(encoding="utf-8"))["items"]

    if args.zip:
        n = ergebnis_schreiben(items)
        log(f"{n} Einträge in ergebnis.json")
        zip_bauen()
        return

    if args.nur == "videos":
        items_run = [i for i in items if i["kind"] in ("youtube", "tiktok")]
    elif args.nur:
        items_run = [i for i in items if i["kind"] == args.nur]
    else:
        items_run = [i for i in items if i["kind"] != "youtube_other"]

    offen = []
    for it in items_run:
        c = cache_lesen(it["key"])
        if c is None:
            offen.append(it)
        elif c.get("_fehler") and ist_gesperrt(c["_fehler"]):
            offen.append(it)          # Rate-Limit aus älterem Lauf -> immer neu versuchen
        elif c.get("_fehler") and it["kind"] == "tiktok" and "Unsupported URL" in c["_fehler"]:
            offen.append(it)          # TikTok-Kurzlinks: neue Auflösung
        elif args.neu and c.get("_fehler") and not (c.get("_dauerhaft") or ist_dauerhaft(c["_fehler"])):
            offen.append(it)
        elif args.whisper and it["kind"] in ("youtube", "tiktok") and not c.get("transkript") \
                and not c.get("_fehler") and not str(c.get("transkript_quelle") or "").startswith("zu_lang"):
            offen.append(it)
    if args.limit:
        offen = offen[: args.limit]
    log(f"{len(items_run)} Links insgesamt, {len(items_run) - len(offen)} schon erledigt, {len(offen)} jetzt dran.")

    import requests
    import yt_dlp

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "de-DE,de;q=0.9,ru;q=0.8,en;q=0.7"})
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
                "extract_flat": False, "socket_timeout": 30, "retries": 3}
    if args.cookies:
        ydl_opts["cookiesfrombrowser"] = (args.cookies,)
    ydl_opts["sleep_interval_requests"] = 0.75   # kleine Pause zwischen den Einzel-Anfragen pro Video

    ok = fail = gesperrt_zaehler = 0
    yt_gesperrt = False
    abbruch = False
    start = time.time()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for n, it in enumerate(offen, 1):
            if yt_gesperrt and it["kind"] == "youtube":
                continue
            rest = ""
            if n > 3:
                pro = (time.time() - start) / (n - 1)
                rest = f" · noch ca. {int(pro * (len(offen) - n + 1) / 60)} min"
            log(f"{n}/{len(offen)}{rest}  {it['kind']:7}  {it['url'][:80]}")
            versuch = 0
            while True:
                try:
                    if it["kind"] == "tiktok":
                        d = tiktok_holen(ydl, session, it, args)
                        log(f"    ✓ {(d.get('titel') or d.get('_hinweis') or '')[:70]}")
                    elif it["kind"] == "youtube":
                        d = video_holen(ydl, it, args)
                        log(f"    ✓ {(d.get('titel') or '')[:70]}  [{d.get('transkript_quelle') or 'kein Transkript'}]")
                    else:
                        d = web_holen(session, it)
                        log(f"    ✓ {(d.get('titel') or '–')[:70]}")
                    cache_schreiben(it["key"], d)
                    ok += 1
                    gesperrt_zaehler = 0
                except KeyboardInterrupt:
                    abbruch = True
                    log("Abgebrochen – beim nächsten Start geht es hier weiter.")
                except Exception as e:
                    msg = str(e).splitlines()[0][:300]
                    if ist_gesperrt(msg):
                        # NICHT als Fehler speichern -> wird beim nächsten Lauf automatisch neu versucht
                        versuch += 1
                        if versuch <= 1:
                            log(f"    ⏸ YouTube bremst (Rate-Limit). Warte {args.sperre_min} min und versuche es dann nochmal …")
                            time.sleep(args.sperre_min * 60)
                            continue
                        gesperrt_zaehler += 1
                        log("    ⏸ Immer noch gesperrt – YouTube wird für diesen Lauf übersprungen, Webseiten laufen weiter.")
                        log("      Später einfach start.bat erneut starten (am besten mit --cookies chrome).")
                        yt_gesperrt = True
                    else:
                        dauerhaft = ist_dauerhaft(msg)
                        fehler(it["key"], msg)
                        cache_schreiben(it["key"], {"key": it["key"], "kind": it["kind"], "url": it["url"],
                                                    "_fehler": msg, "_dauerhaft": dauerhaft})
                        log(f"    ✗ {'(gelöscht/privat) ' if dauerhaft else ''}{msg[:110]}")
                        fail += 1
                break
            if abbruch:
                break
            try:
                time.sleep(args.pause_yt if it["kind"] == "youtube" else args.pause)
            except KeyboardInterrupt:
                log("Abgebrochen – beim nächsten Start geht es hier weiter.")
                break

    n = ergebnis_schreiben(items)
    log(f"Fertig. Neu: {ok} ok, {fail} Fehler. ergebnis.json enthält {n} Einträge.")
    zip_bauen()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
