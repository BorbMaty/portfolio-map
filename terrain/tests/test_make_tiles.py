"""Tests for the Deep Zoom tiling in make_tiles.py."""

import pytest
from PIL import Image

from make_tiles import level_sizes, tile_box, tile_grid, write_tiles


def test_level_sizes_halve_and_round_up():
    assert level_sizes(8, 4) == [(1, 1), (2, 1), (4, 2), (8, 4)]
    assert level_sizes(5, 3) == [(1, 1), (2, 1), (3, 2), (5, 3)]


def test_level_count_for_8192():
    # ceil(log2(8192)) + 1 = 14 levels, 0..13.
    assert len(level_sizes(8192, 8192)) == 14


@pytest.mark.parametrize("size", [(0, 4), (4, 0)])
def test_level_sizes_rejects_empty(size):
    with pytest.raises(ValueError):
        level_sizes(*size)


def test_tile_grid():
    assert tile_grid(8, 4, tile_px=3) == (3, 2)
    assert tile_grid(254, 254) == (1, 1)
    assert tile_grid(255, 254) == (2, 1)


def test_tile_box_overlap_on_inner_sides_only():
    # 8x4 image, tile 3, overlap 1 (the DZI wiki example; its edge-tile sizes are inconsistent,
    # so these follow the reference deepzoom.py rule: overlap on every side with a neighbour).
    assert tile_box(0, 0, 8, 4, tile_px=3, overlap_px=1) == (0, 0, 4, 4)  # 4x4
    assert tile_box(1, 0, 8, 4, tile_px=3, overlap_px=1) == (2, 0, 7, 4)  # 5x4
    assert tile_box(2, 0, 8, 4, tile_px=3, overlap_px=1) == (5, 0, 8, 4)  # 3x4, clipped
    assert tile_box(0, 1, 8, 4, tile_px=3, overlap_px=1) == (0, 2, 4, 4)  # 4x2


def test_inner_tiles_are_256px():
    assert tile_box(1, 1, 1000, 1000) == (253, 253, 509, 509)


def test_write_tiles_layout(tmp_path):
    src = tmp_path / "render.png"
    Image.new("RGBA", (300, 200), (90, 120, 60, 255)).save(src)
    count = write_tiles(src, tmp_path / "out", quality=80)

    files = tmp_path / "out" / "terrain_files"
    top = files / "9"  # ceil(log2(300)) = 9
    assert sorted(p.name for p in top.iterdir()) == ["0_0.webp", "1_0.webp"]
    assert Image.open(top / "1_0.webp").size == (47, 200)  # x 253..300
    assert (files / "0" / "0_0.webp").exists()
    assert count == len(list(files.rglob("*.webp")))
    assert Image.open(tmp_path / "out" / "preview.webp").size == (300, 200)  # already under PREVIEW_MAX_PX
    dzi = (tmp_path / "out" / "terrain.dzi").read_text(encoding="utf-8")
    assert 'Width="300"' in dzi and 'Height="200"' in dzi and 'Format="webp"' in dzi


def test_preview_is_first_level_that_fits(tmp_path):
    src = tmp_path / "render.png"
    Image.new("RGB", (2100, 1000)).save(src)
    write_tiles(src, tmp_path, quality=50)
    assert Image.open(tmp_path / "preview.webp").size == (525, 250)  # 2100 -> 1050 (too big) -> 525
