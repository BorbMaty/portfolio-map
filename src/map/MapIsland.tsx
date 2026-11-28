/**
 * Map island. The server renders the terrain preview with landmark links placed by normalised coordinates, so the
 * map works without JS. Hydrated with `client:visible`: once the map scrolls into view, OpenSeadragon (loaded as a
 * separate chunk) shows the deep-zoom tiles over the preview, and the landmarks follow every pan and zoom.
 * Clicking a landmark flies the view to it, then follows the link; a project page opens the map already showing its
 * landmark (`focusId`), so the flight and the page read as one move.
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
  /** Zoom level the map flies to for this landmark (1 = whole map). */
  zoom: number;
}

interface Props {
  landmarks: Landmark[];
  /** Full render size in px (from terrain.dzi); sets the frame's aspect ratio so landmarks land on the right pixels. */
  width: number;
  height: number;
  /** Landmark to open on (a project page): the map starts zoomed onto it instead of showing the whole map. */
  focusId?: string;
}

/** Zoom factor of one button press. */
const ZOOM_STEP = 1.6;

/** Where a focused landmark sits across the frame (0-1): left of centre, clear of the project panel on the right. */
const FOCUS_X = 0.3;

/** Longest a flight may take before the link is followed anyway (animation 1.2 s plus margin), in ms. */
const FLIGHT_TIMEOUT_MS = 1600;

const prefersReducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function MapIsland({ landmarks, width, height, focusId }: Props) {
  const frame = useRef<HTMLDivElement>(null);
  const viewerEl = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const viewer = useRef<OpenSeadragon.Viewer | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Dynamic import: OpenSeadragon (~87 KB gzipped) is its own chunk, fetched only once the map is visible.
    import('openseadragon').then(({ default: OSD }) => {
      if (cancelled || !viewerEl.current) return;
      const reduceMotion = prefersReducedMotion();
      const v = OSD({
        element: viewerEl.current,
        tileSources: '/map/terrain.dzi',
        showNavigationControl: false, // own buttons below; the default ones load extra images
        // The wheel scrolls the page, not the map: a landing page must not trap scrolling (decided 2026-11-28).
        // Zoom is by buttons, double-click or pinch; a single click does nothing, so clicking around is safe.
        gestureSettingsMouse: { scrollToZoom: false, clickToZoom: false, dblClickToZoom: true },
        animationTime: reduceMotion ? 0 : 1.2,
        visibilityRatio: 1, // the map can't be dragged out of its frame
        constrainDuringPan: true,
        minZoomLevel: 1, // the frame has the image's aspect ratio, so zoom 1 is the whole map
      });
      viewer.current = v;

      // The canvas is a tab stop (OpenSeadragon's keyboard panning): give it a name. Its built-in flip (f) and
      // rotate (r) keys would turn the terrain under the landmark labels, so they are switched off.
      v.canvas.setAttribute('aria-label', 'Map: drag or use the arrow keys to pan');
      v.addHandler('canvas-key', (e) => {
        const key = (e.originalEvent as KeyboardEvent).code;
        if (key === 'KeyF' || key === 'KeyR') e.preventDefaultAction = true;
      });

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
        const focus = landmarks.find((l) => l.id === focusId);
        if (focus) show(v, focus, true);
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

  /** Zoom onto a landmark and place it at FOCUS_X across the frame (OpenSeadragon clamps it near the map edges). */
  const show = (v: OpenSeadragon.Viewer, l: Landmark, immediately: boolean) => {
    // Viewport width is 1 at zoom 1, so at zoom z the view spans 1/z: shift the centre right by (0.5 - FOCUS_X)/z,
    // written in image pixels (the viewport's x unit is the image width).
    const centre = v.viewport.imageToViewportCoordinates((l.x + (0.5 - FOCUS_X) / l.zoom) * width, l.y * height);
    v.viewport.zoomTo(l.zoom, undefined, immediately);
    v.viewport.panTo(centre, immediately);
    v.viewport.applyConstraints(immediately);
  };

  /** Landmark click: fly there, then follow the link. Modified clicks keep normal link behaviour (new tab etc.). */
  const fly = (e: MouseEvent, l: Landmark) => {
    const v = viewer.current;
    if (!v || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || prefersReducedMotion()) return;
    e.preventDefault();
    let gone = false;
    const go = () => {
      if (gone) return;
      gone = true;
      location.assign(l.href);
    };
    // animation-finish never fires if the view is already there, hence the timeout as well.
    v.addOnceHandler('animation-finish', go);
    setTimeout(go, FLIGHT_TIMEOUT_MS);
    show(v, l, false);
  };

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
            <a href={l.href} aria-label={`${l.name}: ${l.label}`} onClick={(e) => fly(e, l)}>
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
