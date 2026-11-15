/*
 * Service worker AgroSentry (phase 4c).
 *
 * Stratégies :
 * - navigation : réseau d'abord, repli sur `index.html` en cache (hors-ligne) ;
 * - fichiers statiques : cache d'abord puis mise à jour en arrière-plan.
 * Les tuiles de carte (GIBS, Esri, relief) et l'API ne sont jamais mises en
 * cache ici : elles changent souvent et doivent rester fraîches.
 */

const CACHE = "agrosentry-v2";
const FICHIERS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (evenement) => {
  evenement.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(FICHIERS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evenement) => {
  evenement.waitUntil(
    caches
      .keys()
      .then((noms) =>
        Promise.all(noms.filter((nom) => nom !== CACHE).map((nom) => caches.delete(nom))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (evenement) => {
  const requete = evenement.request;
  if (requete.method !== "GET") return;
  if (!requete.url.startsWith(self.location.origin)) return;

  if (requete.mode === "navigate") {
    evenement.respondWith(
      fetch(requete)
        .then((reponse) => {
          const copie = reponse.clone();
          caches.open(CACHE).then((cache) => cache.put("/index.html", copie));
          return reponse;
        })
        .catch(() => caches.match("/index.html")),
    );
    return;
  }

  evenement.respondWith(
    caches.match(requete).then((enCache) => {
      const reseau = fetch(requete)
        .then((reponse) => {
          if (reponse.ok) {
            const copie = reponse.clone();
            caches.open(CACHE).then((cache) => cache.put(requete, copie));
          }
          return reponse;
        })
        .catch(() => enCache);
      return enCache || reseau;
    }),
  );
});
