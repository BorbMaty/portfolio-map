/**
 * Phase 1 smoke tests against the production build (see playwright.config.ts).
 * Project lists are read from the MDX frontmatter so new projects are covered automatically.
 */
import { test, expect } from '@playwright/test';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { isDraftSource } from '../src/lib/draft.ts';

// Minimal frontmatter read: only slug and draft are needed, and both are plain one-line scalars.
const projectDir = new URL('../src/content/projects/', import.meta.url);
const projects = readdirSync(projectDir)
  .filter((f) => f.endsWith('.mdx'))
  .map((f) => {
    const src = readFileSync(new URL(f, projectDir), 'utf8');
    const slug = src.match(/^slug:\s*(\S+)/m)?.[1];
    if (!slug) throw new Error(`${f}: no slug in frontmatter`);
    return { slug, draft: isDraftSource(src), youtube: /^hero:\s*\n\s+kind:\s*youtube\b/m.test(src) };
  });
const published = projects.filter((p) => !p.draft).map((p) => p.slug);
const drafts = projects.filter((p) => p.draft).map((p) => p.slug);
const videoProjects = projects.filter((p) => !p.draft && p.youtube).map((p) => p.slug);

// Same fallback as astro.config.mjs: run the tests with the SITE_URL the build used.
const site = process.env.SITE_URL || 'http://localhost:4321';

test('isDraftSource reads only the frontmatter and every YAML spelling of true', () => {
  expect(isDraftSource('---\ntitle: a\ndraft: true\n---\nbody')).toBe(true);
  expect(isDraftSource('---\r\ndraft: True  # wip\r\n---\r\n')).toBe(true);
  expect(isDraftSource('---\ndraft: false\n---\n')).toBe(false);
  expect(isDraftSource('---\ntitle: a\n---\n```yaml\ndraft: true\n```\n')).toBe(false);
});

test('there is at least one published project', () => {
  expect(published.length).toBeGreaterThan(0);
});

for (const path of ['/', '/cv/', '/about/', '/cv.pdf', ...published.map((s) => `/projects/${s}/`)]) {
  test(`GET ${path} returns 200`, async ({ request }) => {
    const res = await request.get(path);
    expect(res.status()).toBe(200);
  });
}

test('unknown route shows the 404 page', async ({ page }) => {
  // Slash-ending path: with trailingSlash 'always', astro preview answers slash-less URLs with its own bare
  // 404 before reaching 404.html (Cloudflare Pages serves 404.html for any unknown path).
  const res = await page.goto('/no-such-page/');
  expect(res?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Here be dragons');
  // Not a real page: crawlers must not index it, and it must not claim a canonical URL.
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex');
  await expect(page.locator('link[rel="canonical"], meta[property="og:url"]')).toHaveCount(0);
});

test('internal links resolve directly, without redirects', async ({ page, request }) => {
  // Collect every same-site link from every page, then require a direct 200: a slash-less page link
  // would cost a redirect per click on Cloudflare Pages.
  const pages = ['/', '/cv/', '/about/', ...published.map((s) => `/projects/${s}/`)];
  const links = new Set<string>();
  for (const path of pages) {
    await page.goto(path);
    for (const href of await page.locator('a[href^="/"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')!))) {
      links.add(href.split('#')[0] || '/');
    }
  }
  for (const href of links) {
    const res = await request.get(href, { maxRedirects: 0 });
    expect(res.status(), `link ${href}`).toBe(200);
  }
});

test('/cv has exactly one h1', async ({ page }) => {
  await page.goto('/cv/');
  await expect(page.locator('h1')).toHaveCount(1);
});

for (const slug of published) {
  test(`project ${slug} has title, pitch, a link and OG tags`, async ({ page }) => {
    await page.goto(`/projects/${slug}/`);
    const title = (await page.locator('h1').innerText()).trim();
    expect(title).not.toBe('');
    await expect(page.locator('.pitch')).not.toBeEmpty();
    expect(await page.locator('.links a[href]').count()).toBeGreaterThanOrEqual(1);
    // Plain string checks (no RegExp built from content, so titles like "C++" can't break them).
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content');
    expect(ogTitle?.startsWith(title)).toBe(true);
    // Exact absolute URLs on the configured site, so a localhost build can never pass for production.
    const expectedUrl = new URL(`/projects/${slug}/`, site).href;
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', expectedUrl);
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute('content', expectedUrl);
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content');
    expect(new URL(ogImage ?? '').origin).toBe(new URL(site).origin);
  });
}

for (const slug of drafts) {
  test(`draft ${slug} is not published or linked`, async ({ page, request }) => {
    expect((await request.get(`/projects/${slug}/`)).status()).toBe(404);
    for (const path of ['/', '/cv/']) {
      await page.goto(path);
      await expect(page.locator(`a[href*="/projects/${slug}"]`)).toHaveCount(0);
    }
  });
}

