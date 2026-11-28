"""Build the terrain scene from tiles-src/heightmap.png (gen_island.py) and render it.

Run inside Blender (needs bpy, so not part of the uv project):
  blender -b -P terrain/scene.py -- [--exaggeration 2.5] [--size 1024] [--tilt 25] [--out draft.png] [--save]

Scale: 1 Blender unit = 1 km, so the camera and light numbers read as real distances.
Output: tiles-src/draft.png or --out name, tiles-src/landmarks.json (landmark positions on the render, the
format of src/map/regions.ts), and tiles-src/terrain.blend with --save.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# Blender's Python does not see the uv project; framing.py is plain Python next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from framing import frame_size, project

SRC = Path(__file__).resolve().parents[1] / "tiles-src"

# Most grid cells along the longer side; 1024 matches the draft render width.
MAX_GRID_CELLS = 1024


def parse_args() -> argparse.Namespace:
    """Read the options after Blender's `--` separator.

    Returns:
        Namespace with exaggeration (factor), size (px), tilt (degrees), out (file name) and save (bool).
    """
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="scene.py")
    p.add_argument("--exaggeration", type=float, default=2.5, help="vertical scale factor")
    p.add_argument("--size", type=int, default=1024, help="longer side of the render in px")
    p.add_argument("--tilt", type=float, default=25.0, help="camera angle from straight down, degrees")
    p.add_argument("--out", default="draft.png", help="output file name inside tiles-src/")
    p.add_argument("--save", action="store_true", help="also save terrain.blend for manual tweaking")
    return p.parse_args(argv)


def build_terrain(meta: dict, exaggeration: float) -> tuple[bpy.types.Object, float]:
    """Make a displaced grid matching the heightmap's ground size.

    Args:
        meta: contents of heightmap.json (from gen_island.py).
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


