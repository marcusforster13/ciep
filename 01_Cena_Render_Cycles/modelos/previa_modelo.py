"""Previa rapida de um .glb (Cycles, ceu claro): blender -b --factory-startup --python previa_modelo.py -- <modelo.glb> <saida.jpg> [distancia]"""
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
sc = bpy.context.scene
vs = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
h = max(v.z for v in vs); d = float(a[2]) if len(a) > 2 else h * 1.6
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (d * .7, -d, h * .45); cam.rotation_euler = (Vector((0, 0, h * .45)) - cam.location).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = 35
sol = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); sol.data.energy = 3.5; sol.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(sol)
w = bpy.data.worlds.new("w"); sc.world = w; w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .7, .9, 1)
chao = bpy.data.meshes.new("chao"); chao.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
sc.collection.objects.link(bpy.data.objects.new("chao", chao))
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 900, 900
sc.render.image_settings.file_format = "JPEG"; sc.render.filepath = a[1]
bpy.ops.render.render(write_still=True); print("[PREVIA]", a[1])
