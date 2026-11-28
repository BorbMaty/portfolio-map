# Portfolio Map

Mara's CV and portfolio site. Phase 1 (this) is a plain, shareable portfolio: landing page with a quest log,
one page per project, an ATS-friendly `/cv` and a generated `/cv.pdf`. Phase 2 adds an explorable
realistic-terrain fantasy map on top. The full plan is in [`docs/PLAN.md`](docs/PLAN.md).

Stack: Astro 7 + TypeScript (strict), MDX content collections, plain CSS, one Preact island for the map,
Playwright for the PDF and smoke tests, Lighthouse CI, Cloudflare Pages.

## Run it

Requires Node 24+ and pnpm (`corepack enable pnpm`).

```sh
pnpm install
pnpm exec playwright install chromium   # once, for the PDF and tests
pnpm dev                                # http://localhost:4321 (drafts visible)
pnpm build:all                          # type-check + build to dist/ + dist/cv.pdf
pnpm test                               # smoke tests against the production build
```

`SITE_URL` (e.g. `https://example.dev`) sets canonical and Open Graph URLs; it defaults to
`http://localhost:4321`.

## Add a project

1. Create `src/content/projects/<slug>.mdx`. Copy the frontmatter of an existing project; the schema in
   `src/content.config.ts` validates it at build time. Use `draft: true` until it is ready: drafts show in
   `pnpm dev` only.
2. Put images in `src/assets/media/<slug>/` (not `public/`), so they get AVIF/WebP and `srcset`. Screenshots in
   `src/assets/media/<slug>/gallery/` can be shown with `<Gallery slug="<slug>" />`.
3. Add or update its entry in `src/map/regions.ts` (`projectSlug`, normalised `x`/`y`).

CV facts live in `src/content/cv.yaml`. Never commit licensed assets (TurboSquid models, Meta controller
models, built APKs/EXEs).

## Rebuild the terrain (map phase 2)

Real elevation (Copernicus GLO-30 DEM, Reghin / Gorgenyi area) rendered in Blender. Everything generated goes
to `tiles-src/`, which is not versioned. Needs [uv](https://docs.astral.sh/uv/) and Blender 5.2.

```sh
cd terrain && uv run fetch_dem.py                  # download DEM tiles (~85 MB once), write heightmap.png/.json
cd .. && blender -b -P terrain/scene.py            # render tiles-src/draft.png (~10 s)
blender -b -P terrain/scene.py -- --exaggeration 3 --tilt 30 --save   # tweak; --save keeps terrain.blend
blender -b -P terrain/scene.py -- --size 4096 --out render.png  # tile source (8192 px in 3.1)
pnpm tiles                                         # tiles-src/render.png -> public/map/terrain.dzi + WebP tiles
cd terrain && uv run pytest                        # tests for the crop and tiling maths
```

`fetch_dem.py --bbox S W N E` picks another area (degrees). `pnpm tiles --quality 70` makes smaller tiles.
The tiles are generated and not versioned. CI downloads the render from the GitHub Release `terrain-src-1` and
runs `pnpm tiles` before the build; to use it locally instead of rendering:
`gh release download terrain-src-1 --pattern render.png --dir tiles-src && pnpm tiles`.

The camera framing (tilt, exaggeration, bbox) is frozen: landmark positions in `src/map/regions.ts` are fractions of
the render, so a new render may only change its size. A new render goes in a new release (`terrain-src-2`) and the
`TERRAIN_RELEASE` value in `.github/workflows/ci.yml`.

## Deployment (Cloudflare Pages)

The site is built and deployed by GitHub Actions (`.github/workflows/ci.yml`), not by Cloudflare's own build:
the PDF step needs Playwright Chromium and its system libraries, which Cloudflare's build image cannot install.
Cloudflare Pages and Actions on a public repo are free.

One-time setup:

1. Cloudflare dashboard → Workers & Pages → Create → Pages → **Direct Upload**, name the project and upload
   any placeholder folder (CI replaces it). No build settings are needed; for reference the equivalent is
   build command `pnpm build:all`, output directory `dist`. Current project: `portfoliobml`.
2. Create a custom API token: one Account policy, your account only, **Cloudflare Pages: Edit**, 1-year expiry.
3. GitHub repo → Settings → Secrets and variables → Actions:
   - secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (the id in the dashboard URL)
   - variables `CLOUDFLARE_PROJECT` (the project name) and `SITE_URL` (no trailing slash; currently
     `https://portfoliobml.pages.dev` until a domain is chosen)
4. Pages project → Metrics → **Web Analytics** → Enable. Cloudflare injects the beacon on each deploy; no code.

Every push to `main` then builds, tests, runs Lighthouse (mobile; performance >= 0.9, accessibility >= 0.95),
deploys `dist/` and checks that the live `/` has the right canonical URL and `/cv.pdf` is a PDF. Deploy and
check are skipped until `CLOUDFLARE_PROJECT` and `SITE_URL` are set.