def terrain_material(relief_km: float, sea_km: float) -> bpy.types.Material:
    """Draft procedural material: sea coloured by depth, land by height, rock on steep land.

    There is no separate water surface: the sea floor is smooth (gen_island.py), so colouring
    everything below sea level as water reads as calm sea, and the river channel fills too.
    Land heights are normalised 0-1 from sea level to the top; slope comes from the surface
    normal's Z component (1 = flat, 0 = vertical). Final textures come in phase 3.1.

    Args:
        relief_km: displaced height range in km (top of the terrain).
        sea_km: displaced height of sea level in km.
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

    def ramp(stops: list[tuple[float, tuple[float, float, float]]]) -> bpy.types.ShaderNode:
        """Colour ramp node with the given (position, RGB) stops."""
        node = nodes.new("ShaderNodeValToRGB")
        els = node.color_ramp.elements
        els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
        els[1].position, els[1].color = stops[-1][0], (*stops[-1][1], 1)
        for p, c in stops[1:-1]:
            els.new(p).color = (*c, 1)
        return node

    # Land: beach sand at the waterline -> meadows -> forest -> bare tops -> pale peaks.
    height = nodes.new("ShaderNodeMapRange")
    height.inputs["From Min"].default_value = sea_km
    height.inputs["From Max"].default_value = relief_km
    links.new(pos.outputs["Z"], height.inputs["Value"])
    band = ramp(
        [
            (0.0, (0.76, 0.70, 0.50)),
            (0.012, (0.30, 0.42, 0.16)),
            (0.25, (0.12, 0.25, 0.08)),
            (0.65, (0.30, 0.30, 0.20)),
            (0.88, (0.80, 0.80, 0.78)),
        ]
    )
    links.new(height.outputs["Result"], band.inputs["Fac"])

    # Sea: turquoise shallows -> deep blue, by depth below sea level.
    depth = nodes.new("ShaderNodeMapRange")
    depth.inputs["From Min"].default_value = sea_km
    depth.inputs["From Max"].default_value = sea_km * 0.4  # 60 % of the way down to the deepest point
    links.new(pos.outputs["Z"], depth.inputs["Value"])
    water = ramp([(0.0, (0.22, 0.55, 0.58)), (0.35, (0.07, 0.25, 0.42)), (1.0, (0.03, 0.10, 0.26))])
    links.new(depth.outputs["Result"], water.inputs["Fac"])

    is_land = nodes.new("ShaderNodeMath")
    is_land.operation = "GREATER_THAN"
    is_land.inputs[1].default_value = sea_km
    links.new(pos.outputs["Z"], is_land.inputs[0])

    # Steep where normal Z drops below ~0.8 (about 37 degrees), fully rock below 0.6.
    slope = nodes.new("ShaderNodeMapRange")
    slope.inputs["From Min"].default_value = 0.8
    slope.inputs["From Max"].default_value = 0.6
    links.new(nrm.outputs["Z"], slope.inputs["Value"])
    rock_on_land = nodes.new("ShaderNodeMath")
    rock_on_land.operation = "MULTIPLY"
    links.new(slope.outputs["Result"], rock_on_land.inputs[0])
    links.new(is_land.outputs[0], rock_on_land.inputs[1])

    rocky = nodes.new("ShaderNodeMix")
    rocky.data_type = "RGBA"
    rocky.inputs["B"].default_value = (0.35, 0.32, 0.28, 1)  # rock
    links.new(rock_on_land.outputs[0], rocky.inputs["Factor"])
    links.new(band.outputs["Color"], rocky.inputs["A"])

    land_or_sea = nodes.new("ShaderNodeMix")
    land_or_sea.data_type = "RGBA"
    links.new(is_land.outputs[0], land_or_sea.inputs["Factor"])
    links.new(water.outputs["Color"], land_or_sea.inputs["A"])
    links.new(rocky.outputs["Result"], land_or_sea.inputs["B"])
    links.new(land_or_sea.outputs["Result"], bsdf.inputs["Base Color"])

    # Water is glossier than land, which gives the sea a soft sheen under the sun.
    gloss = nodes.new("ShaderNodeMapRange")
    gloss.inputs["To Min"].default_value = 0.35
    gloss.inputs["To Max"].default_value = 0.9
    links.new(is_land.outputs[0], gloss.inputs["Value"])
    links.new(gloss.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def add_camera(meta: dict, relief_km: float, tilt_deg: float) -> tuple[float, float]:
    """Orthographic camera south of centre, tilted north, framing the terrain edge to edge.

    The frame sits just inside the terrain, so no sky shows at any edge. Landmark positions are
    stored as fractions of this frame (src/map/regions.ts), so changing tilt or exaggeration
    moves every landmark: only the render size may change after they are placed.

    Args:
        meta: contents of heightmap.json (ground size in metres).
        relief_km: displaced relief height in km (Blender units).
        tilt_deg: camera angle from straight down, degrees.

    Returns:
        (width_km, height_km) of the framed area, for the render aspect ratio.
    """
    width_km = meta["size_m"]["width"] / 1000
    height_km = meta["size_m"]["height"] / 1000
    # Ortho, so distance does not change scale; it only has to keep the whole tilted map in front of the camera.
    dist_km = 2 * max(width_km, height_km) + relief_km
    t = math.radians(tilt_deg)
    target = Vector((0, 0, relief_km / 2))

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    # The frame that shows terrain at every edge (derivation in framing.py).
    try:
        frame_w, frame_h = frame_size(width_km, height_km, relief_km, tilt_deg)
    except ValueError as e:
        sys.exit(str(e))
    cam_data.ortho_scale = max(frame_w, frame_h)  # Blender fits ortho_scale to the longer render side
    cam_data.clip_end = 2 * dist_km
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = target + Vector((0, -math.sin(t), math.cos(t))) * dist_km
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return frame_w, frame_h


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
    """Reset the scene, build terrain, camera and light, render to tiles-src/<out>.

    Raises:
        SystemExit: if heightmap.json is missing (gen_island.py has not been run).
    """
    args = parse_args()
    meta_path = SRC / "heightmap.json"
    if not meta_path.exists():
        sys.exit(f"{meta_path} not found: run `uv run --project terrain terrain/gen_island.py` first")
    meta = json.loads(meta_path.read_text())
    lo_m = meta["elevation_m"]["min"]

    def displaced_km(elevation_m: float) -> float:
        """Height of an elevation in the scene: the lowest point sits at z = 0."""
        return (elevation_m - lo_m) / 1000 * args.exaggeration

    bpy.ops.wm.read_factory_settings(use_empty=True)
    terrain, relief_km = build_terrain(meta, args.exaggeration)
    terrain.data.materials.append(terrain_material(relief_km, displaced_km(meta["sea_level_m"])))
    frame_w, frame_h = add_camera(meta, relief_km, args.tilt)
    add_light()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    # --size is the longer side; the other follows the framed area so the image has no empty bands.
    scale = args.size / max(frame_w, frame_h)
    scene.render.resolution_x, scene.render.resolution_y = round(frame_w * scale), round(frame_h * scale)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(SRC / args.out)
    bpy.ops.render.render(write_still=True)

    # Where each landmark lands on this render (tilt shifts high ground up the image), rounded to 0.1 % of the
    # image: copy these into src/map/regions.ts.
    width_km, height_km = meta["size_m"]["width"] / 1000, meta["size_m"]["height"] / 1000
    spots = {}
    for name, lm in meta["landmarks"].items():
        u, v = project(lm["x"], lm["y"], displaced_km(lm["elevation_m"]), width_km, height_km, relief_km, args.tilt)
        spots[name] = {"x": round(u, 3), "y": round(v, 3)}
    (SRC / "landmarks.json").write_text(json.dumps(spots, indent=2))

    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=str(SRC / "terrain.blend"))


if __name__ == "__main__":
    main()
