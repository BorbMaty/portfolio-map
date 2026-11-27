# Fantasy Map Portfolio — Full Plan

Transcribed from `Fantasy Map Portfolio — Full Plan.pdf` (2026-11-27). This file is the source of truth
from now on; update it here, not in the PDF.

## Goal and audience

A personal portfolio and CV site, built as an explorable fantasy map, that gets Mara interviews with
international employers.

- **Audience:** global tech recruiters and engineering leads. English only for v1.
- **Reader time:** recruiters give 30 seconds; engineers who click through give 5 to 10 minutes. The site
  must work for both.
- **The one-line story (hero text):** *I build software that sees, simulates and monitors the physical world.*
- **Success:** a recruiter finds name, role, top 2 projects, CV and contact within 10 seconds; an engineer
  can reach code, architecture and numbers for each flagship.

## Content: regions and project pages

Two flagships anchor the map; everything else is smaller and optional. PV paper, Moldflow, the hackathon,
the parser and the lab fork stay off.

| Region | Project | Weight | Page leads with | Must show |
|---|---|---|---|---|
| The Homestead | Tractor VR (John Deere 6195M, Quest 2) | Flagship | 30–60 s gameplay video | Physics model (PHYSICS.md), 3 builds from one project, benchmark table (Quest 71.8 fps, 0 % over budget), Blender-by-script pipeline, 9-lesson tutorial; link to the public repo github.com/BorbMaty/TractorVR (licensed tractor model not included), plus video, physics and benchmark charts, gallery |
| The Watchtower | PrinterMonitor (BA thesis) | Flagship | Architecture diagram + live dashboard clip | YOLOv8x 9 classes, mAP50 92.6 %, ~23 ms/frame on Vertex AI T4; Pi + 3 cameras + Pub/Sub + Cloud Functions; Terraform; dataset leakage audit |
| Harvest Fields | AgriCulture_CNN | Small | Detection GIF on a field video | YOLOv5, 8 agricultural classes, merged 21 datasets |
| The Observatory | SolarSystem → digital twin | Medium | Short clip, desktop + VR tabletop | JSON-driven scene, live HTTP telemetry → ok / warning / fault, desktop/VR mode switch; pitched as a digital twin prototype |
| Village | Sapi-Foglalo *or* movie_catalog | Tiny | One screenshot | Full-stack basics (FastAPI + SQLAlchemy + Azure MySQL, or Express + MySQL + auth) |
| Warchief's Keep | Claude agent setup | Optional, later | Short write-up | Agentic workflow, Warcraft-themed agents |
| Capital | About, skills, education | — | Photo + 3-line bio | Sapientia CS degree, BA thesis title, skills grouped (ML/CV, XR/Unity, cloud/GCP, full-stack) |
| Harbor | Contact + CV | — | Buttons | Email, GitHub, LinkedIn, CV PDF download |

Every project page uses one template: hero media → one-line pitch → problem → what I built (stack chips) →
3–4 numbers → architecture picture → what I learned → links (repo, docs, video).

Teamwork is missing now that the hackathon is out: mention team work on the CV page and in the About text.

## Visual concept

The realm is a stylised Transylvania with invented fantasy names: rolling hills, a mountain arc, a river
valley. It's personal (the tractor sim is set near Reghin), original, and avoids any Warcraft or Blizzard
lookalike.

**Geography (rough placement):**

- Mountain arc across the north and east (the Görgényi feel): **Observatory** on the highest peak.
- Central valley with fields and a river: **Homestead** and **Harvest Fields** side by side.
- A ridge above the valley: **Watchtower**, looking over everything it monitors.
- River runs south to the **Harbor**; **Capital** sits at the crossroads in the middle; **Village** on a side road.
- Fog of war over unexplored edges; it clears as regions are visited (and leaves room for future projects).

**Art direction: realistic terrain (decided 2026-11-27).** The map is a realistic, rendered landscape seen
from above at a slight tilt, like a satellite view of a valley. The fantasy comes from the names, the label
lettering, the landmarks and the fog, not the drawing style.

**Terrain pipeline (reuses the tractor-sim Blender skills):**

1. Real elevation data for the Reghin / Mezőség / Görgényi area (Copernicus GLO-30 DEM, free) → cropped and
   exaggerated in Blender. Use a real area, but the realm stays fictional.
2. Procedural materials: grass, fields, forest by slope and height, rivers, snow on the peaks; Poly Haven
   textures (CC0), as in the sim.
3. Landmarks modelled by script: reuse own farm assets (barn, shed, Székely gate) for the Homestead; new ones
   for the Watchtower, Observatory, Capital, Harbor.
4. Orthographic (or slightly oblique) render at about 8192 × 8192, plus a dusk/night render for the night theme.
5. Cut into deep-zoom tiles (WebP) → served static; labels and landmark hit-areas are an HTML/SVG overlay on
   top, so they stay crisp, clickable and accessible.

