"""Camera framing and projection maths for the tilted orthographic terrain render.

Pure Python (no bpy), so scene.py can use it inside Blender and pytest can check it outside.

Geometry: the terrain spans x in [-W/2, W/2] (east), y in [-H/2, H/2] (north), z in [0, R] (km).
The ortho camera looks at (0, 0, R/2), tilted north by t from straight down. A point then lands
at image offset u = x (right) and v = y*cos(t) + (z - R/2)*sin(t) (up) from the image centre.
"""

from __future__ import annotations

import math

# Frame inset: covers the ragged mesh edge so no background shows.
INSET = 0.98


def frame_size(width_km: float, height_km: float, relief_km: float, tilt_deg: float) -> tuple[float, float]:
    """Size (km) of the largest frame that shows terrain at every edge.

    The north edge at z = 0 sits lowest at H/2*cos(t) - R/2*sin(t), and the south edge at z = R
    sits highest at the mirror of that, so this inner extent is terrain at every height.

    Args:
        width_km, height_km: ground size of the terrain in km.
        relief_km: displaced height range in km.
        tilt_deg: camera angle from straight down, degrees.

    Returns:
        (frame_w_km, frame_h_km).

    Raises:
        ValueError: if the tilt and relief hide the whole map (no positive frame height).
    """
    t = math.radians(tilt_deg)
    frame_w = width_km * INSET
    frame_h = (height_km * math.cos(t) - relief_km * math.sin(t)) * INSET
    if frame_h <= 0:
        raise ValueError(f"tilt {tilt_deg} deg / relief {relief_km:.1f} km too large: the relief hides the whole map")
    return frame_w, frame_h


def project(
    x_frac: float,
    y_frac: float,
    z_km: float,
    width_km: float,
    height_km: float,
    relief_km: float,
    tilt_deg: float,
) -> tuple[float, float]:
    """Where a terrain point appears in the render, as fractions of the image.

    Args:
        x_frac, y_frac: position on the heightmap, 0-1, x east, y south (image row order).
        z_km: displaced height of that point in km (0 = lowest point of the terrain).
        width_km, height_km, relief_km, tilt_deg: as for frame_size.

    Returns:
        (x, y) fractions of the render, x right, y down: the format of src/map/regions.ts.
    """
    t = math.radians(tilt_deg)
    frame_w, frame_h = frame_size(width_km, height_km, relief_km, tilt_deg)
    x_km = (x_frac - 0.5) * width_km
    y_km = (0.5 - y_frac) * height_km  # heightmap row 0 is north = +y
    v_km = y_km * math.cos(t) + (z_km - relief_km / 2) * math.sin(t)
    return 0.5 + x_km / frame_w, 0.5 - v_km / frame_h
