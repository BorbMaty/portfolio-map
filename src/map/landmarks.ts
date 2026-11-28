/**
 * The map's landmarks: regions that lead somewhere (published projects, or a fixed href like the Capital and
 * Harbor), with the label and link the map shows. Shared by the landing page and the project pages.
 */
import { getProjects } from '../lib/content';
import type { Landmark } from './MapIsland';
import { regions } from './regions';

/** All landmarks shown on the map, in regions.ts order. */
export async function getLandmarks(): Promise<Landmark[]> {
  const projects = await getProjects();
  return regions.flatMap((r) => {
    const project = projects.find((p) => p.data.slug === r.projectSlug);
    if (project) return [{ ...r, label: project.data.title, href: `/projects/${project.data.slug}/` }];
    if (r.href) return [{ ...r, label: r.id === 'capital' ? 'About' : 'Contact', href: r.href }];
    return [];
  });
}
