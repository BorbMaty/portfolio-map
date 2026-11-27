/**
 * Map regions and their landmark positions.
 * x, y are normalised 0–1 coordinates on the final terrain image (phase 2: a ~8192² Blender render served as
 * deep-zoom tiles via OpenSeadragon), so they stay valid whatever size the map is drawn at.
 * Positions are rough placeholders until the terrain render exists; `zoom` is the phase 2 fly-to zoom level.
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
  { id: 'watchtower', name: 'The Watchtower', projectSlug: 'printer-monitor', x: 0.62, y: 0.38, zoom: 3 },
  { id: 'homestead', name: 'The Homestead', projectSlug: 'tractor-vr', x: 0.45, y: 0.58, zoom: 3 },
  { id: 'harvest-fields', name: 'Harvest Fields', projectSlug: 'agriculture-cnn', x: 0.52, y: 0.64, zoom: 3 },
  { id: 'observatory', name: 'The Observatory', projectSlug: 'solar-system', x: 0.78, y: 0.18, zoom: 3 },
  { id: 'capital', name: 'Capital', href: '/about', x: 0.4, y: 0.45, zoom: 2 },
  { id: 'village', name: 'Village', projectSlug: 'village', x: 0.28, y: 0.55, zoom: 3 },
  { id: 'harbor', name: 'Harbor', href: '/#contact', x: 0.35, y: 0.86, zoom: 2 },
  { id: 'keep', name: "Warchief's Keep", x: 0.15, y: 0.3, zoom: 3 },
];