**Type and palette:** a display serif with fantasy flavour for headings (e.g. Cinzel or IM Fell), a clean sans
for body text (Inter). Parchment `#f3e9d2`, ink `#2b2118`, accent red `#8b2e1f`, plus a dark "night map"
theme. Body text stays modern and readable; the fantasy is in the frame, not the paragraphs.

## UX: three ways in

The map is the experience, but never the only door: a recruiter must reach the CV in one click.

1. **Landing (above the fold):** the full map, faded, with a parchment banner over it: name, role
   ("Software engineer — ML, XR, cloud"), the one-line story, and three buttons: *Explore the map · View CV ·
   Contact*. The two flagships glow and pulse.
2. **Map mode (desktop):** pan with drag, zoom with wheel or buttons; click a landmark → the camera flies to it
   and a scroll panel unrolls from the right with the project page. Hover shows a short tooltip (name + one
   line). Keyboard: Tab between landmarks, Enter opens, Esc closes. A small legend and a "quest log" list of
   all regions for anyone who'd rather click a list.
3. **Plain mode (`/cv`):** a normal, ATS-friendly one-column CV page with the same content, plus a PDF
   download. Toggle in the header on every page.
4. **Mobile (< 768 px):** no pan/zoom map. A vertical "journey path": the map as a scrolling strip, each region
   a stop with a card that opens the project page.

**Every project has its own URL** (`/projects/tractor-vr`), so links in a CV, a LinkedIn post or an email open
straight onto that project — the map behind it, panel open.

**Accessibility:** `prefers-reduced-motion` turns off the fly-to and fog animations; text contrast ≥ 4.5:1 on
parchment; every landmark has an accessible name.

## Tech stack, hosting and costs

A static site: no server, near-zero running cost, fast everywhere.

| Layer | Choice | Why |
|---|---|---|
| Framework | Astro + TypeScript | Static HTML per page (good SEO, fast first paint); interactive map as one island |
| Map | Blender-rendered terrain as deep-zoom raster tiles + HTML/SVG overlay for labels, landmarks and fog | Realistic look; tiles load only what's on screen; landmarks stay DOM elements (clickable, accessible) |
| Pan / zoom | `OpenSeadragon` (or `Leaflet CRS.Simple`) | Built for deep-zoom tiles with HTML overlays; touch-aware |
| Animation | GSAP (fly-to, scroll unroll, fog reveal) | Smooth, respects reduced motion with a flag |
| Content | Markdown/MDX per project in Astro content collections | Edit text without touching code; same source feeds map panels, `/cv` and project URLs |
| CV PDF | Generated from the same content at build time (Playwright print of `/cv`) | One source of truth, never out of date |
| Styling | CSS variables + a little Tailwind or plain CSS | Two themes (parchment / night) |
| Hosting | Cloudflare Pages (or GitHub Pages) | Free, global CDN, preview deploy per branch |
| Video | YouTube unlisted embed behind a click-to-load poster | Free bandwidth; no player loads until clicked |
| Analytics | Cloudflare Web Analytics | Free, no cookies, no consent banner |

**Costs:** about €0/month to run, plus a domain (~€10–15/year for something like `mara<surname>.dev`). Avoid
Firebase Hosting for video: the free tier's daily transfer limit is small, and self-hosted MP4s would hit it fast.

**Performance budget:** landing page < 300 KB before the map loads, first map view < 800 KB of tiles,
Lighthouse ≥ 90 on mobile. Project images as AVIF/WebP with `srcset`.

## Site structure and repo layout

**Routes:**

- `/` — landing banner + map
- `/projects/<slug>` — map with that project's panel open (static page, shareable)
- `/cv` — plain CV page; `/cv.pdf` — generated PDF
- `/about` — Capital panel as a page
- `/404` — "Here be dragons" page with a link home

**Repo (`portfolio-map`):**

```
src/
  content/
    projects/        tractor-vr.mdx, printer-monitor.mdx, agriculture-cnn.mdx,
                     solar-system.mdx, village.mdx
    cv.yaml          education, skills, experience (feeds /cv and the PDF)
    config.ts        content schema (title, region, weight, stack, metrics, links, media)
  map/
    realm.svg        layered map art (terrain, rivers, labels)
    regions.ts       region id → landmark position, project slug, zoom level
    MapIsland.tsx    pan/zoom, fly-to, fog of war, keyboard nav
    ScrollPanel.tsx  the unrolling project panel
  components/        Banner, StackChips, MetricRow, VideoPoster, ThemeToggle, JourneyPath (mobile)
  layouts/           Base.astro, ProjectPage.astro, CvPage.astro
  pages/             index.astro, projects/[slug].astro, cv.astro, about.astro, 404.astro
public/
  media/<slug>/      images (AVIF/WebP), posters, OG images
  fonts/
scripts/
  build-cv-pdf.ts    Playwright print of /cv → public/cv.pdf
.github/workflows/   build, Lighthouse CI, deploy
CLAUDE.md            project guide for the agent setup
```

