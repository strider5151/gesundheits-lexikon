#!/usr/bin/env python3
"""Schritt 2: Ordnet die gesammelten Links Bereichen (health/spirit/numer) und Kategorien zu."""
import json, re, sys, collections, html

from pfade import PRIVAT, DATEN
SRC = PRIVAT / 'ergebnis.json'      # aus der ZIP des Sammlers
OUT = DATEN / 'eintraege.json'

# ---------------------------------------------------------------- Kategorien
# (id, bereich, de, ru, Schlüsselwörter)  – Wortanfänge, klein geschrieben
KAT = [
 # --- Numerologie & Astrologie
 ('numerologie', 'numer', 'Numerologie', 'Нумерология',
  ['numerolog', 'lebenszahl', 'seelenzahl', 'geburtszahl', 'geburtstagszahl', 'schicksalszahl', 'ausdruckszahl',
   'persönlichkeitszahl', 'meisterzahl', 'zahlenmystik', 'engelszahl', 'quersumme', 'нумеролог', 'матриц', 'number of destiny']),
 ('astrologie', 'numer', 'Astrologie & Sternzeichen', 'Астрология и знаки зодиака',
  ['astrolog', 'horoskop', 'sternzeichen', 'aszendent', 'tierkreis', 'merkur rückläufig', 'rückläufig', 'vollmond', 'neumond',
   'mondphase', 'löwenportal', 'löwen portal', 'zodiac', 'гороскоп', 'астролог', 'зодиак', 'widder', 'stier ', 'zwillinge',
   'jungfrau', 'waage', 'skorpion', 'schütze', 'steinbock', 'wassermann', 'fische ', 'human design', 'geburtshoroskop', 'mondknoten',
   'saturn', 'venus ', 'jupiter', 'pluto', 'chinesisches horoskop', 'tarot']),
 # --- Spiritualität
 ('spirit_energie', 'spirit', 'Energie, Chakren & Schwingung', 'Энергия, чакры и вибрации',
  ['chakra', 'schwingung', 'frequenz', '432', '528 hz', 'aura', 'energiefeld', 'zirbeldrüse', '3. auge', 'drittes auge', 'dritte auge',
   'energievampir', 'reiki', 'kundalini', 'energiearbeit', 'prana', 'чакр', 'вибрац', 'энергетик', 'earthing', 'erdung', 'telepath',
   'hellsicht', 'hellfühl', 'medial', 'schaman', 'engel', 'geistführer', 'aufgestiegen', 'sternensaat', 'starseed', 'lichtarbeit',
   'heilstein', 'kristall', 'räucher', 'salbei', 'mantra', 'klangschale', 'solfeggio']),
 ('spirit_bewusstsein', 'spirit', 'Bewusstsein, Seele & Erwachen', 'Сознание, душа и пробуждение',
  ['spirituell', 'spiritualität', 'erwachen', 'erleuchtung', 'seele', 'alte seelen', 'karma', 'reinkarnation', 'wiedergeburt',
   'universum', 'manifest', 'gesetz der anziehung', 'resonanzgesetz', 'law of attraction', 'geldmagnet', 'fülle', 'dispenza',
   'höheres selbst', 'wahres selbst', 'dualseele', 'zwillingsflamme', 'seelenpartner', 'seelenverwandt', 'aufstieg', '5d', 'shift',
   'matrix', 'quantenheilung', 'bewusstseinsebene', 'душ', 'пробужд', 'вселенн', 'карма', 'gott', 'göttlich', 'jenseits', 'nahtod',
   'akasha', 'kosmisch', 'spirit', 'esoter', 'schöpfer', 'vorbestimm', 'synchronizit', 'wunderheil']),
 ('spirit_weisheit', 'spirit', 'Weisheitslehrer & spirituelle Praxis', 'Учителя мудрости и духовная практика',
  ['sadhguru', 'eckhart tolle', 'osho', 'buddha', 'dalai lama', 'zen', 'yogi', 'vedisch', 'tao', 'yin yang', 'yin und yang',
   'mystik', 'meister ', 'erleuchtet', 'gebet', 'beten', 'segen', 'heilige', 'bibel', 'bhagavad', 'mönch']),
 # --- Gesundheit & Psyche
 ('beziehung', 'health', 'Narzissmus & Beziehungen', 'Нарциссизм и отношения',
  ['narzis', 'narciss', 'нарцис', 'toxisch', 'toxic', 'psychopath', 'soziopath', 'manipul', 'gaslight', 'love bombing',
   'kontaktabbruch', 'ex-partner', 'trennung', 'beziehung', 'partnerschaft', 'liebe', 'eifersucht', 'betrogen', 'affäre',
   'mutter', 'vater', 'eltern', 'tochter', 'sohn', 'kinder', 'erziehung', 'pubertät', 'familie', 'geschwister', 'freundschaft',
   'отношени', 'родител', 'abhängig', 'co-abhängig', 'grenzen setzen', 'nein sagen', 'energieräuber']),
 ('psyche', 'health', 'Psyche & Gefühle', 'Психика и чувства',
  ['psych', 'angst', 'panik', 'depress', 'trauma', 'ptbs', 'burnout', 'burn-out', 'stress', 'selbstwert', 'selbstliebe', 'selbstbewusst',
   'loslassen', 'gefühl', 'emotion', 'wut', 'ärger', 'trauer', 'einsam', 'scham', 'schuld', 'trigger', 'inneres kind', 'inneren kind',
   'glaubenssatz', 'glaubenssätze', 'unterbewusst', 'achtsam', 'meditation', 'meditier', 'entspann', 'resilienz', 'mental', 'therapie',
   'coach', 'zwang', 'grübel', 'gedankenkarussell', 'nervensystem', 'vagus', 'eft', 'klopf', 'hypnose', 'психолог', 'страх', 'тревог',
   'депресс', 'любовь к себе', 'лабковск', 'glück', 'dankbar', 'zufrieden', 'motivation', 'antrieb', 'prokrastin', 'aufschieb',
   'bindung', 'kindheit', 'heilung', 'seelisch']),
 ('persoenlichkeit', 'health', 'Persönlichkeit & Entwicklung', 'Личность и развитие',
  ['hochsensib', 'hochbegab', 'adhs', 'adhd', 'autis', 'introvert', 'extrovert', 'persönlichkeit', 'charakter', 'intelligen',
   'kommunikation', 'rhetorik', 'körpersprache',  'konflikt', 'erfolg', 'karriere', 'beruf', 'gewohnheit', 'disziplin',
   'ziele erreichen', 'selbstentwicklung', 'persönlichkeitsentwicklung', 'lernen', 'emotionale intelligenz', 'empath', 'spiegelneuron',
   'mindset',  'philosoph', 'lebensweisheit', 'lebensregel', 'sinn des lebens', 'ikigai', 'zeitmanagement', 'produktiv', 'ordnung', 'aufräum', 'organisier', 'scanner']),
 ('psychosomatik', 'health', 'Psychosomatik', 'Психосоматика',
  ['psychosomat', 'психосомат', 'körper und seele', 'körper und psyche', 'seele und körper', 'krankheit als', 'schmerz als',
   'emotionen im körper', 'gefühle im körper', 'dahlke', 'neurogenes zittern', 'körper spricht', 'seelische ursach', 'was dein körper dir', 'botschaft deines körpers', 'schmerz als schlüssel']),
 ('gewicht', 'health', 'Gewicht, Fasten & Stoffwechsel', 'Вес, голодание и обмен веществ',
  ['abnehm', 'körperfett', 'bauchfett', 'fettverbrenn', 'gewicht', 'übergewicht', 'diät', 'kalorien', 'stoffwechsel', 'fasten',
   'intervallfasten', 'heilfasten', 'blutzucker', 'insulin', 'diabetes', 'glukose', 'dickmacher', 'schlank', 'похуд', 'голодан',
   'сахар в крови', 'metabol', 'sättig', 'heißhunger', 'cheat']),
 ('ernaehrung', 'health', 'Ernährung & Rezepte', 'Питание и рецепты',
  ['ernähr', 'lebensmittel', 'rezept', 'essen', 'nahrung', 'gemüse', 'obst', 'frühstück', 'smoothie', 'protein', 'eiweiß',
   'kohlenhydrat', 'zucker', 'fette ', 'öle ', 'milch', 'brot', 'getreide', 'gluten', 'vegan', 'vegetar', 'fleisch', 'fisch', 
   'nüsse', 'samen', 'chia', 'leinsamen', 'apfelessig', 'zitrone', 'ingwer', 'kurkuma', 'knoblauch', 'tee ', 'kaffee', 'trinkwasser', 'wasser trinken',
   'trinken', 'basisch', 'übersäuer', 'säure', 'detox', 'entgift', 'superfood', 'питани', 'рецепт', 'еда', 'продукт', 'kochen',
   'küche', 'pfanne', 'mikrowelle', 'dge', 'gesund essen', 'gesunde ernährung', 'ballaststoff', 'antioxid', 'histamin']),
 ('darm', 'health', 'Darm & Verdauung', 'Кишечник и пищеварение',
  ['darm', 'verdau', 'magen', 'bauch', 'blähung', 'reizdarm', 'darmflora', 'mikrobiom', 'probiot', 'präbiot', 'verstopf',
   'durchfall', 'sodbrennen', 'leaky gut', 'antibiot', 'кишечник', 'желуд', 'пищевар', 'leber', 'galle', 'bauchspeichel']),
 ('vitamine', 'health', 'Vitamine, Mineralien & Ergänzungen', 'Витамины, минералы и добавки',
  ['vitamin', 'mineral', 'magnesium', 'zink', 'eisen', 'selen', 'jod', 'kalium', 'calcium', 'kalzium', 'omega', 'b12', 'folsäure',
   'nahrungsergänz', 'supplement', 'präparat', 'kollagen', 'q10', 'витамин', 'магний', 'минерал', 'добавк', 'uhrsalz', 'schüßler',
   'mikronährstoff', 'spurenelement']),
 ('schlaf', 'health', 'Schlaf & Erholung', 'Сон и восстановление',
  ['schlaf', 'einschlaf', 'durchschlaf', 'müde', 'müdigkeit', 'erschöpf', 'erholung', 'matratze', 'melatonin', 
   'schnarch', 'сон', 'бессонн', 'усталост', 'regeneration', 'abendroutine', 'morgenroutine']),
 ('bewegung', 'health', 'Bewegung, Rücken & Gelenke', 'Движение, спина и суставы',
  ['rücken', 'bandscheib', 'lws', 'hws', 'nacken', 'schulter', 'knie', 'hüfte', 'gelenk', 'arthrose', 'faszie', 'muskel', 'sehne',
   'übung', 'training', 'krafttraining', 'sport', 'fitness', 'yoga', 'pilates', 'dehn', 'stretch', 'mobil', 'haltung', '10.000 schritte', 'schritte am tag', 'schritte täglich',
   'laufen', 'joggen', 'spazier', 'barfuß', 'bewegung', 'liebscher', 'bracht', 'ischias', 'спин', 'сустав', 'упражнен',
   'мышц', 'knochen', 'osteopor', 'plattfuß', 'fuß', 'füße']),
 ('koerper', 'health', 'Körper, Organe & Beschwerden', 'Тело, органы и недуги',
  ['herz', 'blutdruck', 'kreislauf', 'cholesterin', 'gefäß', 'arterie', 'thrombose', 'niere', 'lunge', 'atem', 'atmung', 'schilddrüse',
   'hormon', 'testosteron', 'östrogen', 'wechseljahr', 'menopause', 'immun', 'entzünd', 'krebs', 'tumor', 'allerg', 'haut', 'haare',
   'zähne', 'zahn', 'augen', 'auge', 'makula', 'ohr', 'tinnitus', 'kopfschmerz', 'migräne', 'schwindel', 'wetterfühl', 'erkält',
   'grippe', 'corona', 'covid', 'impf', 'virus', 'bakteri', 'infekt', 'fieber', 'schmerz', 'krankheit', 'symptom', 'arzt', 'medizin',
   'medikament', 'nebenwirkung', 'diagnose', 'blut', 'zyste', 'rheuma', 'altern', 'jung bleiben', 'jünger', 'anti-aging', 'langlebig', 'longevity',
   'gehirn', 'demenz', 'alzheimer', 'gedächtnis', 'konzentration', 'nerv', 'сердц', 'давлен', 'иммун', 'гормон', 'голов', 'мозг',
   'здоров', 'heilpflanze', 'hausmittel', 'naturheil', 'homöopath', 'ayurveda', 'tcm', 'akupunkt', 'akupressur', 'kälte', 'sauna',
   'dusche', 'kneipp', 'hygiene', 'lüften', 'gift', 'schadstoff', 'schimmel', 'strahlung', 'handy', 'zittern']),
]
KAT_IDX = {k[0]: k for k in KAT}

