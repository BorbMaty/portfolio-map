/**
 * Map regions and their landmark positions.
 * x, y are normalised 0–1 coordinates on the terrain render (terrain/scene.py, served as deep-zoom tiles), so they
 * stay valid whatever size the map is drawn at. The render's framing is frozen for this reason: a new render may
 * only change its size (4096 px now, 8192 px in phase 3.1). `zoom` is the phase 2.4 fly-to zoom level.
 * Positions come from the generator: terrain/gen_island.py places each landmark, terrain/scene.py projects it onto
 * the render and writes tiles-src/landmarks.json; copy the values here after a new render. The Keep is not generated
 * (phase "Later"); its spot on the western islet is set by hand.
 */
export interface Region {
  id: string;
  name: string;
  /** Project shown in this region; the landmark links to /projects/<slug>. */
  projectSlug?: string;
  /** Target for regions without a project (Capital → /about, Harbor → contact). */
  href?: string;
  x: number;
  y: number;
  zoom: number;
}

export const regions: Region[] = [
  { id: 'watchtower', name: 'The Watchtower', projectSlug: 'printer-monitor', x: 0.704, y: 0.349, zoom: 3 },
  { id: 'homestead', name: 'The Homestead', projectSlug: 'tractor-vr', x: 0.643, y: 0.641, zoom: 3 },
  { id: 'harvest-fields', name: 'Harvest Fields', projectSlug: 'agriculture-cnn', x: 0.357, y: 0.628, zoom: 3 },
  { id: 'observatory', name: 'The Observatory', projectSlug: 'solar-system', x: 0.847, y: 0.105, zoom: 3 },
  { id: 'capital', name: 'Capital', href: '/about/', x: 0.52, y: 0.547, zoom: 2 },
  { id: 'village', name: 'Village', projectSlug: 'sapi-foglalo', x: 0.265, y: 0.32, zoom: 3 },
  { id: 'harbor', name: 'Harbor', href: '/#contact', x: 0.531, y: 0.791, zoom: 2 },
  { id: 'keep', name: "Warchief's Keep", x: 0.1, y: 0.74, zoom: 3 },
];
