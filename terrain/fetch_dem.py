"""Download Copernicus GLO-30 DEM tiles and cut a heightmap for the Blender terrain scene.

Writes to `tiles-src/` (git-ignored):
  - dem/<tile>.tif   raw 1x1 degree tiles, downloaded once
  - heightmap.png    16-bit greyscale, 0 = lowest point, 65535 = highest
  - heightmap.json   bbox, size in metres and the real elevation range, read by scene.py

Usage: uv run fetch_dem.py [--bbox SOUTH WEST NORTH EAST]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import shutil
import urllib.error
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge

log = logging.getLogger(__name__)

OUT_DIR = Path(__file__).resolve().parents[1] / "tiles-src"

# Reghin, the edge of Mezoseg and the Gorgenyi foothills (degrees, WGS84).
DEFAULT_BBOX = (46.60, 24.40, 47.00, 25.05)

# Public AWS Open Data bucket, plain HTTPS, no account needed.
# Layout: https://copernicus-dem-30m.s3.amazonaws.com/readme.html
TILE_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"

# GLO-30 pixel pitch along latitude: 1 arc second.
RES_LAT_DEG = 1 / 3600

# Metres per degree of latitude at ~47 N on the WGS84 ellipsoid (meridian arc,
# 111 132.95 - 559.85 cos 2phi; Snyder, "Map Projections - A Working Manual", USGS 1987, p. 25).
M_PER_DEG_LAT = 111_170.0

# GLO-30 is georeferenced pixel-is-point: tile N46 E024 really spans lat 46.00014-47.00014 and
# lon 23.99986-24.99986, i.e. it is shifted half a pixel north and west of its whole-degree name.
# shortcut: assumes 1" lon spacing, true below 50 N; above that GLO-30 widens it, so revisit if the bbox moves north.
HALF_PX_DEG = RES_LAT_DEG / 2


def tile_names(south: float, west: float, north: float, east: float) -> list[str]:
    """List the 1x1 degree GLO-30 tile names that cover a bbox.

    Args:
        south, west, north, east: bbox edges in degrees (northern/eastern hemisphere only).

    Returns:
        Tile names such as "Copernicus_DSM_COG_10_N46_00_E024_00_DEM".

    Raises:
        ValueError: if the bbox is empty or not in the N/E hemisphere.
    """
    if not (0 <= south < north and 0 <= west < east):
        raise ValueError(f"bbox must be non-empty and in the N/E hemisphere, got {(south, west, north, east)}")
    names = []
    # A point at lat y lies in tile floor(y - half px), at lon x in tile floor(x + half px) (see HALF_PX_DEG);
    # so a south or east edge on a whole degree needs the neighbouring tile for its last row/column.
    for lat in range(math.floor(south - HALF_PX_DEG), math.ceil(north - HALF_PX_DEG)):
        for lon in range(math.floor(west + HALF_PX_DEG), math.ceil(east + HALF_PX_DEG)):
            names.append(f"Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM")
    return names


def lon_resolution(lat_mid_deg: float) -> float:
    """Longitude step (degrees) that gives square pixels on the ground at a latitude.

    A degree of longitude is cos(latitude) times as long as a degree of latitude, so the
    step must grow by 1/cos to cover the same metres. Over a ~0.5 degree area this flat
    approximation is well under 1 % off, so no real map projection is needed.
    """
    return RES_LAT_DEG / math.cos(math.radians(lat_mid_deg))


def to_uint16(elev_m: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Stretch elevations to the full 16-bit range.

    Args:
        elev_m: elevation grid in metres.

    Returns:
        (heightmap, min_m, max_m): the uint16 grid and the real range it maps to.

    Raises:
        ValueError: if the grid has NaN (missing data) or is flat, since the stretch would divide by zero.
    """
    if np.isnan(elev_m).any():
        raise ValueError("elevation grid has NaN pixels: a tile is missing or the bbox leaves the data")
    lo, hi = float(elev_m.min()), float(elev_m.max())
    if hi <= lo:
        raise ValueError("elevation grid is flat")
    scaled = (elev_m - lo) / (hi - lo) * 65535
    return np.round(scaled).astype(np.uint16), lo, hi


def download(name: str, dem_dir: Path) -> Path:
    """Fetch one tile unless it is already on disk.

    Args:
        name: GLO-30 tile name (see tile_names).
        dem_dir: folder the .tif is stored in.

    Returns:
        Path of the local .tif.

    Raises:
        RuntimeError: if the tile does not exist in GLO-30 (sea or a void) or the server errors.
        urllib.error.URLError / TimeoutError: on network failure.
    """
    path = dem_dir / f"{name}.tif"
    if path.exists():
        return path
    url = TILE_URL.format(name=name)
    log.info("downloading %s", url)
    tmp = path.with_suffix(".part")
    # Write to .part first so an interrupted download never looks like a finished tile.
    try:
        # 60 s per read, so a stalled S3 connection fails instead of hanging forever.
        with urllib.request.urlopen(url, timeout=60) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except urllib.error.HTTPError as e:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"tile {name} not available in GLO-30 (HTTP {e.code}; sea or void?)") from e
    tmp.replace(path)
    return path


def main() -> None:
    """Download the tiles, crop and resample to square pixels, write heightmap.png + .json.

    Raises:
        ValueError: on a bad bbox, or if the cropped grid has missing data or is flat.
        RuntimeError: if a tile cannot be downloaded.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"), default=DEFAULT_BBOX)
    south, west, north, east = parser.parse_args().bbox

    dem_dir = OUT_DIR / "dem"
    dem_dir.mkdir(parents=True, exist_ok=True)
    paths = [download(n, dem_dir) for n in tile_names(south, west, north, east)]

    # merge() mosaics the tiles, crops to the bbox and resamples in one pass;
    # the wider longitude step makes each output pixel square on the ground.
    lat_mid = (south + north) / 2
    sources = [rasterio.open(p) for p in paths]
    try:
        mosaic, _ = merge(
            sources,
            bounds=(west, south, east, north),
            res=(lon_resolution(lat_mid), RES_LAT_DEG),
            resampling=rasterio.enums.Resampling.bilinear,
            nodata=np.nan,  # uncovered pixels become NaN, which to_uint16 rejects, instead of a silent 0 m
        )
    finally:
        for s in sources:
            s.close()

    heightmap, lo, hi = to_uint16(mosaic[0])
    rows, cols = heightmap.shape
    png = OUT_DIR / "heightmap.png"
    with warnings.catch_warnings():
        # A PNG holds no geodata by design; the bbox goes to heightmap.json instead.
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(png, "w", driver="PNG", width=cols, height=rows, count=1, dtype="uint16") as dst:
            dst.write(heightmap, 1)

    pixel_m = RES_LAT_DEG * M_PER_DEG_LAT
    meta = {
        "bbox": {"south": south, "west": west, "north": north, "east": east},
        "pixels": {"width": cols, "height": rows},
        "size_m": {"width": cols * pixel_m, "height": rows * pixel_m},
        "elevation_m": {"min": lo, "max": hi},
    }
    (OUT_DIR / "heightmap.json").write_text(json.dumps(meta, indent=2))
    log.info("wrote %s (%dx%d px, %.0f-%.0f m)", png, cols, rows, lo, hi)


if __name__ == "__main__":
    main()