# Bücher (Blinkist etc.) bekommen den Typ "book"
BOOK_DOMAINS = ('blinkist.com', 'audible.de', 'getabstract.com')

# ---------------------------------------------------------------- Aussortieren
SKIP_DOMAINS = ('gemini.google.com', 'g.co', 'perplexity.ai', 'chatgpt.com', 'chat.openai.com', 'instagram.com', 'facebook.com',
                'm.facebook.com', 'pinterest.com', 'de.pinterest.com', 'pin.it', 'amazon.de', 'amazon.com', 'amzn.eu', 'amzn.to',
                'apps.apple.com', 'play.google.com', 'werkenntdenbesten.de', 'google.com', 'google.de', 'maps.google.com',
                'goo.gl', 'whatsapp.com', 'chat.whatsapp.com', 'wa.me', 'drive.google.com', 'docs.google.com', 'photos.app.goo.gl',
                'music.yamaha.com', 'web.de', 'gmx.net', 'doctolib.de', 'jameda.de', 'ebay.de', 'kleinanzeigen.de', 'paypal.com',
                'bit.ly', 'linktr.ee', 'x.com', 'twitter.com', 't.me', 'vk.com', 'ok.ru', 'spotify.com', 'open.spotify.com',
                'zoom.us', 'teams.microsoft.com', 'outlook.com', 'onedrive.live.com', 'dropbox.com', 'wetransfer.com', 'canva.com')
