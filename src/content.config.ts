/**
 * Content collections: the single source of truth for project pages, the quest log, /cv and the PDF.
 * Astro 7 loader API (the old `src/content/config.ts` location is gone since Astro 5).
 */
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { isDraftSource } from './lib/draft';

// Production builds never load drafts: Astro only deletes an original image after transforming it, so an
// image imported by an unrendered draft would still be copied into dist/. `astro dev` keeps drafts visible.
// `?raw` reads the files as text (no MDX compile, no Node types needed); same frontmatter check as the tests.
const projectSources = import.meta.glob<string>('./content/projects/*.mdx', { query: '?raw', import: 'default', eager: true });
const draftFiles = import.meta.env.PROD
  ? Object.entries(projectSources)
      .filter(([, src]) => isDraftSource(src))
      .map(([path]) => path.split('/').pop()!)
  : [];

const projects = defineCollection({
  loader: glob({ pattern: ['*.mdx', ...draftFiles.map((f) => `!${f}`)], base: './src/content/projects' }),
  // `image` validates and imports local images so astro:assets can emit AVIF/WebP + srcset.
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      slug: z.string().regex(/^[a-z0-9-]+$/, 'kebab-case only, used in /projects/<slug>'),
      region: z.string(),
      regionId: z.enum(['homestead', 'watchtower', 'harvest-fields', 'observatory', 'village', 'keep']),
      weight: z.enum(['flagship', 'medium', 'small']),
      order: z.number(),
      pitch: z.string().max(120),
      period: z.string(),
      role: z.string(),
      stack: z.array(z.string()),
      metrics: z.array(z.object({ label: z.string(), value: z.string() })).max(4),
      links: z.array(
        z.object({
          label: z.string(),
          href: z.string(),
          kind: z.enum(['repo', 'docs', 'video', 'live']),
        }),
      ),
      // Image heroes are imported files; YouTube heroes carry the video id in `src` and an optional poster image.
      hero: z.discriminatedUnion('kind', [
        z.object({ kind: z.literal('image'), src: image(), alt: z.string().trim().min(1) }),
        z.object({
          kind: z.literal('youtube'),
          // YouTube ids are 11 chars of [A-Za-z0-9_-]; a placeholder or a pasted URL fails the build here.
          src: z.string().regex(/^[\w-]{11}$/, 'YouTube video id (11 characters), not a URL or placeholder'),
          alt: z.string().trim().min(1),
          poster: image().optional(),
        }),
      ]),
      // Screenshots shown under the body, in this order. Alt text is required here and on heroes: an empty or blank alt fails the build.
      gallery: z.array(z.object({ src: image(), alt: z.string().trim().min(1) })).default([]),
      draft: z.boolean().default(false),
    }),
});

const cv = defineCollection({
  loader: glob({ pattern: 'cv.yaml', base: './src/content' }),
  schema: z.object({
    name: z.string(),
    headline: z.string(),
    location: z.string(),
    email: z.string(),
    links: z.array(z.object({ label: z.string(), href: z.string() })),
    summary: z.string(),
    education: z.array(
      z.object({ degree: z.string(), school: z.string(), period: z.string(), details: z.array(z.string()) }),
    ),
    skills: z.array(z.object({ group: z.string(), items: z.array(z.string()) })),
    experience: z.array(
      z.object({ title: z.string(), org: z.string(), period: z.string(), details: z.array(z.string()) }),
    ),
    languages: z.array(z.object({ name: z.string(), level: z.string() })),
  }),
});

export const collections = { projects, cv };
