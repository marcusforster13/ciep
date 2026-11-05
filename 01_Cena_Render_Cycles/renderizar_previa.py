"""Renderiza previas da cena (Cycles, rapido) em ../.claude/capturas.  Uso: blender -b ciep.blend --python renderizar_previa.py -- Camera_Aerea Camera_Patio"""
import bpy, os, sys
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["Camera_Aerea"]
sc = bpy.context.scene
out = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "capturas"))
os.makedirs(out, exist_ok=True)
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.cycles.samples = 32; sc.cycles.use_denoising = True
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 85
EXTRAS = {"Camera_Aerea": ((-38, -62, 26), (2, 2, 4), 24), "Camera_Fachada": ((-6, -22, 1.75), (-2, 0, 6), 16)}      # cameras so de previa
for nome, (pos, alvo, lente) in EXTRAS.items():
    if nome in args and nome not in bpy.data.objects:
        _c = bpy.data.objects.new(nome, bpy.data.cameras.new(nome)); sc.collection.objects.link(_c); _c.data.clip_end = 400
        _c.location = pos; _c.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler(); _c.data.lens = lente
for nome in args:
    sc.camera = bpy.data.objects[nome]
    sc.render.filepath = os.path.join(out, "previa_" + nome + ".jpg")
    bpy.ops.render.render(write_still=True)
    print("[PREVIA] " + sc.render.filepath)
