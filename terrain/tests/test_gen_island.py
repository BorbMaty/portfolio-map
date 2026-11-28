"""Tests for the fictional coast generator: reproducible, and each landmark gets the ground it needs."""

import numpy as np
import pytest

from gen_island import FORK, LANDMARKS, RIVER, fbm, generate, polyline_distance, to_uint16

# Small grid keeps the tests fast; the layout is in fractions, so it holds at any size.
W, H = 400, 300


@pytest.fixture(scope="module")
def elev():
    return generate(seed=7, width_px=W, height_px=H)


def at(elev, name):
    x, y = LANDMARKS[name]
    return elev[round(y * (H - 1)), round(x * (W - 1))]


def test_same_seed_same_map(elev):
    assert np.array_equal(elev, generate(seed=7, width_px=W, height_px=H))
    assert not np.array_equal(elev, generate(seed=8, width_px=W, height_px=H))


def test_sea_west_and_south_land_north_and_east(elev):
    assert (elev[:, 0] < 0).mean() > 0.9  # west edge
    assert (elev[-1, :] < 0).mean() > 0.9  # south edge
    assert (elev[0, W // 4 :] > 0).mean() > 0.9  # north edge, east of the west coast
    assert (elev[: H * 3 // 4, -1] > 0).mean() > 0.9  # east edge, north of the south coast


def test_every_landmark_is_on_land(elev):
    for name in LANDMARKS:
        assert at(elev, name) > 0, name


def test_observatory_is_on_the_heights(elev):
    land = elev[elev > 0]
    assert at(elev, "observatory") >= np.quantile(land, 0.9)


@pytest.mark.parametrize("seed", [1, 2, 3, 21, 42])
def test_landmark_rules_hold_for_other_seeds(seed):
    e = generate(seed=seed, width_px=W, height_px=H)
    assert all(at(e, name) > 0 for name in LANDMARKS)
    assert 0 < at(e, "harbor") < 30
    assert at(e, "observatory") >= np.quantile(e[e > 0], 0.9)


def test_harbor_is_by_the_sea(elev):
    assert at(elev, "harbor") < 30  # a quay, not a cliff
    x, y = LANDMARKS["harbor"]
    r, c = round(y * (H - 1)), round(x * (W - 1))
    # Sea within 3 % of the map width around the Harbor.
    k = round(0.03 * W)
    assert (elev[r - k : r + k, c - k : c + k] < 0).any()


def test_harvest_fields_are_flat(elev):
    gy, gx = np.gradient(elev, 40.0)  # 40 m/px at full size; the ratio between spots is what matters here
    slope = np.hypot(gx, gy)
    x, y = LANDMARKS["harvest-fields"]
    land_slope = np.median(slope[elev > 0])
    assert slope[round(y * (H - 1)), round(x * (W - 1))] < land_slope


def test_capital_is_beside_the_fork(elev):
    # Near the fork (within 4 % of the map width) but on dry land, so not in the channel.
    aspect = H / W
    d = polyline_distance(np.array(LANDMARKS["capital"][0]), np.array(LANDMARKS["capital"][1]), [FORK, FORK], aspect)
    assert 0.01 < float(d) < 0.04
    assert at(elev, "capital") > 0
    assert all(FORK in branch for branch in RIVER)


def test_polyline_distance():
    x, y = np.array([0.5, 0.0]), np.array([0.1, 0.0])
    d = polyline_distance(x, y, [(0.0, 0.0), (1.0, 0.0)], aspect=1.0)
    assert d == pytest.approx([0.1, 0.0])
    # Regression: a zero-length segment is a point, not a division by zero.
    assert polyline_distance(np.array(0.3), np.array(0.4), [(0.0, 0.0), (0.0, 0.0)], aspect=1.0) == pytest.approx(0.5)


def test_fbm_range_and_seed():
    a = fbm((30, 40), 4, 3, np.random.default_rng(1))
    assert a.shape == (30, 40) and 0 <= a.min() and a.max() <= 1
    assert np.array_equal(a, fbm((30, 40), 4, 3, np.random.default_rng(1)))


def test_to_uint16_stretch():
    hm, lo, hi = to_uint16(np.array([[-100.0, 0.0], [100.0, 900.0]]))
    assert (lo, hi) == (-100.0, 900.0) and hm.min() == 0 and hm.max() == 65535
    with pytest.raises(ValueError):
        to_uint16(np.zeros((2, 2)))