Adding a future project = one MDX file + one entry in `regions.ts` (+ clearing a patch of fog).

> Implementation notes (phase 1): Astro 7 moved the content config to `src/content.config.ts`; project
> images live in `src/assets/media/<slug>/` so `astro:assets` can optimise them; the PDF is written to
> `dist/cv.pdf`.

## Pre-work on the project repos

The map links straight into GitHub, so the repos are part of the portfolio. This work can run in parallel
with the site build.

**Tractor VR → public showcase repo**

- [x] New public repo `BorbMaty/TractorVR`; TurboSquid tractor and every mesh cut from it absent from all
  100 commits (checked 2026-11-27)
- [ ] Purge `Assets/Models/MetaControllers/` from history (Oculus SDK License); controllers fall back to
  `ControllerRing` when missing; README says where to import them
- [ ] Add a `LICENSE` (MIT or all rights reserved); note Poly Haven CC0 and XR Hands sample licences
- [ ] Delete `Assets/_Recovery/` and add it to `.gitignore`
- [ ] Test clone on another machine: opens in Unity, Play works with the placeholder
- [ ] Record a 30–60 s gameplay video over Link (cab view, ploughing, night lights, tutorial stars) + a 10 s
  loop for the map tooltip
- [ ] Export the physics and benchmark charts (`physics_gears`, `bench_gpu`) as WebP
- [ ] Pick 6–8 screenshots for the gallery

**PrinterMonitor**

- [ ] Move `critique.md`, `main_review.md`, `debugging/` into `docs/` or delete them
- [ ] Add a dashboard screenshot or GIF to the README top

**AgriCulture_CNN**

- [ ] Move `best.pt` to a GitHub release asset or Git LFS
- [ ] Add a detection GIF; translate any Hungarian bits

**SolarSystem**

- [ ] Make the repo visible (or create a public one); README in English with a clip and the architecture
  diagram; frame it as a digital twin prototype

**Village project**

- [ ] Pick Sapi-Foglalo or movie_catalog; English README + one screenshot

**GitHub profile**

- [ ] Pin the featured repos; profile README with the one-line story and a link to the site

## Roadmap and Claude Code handoff

Build in an order where every phase leaves something usable: after phase 1 the site already works as a
plain portfolio, even with no map. *Ship a shareable CV first, then the map, then the polish.*

| Phase | Name | Contents | Gate |
|---|---|---|---|
| 0 | Prep the repos | Finish tractor repo, gameplay video, tidy READMEs, write project texts, pick domain | — |
| 1 | Content + CV | Astro + content, project pages, `/cv` page + PDF, per-project URLs, deploy to CF Pages | CV shareable |
| 2 | The map | Terrain render (draft), pan / zoom + fly-to, scroll panels, mobile journey path, keyboard nav | Works on a phone |
| 3 | Polish + launch | Final terrain render, fog of war, night theme, OG images + SEO, Lighthouse 90+ | Launch |

Later: Warchief's Keep · digital twin in the Observatory · 3D diorama easter egg.

Phase 0 runs alongside phase 1; the map art in phase 3 can keep improving after launch.

**Handoff to Claude Code (via the Warchief setup):**

1. Put this plan in the new repo as `docs/PLAN.md`, and a `CLAUDE.md` with the stack, the content schema,
   the performance budget and "never commit licensed assets".
2. One prompt per phase, not the whole site at once. Each prompt names its gate as the acceptance test
   (e.g. phase 1: "`/cv` passes Lighthouse ≥ 90 on mobile and the PDF matches the page").
3. Tractor repo is public; finish the three fixes in Pre-work before linking it from the site.
4. Mara writes the project texts herself (phase 0); the agents build the frame around them.

## Risks and open decisions

| Risk | Effect | Mitigation |
|---|---|---|
| Map art takes forever | Site never ships | Ship phase 1 with a low-res draft render; refine the Blender scene after the site works |
| Recruiters skip the map | Lost interviews | Banner with CV button above the fold; `/cv` + PDF; per-project URLs |
| Mobile feels broken | Most first visits are on phones | Journey-path layout instead of pan/zoom below 768 px |
| Licensed assets leak | Licence breach | Fresh public repo, tractor model purged and full history checked; Meta controller models still to purge |
| Gimmick over substance | Looks like a toy | Every panel leads with numbers, architecture and links to code |
| Trademark use | Takedown risk | Name "John Deere 6195M" factually; no JD logo or brand colours as site art |

**Open decisions:**

- [x] Art style: realistic terrain — decided
- [ ] Village: Sapi-Foglalo, movie_catalog, or neither
- [ ] Include Warchief's Keep at launch, or later
- [ ] Domain name
- [ ] Fantasy names for the regions (keep these, or invent new ones)
- [x] Photo of yourself on the Capital panel: decided (answer not recorded in the PDF)
