"""Generate the fictional coast heightmap for the Blender terrain scene.

Land runs off the north and east edges; open sea lies west and south. Noise gives the natural
detail, and a few shaping steps guarantee the ground each landmark needs: a mountain backbone
(Observatory, Watchtower), a flat plain (Harvest Fields), a sheltered bay (Harbor) and a river
that forks at the Capital and reaches the sea through the bay.

Writes to tiles-src/ (git-ignored):
  - heightmap.png   16-bit greyscale, 0 = lowest point, 65535 = highest
  - heightmap.json  ground size, elevation range, sea level and landmark spots, read by scene.py

Usage: uv run --project terrain terrain/gen_island.py [--seed 7]
"""

from __future__ import annotations

import argparse
import json
import logging
from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parents[1] / "tiles-src"

# 1600 x 1200 px at 40 m/px: a 64 x 48 km realm, close to the real Reghin area it replaces.
WIDTH_PX, HEIGHT_PX = 1600, 1200
PIXEL_M = 40.0
SEA_LEVEL_M = 0.0

# Shaping constants below (positions, radii, heights) were tuned by eye on the seed-21 draft (2026-11-28).
# Positions and radii are fractions of the map width; heights are metres.

# Landmark spots as (x, y) fractions of the heightmap, x east, y south. Ids match src/map/regions.ts.
LANDMARKS: dict[str, tuple[float, float]] = {
    "observatory": (0.84, 0.16),
    "watchtower": (0.70, 0.36),
    "village": (0.27, 0.32),
    "capital": (0.52, 0.525),  # on the south-east bank of the fork, between the eastern and southern arms
    "homestead": (0.64, 0.62),
    "harvest-fields": (0.36, 0.60),
    "harbor": (0.53, 0.75),  # east of the river mouth, on the bay
}

# River: two branches meet at the fork beside the Capital, then one course runs south into the bay.
FORK = (0.50, 0.50)
RIVER = [
    [(0.69, 0.33), (0.61, 0.43), FORK],  # from the mountain foothills
    [(0.30, 0.14), (0.40, 0.36), FORK],  # from the north-west hills
    [FORK, (0.47, 0.66), (0.46, 0.84)],  # to the bay
]


def fbm(shape: tuple[int, int], cells: int, octaves: int, rng: np.random.Generator) -> np.ndarray:
    """Fractal value noise in 0-1: octaves of smooth random grids, each twice as fine and half as strong.

    Args:
        shape: (rows, cols) of the output.
        cells: grid cells across the longer side for the coarsest octave.
        octaves: number of octaves.
        rng: random generator (seeded, so the map is reproducible).

    Returns:
        Array of `shape` with values in [0, 1].
    """
    rows, cols = shape
    total = np.zeros(shape)
    amp_sum = 0.0
    for o in range(octaves):
        n = cells * 2**o
        gy, gx = max(2, round(n * rows / max(shape)) + 2), max(2, round(n * cols / max(shape)) + 2)
        grid = rng.random((gy, gx))
        # Sample the coarse grid at every pixel; smoothstep weights hide the grid lines (value noise).
        # The 1.001 keeps the last sample just below the last grid line, so iy + 1 stays inside the grid.
        fy = np.linspace(0, gy - 1.001, rows)[:, None]
        fx = np.linspace(0, gx - 1.001, cols)[None, :]
        iy, ix = fy.astype(int), fx.astype(int)
        ty, tx = fy - iy, fx - ix
        ty, tx = ty * ty * (3 - 2 * ty), tx * tx * (3 - 2 * tx)
        top = grid[iy, ix] * (1 - tx) + grid[iy, ix + 1] * tx
        bottom = grid[iy + 1, ix] * (1 - tx) + grid[iy + 1, ix + 1] * tx
        amp = 0.5**o
        total += amp * (top * (1 - ty) + bottom * ty)
        amp_sum += amp
    return total / amp_sum


