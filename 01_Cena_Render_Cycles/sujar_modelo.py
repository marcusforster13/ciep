# Envelhece um modelo do autor (GLB PBR) por script: encardido nas frestas, manchas perto da base e
# rugosidade maior onde suja. Grava um GLB NOVO ao lado (<nome>_sujo_realista.glb); o original fica intacto.
# Uso: blender -b --factory-startup --python sujar_modelo.py -- <nome> [forca_frestas] [forca_base] [cor_base]
#   nome: arquivo em modelos/ sem "_realista.glb" (ex.: bancada_banheiro)
#   cor_base: "encardido" (marrom acinzentado) ou "amarelado" (mancha de urina/calcario)
#   5o: forca do encardido geral; 6o: "atlas" para modelos de cores lisas (sem textura): assa as cores
#   numa textura unica com UV nova e troca todos os materiais por um so antes de sujar
import bpy, os, sys, numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
arg = sys.argv[sys.argv.index("--") + 1:]
nome = arg[0]; f_fresta = float(arg[1]) if len(arg) > 1 else .9; f_base = float(arg[2]) if len(arg) > 2 else .6
cor_base = arg[3] if len(arg) > 3 else "encardido"; f_geral = float(arg[4]) if len(arg) > 4 else .3
ATLAS = "atlas" in arg[5:]; FANTASMA = "fantasma" in arg[5:]      # "fantasma": marcas de caneta mal apagada (quadro branco)
ENTRA = os.path.join(AQUI, "modelos", nome + "_realista.glb")
SAI = os.path.join(AQUI, "modelos", nome + "_sujo_realista.glb")
TMP = os.path.join(os.environ.get("TEMP", AQUI), "sujar_" + nome); os.makedirs(TMP, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ENTRA)
obs = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.context.view_layer.update()
zs = [(o.matrix_world @ v.co).z for o in obs for v in o.data.vertices]; z0, z1 = min(zs), max(zs); h = max(z1 - z0, 1e-3)

def _bsdf(m): return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
def _img_atras(sock, prof=3):                      # imagem que alimenta um soquete (direto ou via separar cor / mistura)
    if not sock.is_linked or prof < 0: return None
    n = sock.links[0].from_node
    if n.type == "TEX_IMAGE": return n.image
    for i in n.inputs:
        im = _img_atras(i, prof - 1)
        if im: return im
def img_cor(m): p = _bsdf(m); return _img_atras(p.inputs["Base Color"]) if p else None
def img_rug(m): p = _bsdf(m); return _img_atras(p.inputs["Roughness"]) if p else None
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 64
sc.render.bake.margin = 16

def fazer_atlas(lado=1024):
    """Modelo de cores lisas: UV nova sem sobreposicao, assa cor e rugosidade/metal nela, um material so."""
    for o in obs:                                  # malha compartilhada (copias): uma copia propria por objeto
        if o.data.users > 1: o.data = o.data.copy()
    for o in obs:
        for l in o.data.uv_layers: l.active_render = True; break
        o.data.uv_layers.new(name="Atlas")
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs: o.select_set(True); o.data.uv_layers.active = o.data.uv_layers["Atlas"]
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.01, scale_to_bounds=True); bpy.ops.object.mode_set(mode="OBJECT")
    col = bpy.data.images.new(nome + "_BaseColor", lado, lado); rm = bpy.data.images.new(nome + "_Metallic-Roughness", lado, lado)
    rm.colorspace_settings.name = "Non-Color"
    for alvo, qual in ((col, "cor"), (rm, "rm")):
        guarda = []
        for m in {s.material for o in obs for s in o.material_slots if s.material}:
            nt = m.node_tree; nos = nt.nodes; L = nt.links; p = _bsdf(m); ja = {n.name for n in nos}
            out = next(n for n in nos if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
            antes = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
            em = nos.new("ShaderNodeEmission")
            if qual == "cor":
                if p.inputs["Base Color"].is_linked: L.new(p.inputs["Base Color"].links[0].from_socket, em.inputs["Color"])
                else: em.inputs["Color"].default_value = p.inputs["Base Color"].default_value
            else:
                cc = nos.new("ShaderNodeCombineColor"); L.new(cc.outputs[0], em.inputs["Color"])
                for k, nm in ((1, "Roughness"), (2, "Metallic")):
                    if p.inputs[nm].is_linked: L.new(p.inputs[nm].links[0].from_socket, cc.inputs[k])
                    else: cc.inputs[k].default_value = p.inputs[nm].default_value
            L.new(em.outputs[0], out.inputs["Surface"])
            uv = nos.new("ShaderNodeUVMap"); uv.uv_map = "Atlas"; ti = nos.new("ShaderNodeTexImage"); ti.image = alvo
            L.new(uv.outputs[0], ti.inputs["Vector"]); nos.active = ti; guarda.append((m, ja, antes, out))
        bpy.ops.object.bake(type="EMIT")
        for m, ja, antes, out in guarda:
            if antes: m.node_tree.links.new(antes, out.inputs["Surface"])
            for nd in list(m.node_tree.nodes):
                if nd.name not in ja: m.node_tree.nodes.remove(nd)
    for im in (col, rm): im.pack()
    novo = bpy.data.materials.new(nome + "_Atlas"); novo.use_nodes = True; nt = novo.node_tree; p = _bsdf(novo)
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = col; nt.links.new(tc.outputs["Color"], p.inputs["Base Color"])
    tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = rm; sp = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tr.outputs["Color"], sp.inputs[0])
    nt.links.new(sp.outputs[1], p.inputs["Roughness"]); nt.links.new(sp.outputs[2], p.inputs["Metallic"])
    for o in obs:
        me = o.data
        for l in [l for l in me.uv_layers if l.name != "Atlas"]: me.uv_layers.remove(l)
        me.uv_layers["Atlas"].name = "UVMap"; me.materials.clear(); me.materials.append(novo)
    print("[SUJAR] atlas %dx%d feito (cores lisas -> textura)" % (lado, lado))