test('every image has alt text; content images describe themselves', async ({ page }) => {
  for (const path of ['/', '/cv/', '/about/', ...published.map((s) => `/projects/${s}/`)]) {
    await page.goto(path);
    // Decorative images (quest-log thumbnails, map backdrop) carry alt="" on purpose; a missing attribute is a bug.
    await expect(page.locator('img:not([alt])'), `${path}: <img> without alt`).toHaveCount(0);
    // Images inside the project panel (hero, body figures, gallery) are content and need a description.
    await expect(page.locator('.panel img[alt=""]'), `${path}: content image with empty alt`).toHaveCount(0);
  }
  // Guard against a vacuous pass: if `.panel` were renamed, the selector above would match nothing.
  await page.goto(`/projects/${published[0]}/`);
  expect(await page.locator('.panel img').count()).toBeGreaterThan(0);
});

test('Download CV saves a real PDF with a name-based ASCII filename', async ({ page }) => {
  for (const path of ['/', '/cv/']) {
    await page.goto(path);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('link', { name: 'Download CV (PDF)' }).click(),
    ]);
    // e.g. Matyas-Levente-Borbath-CV.pdf: accents stripped, never the bare "cv.pdf" or an error page saved as .htm.
    expect(download.suggestedFilename(), path).toMatch(/^[A-Za-z0-9]+(-[A-Za-z0-9]+)*-CV\.pdf$/);
    const head = readFileSync(await download.path()).subarray(0, 5).toString('latin1');
    expect(head, `${path}: downloaded file is not a PDF`).toBe('%PDF-');
  }
});

test('quest-log images are never upscaled from a too-small source', async ({ page }) => {
  // For srcset images Chrome reports naturalWidth as the slot width it derived from `sizes`; if that is smaller than
  // the rendered width, the chosen file is stretched (the blurry flagship cards fixed on 2026-11-28).
  for (const width of [800, 1000, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    const imgs = page.locator('.quest img');
    await imgs.last().scrollIntoViewIfNeeded();
    for (const img of await imgs.all()) {
      await expect(img).toHaveJSProperty('complete', true);
      const { shown, slot } = await img.evaluate((i: HTMLImageElement) => ({
        shown: i.getBoundingClientRect().width,
        slot: i.naturalWidth,
      }));
      expect(slot, `viewport ${width}: ${await img.getAttribute('src')}`).toBeGreaterThanOrEqual(Math.floor(shown));
    }
  }
});

test('the landing page ships no map JS until phase 2.3', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('astro-island')).toHaveCount(0);
});

test('no draft media is copied into dist/', () => {
  const files = (dir: URL) =>
    readdirSync(dir, { recursive: true, withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => join(e.parentPath, e.name));
  const hash = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
  // Byte-identical copies are what leaks: Astro emits an imported original and only deletes it after transforming it.
  const distHashes = new Set(files(new URL('../dist/', import.meta.url)).map(hash));
  for (const slug of drafts) {
    const media = new URL(`../src/assets/media/${slug}/`, import.meta.url);
    if (!existsSync(media)) continue;
    for (const file of files(media)) {
      expect(distHashes.has(hash(file)), `draft media ${file} found in dist/`).toBe(false);
    }
  }
});

test('the production build contains no TODO( placeholders', () => {
  // Scans every text file in dist/. cv.pdf is printed from /cv/, so a clean cv/index.html means a clean PDF
  // (the PDF itself stores text in compressed streams, which a plain search can't read).
  const dist = new URL('../dist/', import.meta.url);
  const offenders = readdirSync(dist, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && /\.(html|xml|txt|json|js|css)$/.test(e.name))
    .map((e) => join(e.parentPath, e.name))
    .filter((file) => readFileSync(file, 'utf8').includes('TODO('));
  expect(offenders, 'files still containing TODO(').toEqual([]);
});

test('YouTube heroes load no iframe until the poster is clicked', async ({ page }) => {
  // Dormant until a project has a video hero (tractor-vr uses an image until its video is uploaded).
  test.skip(videoProjects.length === 0, 'no published project has a YouTube hero yet');
  // Block YouTube itself so the test stays offline and fast; only the iframe insertion matters.
  await page.route(/youtube(-nocookie)?\.com/, (route) => route.abort());
  for (const slug of videoProjects) {
    await page.goto(`/projects/${slug}/`);
    await expect(page.locator('iframe')).toHaveCount(0);
    await expect(page.locator('.video .play')).toHaveAttribute('href', /^https:\/\/www\.youtube\.com\/watch\?v=/);
    await page.locator('.video .play').click();
    await expect(page.locator('iframe[src*="youtube-nocookie.com/embed/"]')).toHaveCount(1);
  }
});

// The landing page size budget (< 300 KB) is asserted by Lighthouse CI (lighthouserc.json), which measures
// real transfer sizes including lazy-loaded resources.
