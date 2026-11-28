"""Tests for the DEM crop maths in fetch_dem.py."""

import math

import numpy as np
import pytest

from fetch_dem import RES_LAT_DEG, lon_resolution, tile_names, to_uint16


def test_tile_names_default_bbox_spans_two_tiles():
    names = tile_names(46.6, 24.4, 47.0, 25.05)
    assert names == [
        "Copernicus_DSM_COG_10_N46_00_E024_00_DEM",
        "Copernicus_DSM_COG_10_N46_00_E025_00_DEM",
    ]


def test_tile_names_whole_degree_edges_follow_half_pixel_shift():
    # Regression: tiles are shifted half a pixel north-west, so a south edge on 46.0 needs N45
    # and an east edge on 25.0 needs E025; north 47.0 and west 24.0 need nothing extra.
    names = tile_names(46.0, 24.0, 47.0, 25.0)
    assert names == [
        "Copernicus_DSM_COG_10_N45_00_E024_00_DEM",
        "Copernicus_DSM_COG_10_N45_00_E025_00_DEM",
        "Copernicus_DSM_COG_10_N46_00_E024_00_DEM",
        "Copernicus_DSM_COG_10_N46_00_E025_00_DEM",
    ]


def test_to_uint16_rejects_nan():
    with pytest.raises(ValueError, match="NaN"):
        to_uint16(np.array([[300.0, np.nan]]))


@pytest.mark.parametrize("bbox", [(47, 24, 46, 25), (46, 25, 47, 24), (-1, 24, 46, 25)])
def test_tile_names_rejects_bad_bbox(bbox):
    with pytest.raises(ValueError):
        tile_names(*bbox)


def test_lon_resolution_gives_square_ground_pixels():
    # Ground width of one lon step = step * cos(lat); it must equal one lat step.
    lat = 46.8
    assert lon_resolution(lat) * math.cos(math.radians(lat)) == pytest.approx(RES_LAT_DEG)
    assert lon_resolution(0) == pytest.approx(RES_LAT_DEG)


def test_to_uint16_stretches_full_range():
    hm, lo, hi = to_uint16(np.array([[300.0, 800.0], [1300.0, 550.0]]))
    assert (lo, hi) == (300.0, 1300.0)
    assert hm.dtype == np.uint16
    assert hm.min() == 0 and hm.max() == 65535
    assert hm[0, 1] == round(0.5 * 65535)


def test_to_uint16_rejects_flat_grid():
    with pytest.raises(ValueError):
        to_uint16(np.full((2, 2), 400.0))
