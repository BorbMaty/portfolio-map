# Roadmap

Small phases, one branch and one PR each (aim < ~400 changed lines). A phase starts only when the previous
gate passes. Code phases and Mara's writing phases are never mixed. Context and rationale: [`PLAN.md`](PLAN.md).

Status: `[x]` done · `[ ]` open.

## Phase 1 — plain portfolio

- [x] **1.0 Content + CV scaffold** — content model, pages, map placeholder, `cv.pdf`, smoke tests, CI
  (PR #1, `d6c24b1`).
- [x] **1.1 Make the checks honest** (PR #6) — OG tests assert the real `SITE_URL`; landing size budget moves to
  Lighthouse CI; CI `permissions: contents: read` and no cancelled deploys; PDF script cleanup and a hard
  2-page budget; title assertion without regex; 404 page `noindex` and no canonical.
  *Gate:* CI green, and each fixed check fails when deliberately broken.
- [x] **1.2 Links and video** (PR #7) — `trailingSlash: 'always'` and links updated; tractor hero is an image until a
  real video exists; YouTube id validated; no-JS fallback link.
  *Gate:* no redirecting internal links in `dist/` (tested); a malformed id fails the build.
- [x] **1.3 Gallery and media** (PR #8) — gallery in the schema (`{ src, alt }`) with real alt text; draft media kept
  out of the build; drop `client:visible` from `MapIsland` (decided 2026-11-27: no map JS until phase 2.3,
  where it comes back with OpenSeadragon).
  *Gate:* tests assert every image has alt text and no draft media in `dist/`.
- [x] **1.4 Content pass (Mara writes)** (PR #11) — project texts, `cv.yaml`, charts, screenshots, gameplay video.
  Claude formats, fact-checks against the repos and fixes layout only.
  *Gate:* a test fails on any `TODO(` in the production build.
  Open: the Tractor VR gameplay video (image hero until it is on YouTube); AgriCulture CNN and Solar System are drafts
  (decided 2026-11-28; Solar System has no public repo).
- [ ] **1.5 Go live** — Cloudflare Pages project, secrets/variables, `SITE_URL`, first deploy, link previews
  checked, Cloudflare Web Analytics.
  *Gate:* `https://<name>.pages.dev` serves the site and `/cv.pdf`. **Phase 1 done.**

## Phase 2 — the map

- [ ] **2.1 Terrain draft** — Copernicus GLO-30 DEM → Blender scene by script → low-res draft render
  (sources outside git, `tiles-src/`). *Gate:* one draft render approved.
- [ ] **2.2 Tiles** — script cutting the render into deep-zoom WebP tiles. *Gate:* tiles rebuild from one command.
- [ ] **2.3 Pan / zoom** — OpenSeadragon in `MapIsland`, landmark overlay from `regions.ts`.
  *Gate:* first map view < 800 KB; landmarks stay pinned while zooming. Exclude map tiles from the
  landing `resource-summary` budget in `lighthouserc.json` (it counts everything since 1.1).
- [ ] **2.4 Fly-to + panel** — landmark click animates the view and opens `ProjectPanel`; `/projects/<slug>`
  opens the map with that panel. No GSAP: OpenSeadragon animates the viewport, CSS animates the panel.
  *Gate:* every project URL opens the map with the right panel.
- [ ] **2.5 Keyboard + motion** — Tab between landmarks, Enter opens, Esc closes; reduced motion disables
  animation. *Gate:* keyboard-only test passes.
- [ ] **2.6 Mobile journey path** — vertical path layout below 768 px.
  *Gate:* works on a real phone. **Phase 2 done.**

## Phase 3 — polish and launch

- [ ] **3.1** Final terrain render + night render.
- [ ] **3.2** Fog of war.
- [ ] **3.3** Per-project OG images, sitemap, SEO.
- [ ] **3.4** Domain, final Lighthouse and content check → **launch**.

## Later

Warchief's Keep · digital twin in the Observatory · 3D diorama easter egg.
