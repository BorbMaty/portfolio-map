# Portfolio Map — project guide for Claude

Mara's CV + portfolio site. It will later sit on top of an explorable, realistic-terrain fantasy map.
Full plan: `docs/PLAN.md`. Phases and gates: `docs/ROADMAP.md` (one PR per phase; tick it off when merged).

## Stack (fixed, don't substitute)
- Astro 7 + TypeScript (strict), MDX, content collections (`src/content.config.ts`, loader API)
- Plain CSS with custom properties; two themes `day` (default) and `night`; no UI framework
- One Preact island only: `src/map/MapIsland.tsx`
- Playwright (PDF generation + smoke tests), Lighthouse CI in GitHub Actions
- Hosting: Cloudflare Pages, static output, deployed from GitHub Actions with wrangler.
  Site URL from env `SITE_URL`.
- Package manager: pnpm. Ask before adding any dependency.

## Rules
- **Never commit licensed assets:** TurboSquid models, Meta controller models, built APKs/EXEs.
  Only Mara's own screenshots/charts go in `src/assets/media/`.
- Content lives only in `src/content/` (projects as MDX, `cv.yaml`). Pages and components never hard-code
  project or CV facts.
- Project images go in `src/assets/media/<slug>/` (not `public/`) so `astro:assets` makes AVIF/WebP + srcset.
- Never invent CV facts (dates, employers, emails, skill levels). Unknowns are `TODO(Mara)`.
- Commits: Conventional Commits `type(scope): message`. No Claude co-author trailers.
- Every task ends with `pnpm build && pnpm test` green.

## Performance budget
- Landing page < 300 KB transferred before the map image.
- First map view < 800 KB of tiles (phase 2).
- Lighthouse mobile: performance >= 0.9, accessibility >= 0.95 on `/` and `/cv`.
- Images AVIF/WebP via `astro:assets` with srcset; fonts self-hosted, `font-display: swap`, max 2 families.
- Contrast >= 4.5:1 in both themes, visible focus, `prefers-reduced-motion` respected.

## Phase 2 hooks
- `src/map/regions.ts`: normalised 0–1 coordinates on the final terrain image (deep-zoom, OpenSeadragon).
- `src/components/ProjectPanel.astro`: the project panel markup, reused by the map's scroll panel.