def polyline_distance(x: np.ndarray, y: np.ndarray, points: list[tuple[float, float]], aspect: float) -> np.ndarray:
    """Distance (in heightmap-width units) from every pixel to a polyline.

    Args:
        x, y: pixel coordinates as fractions, broadcastable grids.
        points: polyline vertices as (x, y) fractions.
        aspect: height / width of the map, so y distances are measured in the same unit as x.

    Returns:
        Array of distances, the broadcast shape of x and y.
    """
    best = np.full(np.broadcast(x, y).shape, np.inf)
    for (x0, y0), (x1, y1) in pairwise(points):
        dx, dy = x1 - x0, (y1 - y0) * aspect
        # Project each pixel on the segment, clamp to its ends, take the distance to that point.
        # max(): a zero-length segment is a point; avoid dividing by zero.
        t = np.clip(((x - x0) * dx + (y - y0) * aspect * dy) / max(dx * dx + dy * dy, 1e-12), 0, 1)
        best = np.minimum(best, np.hypot(x - (x0 + t * dx), (y - y0) * aspect - t * dy))
    return best


def gaussian(x: np.ndarray, y: np.ndarray, cx: float, cy: float, radius: float, aspect: float) -> np.ndarray:
    """Round bump of height 1 at (cx, cy).

    Args:
        x, y: pixel coordinates as fractions (broadcastable grids).
        cx, cy: centre as fractions.
        radius: fall-off distance in map-width units (the bump is 1/e high at this distance).
        aspect: height / width of the map.

    Returns:
        Array in (0, 1], the broadcast shape of x and y.
    """
    return np.exp(-(((x - cx) ** 2 + ((y - cy) * aspect) ** 2) / radius**2))


def generate(seed: int, width_px: int = WIDTH_PX, height_px: int = HEIGHT_PX) -> np.ndarray:
    """Elevation grid in metres (sea level 0) for the fictional coast.

    Args:
        seed: random seed; the same seed always gives the same map.
        width_px, height_px: grid size (tests use a small one).

    Returns:
        Float array (height_px, width_px) of elevations in metres; below 0 is sea.
    """
    rng = np.random.default_rng(seed)
    aspect = height_px / width_px
    y, x = np.mgrid[0:height_px, 0:width_px]
    x, y = x / (width_px - 1), y / (height_px - 1)
    shape = (height_px, width_px)

    # Coast: land potential is positive inland, negative in the west and south sea strips;
    # min() of the two rounds the south-west corner. Coarse noise makes the shoreline wander.
    land = np.minimum((x - 0.13) / 0.2, (0.86 - y) / 0.2) + (fbm(shape, 4, 5, rng) - 0.5) * 1.4
    land += (fbm(shape, 24, 4, rng) - 0.5) * 0.6  # fine noise: coves and headlands along the shore
    land -= 2.2 * gaussian(x, y, 0.47, 0.86, 0.075, aspect)  # the Harbor's bay, cut into the south coast
    # Solid ground under every landmark: 1.5 outweighs the coast noise (at most about 1), so no seed puts a town
    # in the sea. `dry` (a tighter patch) later keeps the river channel off the landmark itself.
    dry = np.zeros(shape)
    for lx, ly in LANDMARKS.values():
        land += 1.5 * gaussian(x, y, lx, ly, 0.02, aspect)
        dry = np.maximum(dry, gaussian(x, y, lx, ly, 0.01, aspect))

    # Land relief: a gentle rise from the shore, rolling hills, and a north-east mountain backbone.
    hills = fbm(shape, 12, 7, rng)
    ridged = 1 - np.abs(2 * fbm(shape, 10, 6, rng) - 1)  # sharp crests where the noise crosses 0.5
    backbone = np.clip(
        1 - polyline_distance(x, y, [(1.02, 0.02), (0.84, 0.16), (0.70, 0.40), (0.78, 0.62)], aspect) / 0.16, 0, 1
    )
    peak = gaussian(x, y, *LANDMARKS["observatory"], 0.07, aspect)
    elevation = (
        60 * np.tanh(np.clip(land, 0, None) * 2)
        + 480 * hills * np.clip(land, 0, 1)
        + 1100 * backbone**1.5 * (0.45 + 0.55 * ridged)
        + 700 * peak
    )

    # Harvest Fields: blend towards a low, flat plain.
    plain = gaussian(x, y, *LANDMARKS["harvest-fields"], 0.11, aspect)
    elevation = elevation * (1 - plain) + 45 * plain
    # Harbor: a low quay a few metres above the water.
    quay = gaussian(x, y, *LANDMARKS["harbor"], 0.03, aspect)
    elevation = elevation * (1 - quay) + 6 * quay

    # River: a valley that softens the relief around the course, then a channel cut just below sea level,
    # so the rendered sea colour fills it.
    # Domain warp: measuring the distance from slightly shifted pixel positions bends the straight
    # polyline into meanders.
    # The warp fades out around the fork, so the fork stays where the layout puts it and the Capital stays dry.
    calm = 1 - gaussian(x, y, *FORK, 0.08, aspect)
    wx = x + 0.3 * (fbm(shape, 6, 3, rng) - 0.5) * calm
    wy = y + 0.3 * (fbm(shape, 6, 3, rng) - 0.5) * calm
    d = np.full(shape, np.inf)
    for branch in RIVER:
        d = np.minimum(d, polyline_distance(wx, wy, branch, aspect))
    valley = np.exp(-((d / 0.045) ** 2))
    # The channel is cut everywhere except right at a landmark: the warp can swing a branch onto one (e.g. the
    # Harbor for some seeds). The dry patch (0.01) is narrower than the Capital's 0.025 distance from the fork.
    channel = np.exp(-((d / 0.0035) ** 2)) * (1 - dry)
    elevation = elevation * (1 - 0.85 * valley)
    elevation = elevation * (1 - channel) - 4 * channel

    # Sea floor: smooth (little noise) so the water reads as calm; deeper away from the coast.
    sea_floor = 140 * np.clip(land, -3, 0)
    # Land stays at least 1 m above the sea, except in the river channel, which must hold water.
    land_elevation = np.where(channel >= 0.5, elevation, np.maximum(elevation, 1.0))
    return np.where(land > 0, land_elevation, sea_floor)


