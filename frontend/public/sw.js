/* YatraAI offline shell. Map tiles are deliberately never cached. */
const VERSION = "yatraai-phase7-v1";
const SHELL_CACHE = `${VERSION}-shell`;
const SNAPSHOT_CACHE = `${VERSION}-trip-snapshots`;
const TILE_HOSTS = ["tile.openstreetmap.org", "maps.googleapis.com", "api.mapbox.com", "tiles.mapbox.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(["/", "/manifest.json"])).catch(() => undefined));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => ![SHELL_CACHE, SNAPSHOT_CACHE].includes(key)).map((key) => caches.delete(key)))),
  );
  self.clients.claim();
});

function isMapTile(url) {
  return TILE_HOSTS.some((host) => url.hostname === host || url.hostname.endsWith(`.${host}`)) || /\/tile[s]?\//i.test(url.pathname);
}

function isTripSnapshot(url) {
  return url.pathname.startsWith("/api/trips/");
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok && response.type === "basic") await cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    return cached || new Response("Offline snapshot unavailable.", { status: 503, headers: { "Content-Type": "text/plain" } });
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (isMapTile(url)) return;
  if (url.origin === self.location.origin && isTripSnapshot(url)) {
    event.respondWith(networkFirst(request, SNAPSHOT_CACHE));
    return;
  }
  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, SHELL_CACHE));
  }
});