SKIP_TITLE = re.compile(r'(^-?$|404|nicht gefunden|not found|just a moment|client challenge|bevor sie (zur|fortfahren)|'
                        r'access denied|attention required|making sure|seite wurde nicht|page not found|error|fehler 4|'
                        r'^instagram$|^pinterest$|^perplexity$|google image result|^facebook$|anmelden|log in|sign in|'
                        r'^tiktok|^youtube$|cookie|datenschutz|too many requests|^429|google search|bestenliste|^dm |drogerie markt|^taff|aktuelle infos, news)', re.I)

# Persönliches/Werbung bei Videos aussortieren? -> nein, alles was öffentlich ist bleibt


def norm(t):
    return (t or '').lower().replace('ß', 'ss').replace('ẞ', 'ss')


_RX = {}


def score(text, words):
    """Zählt Wörter, die an einer Wortgrenze beginnen (Präfix-Treffer)."""
    s = 0
    for w in words:
        w2 = w.replace('ß', 'ss').strip()
        if not w2:
            continue
        rx = _RX.get(w2)
        if rx is None:
            rx = _RX[w2] = re.compile(r'(?<![a-zäöüа-яё0-9])' + re.escape(w2))
        if rx.search(text):
            s += 1
    return s


def sauber_titel(t, domain=None):
    if not t:
        return t
    t = html.unescape(t).replace('‎', '').strip()
    t = re.sub(r'\s*Zusammenfassung von Kernaussagen und Bewertung\s*', ' – ', t)
    t = re.sub(r'\s*[-–|]\s*Blinkist\s*$', '', t)
    # Seitennamen hinten abschneiden ("… | therapie.de", "… - WELT")
    t = re.sub(r'\s*[|–—-]\s*(therapie\.de|DIE WELT|WELT|FOCUS online|FOCUS|BRIGITTE\.de|NDR\.de.*|t-online|STERN\.de|stern\.de|'
               r'SPIEGEL|DER SPIEGEL|BARMER|AOK.*|TK|netdoktor\.de|NetDoktor|Utopia\.de|CHIP|GLAMOUR|RTL\.de|EAT SMARTER|'
               r'Zentrum der Gesundheit|vital\.de|Apotheken Umschau|MSD Manual.*|eltern\.de|Spektrum.*)\s*$', '', t, flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip(' –-|')
    return t


def kurz_beschreibung(e):
    """Lesbarer Kurztext aus Video-Beschreibung bzw. og:description."""
    d = e.get('beschreibung') or ''
    if e['kind'] == 'web' and not d:
        d = e.get('text_auszug') or ''
    d = html.unescape(d)
    zeilen = []
    for z in d.splitlines():
        z = z.strip()
        if not z:
            if zeilen and len(' '.join(zeilen)) > 200:
                break
            continue
        zl = z.lower()
        if re.search(r'https?://|www\.|@|#\w|abonnier|abo |patreon|paypal|instagram|facebook|tiktok|telegram|kanal|'
                     r'newsletter|rabatt|code |werbung|anzeige|affiliate|amazon|shop|bestell|kontakt|impressum|'
                     r'kapitel|timestamps|^\d{1,2}:\d\d|copyright|©|musik:|music:|subscribe|follow|support', zl):
            continue
        zeilen.append(z)
        if len(' '.join(zeilen)) > 420:
            break
    t = re.sub(r'\s+', ' ', ' '.join(zeilen)).strip()
    if len(t) > 380:
        t = t[:380].rsplit(' ', 1)[0] + ' …'
    return t or None


def main():
    data = json.load(open(SRC, encoding='utf-8'))['eintraege']
    out, skip = [], collections.Counter()
    for e in data:
        if e.get('_fehler'):
            skip['fehler'] += 1
            continue
        kind = e['kind']
        dom = (e.get('domain') or '').lower()
        titel = sauber_titel(e.get('titel'), dom)
        if kind == 'web':
            if any(dom == s or dom.endswith('.' + s) for s in SKIP_DOMAINS):
                skip['domain'] += 1
                continue
            if str(e.get('status')) in ('404', '410', '500') or e.get('_schutzseite'):
                skip['kaputt'] += 1
                continue
            if not titel or SKIP_TITLE.search(titel) or len(titel) < 8:
                skip['titel'] += 1
                continue
        if kind == 'tiktok' and not titel:
            skip['tiktok'] += 1
            continue

        beschr = kurz_beschreibung(e)
        ctx = ' '.join(e.get('chat_kontext') or [])
        t_title = norm(titel)
        t_rest = norm(' '.join(e.get('tags') or []) + ' ' + (e.get('beschreibung') or '')[:1500] + ' ' + (e.get('text_auszug') or '')[:800])
        t_ctx = norm(ctx)

        sc = {}
        for kid, area, de, ru, words in KAT:
            sc[kid] = 4 * score(t_title, words) + 1 * min(score(t_rest, words), 4) + 2 * min(score(t_ctx, words), 2)
        # Bereich bestimmen: Numerologie/Astrologie und Spiritualität getrennt halten
        area_sc = collections.Counter()
        for kid, s in sc.items():
            area_sc[KAT_IDX[kid][1]] += s
        title_numer = sc['numerologie'] + sc['astrologie']
        title_spirit = sc['spirit_energie'] + sc['spirit_bewusstsein'] + sc['spirit_weisheit']
        if title_numer >= 4:
            area = 'numer'
        elif title_spirit >= 4 and title_spirit >= 0.5 * area_sc['health']:
            area = 'spirit'
        else:
            area = 'health'
        cands = sorted([(s, kid) for kid, s in sc.items() if KAT_IDX[kid][1] == area and s > 0], reverse=True)
        if not cands:
            cats = ['allgemein'] if area == 'health' else (['spirit_bewusstsein'] if area == 'spirit' else ['astrologie'])
        else:
            top = cands[0][0]
            cats = [kid for s, kid in cands if s >= max(3, top * 0.6)][:2] or [cands[0][1]]

        typ = 'video' if kind in ('youtube', 'tiktok') else ('book' if any(b in dom for b in BOOK_DOMAINS) else 'article')
        lang = (e.get('sprache') or '').split('-')[0] or None
        if not lang:
            lang = 'ru' if re.search('[а-яА-Я]', titel or '') else 'de'
        o = {
            'id': re.sub(r'[^A-Za-z0-9]', '', e['key'].split(':', 1)[1])[-11:] if kind == 'youtube' else
                  'w' + __import__('hashlib').sha1(e['key'].encode()).hexdigest()[:10],
            'key': e['key'], 'typ': typ, 'kind': kind, 'area': area, 'cats': cats,
            'titel': titel, 'beschreibung': beschr, 'url': e.get('endgueltige_url') or e.get('url'),
            'domain': dom if kind == 'web' else ('youtube.com' if kind == 'youtube' else 'tiktok.com'),
            'kanal': e.get('kanal'), 'dauer': e.get('dauer'), 'short': e.get('ist_short'),
            'lang': lang, 'thumb': e.get('thumbnail'), 'transkript': e.get('transkript'),
            'transkript_lang': e.get('transkript_sprache'), 'kapitel': e.get('kapitel') or [],
            'datum': e.get('zuerst_geteilt'), 'chats': e.get('chats'), 'n': e.get('mal_geteilt') or 1,
            'yt_tags': (e.get('tags') or [])[:12], '_score': {k: v for k, v in sc.items() if v},
        }
        out.append(o)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('übernommen', len(out), 'aussortiert', dict(skip))
    print(collections.Counter(o['area'] for o in out))
    c = collections.Counter(c for o in out for c in o['cats'][:1])
    for k, v in c.most_common():
        print(f'  {k:20} {v}')
    print(collections.Counter(o['typ'] for o in out))


if __name__ == '__main__':
    main()
