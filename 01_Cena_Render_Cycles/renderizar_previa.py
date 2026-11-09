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
EXTRAS = {"Camera_Aerea": ((-38, -62, 26), (2, 2, 4), 24), "Camera_Fachada": ((-6, -22, 1.75), (-2, 0, 6), 16), "Camera_Muro": ((-6, -45, 1.75), (-14, -38, 1.6), 20), "Camera_Arvore": ((-14, -32, 1.75), (-24, -22, 4.0), 16), "Camera_Lixeiras": ((11.0, -5.0, 1.6), (12.5, -1.7, .6), 22), "Camera_Extintor": ((-6.5, 11.4, 1.6), (-3.0, 12.9, 1.3), 18), "Camera_Poste": ((-20, -10, 1.7), (-26, -3.5, 5.0), 18), "Camera_Sala_Fundo": ((11.3, 13.6, 1.6), (2.2, 17.5, 1.2), 15)}      # cameras so de previa
for nome, (pos, alvo, lente) in EXTRAS.items():
    if nome in args and nome not in bpy.data.objects:
        _c = bpy.data.objects.new(nome, bpy.data.cameras.new(nome)); sc.collection.objects.link(_c); _c.data.clip_end = 400
        _c.location = pos; _c.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler(); _c.data.lens = lente
for nome in args:
    sc.camera = bpy.data.objects[nome]
    sc.render.filepath = os.path.join(out, "previa_" + nome + ".jpg")
    bpy.ops.render.render(write_still=True)
    print("[PREVIA] " + sc.render.filepath)
