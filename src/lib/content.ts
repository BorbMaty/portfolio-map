import { getCollection, getEntry } from 'astro:content';

/** Projects sorted by `order`; drafts are visible in `astro dev` and excluded from production builds. */
export async function getProjects() {
  const all = await getCollection('projects', ({ data }) => !(import.meta.env.PROD && data.draft));
  return all.sort((a, b) => a.data.order - b.data.order);
}

/** True for real URLs; TODO placeholders in cv.yaml are rendered as plain text instead of broken links. */
export const isUrl = (href: string) => /^https?:\/\//.test(href);

/** True when `email` looks like an address (so we never emit `mailto:TODO(Mara)`). */
export const isEmail = (email: string) => /^[^\s@]+@[^\s@]+$/.test(email);

/** The single CV entry from `src/content/cv.yaml`. Throws if the file is missing so the build fails loudly. */
export async function getCv() {
  const entry = await getEntry('cv', 'cv');
  if (!entry) throw new Error('src/content/cv.yaml not found or failed to load');
  return entry.data;
}
