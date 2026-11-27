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
    return { slug, draft: /^draft:\s*true\s*$/m.test(src) };
  });
const published = projects.filter((p) => !p.draft).map((p) => p.slug);
const drafts = projects.filter((p) => p.draft).map((p) => p.slug);

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
  const res = await page.goto('/no-such-page');
  expect(res?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Here be dragons');
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
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', new RegExp(`^${title}`));
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute('content', new RegExp(`/projects/${slug}/?$`));
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', /^https?:\/\//);
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

test('YouTube iframe is absent until the poster is clicked', async ({ page }) => {
  // Block YouTube itself so the test stays offline and fast; only the iframe insertion matters.
  await page.route(/youtube(-nocookie)?\.com/, (route) => route.abort());
  await page.goto('/projects/tractor-vr/');
  await expect(page.locator('iframe')).toHaveCount(0);
  await page.locator('.video button').click();
  await expect(page.locator('iframe[src*="youtube-nocookie.com/embed/"]')).toHaveCount(1);
});

test('landing page stays under 300 KB before the map image', async ({ page }) => {
  // Sums uncompressed bodies (preview does not compress), so the real transfer is smaller than this.
  let bytes = 0;
  page.on('response', async (res) => {
    if (res.url().includes('/map/')) return;
    bytes += (await res.body().catch(() => Buffer.alloc(0))).length;
  });
  await page.goto('/', { waitUntil: 'networkidle' });
  expect(bytes).toBeLessThan(300 * 1024);
});