def to_uint16(elev_m: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Stretch elevations to the full 16-bit range. Returns (heightmap, min_m, max_m).

    Raises:
        ValueError: if the grid is flat.
    """
    lo, hi = float(elev_m.min()), float(elev_m.max())
    if hi <= lo:
        raise ValueError("elevation grid is flat")
    return np.round((elev_m - lo) / (hi - lo) * 65535).astype(np.uint16), lo, hi


def main() -> None:
    """Generate the coast and write heightmap.png + heightmap.json."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=21, help="random seed (same seed = same map); 21 chosen 2026-11-28")
    seed = parser.parse_args().seed

    elevation = generate(seed)
    heightmap, lo, hi = to_uint16(elevation)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(heightmap).save(OUT_DIR / "heightmap.png")  # uint16 array -> 16-bit greyscale PNG

    rows, cols = heightmap.shape
    meta = {
        "seed": seed,
        "pixels": {"width": cols, "height": rows},
        "size_m": {"width": cols * PIXEL_M, "height": rows * PIXEL_M},
        "elevation_m": {"min": lo, "max": hi},
        "sea_level_m": SEA_LEVEL_M,
        # Elevation at each landmark, so scene.py can project it onto the tilted render.
        "landmarks": {
            name: {"x": x, "y": y, "elevation_m": float(elevation[round(y * (rows - 1)), round(x * (cols - 1))])}
            for name, (x, y) in LANDMARKS.items()
        },
    }
    (OUT_DIR / "heightmap.json").write_text(json.dumps(meta, indent=2))
    log.info("seed %d: %dx%d px, %.0f to %.0f m", seed, cols, rows, lo, hi)


if __name__ == "__main__":
    main()
