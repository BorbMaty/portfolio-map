"""Tests for the render framing and landmark projection maths."""

import math

import pytest

from framing import INSET, frame_size, project


def test_frame_size_straight_down_is_the_inset_map():
    assert frame_size(60, 40, 2, 0) == pytest.approx((60 * INSET, 40 * INSET))


def test_frame_size_tilt_shrinks_height():
    w, h = frame_size(60, 40, 2, 30)
    assert w == pytest.approx(60 * INSET)
    assert h == pytest.approx((40 * math.cos(math.radians(30)) - 2 * math.sin(math.radians(30))) * INSET)


def test_frame_size_rejects_hidden_map():
    with pytest.raises(ValueError):
        frame_size(60, 1, 10, 60)


def test_centre_at_mid_height_projects_to_image_centre():
    assert project(0.5, 0.5, 1.0, 60, 40, 2.0, 25) == pytest.approx((0.5, 0.5))


def test_higher_ground_moves_up_the_image():
    low = project(0.5, 0.5, 0.0, 60, 40, 2.0, 25)
    high = project(0.5, 0.5, 2.0, 60, 40, 2.0, 25)
    assert high[0] == pytest.approx(low[0]) and high[1] < low[1]


def test_straight_down_maps_heightmap_fractions_through_the_inset():
    # No tilt: the image is the map, scaled by 1/INSET around the centre.
    x, y = project(0.2, 0.9, 0.7, 60, 40, 2.0, 0)
    assert x == pytest.approx(0.5 + (0.2 - 0.5) / INSET)
    assert y == pytest.approx(0.5 + (0.9 - 0.5) / INSET)
