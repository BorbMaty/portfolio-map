/**
 * Prints /cv to dist/cv.pdf with Playwright Chromium, so the PDF always matches the CV page.
 * Run after `astro build` (pnpm build:all does both). Node 24 runs this .ts file directly (type stripping),
 * so only erasable TypeScript syntax is allowed here.
 *
 * Exits non-zero if the server, browser or print step fails, or the PDF exceeds 2 pages,
 * so CI never deploys a site without a valid PDF.
 */
import { preview } from 'astro';
import { chromium } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const outPath = fileURLToPath(new URL('../dist/cv.pdf', import.meta.url));
const MAX_PAGES = 2; // CV page budget from the phase 1 spec (A4, 2 pages max)

// Port 4329 avoids clashing with `astro dev` (4321) if it is running.
const server = await preview({ root, server: { port: 4329 }, logLevel: 'warn' });
// Declared outside try so finally can close it; launched inside so a launch failure still stops the server.
let browser: Awaited<ReturnType<typeof chromium.launch>> | undefined;
try {
  browser = await chromium.launch();
  const page = await browser.newPage();
  const response = await page.goto(`http://localhost:${server.port}/cv/`, { waitUntil: 'networkidle' });
  if (!response?.ok()) throw new Error(`/cv returned HTTP ${response?.status()}`);
  // Web fonts must be ready, otherwise the PDF falls back to system fonts.
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: outPath, format: 'A4', printBackground: true });

  // Count pages by their "/Type /Page" objects (not "/Pages"); the 2-page budget is a hard failure.
  const pdf = (await readFile(outPath)).toString('latin1');
  const pages = pdf.match(/\/Type\s*\/Page(?!s)/g)?.length ?? 0;
  console.log(`cv.pdf written: ${outPath} (${pages} page${pages === 1 ? '' : 's'})`);
  if (pages > MAX_PAGES) {
    console.error(`error: cv.pdf has ${pages} pages, budget is ${MAX_PAGES}. Shorten the CV content.`);
    process.exitCode = 1;
  }
} finally {
  await browser?.close();
  await server.stop();
}