if ATLAS: fazer_atlas()

mats = {s.material for o in obs for s in o.material_slots if s.material and img_cor(s.material)}
mascaras = {}
for m in mats:                                  # um no de imagem alvo por material, no tamanho da cor base
    cor = img_cor(m); w, hh = cor.size
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

for o in obs: o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
bpy.ops.object.bake(type="EMIT")
print("[SUJAR] mascara assada para", nome)

fantasmas = {}
if FANTASMA:                                     # 2a passada: faixas de escrita apagada (eixo longo do quadro = y, altura = z)
    for m, (alvo, antes, out, ja) in mascaras.items():
        nt = m.node_tree; nos = nt.nodes; L = nt.links
        fa = bpy.data.images.new("Fantasma_" + m.name, *alvo.size, float_buffer=True); fa.colorspace_settings.name = "Non-Color"
        tc = nos.new("ShaderNodeTexCoord"); mp = nos.new("ShaderNodeMapping"); L.new(tc.outputs["Object"], mp.inputs["Vector"])
        mp.inputs["Scale"].default_value = (1, 2.2, 16)                            # tracos compridos na horizontal
        n1 = nos.new("ShaderNodeTexNoise"); L.new(mp.outputs[0], n1.inputs["Vector"]); n1.inputs["Detail"].default_value = 4; n1.inputs["Scale"].default_value = 3
        n2 = nos.new("ShaderNodeTexNoise"); L.new(tc.outputs["Object"], n2.inputs["Vector"]); n2.inputs["Scale"].default_value = 1.4; n2.inputs["Detail"].default_value = 2
        n3 = nos.new("ShaderNodeTexNoise"); L.new(tc.outputs["Object"], n3.inputs["Vector"]); n3.inputs["Scale"].default_value = 40; n3.inputs["Detail"].default_value = 6
        cc = nos.new("ShaderNodeCombineColor"); L.new(n1.outputs["Fac"], cc.inputs[0]); L.new(n2.outputs["Fac"], cc.inputs[1]); L.new(n3.outputs["Fac"], cc.inputs[2])
        em = nos.new("ShaderNodeEmission"); L.new(cc.outputs[0], em.inputs["Color"]); L.new(em.outputs[0], out.inputs["Surface"])
        ti = nos.new("ShaderNodeTexImage"); ti.image = fa; nos.active = ti; fantasmas[m] = fa
    bpy.ops.object.bake(type="EMIT")
    print("[SUJAR] fantasma de caneta assado")

TINTA = {"encardido": np.array((.52, .46, .36)), "amarelado": np.array((.80, .62, .30))}
for m, (alvo, antes, out, ja) in mascaras.items():
    nt = m.node_tree
    if antes: nt.links.new(antes, out.inputs["Surface"])            # devolve o shader original
    w, hh = alvo.size
    M = np.array(alvo.pixels[:], dtype=np.float32).reshape(hh, w, 4)
    uso = M[..., 3] > .5 if M[..., 3].min() < .5 else np.ones(M.shape[:2], bool)
    b = M[..., 2]; lo, hi = np.percentile(b[uso], 10), np.percentile(b[uso], 90)
    ruido = np.clip((b - lo) / max(hi - lo, 1e-4), 0, 1)               # ruido normalizado: manchas de verdade, nao um veu
    fresta = np.clip(M[..., 0], 0, 1) ** 1.2 * (.35 + .65 * ruido) * f_fresta
    geral = ruido ** 2.5 * f_geral                                      # encardido de uso, em manchas, na peca toda
    perto = np.clip(M[..., 1], 0, 1) ** 1.3 * (.25 + .75 * ruido) * f_base
    cor = img_cor(m); C = np.array(cor.pixels[:], dtype=np.float32).reshape(hh, w, 4)
    sujo = C[..., :3] * (1 - np.clip(fresta + geral, 0, 1)[..., None] * (1 - TINTA["encardido"]))
    sujo = sujo * (1 - perto[..., None] * (1 - TINTA[cor_base]))
    if m in fantasmas:                                                 # so na parte branca do quadro (moldura e texto ficam)
        F = np.array(fantasmas[m].pixels[:], dtype=np.float32).reshape(hh, w, 4)
        lum = C[..., :3].mean(-1); branco = np.clip((lum - .78) / .1, 0, 1)
        tr = np.clip((F[..., 0] - .52) / .1, 0, 1) * np.clip((F[..., 1] - .42) / .2, 0, 1) * (.6 + .4 * F[..., 2])
        borrao = np.clip((F[..., 1] - .5) / .3, 0, 1) * .35
        g = np.clip(tr + borrao, 0, 1) * branco * .5                           # forca fixa: marcas leves
        sujo = sujo * (1 - g[..., None] * (1 - np.array((.62, .64, .70))))
        print("[SUJAR] fantasma: cobertura %.3f" % (g > .02).mean())
    C[..., :3] = np.clip(sujo, 0, 1); cor.pixels[:] = C.ravel()
    orm = img_rug(m)
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
