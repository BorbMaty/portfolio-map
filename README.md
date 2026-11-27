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

## Deployment (Cloudflare Pages)

The site is built and deployed by GitHub Actions (`.github/workflows/ci.yml`), not by Cloudflare's own build:
the PDF step needs Playwright Chromium and its system libraries, which Cloudflare's build image cannot install.
Cloudflare Pages and Actions on a public repo are free.

One-time setup:

1. Cloudflare dashboard → Workers & Pages → Create → Pages → **Direct Upload**, name the project
   (e.g. `portfolio-map`). No build settings are needed; for reference the equivalent is build command
   `pnpm build:all`, output directory `dist`.
2. Create an API token with the **Cloudflare Pages: Edit** permission.
3. GitHub repo → Settings → Secrets and variables → Actions:
   - secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
   - variables `CLOUDFLARE_PROJECT` (the project name) and `SITE_URL` (the final domain, once chosen)

Every push to `main` then builds, tests, runs Lighthouse (mobile; performance >= 0.9, accessibility >= 0.95)
and deploys `dist/`. The deploy step is skipped until `CLOUDFLARE_PROJECT` is set.
