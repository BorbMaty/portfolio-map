import { getCollection, getEntry } from 'astro:content';

/** Projects sorted by `order`; drafts are visible in `astro dev` and excluded from production builds. */
export async function getProjects() {
  const all = await getCollection('projects', ({ data }) => !(import.meta.env.PROD && data.draft));
  return all.sort((a, b) => a.data.order - b.data.order);
}

/** The single CV entry from `src/content/cv.yaml`. Throws if the file is missing so the build fails loudly. */
export async function getCv() {
  const entry = await getEntry('cv', 'cv');
  if (!entry) throw new Error('src/content/cv.yaml not found or failed to load');
  return entry.data;
}
