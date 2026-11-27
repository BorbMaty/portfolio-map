/**
 * Map island. Phase 1: a static 16:9 draft image with landmark links placed by normalised coordinates.
 * Rendered on the server only (no client directive), so phase 1 ships no map JS.
 * Phase 2.3 replaces the <img> with OpenSeadragon deep-zoom tiles, hydrates it, and keeps the landmark overlay.
 * Hidden below 768 px by CSS; mobile visitors use the quest log instead.
 */
import './map.css';

export interface Landmark {
  id: string;
  name: string;
  /** Short description used in the accessible name, e.g. the project title. */
  label: string;
  href: string;
  /** Normalised 0–1 position on the map image. */
  x: number;
  y: number;
}

interface Props {
  landmarks: Landmark[];
}

export default function MapIsland({ landmarks }: Props) {
  return (
    <div class="map-frame">
      <img src="/map/draft.webp" alt="" width={1600} height={900} loading="lazy" decoding="async" />
      <ul class="map-landmarks">
        {landmarks.map((l) => (
          <li key={l.id} style={{ left: `${l.x * 100}%`, top: `${l.y * 100}%` }}>
            <a href={l.href} aria-label={`${l.name}: ${l.label}`}>
              {l.name}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
