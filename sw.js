/* Service Worker – Gesundheits-Lexikon
   Kern (Seite, Daten, Soforthilfe): erst Netz, nach 4 s oder offline aus dem Speicher.
   Bilder/Vorschaubilder/Transkripte: aus dem Speicher, sonst Netz (werden beim Ansehen gespeichert). */
// WICHTIG: Cache-Namen NIE ändern – darin liegt die Offline-Version der Nutzer (Bilder, Transkripte).
const CORE = "lex-core-v1", MEDIA = "lex-media-v1", TEXT = "lex-text-v1";
const CORE_FILES = ["./", "data.js?v=24", "hilfe.js?v=24", "manifest.webmanifest", "icons/icon-192.png", "icons/favicon-32.png", "icons/icon.svg"];

self.addEventListener("install", ev => {
  ev.waitUntil(caches.open(CORE).then(c => c.addAll(CORE_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", ev => {
  ev.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => ![CORE, MEDIA, TEXT].includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function netFirst(req, key, ms){
  const c = await caches.open(CORE);
  const net = fetch(req).then(r => { if (r && r.ok) c.put(key, r.clone()); return r; });
  try {
    const r = await Promise.race([net, new Promise((_, rej) => setTimeout(() => rej(new Error("langsam")), ms))]);
    if (r && r.ok) return r;
    const m = await c.match(key, {ignoreSearch:true});
    return m || r;
  } catch (e) {
    const m = await c.match(key, {ignoreSearch:true});
    if (m) return m;
    return net;
  }
}
async function cacheFirst(req, name){
  const c = await caches.open(name);
  const m = await c.match(req, {ignoreSearch:true});
  if (m) return m;
  const r = await fetch(req);
  if (r && r.ok) c.put(req, r.clone());
  return r;
}
async function staleWhileRevalidate(req, name){
  const c = await caches.open(name);
  const m = await c.match(req, {ignoreSearch:true});
  const net = fetch(req).then(r => { if (r && r.ok) c.put(req, r.clone()); return r; }).catch(() => m);
  return m || net;
}

self.addEventListener("fetch", ev => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  const p = url.pathname;
  if (req.mode === "navigate") return ev.respondWith(netFirst(req, "./", 4000));
  if (/\/(data|hilfe)\.js$/.test(p) || p.endsWith("manifest.webmanifest")) return ev.respondWith(netFirst(req, req, 4000));
  if (/\/(bilder|thumbs|icons)\//.test(p)) return ev.respondWith(cacheFirst(req, MEDIA));
  if (/\/transkripte\//.test(p) || p.endsWith("/tsuche.js")) return ev.respondWith(staleWhileRevalidate(req, TEXT));
});
