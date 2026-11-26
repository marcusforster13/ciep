# Envelhece um modelo do autor (GLB PBR) por script: encardido nas frestas, manchas perto da base e
# rugosidade maior onde suja. Grava um GLB NOVO ao lado (<nome>_sujo_realista.glb); o original fica intacto.
# Uso: blender -b --factory-startup --python sujar_modelo.py -- <nome> [forca_frestas] [forca_base] [cor_base]
#   nome: arquivo em modelos/ sem "_realista.glb" (ex.: bancada_banheiro)
#   cor_base: "encardido" (marrom acinzentado) ou "amarelado" (mancha de urina/calcario)
import bpy, os, sys, numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
arg = sys.argv[sys.argv.index("--") + 1:]
nome = arg[0]; f_fresta = float(arg[1]) if len(arg) > 1 else .9; f_base = float(arg[2]) if len(arg) > 2 else .6
cor_base = arg[3] if len(arg) > 3 else "encardido"; f_geral = float(arg[4]) if len(arg) > 4 else .3
ENTRA = os.path.join(AQUI, "modelos", nome + "_realista.glb")
SAI = os.path.join(AQUI, "modelos", nome + "_sujo_realista.glb")
TMP = os.path.join(os.environ.get("TEMP", AQUI), "sujar_" + nome); os.makedirs(TMP, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ENTRA)
obs = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.context.view_layer.update()
zs = [(o.matrix_world @ v.co).z for o in obs for v in o.data.vertices]; z0, z1 = min(zs), max(zs); h = max(z1 - z0, 1e-3)

def img_do(mat, chave):
    for nd in mat.node_tree.nodes:
        if nd.type == "TEX_IMAGE" and nd.image and chave in nd.image.name: return nd.image
mats = {s.material for o in obs for s in o.material_slots if s.material}
mascaras = {}
for m in mats:                                  # um no de imagem alvo por material, no tamanho da cor base
    cor = img_do(m, "BaseColor"); w, hh = cor.size
    alvo = bpy.data.images.new("Mascara_" + m.name, w, hh, float_buffer=True); alvo.colorspace_settings.name = "Non-Color"
    nt = m.node_tree; nos = nt.nodes; L = nt.links; ja = {n.name for n in nos}
    ao = nos.new("ShaderNodeAmbientOcclusion"); ao.only_local = True; ao.samples = 24; ao.inputs["Distance"].default_value = max(.03, h * .12)
    cav = nos.new("ShaderNodeMapRange"); L.new(ao.outputs["AO"], cav.inputs["Value"]); cav.inputs[1].default_value, cav.inputs[2].default_value = .95, .45
    cav.inputs[3].default_value, cav.inputs[4].default_value = 0, 1                        # AO 0,95 -> 0 (limpo), 0,45 -> 1 (fresta)
    geo = nos.new("ShaderNodeNewGeometry"); sep = nos.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Position"], sep.inputs[0])
    base = nos.new("ShaderNodeMapRange"); L.new(sep.outputs["Z"], base.inputs["Value"])
    base.inputs[1].default_value, base.inputs[2].default_value = z0, z0 + h * .45; base.inputs[3].default_value, base.inputs[4].default_value = 1, 0
    tc = nos.new("ShaderNodeTexCoord"); nz = nos.new("ShaderNodeTexNoise"); L.new(tc.outputs["Object"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0 / h + 6; nz.inputs["Detail"].default_value = 8; nz.inputs["Roughness"].default_value = .62
    cc = nos.new("ShaderNodeCombineColor"); L.new(cav.outputs[0], cc.inputs[0]); L.new(base.outputs[0], cc.inputs[1]); L.new(nz.outputs["Fac"], cc.inputs[2])
    em = nos.new("ShaderNodeEmission"); L.new(cc.outputs[0], em.inputs["Color"])
    out = next(n for n in nos if n.type == "OUTPUT_MATERIAL" and n.is_active_output); mascaras[m] = (alvo, out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None, out, ja)
    L.new(em.outputs[0], out.inputs["Surface"])
    ti = nos.new("ShaderNodeTexImage"); ti.image = alvo; nos.active = ti

sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 64
sc.render.bake.margin = 16
for o in obs: o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
bpy.ops.object.bake(type="EMIT")
print("[SUJAR] mascara assada para", nome)

TINTA = {"encardido": np.array((.52, .46, .36)), "amarelado": np.array((.80, .62, .30))}
for m, (alvo, antes, out, ja) in mascaras.items():
    nt = m.node_tree
    if antes: nt.links.new(antes, out.inputs["Surface"])            # devolve o shader original
    w, hh = alvo.size
    M = np.array(alvo.pixels[:], dtype=np.float32).reshape(hh, w, 4)
    _d = bpy.data.images.new("dbg", w, hh); _d.pixels[:] = np.concatenate([M[..., :3], np.ones((hh, w, 1), np.float32)], -1).ravel(); _d.filepath_raw = os.path.join(TMP, "mascara.png"); _d.file_format = "PNG"; _d.save()
    uso = M[..., 3] > .5 if M[..., 3].min() < .5 else np.ones(M.shape[:2], bool)
    b = M[..., 2]; lo, hi = np.percentile(b[uso], 10), np.percentile(b[uso], 90)
    ruido = np.clip((b - lo) / max(hi - lo, 1e-4), 0, 1)               # ruido normalizado: manchas de verdade, nao um veu
    fresta = np.clip(M[..., 0], 0, 1) ** 1.2 * (.35 + .65 * ruido) * f_fresta
    geral = ruido ** 2.5 * f_geral                                      # encardido de uso, em manchas, na peca toda
    perto = np.clip(M[..., 1], 0, 1) ** 1.3 * (.25 + .75 * ruido) * f_base
    cor = img_do(m, "BaseColor"); C = np.array(cor.pixels[:], dtype=np.float32).reshape(hh, w, 4)
    sujo = C[..., :3] * (1 - np.clip(fresta + geral, 0, 1)[..., None] * (1 - TINTA["encardido"]))
    sujo = sujo * (1 - perto[..., None] * (1 - TINTA[cor_base]))
    C[..., :3] = np.clip(sujo, 0, 1); cor.pixels[:] = C.ravel()
    orm = img_do(m, "Roughness")
    if orm and orm.size[:] == cor.size[:]:
        R = np.array(orm.pixels[:], dtype=np.float32).reshape(hh, w, 4)
        R[..., 1] = np.clip(R[..., 1] + .3 * np.clip(fresta + perto + geral, 0, 1), 0, 1); orm.pixels[:] = R.ravel()
        imgs = (cor, orm)
    else: imgs = (cor,)
    for im in imgs:                                                    # reembute a versao suja (senao o GLB sai com a imagem original)
        im.file_format = "PNG"; im.update(); im.pack()
    for nd in list(nt.nodes):                                          # tira os nos da mascara
        if nd.name not in ja: nt.nodes.remove(nd)
    print("[SUJAR] %s: fresta media %.3f, base media %.3f" % (m.name, fresta.mean(), perto.mean()))

bpy.ops.export_scene.gltf(filepath=SAI, export_format="GLB", export_image_format="AUTO", export_yup=True)
print("[SUJAR] gravado", SAI, os.path.getsize(SAI) // 1024, "KB")
