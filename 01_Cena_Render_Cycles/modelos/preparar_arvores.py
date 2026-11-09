"""
Prepara arvores do Poly Haven (CC0) para VR: de milhoes de poligonos para ~20 mil triangulos, mantendo o aspecto.
  - tronco e galhos: reducao (decimate) para um numero alvo de triangulos;
  - folhas: mantem uma fracao das "ilhas" (cada folha/cacho e um cartao com transparencia) e aumenta cada uma em torno
    do proprio centro, para a copa continuar cheia;
  - escala para a altura real informada; base em z = 0, centrada.
Uso: blender -b --factory-startup --python preparar_arvores.py -- <entrada.gltf> <saida.glb> <altura_m> <tris_folhas> <tris_galhos> <tris_tronco>
"""
import bpy, bmesh, sys, random, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
ENT, SAI, ALT, TF, TG, TT = a[0], a[1], float(a[2]), int(a[3]), int(a[4]), int(a[5])
rnd = random.Random(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ENT)
malhas = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.polygons) > 50]
ob = max(malhas, key=lambda o: len(o.data.polygons))
for o in bpy.data.objects:
    if o is not ob: bpy.data.objects.remove(o, do_unlink=True)
mw = ob.matrix_world.copy(); ob.parent = None; ob.data.transform(mw); ob.matrix_world.identity()
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.separate(type="MATERIAL"); bpy.ops.object.mode_set(mode="OBJECT")
partes = [o for o in bpy.data.objects if o.type == "MESH"]
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
for o in partes:
    nome = o.data.materials[0].name.lower() if o.data.materials else ""
    t0 = tris(o)
    if "lea" in nome or "folh" in nome or "flower" in nome:
        bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
        ilhas, visto = [], set()
        for f in bm.faces:                                      # ilhas por vertices compartilhados
            if f.index in visto: continue
            pilha, ilha = [f], []
            visto.add(f.index)
            while pilha:
                g = pilha.pop(); ilha.append(g)
                for v in g.verts:
                    for h in v.link_faces:
                        if h.index not in visto: visto.add(h.index); pilha.append(h)
            ilhas.append(ilha)
        tpi = max(1, t0 / max(1, len(ilhas)))
        frac = min(1.0, TF / max(1, t0))
        s = min(2.4, 1 / math.sqrt(frac) * .45) if frac < 1 else 1.0
        apagar = []
        for ilha in ilhas:
            if rnd.random() > frac: apagar += ilha; continue
            vs = {v for f in ilha for v in f.verts}; c = sum((v.co for v in vs), Vector()) / len(vs)
            for v in vs: v.co = c + (v.co - c) * s
        bmesh.ops.delete(bm, geom=apagar, context="FACES")
        bm.to_mesh(o.data); bm.free()
        print("[ARVORE] folhas: %d ilhas, %d -> %d tris (fracao %.3f, escala %.2f)" % (len(ilhas), t0, tris(o), frac, s))
    else:
        alvo = TT if "trunk" in nome or "tronco" in nome else TG
        if not ("trunk" in nome or "tronco" in nome):          # galhos: tira os raminhos finos (ilhas pequenas), a copa esconde
            bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table(); visto, apagar = set(), []
            alt_total = max(v.co.z for v in bm.verts) - min(v.co.z for v in bm.verts)
            for f in bm.faces:
                if f.index in visto: continue
                pilha, ilha = [f], []; visto.add(f.index)
                while pilha:
                    g = pilha.pop(); ilha.append(g)
                    for v in g.verts:
                        for h in v.link_faces:
                            if h.index not in visto: visto.add(h.index); pilha.append(h)
                vs = [v.co for f2 in ilha for v in f2.verts]
                diag = (Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))) - Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))).length
                if diag < alt_total * .12: apagar += ilha
            bmesh.ops.delete(bm, geom=apagar, context="FACES"); bm.to_mesh(o.data); bm.free()
            print("[ARVORE] galhos finos retirados: %d -> %d tris" % (t0, tris(o))); t0 = tris(o)
        if t0 > alvo:
            d = o.modifiers.new("dec", "DECIMATE"); d.ratio = alvo / t0
            bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="dec")
        print("[ARVORE] %s: %d -> %d tris" % (nome, t0, tris(o)))
# junta, escala para a altura real, base no chao, centrada
for o in partes: o.select_set(True)
bpy.context.view_layer.objects.active = partes[0]; bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
vs = [v.co for v in ob.data.vertices]
mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
k = ALT / (mx.z - mn.z)
for v in ob.data.vertices: v.co = (v.co - Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))) * k
for p in ob.data.polygons: p.use_smooth = True
for m in ob.data.materials:                                       # folhas: recorte por transparencia, dos dois lados
    if m and any(t in m.name.lower() for t in ("lea", "folh", "flower")):
        try: m.blend_method = "CLIP"
        except Exception: pass
        m.use_backface_culling = False
ob.name = "Arvore"
bpy.ops.export_scene.gltf(filepath=SAI, export_format="GLB", use_selection=False, export_image_format="AUTO")
print("[ARVORE] PRONTO %s: %d tris, %.1f m de altura" % (SAI, tris(ob), ALT))
