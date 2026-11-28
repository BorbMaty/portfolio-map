"""Build the terrain scene from tiles-src/heightmap.png and render a draft.

Run inside Blender (needs bpy, so not part of the uv project):
  blender -b -P terrain/scene.py -- [--exaggeration 2.5] [--size 1024] [--tilt 25] [--save]

Scale: 1 Blender unit = 1 km, so the camera and light numbers read as real distances.
Output: tiles-src/draft.png (and tiles-src/terrain.blend with --save).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SRC = Path(__file__).resolve().parents[1] / "tiles-src"

# Most grid cells along the longer side; 1024 matches the draft render width.
MAX_GRID_CELLS = 1024


def parse_args() -> argparse.Namespace:
    """Read the options after Blender's `--` separator.

    Returns:
        Namespace with exaggeration (factor), size (px), tilt (degrees) and save (bool).
    """
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="scene.py")
    p.add_argument("--exaggeration", type=float, default=2.5, help="vertical scale factor")
    p.add_argument("--size", type=int, default=1024, help="render width and height in px")
    p.add_argument("--tilt", type=float, default=25.0, help="camera angle from straight down, degrees")
    p.add_argument("--save", action="store_true", help="also save terrain.blend for manual tweaking")
    return p.parse_args(argv)


def build_terrain(meta: dict, exaggeration: float) -> tuple[bpy.types.Object, float]:
    """Make a displaced grid matching the heightmap's ground size.

    Args:
        meta: contents of heightmap.json (from fetch_dem.py).
        exaggeration: vertical scale factor (1 = true relief).

    Returns:
        (terrain object, displaced relief height in km).
    """
    width_km = meta["size_m"]["width"] / 1000
    height_km = meta["size_m"]["height"] / 1000
    relief_km = (meta["elevation_m"]["max"] - meta["elevation_m"]["min"]) / 1000 * exaggeration

    # Half the heightmap resolution is plenty for a draft render (~580k vertices for the default bbox);
    # the cap keeps a larger bbox from building a mesh of millions of vertices.
    step = max(2, math.ceil(max(meta["pixels"]["width"], meta["pixels"]["height"]) / MAX_GRID_CELLS))
    cols, rows = meta["pixels"]["width"] // step, meta["pixels"]["height"] // step
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=cols, y_subdivisions=rows, size=1, calc_uvs=True)
    terrain = bpy.context.active_object
    terrain.name = "Terrain"
    terrain.scale = (width_km, height_km, 1)

    # Non-Color: the PNG stores heights, so no sRGB curve may bend them.
    image = bpy.data.images.load(str(SRC / "heightmap.png"))
    image.colorspace_settings.name = "Non-Color"
    tex = bpy.data.textures.new("Heightmap", type="IMAGE")
    tex.image = image
    tex.extension = "EXTEND"  # no wrap-around spikes at the edges

    disp = terrain.modifiers.new("Displace", type="DISPLACE")
    disp.texture = tex
    disp.texture_coords = "UV"
    disp.mid_level = 0.0
    disp.strength = relief_km
    bpy.ops.object.shade_smooth()
    return terrain, relief_km


def terrain_material(relief_km: float) -> bpy.types.Material:
    """Draft procedural material: colour by height, rock on steep slopes.

    Heights are normalised to 0-1 over the relief; slope comes from the surface normal's
    Z component (1 = flat, 0 = vertical). Final textures (Poly Haven) come in phase 3.1.
    """
    mat = bpy.data.materials.new("TerrainDraft")
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9

    geo = nodes.new("ShaderNodeNewGeometry")
    pos = nodes.new("ShaderNodeSeparateXYZ")
    nrm = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Position"], pos.inputs[0])
    links.new(geo.outputs["Normal"], nrm.inputs[0])

    height = nodes.new("ShaderNodeMapRange")
    height.inputs["From Max"].default_value = relief_km
    links.new(pos.outputs["Z"], height.inputs["Value"])

    # Valley meadows -> forest on the hills -> bare tops -> pale peaks.
    band = nodes.new("ShaderNodeValToRGB")
    els = band.color_ramp.elements
    els[0].color = (0.30, 0.42, 0.16, 1)
    els[1].position, els[1].color = 0.92, (0.80, 0.80, 0.78, 1)
    for pos_, col in [(0.25, (0.12, 0.25, 0.08, 1)), (0.70, (0.30, 0.30, 0.20, 1))]:
        e = els.new(pos_)
        e.color = col
    links.new(height.outputs["Result"], band.inputs["Fac"])

    # Steep where normal Z drops below ~0.8 (about 37 degrees), fully rock below 0.6.
    slope = nodes.new("ShaderNodeMapRange")
    slope.inputs["From Min"].default_value = 0.8
    slope.inputs["From Max"].default_value = 0.6
    links.new(nrm.outputs["Z"], slope.inputs["Value"])

    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (0.35, 0.32, 0.28, 1)  # rock
    links.new(slope.outputs["Result"], mix.inputs["Factor"])
    links.new(band.outputs["Color"], mix.inputs["A"])
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def add_camera(meta: dict, relief_km: float, tilt_deg: float) -> None:
    """Orthographic camera south of centre, tilted north, framing the whole map.

    Args:
        meta: contents of heightmap.json (ground size in metres).
        relief_km: displaced relief height in km (Blender units).
        tilt_deg: camera angle from straight down, degrees.
    """
    width_km = meta["size_m"]["width"] / 1000
    height_km = meta["size_m"]["height"] / 1000
    # Ortho, so distance does not change scale; it only has to keep the whole tilted map in front of the camera.
    dist_km = 2 * max(width_km, height_km) + relief_km
    t = math.radians(tilt_deg)
    target = Vector((0, 0, relief_km / 2))

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    # Tilt shortens the north-south extent by cos(tilt); fit whichever side is larger, plus 2 % margin.
    cam_data.ortho_scale = max(width_km, height_km * math.cos(t) + relief_km * math.sin(t)) * 1.02
    cam_data.clip_end = 2 * dist_km
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = target + Vector((0, -math.sin(t), math.cos(t))) * dist_km
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def add_light() -> None:
    """Add the sun and a flat sky colour.

    The sun comes from the north-west (azimuth 315 degrees) at 35 degrees elevation, the
    cartographic hillshade convention, so valleys read as valleys and not as ridges.
    """
    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 4.0
    sun_data.angle = math.radians(2)  # slightly soft shadows
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    # Light travels along the sun's -Z; aim it from NW (azimuth 315) down at 35 degrees.
    az, el = math.radians(315), math.radians(35)
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    sun.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (0.55, 0.62, 0.70)
    if world.node_tree:
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.70, 1)
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6


def main() -> None:
    """Reset the scene, build terrain, camera and light, render draft.png.

    Raises:
        SystemExit: if heightmap.json is missing (fetch_dem.py has not been run).
    """
    args = parse_args()
    meta_path = SRC / "heightmap.json"
    if not meta_path.exists():
        sys.exit(f"{meta_path} not found: run `uv run fetch_dem.py` in terrain/ first")
    meta = json.loads(meta_path.read_text())

    bpy.ops.wm.read_factory_settings(use_empty=True)
    terrain, relief_km = build_terrain(meta, args.exaggeration)
    terrain.data.materials.append(terrain_material(relief_km))
    add_camera(meta, relief_km, args.tilt)
    add_light()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = args.size
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(SRC / "draft.png")
    bpy.ops.render.render(write_still=True)
    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=str(SRC / "terrain.blend"))


if __name__ == "__main__":
    main()
