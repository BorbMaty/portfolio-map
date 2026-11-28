/**
 * Size of the terrain render, read at build time from the Deep Zoom metadata written by `pnpm tiles`.
 * The map frame uses it for its aspect ratio and the <img> width/height (no layout shift).
 */

export interface MapImageSize {
  width: number;
  height: number;
}

// Vite inlines the file's text at build time. A glob (not a plain `?raw` import) returns {} when the file is
// missing, so the error below can name the fix instead of a bare "failed to resolve import".
const dziFiles = import.meta.glob<string>('/public/map/terrain.dzi', { query: '?raw', import: 'default', eager: true });

/**
 * Reads `<Size Width=".." Height=".."/>` from public/map/terrain.dzi.
 * Throws when the tiles have not been generated, so the build fails loudly instead of shipping a map with no image.
 */
export function readMapImageSize(): MapImageSize {
  const xml = dziFiles['/public/map/terrain.dzi'];
  if (xml === undefined) {
    throw new Error('public/map/terrain.dzi not found: run `pnpm tiles` (see README, "Rebuild the terrain")');
  }
  const match = /<Size\s+Width="(\d+)"\s+Height="(\d+)"/.exec(xml);
  if (!match) throw new Error('public/map/terrain.dzi: no <Size Width Height> element');
  return { width: Number(match[1]), height: Number(match[2]) };
}
