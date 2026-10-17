"""Pastel clay illustrations for the site, built from primitives and rendered with Cycles.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup \
        --python website/art/make_art.py -- [scene ...]

Writes transparent PNGs to website/public/img/. Scenes: office, umbrella, coins, stamp.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "img")
PASTEL = {
    "mint": (0.80, 0.94, 0.86), "peach": (1.00, 0.82, 0.70), "sky": (0.72, 0.84, 0.98), "lavender": (0.80, 0.74, 0.97),
    "butter": (1.00, 0.90, 0.55), "blush": (0.98, 0.72, 0.80), "cream": (1.00, 0.97, 0.92), "slate": (0.36, 0.34, 0.45),
    "coral": (0.95, 0.52, 0.52), "gold": (0.98, 0.80, 0.42), "white": (0.98, 0.98, 0.98), "storm": (0.74, 0.72, 0.86),
}


# ----------------------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()                       # the old scene's materials are gone
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 900, 720
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1.0, 0.98, 0.96, 1)
    bg.inputs[1].default_value = 0.35


_mats = {}


def mat(name, rough=0.55):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*(c ** 2.2 for c in PASTEL[name]), 1)   # palette is sRGB; Blender wants linear
    b.inputs["Roughness"].default_value = rough
    _mats[name] = m
    return m


def finish(obj, colour, bevel=0.0, smooth=False, subsurf=0):
    obj.data.materials.append(mat(colour))
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width, mod.segments = bevel, 4
    if subsurf:
        obj.modifiers.new("sub", "SUBSURF").levels = subsurf
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def box(loc, size, colour, bevel=0.06, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, colour, bevel=bevel)


def ball(loc, r, colour, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.object
    o.scale = scale
    return finish(o, colour, smooth=True)


def cyl(loc, r, depth, colour, rot=(0, 0, 0), bevel=0.03, verts=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object
    finish(o, colour, bevel=bevel)
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.shade_auto_smooth() if hasattr(o.data, "shade_auto_smooth") else None
    return o


def ground(r=3.2, colour="mint"):
    o = cyl((0, 0, -0.12), r, 0.24, colour, bevel=0.08, verts=96)
    return o


def lights(key=(4, -4, 7), power=260):
    bpy.ops.object.light_add(type="AREA", location=key)
    k = bpy.context.object
    k.data.energy, k.data.size = power, 5
    k.rotation_euler = (Vector((0, 0, 0)) - Vector(key)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.light_add(type="AREA", location=(-5, -2, 4))
    f = bpy.context.object
    f.data.energy, f.data.size = 70, 6
    f.rotation_euler = (Vector((0, 0, 1)) - Vector((-5, -2, 4))).to_track_quat("-Z", "Y").to_euler()


def camera(loc=(7.5, -8.5, 6.2), target=(0, 0, 1.2), lens=60):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.data.lens = lens
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = c


def render(name):
    os.makedirs(OUT, exist_ok=True)
    bpy.context.scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


# ----------------------------------------------------------------------------- scenes
def office():
    """A prim little insurance office under its own storm cloud."""
    reset()
    ground(3.4, "mint")
    box((0, 0, 1.2), (3.0, 2.0, 2.4), "cream", bevel=0.1)              # building
    box((0, 0, 2.55), (3.3, 2.3, 0.3), "blush", bevel=0.08)            # cornice
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=2.25, depth=1.5, location=(0, 0, 3.45), rotation=(0, 0, math.pi / 4))
    roof = bpy.context.object
    roof.scale = (1.0, 0.72, 1)
    finish(roof, "lavender", bevel=0.05)
    for x in (-1.0, 0.0, 1.0):                                          # columns
        cyl((x, -1.05, 1.15), 0.14, 2.1, "white")
    for x in (-0.95, 0.95):                                             # windows
        for z in (0.85, 1.75):
            box((x, -1.01, z), (0.5, 0.06, 0.55), "sky", bevel=0.02)
    box((0, -1.01, 0.55), (0.6, 0.08, 1.1), "peach", bevel=0.03)        # door
    box((0, -1.08, 2.25), (1.9, 0.08, 0.32), "butter", bevel=0.03)      # sign
    for x, z, r in ((-0.9, 5.0, 0.75), (0.0, 5.3, 0.95), (0.95, 5.0, 0.75), (0.45, 4.75, 0.6), (-0.4, 4.75, 0.6)):
        ball((x, 0.2, z), r, "storm")                                   # cloud
    verts = [(-0.10, 0, 0.55), (0.25, 0, 0.55), (0.05, 0, 0.1), (0.3, 0, 0.1), (-0.2, 0, -0.65), (-0.02, 0, -0.12), (-0.28, 0, -0.12)]
    me = bpy.data.meshes.new("bolt")
    me.from_pydata(verts, [], [list(range(len(verts)))])
    bolt = bpy.data.objects.new("bolt", me)
    bpy.context.collection.objects.link(bolt)
    bolt.location = (1.15, -0.6, 3.95)
    bolt.scale = (1.3, 1.3, 1.3)
    bpy.context.view_layer.objects.active = bolt
    bolt.select_set(True)
    sol = bolt.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.12
    finish(bolt, "butter", bevel=0.02)
    for i, (x, y) in enumerate(((-2.4, -1.2), (2.5, -0.6), (-2.0, 1.4), (2.2, 1.5))):   # shrubs
        ball((x, y, 0.35), 0.38 + 0.06 * (i % 2), "mint" if i % 2 else "sky")
    lights()
    camera(loc=(8.5, -10.5, 7.2), target=(0, 0, 2.6), lens=46)
    render("office")


def umbrella():
    """A small robot under an umbrella, staying dry for the moment."""
    reset()
    ground(2.6, "sky")
    box((0, 0, 0.75), (1.0, 0.75, 1.0), "white", bevel=0.18)            # body
    box((0, 0, 1.6), (0.85, 0.7, 0.62), "white", bevel=0.18)            # head
    for x in (-0.18, 0.18):
        ball((x, -0.36, 1.65), 0.08, "slate")                           # eyes
    box((0, -0.38, 0.8), (0.5, 0.04, 0.28), "blush", bevel=0.03)        # chest panel
    cyl((0, 0, 2.02), 0.03, 0.3, "slate", bevel=0)
    ball((0, 0, 2.2), 0.08, "coral")                                    # antenna
    for x in (-0.35, 0.35):
        box((x, 0, 0.12), (0.28, 0.4, 0.24), "lavender", bevel=0.08)    # feet
    cyl((0.62, 0, 1.6), 0.035, 2.6, "slate", bevel=0)                   # umbrella shaft
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.6, location=(0.62, 0, 2.6), segments=64, ring_count=32)
    can = bpy.context.object
    can.scale = (1, 1, 0.55)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for v in can.data.vertices:
        v.select = v.co.z < -0.01
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    can.modifiers.new("solid", "SOLIDIFY").thickness = 0.04
    finish(can, "peach", smooth=True)
    bpy.ops.mesh.primitive_torus_add(location=(0.82, 0, 0.32), major_radius=0.2, minor_radius=0.035, rotation=(math.pi / 2, 0, 0))
    finish(bpy.context.object, "slate")                                 # handle hook
    for i in range(18):                                                 # rain, kept off the umbrella
        a = i * 2.4
        x, y = 1.9 * math.cos(a), 1.9 * math.sin(a) * 0.6
        if abs(x - 0.62) < 1.7 and abs(y) < 1.7:
            x = x + (1.9 if x >= 0.62 else -1.9)
        ball((x, y, 1.0 + (i * 0.37) % 2.6), 0.07, "sky", scale=(1, 1, 2.2))
    lights()
    camera(loc=(6.0, -8.0, 4.8), target=(0.2, 0, 1.5), lens=46)
    render("umbrella")


def coins():
    """A tall stack of coins, leaning, with the top ones already leaving."""
    reset()
    ground(2.4, "peach")
    z, x = 0.12, 0.0
    for i in range(16):
        lean = 0.004 * i * i
        cyl((x + lean, 0, z), 0.62, 0.16, "gold" if i % 3 else "butter", rot=(0, 0.012 * i, 0), bevel=0.03)
        z += 0.165
    for k, (dx, dz, ry) in enumerate(((1.4, 2.6, 0.9), (2.0, 1.6, 1.6), (1.7, 0.6, 2.3))):
        cyl((dx, -0.2 * k, dz), 0.62, 0.16, "gold", rot=(0.4 * k, ry, 0.3), bevel=0.03)
    for x, y in ((-1.3, -0.6), (-1.0, 0.9)):
        cyl((x, y, 0.09), 0.62, 0.16, "butter", rot=(0, 0, 0), bevel=0.03)
    lights()
    camera(loc=(6.5, -8.0, 4.6), target=(0.4, 0, 1.5), lens=55)
    render("coins")


def stamp():
    """A rubber stamp, and the claim it has just settled."""
    reset()
    box((0, 0, 0.02), (3.4, 2.4, 0.04), "white", bevel=0.01, rot=(0, 0, 0.12))      # the claim form
    for i in range(4):
        box((-0.5 + 0.02 * i, 0.85 - 0.26 * i, 0.05), (1.8 - 0.25 * (i % 2), 0.07, 0.01), "lavender", bevel=0.0, rot=(0, 0, 0.12))
    bpy.ops.object.text_add(location=(-0.25, -0.62, 0.045), rotation=(0, 0, 0.12 + 0.18))
    t = bpy.context.object
    t.data.body = "SETTLED"
    t.data.align_x = "CENTER"
    t.data.size = 0.42
    t.data.extrude = 0.004
    t.data.materials.append(mat("coral"))
    box((1.25, 0.25, 0.75), (1.3, 0.85, 0.3), "blush", bevel=0.08)      # stamp base
    box((1.25, 0.25, 0.56), (1.2, 0.75, 0.08), "coral", bevel=0.02)     # rubber
    cyl((1.25, 0.25, 1.15), 0.16, 0.6, "lavender", bevel=0.03)          # neck
    ball((1.25, 0.25, 1.6), 0.36, "lavender")                           # knob
    lights(key=(3, -4, 8))
    camera(loc=(5.0, -6.5, 5.4), target=(0.4, 0, 0.4), lens=55)
    render("stamp")


SCENES = {"office": office, "umbrella": umbrella, "coins": coins, "stamp": stamp}

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for name in argv or SCENES:
        SCENES[name]()
