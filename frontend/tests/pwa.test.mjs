import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const manifest = JSON.parse(readFileSync(new URL("../public/manifest.json", import.meta.url), "utf8"));
const serviceWorker = readFileSync(new URL("../public/sw.js", import.meta.url), "utf8");

test("PWA manifest exposes a standalone YatraAI shell", () => {
  assert.equal(manifest.name, "YatraAI India Travel Planner");
  assert.equal(manifest.display, "standalone");
  assert.equal(manifest.start_url, "/");
});

test("service worker never caches map tiles and caches trip GET snapshots", () => {
  assert.match(serviceWorker, /isMapTile/);
  assert.match(serviceWorker, /if \(isMapTile\(url\)\) return/);
  assert.match(serviceWorker, /\/api\/trips\//);
});

test("service worker does not cache token-bearing trip requests", () => {
  assert.match(serviceWorker, /const VERSION = "yatraai-phase7-v2"/);
  assert.match(serviceWorker, /function isTokenBearingRequest\(request\)/);
  assert.match(serviceWorker, /X-Trip-Share-Token/);
  assert.match(serviceWorker, /X-Trip-Edit-Token/);
  assert.match(serviceWorker, /!isTokenBearingRequest\(request\)/);
});
