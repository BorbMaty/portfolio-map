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
- [x] **1.5 Go live** (PR #14, #15) — Cloudflare Pages project, secrets/variables, `SITE_URL`, first deploy, link previews
  checked, Cloudflare Web Analytics.
  *Gate:* `https://portfoliobml.pages.dev` serves the site and `/cv.pdf` (checked by CI after every deploy).
  **Phase 1 done.** Decided 2026-11-28: launch on `pages.dev`; a name domain comes in 3.4
  (`printermonitor.app` rejected: it does not read as a CV address).
  Deploy uses `pnpm dlx wrangler` (wrangler-action fails under pnpm 12). Open: `/` and `/cv/` have no `og:image` (3.3).

## Phase 2 — the map

- [x] **2.1 Terrain draft** (PR #18) — Copernicus GLO-30 DEM → Blender scene by script → low-res draft render
  (sources outside git, `tiles-src/`). *Gate:* one draft render approved.
  Approved 2026-11-28: bbox 46.60–47.00 N, 24.40–25.05 E; exaggeration 2.5, tilt 25°. `terrain/` is a uv project
  (rasterio, numpy); its tests are not in CI yet. Look (forest band, snow, edges) is left for 3.1.
- [ ] **2.2 Tiles** — script cutting the render into deep-zoom WebP tiles. *Gate:* tiles rebuild from one command.
- [ ] **2.3 Pan / zoom** — OpenSeadragon in `MapIsland`, landmark overlay from `regions.ts`. Mara places each
  landmark on the draft terrain (real `x`/`y` in `regions.ts`); the 3D models in 3.1 go on the same spots.
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

- [ ] **3.1** Landmark models + final terrain render + night render. Landmarks modelled by script in Blender at
  the `regions.ts` positions: Homestead from own farm assets (barn, shed, Székely gate; no TurboSquid), new
  Watchtower, Observatory, Capital, Harbor, Village; Harvest Fields as crop-field patches in the terrain material,
  no model; the Keep stays in Later. Then the ~8192 px render with Poly Haven (CC0) materials and rivers, and
  the dusk/night render. Split into 3.1a/3.1b if the PR grows past ~400 lines.
- [ ] **3.2** Fog of war.
- [ ] **3.3** Per-project and landing/CV OG images, sitemap, SEO.
- [ ] **3.4** Domain, final Lighthouse and content check → **launch**.

## Later

Warchief's Keep · digital twin in the Observatory · 3D diorama easter egg.
