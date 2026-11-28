/**
 * Map island. The server renders the terrain preview with landmark links placed by normalised coordinates, so the
 * map works without JS. Hydrated with `client:visible`: once the map scrolls into view, OpenSeadragon (loaded as a
 * separate chunk) shows the deep-zoom tiles over the preview, and the landmarks follow every pan and zoom.
 * Hidden below 768 px by CSS (so it never becomes visible and never loads); mobile visitors use the quest log.
 */
import { useEffect, useRef } from 'preact/hooks';
import type OpenSeadragon from 'openseadragon';
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
  /** Full render size in px (from terrain.dzi); sets the frame's aspect ratio so landmarks land on the right pixels. */
  width: number;
  height: number;
}

/** Zoom factor of one button press. */
const ZOOM_STEP = 1.6;

export default function MapIsland({ landmarks, width, height }: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const viewerEl = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const viewer = useRef<OpenSeadragon.Viewer | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Dynamic import: OpenSeadragon (~87 KB gzipped) is its own chunk, fetched only once the map is visible.
    import('openseadragon').then(({ default: OSD }) => {
      if (cancelled || !viewerEl.current) return;
      const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
      const v = OSD({
        element: viewerEl.current,
        tileSources: '/map/terrain.dzi',
        showNavigationControl: false, // own buttons below; the default ones load extra images
        // The wheel scrolls the page, not the map: a landing page must not trap scrolling. Zoom is by buttons,
        // double-click or pinch.
        gestureSettingsMouse: { scrollToZoom: false },
        animationTime: reduceMotion ? 0 : 1.2,
        visibilityRatio: 1, // the map can't be dragged out of its frame
        constrainDuringPan: true,
        minZoomLevel: 1, // the frame has the image's aspect ratio, so zoom 1 is the whole map
      });
      viewer.current = v;

      // Landmarks stay in their own list (accessible, owned by Preact); on every frame drawn, each marker moves
      // to the screen pixel of its map point.
      const items = Array.from(list.current?.querySelectorAll<HTMLLIElement>('li') ?? []);
      const place = () => {
        items.forEach((li, i) => {
          const point = v.viewport.imageToViewportCoordinates(landmarks[i].x * width, landmarks[i].y * height);
          const px = v.viewport.pixelFromPoint(point, true);
          li.style.left = `${px.x}px`;
          li.style.top = `${px.y}px`;
        });
      };
      v.addHandler('update-viewport', place);
      v.addHandler('open', () => {
        frame.current?.classList.add('is-live');
        // Keep the preview underneath until the first full view is drawn, so there is no blank flash.
        v.world.getItemAt(0).addOnceHandler('fully-loaded-change', () => frame.current?.classList.add('is-loaded'));
      });
    });
    return () => {
      cancelled = true;
      viewer.current?.destroy();
      viewer.current = null;
    };
  }, []);

  const zoom = (factor: number) => {
    viewer.current?.viewport.zoomBy(factor);
    viewer.current?.viewport.applyConstraints();
  };

  return (
    <div class="map-frame" ref={frame} style={{ aspectRatio: `${width} / ${height}` }}>
      <img src="/map/preview.webp" alt="" width={width} height={height} loading="lazy" decoding="async" />
      <div class="map-viewer" ref={viewerEl} />
      <ul class="map-landmarks" ref={list}>
        {landmarks.map((l) => (
          <li key={l.id} style={{ left: `${l.x * 100}%`, top: `${l.y * 100}%` }}>
            <a href={l.href} aria-label={`${l.name}: ${l.label}`}>
              {l.name}
            </a>
          </li>
        ))}
      </ul>
      <div class="map-zoom">
        <button type="button" aria-label="Zoom in" onClick={() => zoom(ZOOM_STEP)}>
          +
        </button>
        <button type="button" aria-label="Zoom out" onClick={() => zoom(1 / ZOOM_STEP)}>
          −
        </button>
      </div>
    </div>
  );
}
