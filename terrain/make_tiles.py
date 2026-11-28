"""Cut a terrain render into Deep Zoom (DZI) WebP tiles for OpenSeadragon.

Writes <out>/terrain.dzi (XML metadata) and <out>/terrain_files/<level>/<col>_<row>.webp.
Format reference: https://github.com/openseadragon/openseadragon/wiki/The-DZI-File-Format

Usage: uv run --project terrain terrain/make_tiles.py [render.png] [--out public/map] [--quality 80]
"""

from __future__ import annotations

import argparse
import logging
import math
import shutil
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

# 254 + 1 px overlap on both sides = 256 px for inner tiles, the DZI convention (power-of-two tiles).
TILE_PX = 254
OVERLAP_PX = 1

DZI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="webp" Overlap="{overlap}" TileSize="{tile}">
  <Size Width="{width}" Height="{height}"/>
</Image>
"""


def level_sizes(width_px: int, height_px: int) -> list[tuple[int, int]]:
    """Image size at every pyramid level, level 0 (1 px wide) first.

    The top level is the full image; each level below is half the size, odd sizes rounded up,
    until the longer side is 1 px. So there are ceil(log2(longest side)) + 1 levels.

    Args:
        width_px, height_px: full image size in px.

    Returns:
        (width_px, height_px) per level, index = DZI level number.

    Raises:
        ValueError: if a side is not positive.
    """
    if width_px < 1 or height_px < 1:
        raise ValueError(f"image size must be positive, got {width_px}x{height_px}")
    sizes = [(width_px, height_px)]
    while max(sizes[-1]) > 1:
        w, h = sizes[-1]
        sizes.append((math.ceil(w / 2), math.ceil(h / 2)))
    return sizes[::-1]


def tile_grid(width_px: int, height_px: int, tile_px: int = TILE_PX) -> tuple[int, int]:
    """Number of tile columns and rows that cover one level.

    Args:
        width_px, height_px: level size in px.
        tile_px: tile edge in px, without overlap.

    Returns:
        (columns, rows).
    """
    return math.ceil(width_px / tile_px), math.ceil(height_px / tile_px)


def tile_box(
    col: int, row: int, width_px: int, height_px: int, tile_px: int = TILE_PX, overlap_px: int = OVERLAP_PX
) -> tuple[int, int, int, int]:
    """Pixel box (left, top, right, bottom) of one tile within its level.

    Each tile covers its tile_px square plus overlap_px on every side that has a neighbour,
    clipped to the level edge (same as the reference deepzoom.py / vips dzsave).

    Args:
        col, row: tile index within the level.
        width_px, height_px: level size in px.
        tile_px: tile edge in px, without overlap.
        overlap_px: overlap in px added on each inner side.

    Returns:
        (left, top, right, bottom) in px, right/bottom exclusive (PIL crop convention).
    """
    left = col * tile_px - (overlap_px if col > 0 else 0)
    top = row * tile_px - (overlap_px if row > 0 else 0)
    right = min((col + 1) * tile_px + overlap_px, width_px)
    bottom = min((row + 1) * tile_px + overlap_px, height_px)
    return left, top, right, bottom


def write_tiles(src: Path, out_dir: Path, quality: int) -> int:
    """Write terrain.dzi and every tile of every level.

    Args:
        src: render image (PNG).
        out_dir: folder for terrain.dzi and terrain_files/.
        quality: WebP quality 0-100.

    Returns:
        Number of tiles written.

    Raises:
        FileNotFoundError: if src does not exist.
        OSError: if old tiles cannot be removed (e.g. a file is held open on Windows).
    """
    image = Image.open(src).convert("RGB")  # renders may carry an alpha channel; tiles do not need it
    sizes = level_sizes(*image.size)
    files_dir = out_dir / "terrain_files"
    # Start clean so tiles from an older, larger render cannot linger. The .dzi goes first and is
    # written last, so a run that fails half-way never leaves a .dzi describing missing tiles.
    (out_dir / "terrain.dzi").unlink(missing_ok=True)
    if files_dir.exists():
        shutil.rmtree(files_dir)  # no ignore_errors: a locked file must fail loudly, not leave a half-deleted pyramid

    count = 0
    level_img = image
    # Walk from the full image down, halving the previous level: cheaper than resizing the full image each time.
    for level in range(len(sizes) - 1, -1, -1):
        w, h = sizes[level]
        if level_img.size != (w, h):
            level_img = level_img.resize((w, h), Image.Resampling.LANCZOS)
        level_dir = files_dir / str(level)
        level_dir.mkdir(parents=True)
        cols, rows = tile_grid(w, h)
        for col in range(cols):
            for row in range(rows):
                tile = level_img.crop(tile_box(col, row, w, h))
                tile.save(level_dir / f"{col}_{row}.webp", "WEBP", quality=quality, method=6)
                count += 1

    width, height = image.size
    (out_dir / "terrain.dzi").write_text(
        DZI_XML.format(overlap=OVERLAP_PX, tile=TILE_PX, width=width, height=height), encoding="utf-8"
    )
    return count


def main() -> None:
    """Parse arguments and cut the tiles."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", nargs="?", type=Path, default=ROOT / "tiles-src" / "render.png")
    parser.add_argument("--out", type=Path, default=ROOT / "public" / "map")
    parser.add_argument("--quality", type=int, default=80, help="WebP quality 0-100 (lower = smaller tiles)")
    args = parser.parse_args()
    if not 0 <= args.quality <= 100:
        parser.error(f"--quality must be 0-100, got {args.quality}")
    if not args.src.exists():
        parser.error(
            f"{args.src} not found: render it with `blender -b -P terrain/scene.py -- --size 4096 --out render.png`"
        )

    args.out.mkdir(parents=True, exist_ok=True)
    count = write_tiles(args.src, args.out, args.quality)
    size_b = sum(p.stat().st_size for p in (args.out / "terrain_files").rglob("*.webp"))
    log.info("wrote %d tiles (%.1f MB) to %s", count, size_b / 1e6, args.out)


if __name__ == "__main__":
    main()
