/**
 * Phase 1 smoke tests against the production build (see playwright.config.ts).
 * Project lists are read from the MDX frontmatter so new projects are covered automatically.
 */
import { test, expect } from '@playwright/test';
import { readdirSync, readFileSync } from 'node:fs';

// Minimal frontmatter read: only slug and draft are needed, and both are plain one-line scalars.
const projectDir = new URL('../src/content/projects/', import.meta.url);
const projects = readdirSync(projectDir)
  .filter((f) => f.endsWith('.mdx'))
  .map((f) => {
    const src = readFileSync(new URL(f, projectDir), 'utf8');
    const slug = src.match(/^slug:\s*(\S+)/m)?.[1];
    if (!slug) throw new Error(`${f}: no slug in frontmatter`);
    return { slug, draft: /^draft:\s*true\s*$/m.test(src), youtube: /^hero:\s*\n\s+kind:\s*youtube\b/m.test(src) };
  });
const published = projects.filter((p) => !p.draft).map((p) => p.slug);
const drafts = projects.filter((p) => p.draft).map((p) => p.slug);
const videoProjects = projects.filter((p) => !p.draft && p.youtube).map((p) => p.slug);

// Same fallback as astro.config.mjs: run the tests with the SITE_URL the build used.
const site = process.env.SITE_URL || 'http://localhost:4321';

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
