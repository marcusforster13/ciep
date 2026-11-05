"""
A mensagem - ocorrencia em uma escola: cena base para Blender 5.x (gera ciep.blend do zero)

Escola inspirada no CIEP Tancredo Neves (Rio de Janeiro). Referencias em ../_referencias/CIEP_Referencias_VR.
  - Do PROJETO-PADRAO dos CIEPs (acervo Fundacao Oscar Niemeyer, nao especifico desta unidade): bloco principal
    longo de 3 pavimentos em concreto aparente, malha de pilares em modulos, corredor central com salas dos dois
    lados (PRO192-ALB-107.03), terreo com arcadas, janelas em arco arredondado com peitoril pintado em cores
    alternadas (PRO192-ALB-254.02: "cores concretina"), passarela coberta com porticos em arco (foto "ft ciep 02").
  - Da UNIDADE TANCREDO NEVES (foto Leonardo Finotti / Arquitectura Viva): aparencia geral da fachada e do patio.
  - NENHUMA MEDIDA ABAIXO E OFICIAL. Todas sao ESTIMADAS a partir das proporcoes dos desenhos e fotos (ver
    MEDIDAS_ESTIMADAS no fim deste arquivo e 05_Treinamento/AMBIENTE_E_REFERENCIAS.md).

Area jogavel (primeira versao): entrada (portao e guarita), patio, passarela, galeria do terreo, recepcao, sala da
direcao, trecho do corredor central, banheiro masculino e uma sala de aula. O resto do predio e so volume externo.

Uso:  blender -b --factory-startup --python ciep.py
Unidades em metros. X = ao longo da fachada, Y = para dentro do predio (o patio fica em Y < 0), Z = para cima.
Sem logotipos e sem brasoes oficiais. Objetos I_* sao interativos; vazios P_* sao pontos usados pelo site.
"""
import bpy, bmesh, math, random, os
import numpy as np
from mathutils import Vector, Matrix

PI = math.pi
rnd = random.Random(2026)
try:
    AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    AQUI = os.path.join(os.path.expanduser("~"), "Desktop", "novovr", "01_Cena_Render_Cycles")

def say(m): print("[CIEP] " + m)

# ------------------------------------------------------------------ limpeza
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
scene = bpy.context.scene

def collection(name):
    c = bpy.data.collections.new(name); scene.collection.children.link(c); return c

# ------------------------------------------------------------------ materiais (mesmas funcoes do Cassino clandestino)
def hx(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
def lin(c): return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def mat(name, color, rough=.8, metal=0., emit=None, forca=0., alpha=None):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes.get("Principled BSDF")
    c = lin(hx(color))
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(hx(emit)), 1)
        b.inputs["Emission Strength"].default_value = forca
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try: setattr(m, attr, val)
            except Exception: pass
    m.diffuse_color = (*c, 1 if alpha is None else alpha)
    return m

def np_image(name, arr):
    h, w, _ = arr.shape
    rgba = np.ones((h, w, 4), dtype=np.float32); rgba[..., :3] = arr
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(np.flipud(rgba).ravel()); img.pack()
    return img

def img_mat(name, img, tile_m, rough=.6):
    """Textura gerada, projetada em caixa (coordenadas do objeto, em metros)."""
    m = bpy.data.materials.new(name); nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile_m,) * 3
    tex.projection = "BOX"; tex.projection_blend = .1
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (.5, .5, .5, 1)
    return m

def tela_mat(nome, img, forca=2.5):
    """Material com imagem e UV propria (prefixo Img_: o pipeline preserva a UV)."""
    m = bpy.data.materials.new("Img_" + nome); nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if forca:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = forca
    b.inputs["Roughness"].default_value = .4
    return m

def tex_granilite(S=512):
    """Piso de granilite (comum em escolas publicas): fundo cinza com graos e juntas de dilatacao."""
    r = np.random.default_rng(4)
    a = np.ones((S, S, 3)) * np.array(hx("#9b9890")) * (1 + .03 * r.standard_normal((S, S, 1)))
    for cor, n in (("#5f5c58", 2600), ("#d8d4ca", 2200), ("#7a6a5a", 900)):
        ys, xs = r.integers(0, S, n), r.integers(0, S, n)
        for dy in (0, 1):
            for dx in (0, 1): a[(ys + dy) % S, (xs + dx) % S] = hx(cor)
    yy, xx = np.mgrid[0:S, 0:S]
    a[(xx % (S // 2) < 2) | (yy % (S // 2) < 2)] = hx("#4d4b47")
    return np.clip(a, 0, 1)

def tex_ceramica(cor, rejunte="#8d8a84", S=256, n=4):
    r = np.random.default_rng(int(sum(cor) * 1000)); cel = S // n
    a = np.kron(r.uniform(.9, 1.05, (n, n, 1)), np.ones((cel, cel, 1))) * np.array(cor)
    a *= (1 + .03 * r.standard_normal((S, S, 1)))
    yy, xx = np.mgrid[0:S, 0:S]
    a[(xx % cel < 2) | (yy % cel < 2)] = np.array(hx(rejunte))
    return np.clip(a, 0, 1)

def tex_persiana(S=256):
    """Janela de vidro com persiana horizontal por dentro (como nas fotos do acervo)."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    lam = (yy * 18) % 1
    a = np.ones((S, S, 3)) * np.array(hx("#c9ccc8")) * (.62 + .38 * np.sin(lam * PI) ** .6)[..., None]
    a[lam < .12] *= .35
    a[(np.abs(xx - .5) < .012)] = hx("#2a2c2e")          # montante do caixilho
    return np.clip(a, 0, 1)

M = {
    "asfalto": mat("Asfalto", "#3a3a3c", .9), "faixa": mat("Pintura_Viaria_Branca", "#d8d6cc", .7),
    "meiofio": mat("Meio_Fio_Concreto", "#9c988f", .95),
    "concreto": mat("Concreto_Aparente", "#a6a29a", .95),
    "patio": mat("Piso_Patio", "#8f8b84", .9),
    "muro": mat("Muro_Reboco", "#d9d6cf", .95),
    "parede": mat("Reboco_Interno", "#e3dfd2", .92),
    "parede_az": mat("Parede_Azul_1070", "#5d7fae", .9),      # "as paredes serao pintadas de azul 1070" (PRO192-ALB-254.02); tom ESTIMADO
    "laje": mat("Laje_Teto", "#d2cec4", .95),
    "porta_mad": mat("Porta_Madeira", "#6b4a30", .6), "mad_cl": mat("Madeira_Clara", "#9a7650", .6),
    "porta_ferro": mat("Porta_Ferro", "#46607f", .5, .3), "poste": mat("Poste_Metal", "#3b3d40", .5, .3),
    "grade": mat("Grade_Metal", "#2f3a46", .5, .3),
    # peitoris pintados (sequencia de cores do desenho PRO192-ALB-254.02: 1006, 1038, 1070, 1035 - tons ESTIMADOS)
    "c1006": mat("Peitoril_Branco_1006", "#e9e7e0", .7), "c1038": mat("Peitoril_Amarelo_1038", "#e7a91c", .6),
    "c1070": mat("Peitoril_Azul_1070", "#3e6aa8", .6), "c1035": mat("Peitoril_Azul_Claro_1035", "#a9c2d8", .65),
    "vidro": mat("Vidro_Janela", "#3b4a52", .08, alpha=.55), "vidro_porta": mat("Vidro_Porta", "#9fb5bd", .05, alpha=.3),
    "escuro": mat("Interior_Escuro", "#1c1e20", .9),
    "esquadria": mat("Esquadria_Aluminio", "#3a3d42", .4, .3),
    "lamp_f": mat("Lampada_Fria", "#ffffff", .4, emit="#eaf2ff", forca=14),
    "preto": mat("Preto_Fosco", "#17181a", .6), "branco": mat("Plastico_Branco", "#eceae4", .45),
    "metal": mat("Metal_Escovado", "#8a8c8e", .35, .4), "inox": mat("Inox", "#b9bcc0", .3, .4),
    "verde_quadro": mat("Quadro_Verde", "#24473a", .7), "cortica": mat("Mural_Cortica", "#9a7650", .9),
    "papel": mat("Papel", "#f6f3ea", .9), "papel_am": mat("Papel_Amarelo", "#efd77a", .9), "papel_az": mat("Papel_Azul", "#9cc2e6", .9),
    "tronco": mat("Tronco_Arvore", "#5c4b3c", 1), "folha": mat("Folhagem", "#3d6a35", .8), "terra": mat("Terra_Canteiro", "#5a4634", 1),
    "grama": mat("Grama", "#5f7d3a", .95),
    "texto_pr": mat("Texto_Preto", "#1a1a1a", .6), "texto_br": mat("Texto_Branco", "#f4f4f0", .6), "texto_az": mat("Texto_Azul", "#16307f", .6),
    "fita": mat("Fita_Isolamento", "#e8c21a", .5),
    "mochila": mat("Mochila_Tecido", "#2b3a55", .85), "mochila2": mat("Mochila_Detalhe", "#b3261e", .7),
    "pia": mat("Louca_Branca", "#eeede8", .25), "divisoria": mat("Divisoria_Granito", "#6b6862", .4),
    "cadeira_az": mat("Assento_Carteira", "#2f5f9e", .5), "tampo": mat("Tampo_Carteira", "#d9cfb4", .5),
    "pint_pm": mat("Viatura_Pintura_Branca", "#e9eaec", .3), "faixa_pm": mat("Viatura_Faixa_Azul", "#1e4fb8", .3),
    "giro_verm": mat("Giroflex_Vermelho", "#5a0a08", .2, emit="#ff1010", forca=.05),
    "giro_azul": mat("Giroflex_Azul", "#08205a", .2, emit="#1040ff", forca=.05),
    "brasao": mat("Brasao_(inserir_imagem_oficial)", "#c8cbd0", .5),
    "int_forro": mat("Interior_Forro", "#1d1f22", .9), "interior": mat("Interior_Carro", "#2a2b2e", .8),
    "tela": mat("Tela_Acesa", "#000000", .2, emit="#9fc4ff", forca=2.0),
}
M["piso"] = img_mat("Piso_Granilite", np_image("piso_granilite", tex_granilite()), 2.0, .45)
M["azulejo"] = img_mat("Azulejo_Branco", np_image("azulejo_branco", tex_ceramica(hx("#e4e2da"), "#a5a39c", n=8)), 1.2, .2)
M["persiana"] = tela_mat("Janela_Persiana", np_image("janela_persiana", tex_persiana()), 0)

# ------------------------------------------------------------------ geometria (mesmas funcoes do Cassino clandestino)
def finish(name, bm, loc, mats, col, parent=None, rot=(0, 0, 0), smooth=False, bevel=0.0, seg=2):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]): me.materials.append(m)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if parent: ob.parent = parent
    ob.location = loc; ob.rotation_euler = rot
    if bevel:
        b = ob.modifiers.new("Chanfro", "BEVEL"); b.width = bevel; b.segments = seg; b.limit_method = "ANGLE"
        for p in me.polygons: p.use_smooth = True
    return ob

def box(name, tam, pos, m, col, parent=None, rot=(0, 0, 0), bevel=0.0, seg=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); bmesh.ops.scale(bm, vec=Vector(tam), verts=bm.verts)
    return finish(name, bm, pos, m, col, parent, rot, bevel=bevel, seg=seg)

def cyl(name, r1, r2, h, pos, m, col, parent=None, rot=(0, 0, 0), seg=20):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h)
    return finish(name, bm, pos, m, col, parent, rot, smooth=True)

def barra(name, a, b, r, m, col, parent=None, seg=10):
    a, b = Vector(a), Vector(b); d = b - a
    ob = cyl(name, r, r, d.length, (a + b) / 2, m, col, parent, seg=seg)
    ob.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return ob

def esfera(nome, r, pos, m, col, parent=None, sub=2, esc=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r); bmesh.ops.scale(bm, vec=Vector(esc), verts=bm.verts)
    return finish(nome, bm, pos, m, col, parent, smooth=True)

def malha(name, verts, faces, m, col, parent=None, pos=(0, 0, 0), smooth=False, idx=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    if idx:
        bm.faces.ensure_lookup_table()
        for f, i in zip(bm.faces, idx): f.material_index = i
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, pos, m, col, parent, smooth=smooth)

def texto_malha(conteudo, tam, espaco=1.0):
    cu = bpy.data.curves.new("_txt", "FONT"); cu.body = conteudo; cu.size = tam; cu.align_x = "CENTER"; cu.align_y = "CENTER"
    cu.resolution_u = 2; cu.space_character = espaco
    tmp = bpy.data.objects.new("_txt_tmp", cu); scene.collection.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
    return me

VIRADO = {"-y": (PI / 2, 0, 0), "+y": (PI / 2, 0, PI), "-x": (PI / 2, 0, -PI / 2), "+x": (PI / 2, 0, PI / 2), "cima": (0, 0, 0)}
def texto(name, conteudo, tam, pos, virado, m, col, parent=None, espaco=1.0):
    me = texto_malha(conteudo, tam, espaco); me.name = name; me.materials.append(m)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    if parent: ob.parent = parent
    ob.location = pos; ob.rotation_euler = VIRADO[virado] if isinstance(virado, str) else virado
    return ob

def vazio(name, pos, col, rz=0.0, parent=None):
    e = bpy.data.objects.new(name, None); col.objects.link(e); e.location = pos; e.rotation_euler = (0, 0, rz)
    e.empty_display_size = .4
    if parent: e.parent = parent
    return e

def luz(name, tipo, watts, cor, pos, col, parent=None, alvo=None, **kw):
    l = bpy.data.lights.new(name, tipo); l.energy = watts; l.color = lin(hx(cor))
    for k, v in kw.items(): setattr(l, k, v)
    ob = bpy.data.objects.new(name, l); col.objects.link(ob); ob.location = pos
    if parent: ob.parent = parent
    if alvo is not None:
        ob.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return ob

def adesivo(name, ponto_f, nu, nv, col, parent=None, pos=(0, 0, 0), mat_=None):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    g = [[bm.verts.new(ponto_f(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (a / nu, b / nv)
    return finish(name, bm, pos, mat_, col, parent, smooth=True)

DIR_U = {"-y": (1, 0, 0), "+y": (-1, 0, 0), "-x": (0, -1, 0), "+x": (0, 1, 0)}
def quadro(name, centro, virado, larg, alt, m, col, parent=None):
    du = Vector(DIR_U[virado]); c = Vector(centro)
    return adesivo(name, lambda u, v: c + du * (u - .5) * larg + Vector((0, 0, (v - .5) * alt)), 1, 1, col, parent, mat_=m)

def camera(nome, pos, alvo, lente=22):
    cd = bpy.data.cameras.new(nome); cd.lens = lente; cd.clip_end = 400
    ob = bpy.data.objects.new(nome, cd); C_LUZ.objects.link(ob); ob.location = pos
    ob.rotation_euler = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return ob

PH_DIR = os.path.join(AQUI, "modelos", "polyhaven"); _ph = {}
def modelo_ph(nome, asset, pos, rz=0.0, col=None, escala=1.0, max_tris=2000, alt=None, parent=None):
    """Modelo CC0 do Poly Haven (mesmo fluxo do Cassino e do Busca e Apreensao). Devolve None se o arquivo faltar."""
    if asset not in _ph:
        caminho = os.path.join(PH_DIR, asset, asset + "_1k.gltf")
        if not os.path.exists(caminho): _ph[asset] = None
        else:
            antes = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=caminho); bpy.context.view_layer.update()
            novos = [o for o in bpy.data.objects if o not in antes]; malhas = [o for o in novos if o.type == "MESH"]
            for o in malhas:
                mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
            if len(malhas) > 1:
                with bpy.context.temp_override(active_object=malhas[0], selected_objects=malhas, selected_editable_objects=malhas):
                    bpy.ops.object.join()
            ob = malhas[0]; ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)
            for i, sl in enumerate(ob.material_slots):
                if sl.material: sl.material.name = "Modelo_PH_%s_%d" % (asset, i)
            tris = sum(len(pl.vertices) - 2 for pl in ob.data.polygons)
            if tris > max_tris:
                d = ob.modifiers.new("Reduzir", "DECIMATE"); d.ratio = max_tris / tris
                me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get())); ob.modifiers.clear()
            else: me = ob.data.copy()
            vs = [v.co for v in me.vertices]
            mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
            me.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
            for pl in me.polygons: pl.use_smooth = True
            me.name = "PH_" + asset
            for o in [o for o in bpy.data.objects if o not in antes]: bpy.data.objects.remove(o, do_unlink=True)
            _ph[asset] = (me, mx - mn)
    if not _ph[asset]: return None
    me, dims = _ph[asset]
    ob = bpy.data.objects.new(nome, me); (col or C_MOV).objects.link(ob)
    if parent: ob.parent = parent
    k = escala if alt is None else alt / dims.z
    ob.location = pos; ob.rotation_euler = (0, 0, rz); ob.scale = (k, k, k)
    return ob

def ponto(nome, x, y, olha=(0, -1), z=None):
    """Ponto usado pelo site (personagens, rotas): vazio P_<nome>; rz = para onde a pessoa olha."""
    return vazio("P_" + nome, (x, y, FZ if z is None else z), C_LUZ, math.atan2(olha[0], -olha[1]))

# ---- viatura (mesmo modelo e mesmas funcoes do Cassino clandestino: modelos/carros/perua.glb)
CARROS = os.path.join(AQUI, "modelos", "carros")
def repintar(img, cor, nome):
    w, h = img.size; px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
    rgb = px[:, :3]; mx = rgb.max(1); mn = rgb.min(1); sat = (mx - mn) / np.maximum(mx, 1e-4)
    m = (sat > .3) & (mx > .12)
    if m.sum() < 100: return img
    ref = np.median(mx[m]); k = np.clip(mx[m] / ref, 0, 1.6)[:, None]
    rgb[m] = np.clip(np.array(hx(cor), np.float32)[None, :] * k, 0, 1)
    novo = bpy.data.images.new(nome, w, h, alpha=True); novo.pixels.foreach_set(px.ravel()); novo.pack()
    return novo

def carro_modelo(nome, col, arquivo, pos, rz, cor=None, escala=1.0):
    caminho = os.path.join(CARROS, arquivo + ".glb")
    if not os.path.exists(caminho): return None
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=caminho)
    novos = [o for o in bpy.data.objects if o not in antes]
    R = next(o for o in novos if o.parent is None); R.name = nome
    for o in novos:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o)
        if o is not R: o.name = nome + "_" + o.name.split(".")[0]
    if escala != 1.0:
        for o in novos:
            if o.type == "MESH":
                o.data.transform(Matrix.Scale(escala, 4)); o.location = o.location * escala
    corpo = next(o for o in novos if o.type == "MESH" and "Carroceria" in o.name)
    feitos = {}
    for s in corpo.material_slots:
        m = s.material.copy(); m.name = "Modelo_%s_%s" % (nome, s.material.name.split(".")[0]); s.material = m
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        tex = next((n for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.outputs["Color"].is_linked and any(l.to_socket.name == "Base Color" for l in n.outputs["Color"].links)), None)
        nm = m.name.lower()
        if cor and tex and tex.image and not any(k in nm for k in ("glass", "optic", "decal")):
            tex.image = feitos.setdefault(tex.image.name, repintar(tex.image, cor, "pintura_%s_%s" % (nome, tex.image.name)))
        if "glass" in nm and b:
            for l in list(b.inputs["Alpha"].links): m.node_tree.links.remove(l)
            for l in list(b.inputs["Base Color"].links): m.node_tree.links.remove(l)
            b.inputs["Base Color"].default_value = (.03, .045, .055, 1); b.inputs["Alpha"].default_value = .8
            b.inputs["Roughness"].default_value = .06; b.inputs["Metallic"].default_value = 0
            for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
                try: setattr(m, attr, val)
                except Exception: pass
    for o in novos:
        if o.type == "MESH" and o is not corpo:
            for s in o.material_slots:
                if s.material and not s.material.name.startswith("Modelo_"):
                    m = s.material.copy(); m.name = "Modelo_%s_%s" % (nome, s.material.name.split(".")[0]); s.material = m
    R.location = pos; R.rotation_euler = (0, 0, rz)
    bpy.context.view_layer.update()
    pts = [Vector(c) for c in corpo.bound_box]
    hw = max(abs(p.y) for p in pts); comp = max(p.x for p in pts) - min(p.x for p in pts); alt = max(p.z for p in pts)
    ev = corpo.evaluated_get(bpy.context.evaluated_depsgraph_get())
    def sup_y(x, z, lado):
        ok, lc, _, _ = ev.ray_cast(Vector((x, lado * 3.0, z)), Vector((0, -lado, 0)))
        return lc.y if ok else lado * hw
    return R, sup_y, {"hw": hw, "comp": comp, "alt": alt}

def faixa_lateral(nome, R, col, sup_y, x0, x1, z0, z1, m, n=24):
    for lado in (1, -1):
        vs, fs = [], []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            for z in (z0, z1): vs.append((x, sup_y(x, z, lado) + lado * .006, z))
        for i in range(n): fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
        malha(nome, vs, fs, m, col, R)

def giroflex(R, col, x, z, larg=1.1):
    box("Giroflex_Base", (.32, larg, .05), (x, 0, z), M["preto"], col, R, bevel=.015)
    n = 6; w = larg / n
    for k in range(n):
        y = -larg / 2 + w * (k + .5)
        box("Giroflex_Lente_%d" % (k + 1), (.28, w * .92, .09), (x, y, z + .07), M["giro_verm"] if k < 3 else M["giro_azul"], col, R, bevel=.022)
    luz("Giroflex_Luz_Vermelha", "POINT", 0, "#ff1a10", (x, -.35, z + .2), col, R)
    luz("Giroflex_Luz_Azul", "POINT", 0, "#2050ff", (x, .35, z + .2), col, R)

# ================================================================== CIEP
# Planta (metros, ESTIMADA):
#   rua               y -48 .. -40        calcada  y -40 .. -38      muro do terreno em y = -38, portao x -3 .. 3
#   patio             x -55 .. 55, y -38 .. 0   concreto em placas; passarela coberta de x -3 .. 3 ligando o portao ao predio
#   predio principal  x -50 .. 50, y 0 .. 17  (20 modulos de 5 m; 3 pavimentos; o desenho cita "100" no comprimento)
#     galeria do terreo (arcadas)  y 0 .. 3
#     salas da frente              y 3 .. 8      recepcao x -6 .. 0 · direcao x 0 .. 6 · secretaria x -12 .. -6 (fechada)
#     corredor central             y 8 .. 11     trecho acessivel x -15 .. 15 (portas corta-fogo nas pontas)
#     salas dos fundos             y 11 .. 17    banheiro masc. x -15 .. -9 · banheiro fem. x -9 .. -3 (fechado)
#                                                rampa x -3 .. 3 (acesso fechado) · sala de aula 104 x 3 .. 9 · professores x 9 .. 15 (fechada)
FZ = .15                       # nivel do piso do patio e do terreno
PISO = 3.8                     # altura entre pavimentos (ESTIMADA)
Z1, Z2, Z3 = FZ + PISO, FZ + 2 * PISO, FZ + 3 * PISO       # lajes do 1o e 2o pavimento e da cobertura
X0, X1, PROF, MOD = -50.0, 50.0, 17.0, 5.0
PD = PISO - .35                # pe-direito livre do terreo (laje de 35 cm, ESTIMADA)

C_RUA = collection("01_Rua"); C_PAT = collection("02_Patio"); C_FAC = collection("03_Predio_Fachada")
C_TER = collection("04_Terreo_Interior"); C_PAS = collection("05_Passarela"); C_MOV = collection("06_Moveis")
C_INT = collection("08_Interativos"); C_LUZ = collection("09_Luzes_Cameras"); C_VEIC = collection("10_Viatura")
C_SOLTO = collection("12_Objetos_Soltos")       # pecas pequenas/finas: fora do lightmap (saem manchadas no bake)

def parede(nome, a, b, m, col, vaos=(), h=PD, t=.2, z0=FZ, ext=None):
    """Parede reta entre a=(x, y) e b=(x, y), alinhada a um eixo, com vaos [(d0, d1, zbase, ztopo)] medidos a partir de a.
    Cada trecho e uma caixa separada: a malha de colisao usa uma caixa por objeto, entao os vaos ficam livres."""
    ax, ay = a; bx, by = b; horiz = abs(bx - ax) > abs(by - ay)
    L = abs(bx - ax) if horiz else abs(by - ay); sg = 1 if ((bx - ax) if horiz else (by - ay)) > 0 else -1
    def trecho(d0, d1, zb, zt, suf):
        if d1 - d0 < .01 or zt - zb < .01: return
        c = (d0 + d1) / 2
        pos = (ax + sg * c, ay, z0 + (zb + zt) / 2) if horiz else (ax, ay + sg * c, z0 + (zb + zt) / 2)
        box(nome + suf, (d1 - d0, t, zt - zb) if horiz else (t, d1 - d0, zt - zb), pos, m, col)
    if ext is None: ext = t / 2 if t >= .2 else -.07
    d = -ext
    for v0, v1, zb, zt in sorted(vaos):
        trecho(d, v0, 0, h, ""); trecho(v0, v1, 0, zb, "_Mureta"); trecho(v0, v1, zt, h, "_Verga"); d = v1
    trecho(d, L + ext, 0, h, "")

# ---- painel com abertura arredondada (a peca que se repete na fachada dos CIEPs)
def contorno_arredondado(w, h, r, n=8):
    """Retangulo w x h com cantos de raio r, centrado na origem, no sentido anti-horario, a partir do angulo 0."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, PI / 2), (-w / 2 + r, -h / 2 + r, PI), (w / 2 - r, -h / 2 + r, 1.5 * PI)):
        for k in range(n + 1):
            a = a0 + PI / 2 * k / n; pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def painel_simples(nome, w, h, fw, fh, r, fcz, esp, pos, m, col, fundo_aberto=False, rz=0.0):
    """Mesma peca feita por fatias horizontais (robusta): faixas solidas acima/abaixo e laterais seguindo o arco."""
    furo = contorno_arredondado(fw, fh, r, 6)
    ys = sorted({round(y + fcz, 5) for _, y in furo})
    bot = -h / 2 if fundo_aberto else fcz - fh / 2
    bm = bmesh.new()
    def quad(x0, x1, y0, y1):
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4: return
        vs = [bm.verts.new(p) for p in ((x0, -esp / 2, y0), (x1, -esp / 2, y0), (x1, -esp / 2, y1), (x0, -esp / 2, y1),
                                          (x0, esp / 2, y0), (x1, esp / 2, y0), (x1, esp / 2, y1), (x0, esp / 2, y1))]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)):
            bm.faces.new([vs[i] for i in f])
    top = fcz + fh / 2
    quad(-w / 2, w / 2, top, h / 2)                        # faixa acima da abertura
    if not fundo_aberto: quad(-w / 2, w / 2, -h / 2, bot)  # faixa abaixo (peitoril de concreto)
    def meia_larg(y):                                      # meia largura da abertura na altura y
        yy = y - fcz; hy = fh / 2 - r
        if abs(yy) <= hy or (fundo_aberto and yy < 0): return fw / 2      # arco: os pes descem retos ate o chao
        d = abs(yy) - hy; return fw / 2 - r + math.sqrt(max(0, r * r - d * d))
    cortes = sorted({bot, top} | {y for y in ys if bot <= y <= top})
    for y0, y1 in zip(cortes, cortes[1:]):
        hw = min(meia_larg(y0), meia_larg(y1)); hw2 = max(meia_larg(y0), meia_larg(y1))
        for s in (-1, 1):                                   # trapezio de cada lado (aproximado por quad da largura menor)
            x_in0, x_in1 = s * meia_larg(y0), s * meia_larg(y1)
            vs = [bm.verts.new(p) for p in ((x_in0, -esp / 2, y0), (s * w / 2, -esp / 2, y0), (s * w / 2, -esp / 2, y1), (x_in1, -esp / 2, y1),
                                              (x_in0, esp / 2, y0), (s * w / 2, esp / 2, y0), (s * w / 2, esp / 2, y1), (x_in1, esp / 2, y1))]
            for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3)):
                try: bm.faces.new([vs[i] for i in f])
                except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(nome, bm, pos, m, col, rot=(0, 0, rz))

# ------------------------------------------------------------------ 1. rua, calcada, muro e portao
box("Rua_Asfalto", (160, 8, .1), (0, -44, -.05), M["asfalto"], C_RUA)
for x in range(-76, 80, 6): box("Rua_Faixa", (3, .12, .01), (x, -44, .005), M["faixa"], C_RUA)
box("Calcada", (160, 2.2, .15), (0, -39.0, .075), M["meiofio"], C_RUA)
box("Meio_Fio", (160, .15, .2), (0, -40.05, .1), M["meiofio"], C_RUA)
MURO_H = 2.4                                                 # ESTIMADO
for xa, xb in ((-56, -3.0), (3.0, 56)):
    box("Muro_Frente", (xb - xa, .2, MURO_H), ((xa + xb) / 2, -38, FZ + MURO_H / 2), M["muro"], C_PAT)
for sx in (-1, 1):
    box("Muro_Lateral", (.2, 56, MURO_H), (sx * 56, -10, FZ + MURO_H / 2), M["muro"], C_PAT)
    box("Portao_Coluna", (.45, .45, 2.8), (sx * 3.2, -38, FZ + 1.4), M["concreto"], C_PAT)
box("Muro_Fundos", (112, .2, MURO_H), (0, 18.2, FZ + MURO_H / 2), M["muro"], C_PAT)
texto("Muro_Placa_Nome", "CIEP TANCREDO NEVES", .32, (-14, -38.12, FZ + 1.75), "-y", M["texto_az"], C_SOLTO)
texto("Muro_Placa_Sub", "ESCOLA PÚBLICA", .2, (-14, -38.12, FZ + 1.3), "-y", M["texto_az"], C_SOLTO)
# portao de grade (aberto, encostado no muro)
for sx in (-1, 1):
    r = vazio("Portao_Folha", (sx * 2.95, -37.85, FZ), C_PAT, sx * PI * .48 + (PI if sx < 0 else 0))
    box("Portao_Quadro_Sup", (2.9, .05, .06), (1.45, 0, 2.2), M["grade"], C_SOLTO, r)
    box("Portao_Quadro_Inf", (2.9, .05, .06), (1.45, 0, .1), M["grade"], C_SOLTO, r)
    for k in range(15): box("Portao_Barra", (.025, .025, 2.1), (.1 + k * .19, 0, 1.15), M["grade"], C_SOLTO, r)
# guarita da portaria (inspetora)
GX, GY = 6.5, -35.6
parede("Guarita_Frente", (GX - 1.6, GY - 1.4), (GX + 1.6, GY - 1.4), M["muro"], C_PAT, vaos=[(.4, 2.8, 1.0, 2.1)], h=2.6)
parede("Guarita_Fundo", (GX - 1.6, GY + 1.4), (GX + 1.6, GY + 1.4), M["muro"], C_PAT, h=2.6)
parede("Guarita_Lado", (GX + 1.6, GY - 1.4), (GX + 1.6, GY + 1.4), M["muro"], C_PAT, h=2.6)
parede("Guarita_Porta", (GX - 1.6, GY - 1.4), (GX - 1.6, GY + 1.4), M["muro"], C_PAT, vaos=[(1.6, 2.5, 0, 2.1)], h=2.6)
box("Guarita_Laje", (3.6, 3.2, .15), (GX, GY, FZ + 2.67), M["concreto"], C_PAT)
box("Guarita_Vidro", (2.4, .02, 1.1), (GX, GY - 1.4, FZ + 1.55), M["vidro"], C_SOLTO)
box("Guarita_Bancada", (2.6, .5, .05), (GX, GY - 1.05, FZ + .9), M["mad_cl"], C_MOV)

# ------------------------------------------------------------------ 2. patio
box("Patio_Piso", (112, 38, .15), (0, -19, FZ - .075), M["patio"], C_PAT)
for x in range(-54, 56, 4): box("Patio_Junta", (.03, 38, .004), (x, -19, FZ + .002), M["preto"], C_SOLTO)
for y in range(-36, 0, 4): box("Patio_Junta", (110, .03, .004), (0, y, FZ + .002), M["preto"], C_SOLTO)
box("Fundo_Terreno", (112, 3, .15), (0, 17.6, FZ - .075), M["patio"], C_PAT)
# mastros (sem bandeiras: nada de simbolos oficiais), como na foto do acervo
for k, x in enumerate((-9.0, -8.2, -7.4)):
    cyl("Mastro", .04, .05, 9.5 - k * .6, (x, -10.5, FZ + (9.5 - k * .6) / 2), M["poste"], C_SOLTO, seg=10)
box("Mastro_Base", (2.6, 1.0, .3), (-8.2, -10.5, FZ + .15), M["concreto"], C_PAT)
# canteiros e arvores simples (desenho proprio: tronco e copa)
def arvore(nome, x, y, alt=5.5, copa=2.2):
    cyl(nome + "_Tronco", .14, .2, alt * .55, (x, y, FZ + alt * .275), M["tronco"], C_PAT, seg=10)
    for k in range(4):
        a = k * 1.7; esfera(nome + "_Copa", copa * rnd.uniform(.7, 1.0), (x + math.cos(a) * copa * .45, y + math.sin(a) * copa * .45, FZ + alt * .62 + rnd.uniform(0, 1.2)), M["folha"], C_SOLTO, sub=2, esc=(1, 1, .75))
for k, (x, y) in enumerate(((-30, -30), (-22, -24), (22, -26), (34, -31), (-44, -14), (44, -16))):
    box("Canteiro", (4, 4, .35), (x, y, FZ + .17), M["concreto"], C_PAT)
    box("Canteiro_Terra", (3.6, 3.6, .02), (x, y, FZ + .35), M["terra"], C_PAT)
    arvore("Arvore_%d" % k, x, y)
# bancos de concreto e lixeiras
for k, (x, y, rz) in enumerate(((-14, -6, 0), (-20, -6, 0), (14, -6, 0), (20, -6, 0), (-12, -20, PI / 2), (12, -20, PI / 2))):
    r = vazio("Banco_Patio", (x, y, FZ), C_PAT, rz)
    box("Banco_Patio_Tampo", (2.2, .45, .1), (0, 0, .45), M["concreto"], C_PAT, r)
    for sx in (-1, 1): box("Banco_Patio_Pe", (.2, .4, .4), (sx * .85, 0, .2), M["concreto"], C_PAT, r)
for k, (x, y) in enumerate(((-6.0, -2.5), (6.0, -2.5), (-4.0, -30.0))):
    modelo_ph("Lixeira_Patio", "metal_trash_can", (x, y, FZ), 0, C_SOLTO, alt=.9) or cyl("Lixeira_Patio", .25, .22, .8, (x, y, FZ + .4), M["poste"], C_SOLTO)
# bebedouro (na galeria)
r = vazio("Bebedouro", (-8.5, 1.0, FZ), C_MOV)
box("Bebedouro_Corpo", (1.4, .45, .9), (0, 0, .45), M["inox"], C_MOV, r)
box("Bebedouro_Cuba", (1.3, .4, .05), (0, 0, .92), M["inox"], C_MOV, r)
# postes de iluminacao do patio
for x, y in ((-18, -16), (18, -16), (0, -24)):
    modelo_ph("Poste_Patio", "street_lamp_01", (x, y, FZ), 0, C_SOLTO, alt=6.0) or cyl("Poste_Patio", .07, .1, 6, (x, y, FZ + 3), M["poste"], C_SOLTO)

# ------------------------------------------------------------------ 3. predio principal: estrutura, fachadas e cobertura
NM = int((X1 - X0) / MOD)                                   # 20 modulos
CORES = ["c1006", "c1006", "c1038", "c1070", "c1006", "c1035"]      # sequencia do desenho de cores (repetida)
GAL = 3.0                                                   # profundidade da galeria do terreo (ESTIMADA)
# lajes
C_GAL = collection("07_Galeria")
box("Laje_Piso_Terreo", (X1 - X0, PROF, .15), ((X0 + X1) / 2, PROF / 2, FZ - .075), M["piso"], C_GAL)
box("Piso_Terreo_Jogavel", (30.0, 11.0, .15), (0.0, 8.5, FZ - .073), M["piso"], C_TER)      # 2 mm acima: lightmap proprio na area jogavel
box("Laje_1", (X1 - X0, PROF, .35), ((X0 + X1) / 2, PROF / 2, Z1 - .175), M["laje"], C_FAC)
box("Laje_Cobertura", (X1 - X0, PROF, .4), ((X0 + X1) / 2, PROF / 2, Z3 - .2), M["concreto"], C_FAC)
# o volume dos pavimentos superiores (sem interior): bloco escuro recuado atras das janelas
box("Pavimentos_Superiores_Volume", (X1 - X0 - .6, PROF - 1.6, Z3 - Z1 - .6), ((X0 + X1) / 2, PROF / 2, (Z1 + Z3) / 2), M["escuro"], C_FAC)
# platibanda com nervuras verticais (foto do acervo)
PL_H = 1.4
for lado, y in ((-1, -.1), (1, PROF + .1)):
    box("Platibanda", (X1 - X0 + .2, .25, PL_H), ((X0 + X1) / 2, y, Z3 + PL_H / 2 - .2), M["concreto"], C_FAC)
    for k in range(int((X1 - X0) / 1.25) + 1):
        box("Platibanda_Nervura", (.12, .08, PL_H), (X0 + k * 1.25, y + lado * -.16, Z3 + PL_H / 2 - .2), M["concreto"], C_SOLTO)
for x in (X0 - .1, X1 + .1):
    box("Platibanda_Lateral", (.25, PROF + .2, PL_H), (x, PROF / 2, Z3 + PL_H / 2 - .2), M["concreto"], C_FAC)
# empenas laterais
for x in (X0 - .1, X1 + .1):
    box("Empena", (.3, PROF + .2, Z3 - FZ), (x, PROF / 2, (FZ + Z3) / 2), M["concreto"], C_FAC)
# fachadas dos pavimentos superiores (frente y = 0 e fundos y = PROF): uma janela arredondada por modulo
JW, JH, JR = 3.9, 2.55, .75                                 # abertura (ESTIMADA pela foto: ~78% do modulo)
for fy, rz, lado in ((0.0, 0.0, -1), (PROF, PI, 1)):
    for a, z0 in enumerate((Z1, Z2)):
        for k in range(NM):
            xc = X0 + MOD * (k + .5); zc = z0 + PISO / 2
            painel_simples("Fachada_Painel", MOD, PISO, JW, JH, JR, .15, .3, (xc, fy, zc), M["concreto"], C_FAC, rz=rz)
            cor = M[CORES[(k + a) % len(CORES)]]
            # peitoril pintado: o terco de baixo da abertura (cores alternadas, como no desenho e na foto)
            zb = zc + .15 - JH / 2
            # (largura cheia: as pontas entram no concreto dos cantos arredondados e somem)
            box("Fachada_Peitoril_Cor", (JW - .04, .12, .95), (xc, fy - lado * .02, zb + .48), cor, C_FAC)
            # vidro com persiana, recuado atras do peitoril
            quadro("Fachada_Janela", (xc, fy - lado * .1, zc + .15 + .45), "-y" if lado < 0 else "+y", JW - .2, JH - 1.0, M["persiana"], C_SOLTO)
# terreo: arcadas na frente e nos fundos (pilares + arco), galeria coberta
AW, AH, AR = 3.9, PD - .2, 1.2
for fy, rz in ((0.0, 0.0), (PROF, PI)):
    for k in range(NM):
        xc = X0 + MOD * (k + .5)
        painel_simples("Arcada_Arco", MOD, PD, AW, AH, AR, -(PD - AH) / 2, .5, (xc, fy, FZ + PD / 2), M["concreto"], C_FAC, fundo_aberto=True, rz=rz)
    for k in range(NM + 1):                                  # pilares (caixas: entram na colisao)
        x = X0 + MOD * k
        box("Arcada_Coluna", (MOD - AW + .04, .54, PD), (x, fy, FZ + PD / 2), M["concreto"], C_FAC)      # 2 cm maior que o arco: sem faces coincidentes
    box("Arcada_Viga", (X1 - X0, .5, Z1 - FZ - PD), ((X0 + X1) / 2, fy, (FZ + PD + Z1) / 2), M["concreto"], C_FAC)
# letreiro com o nome na fachada (sobre a arcada central, como na foto do Tancredo Neves)
texto("Fachada_Letreiro", "CIEP TANCREDO NEVES", .55, (-12.5, -.33, Z1 - .2), "-y", M["texto_pr"], C_SOLTO)

# ------------------------------------------------------------------ 4. terreo: galeria, salas, corredor
Y_GAL, Y_C0, Y_C1 = GAL, 8.0, 11.0
XA0, XA1 = -15.0, 15.0                                       # trecho acessivel do corredor
# paredes internas das galerias (frente y = 3 e fundos y = 14), de ponta a ponta, em tres trechos: o do meio (area
# jogavel) fica na colecao do interior, com lightmap proprio; as pontas ficam na colecao da galeria.
Y_FUN = PROF - GAL
def parede_galeria(nome, y, entrada=None):
    for xa, xb, col in ((X0, XA0, C_GAL), (XA0, XA1, C_TER), (XA1, X1, C_GAL)):
        vaos = []
        for k in range(NM):
            xc = X0 + MOD * (k + .5)
            if not (xa < xc < xb): continue
            if entrada and entrada[0] < xc < entrada[1]: vaos.append((xc - xa - .9, xc - xa + .9, 0, 2.3))      # entrada da recepcao (vao aberto)
            else: vaos.append((xc - xa - 1.4, xc - xa + 1.4, 1.0, 2.4))                                           # janelas
        parede(nome, (xa, y), (xb, y), M["parede_az"], col, vaos=vaos)
        for v0, v1, zb, zt in vaos:
            if zb < .5: continue
            xc = xa + (v0 + v1) / 2
            box(nome + "_Janela_Vidro", (v1 - v0, .03, zt - zb), (xc, y, FZ + (zb + zt) / 2), M["vidro"], C_SOLTO)
            if col is C_GAL or (y < 5 and not (-6 < xc < 6)) or (y > 5 and not (-15 < xc < -9 or 3 < xc < 9)):      # sala sem acesso: fundo escuro
                box(nome + "_Janela_Fundo", (v1 - v0, .05, zt - zb), (xc, y + (.6 if y < 5 else -.6), FZ + (zb + zt) / 2), M["escuro"], C_SOLTO)
parede_galeria("Galeria_Parede", Y_GAL, entrada=(-6, 0))
parede_galeria("Fundos_Parede", Y_FUN)
for y in (GAL / 2, PROF - GAL / 2):
    box("Galeria_Forro", (X1 - X0, GAL, .02), ((X0 + X1) / 2, y, FZ + PD - .02), M["laje"], C_GAL)      # 1 cm abaixo da laje (sem faces coincidentes)
# miolo fechado do terreo fora do trecho acessivel (salas que nao se visitam): blocos macicos atras das paredes
for xa, xb in ((X0, -12.0), (15.0, X1)):
    box("Terreo_Bloco_Fechado_Frente", (xb - xa - .2, Y_C0 - Y_GAL - .3, PD), ((xa + xb) / 2, (Y_GAL + Y_C0) / 2 + .05, FZ + PD / 2), M["escuro"], C_GAL)
for xa, xb in ((X0, XA0), (XA1, X1)):
    box("Terreo_Bloco_Fechado_Fundos", (xb - xa - .2, Y_FUN - Y_C0 - .3, PD), ((xa + xb) / 2, (Y_C0 + Y_FUN) / 2, FZ + PD / 2), M["escuro"], C_GAL)
# corredor central: paredes y = 8 e y = 11, de -15 a 15
# frente (y = 8): secretaria (-12..-6), recepcao (-6..0, aberta para o corredor), direcao (0..6), sala 101 (6..12), pilar 12..15
parede("Corredor_Parede_Frente", (XA0, Y_C0), (XA1, Y_C0), M["parede"], C_TER,
       vaos=[(-9.9 - XA0, -9.0 - XA0, 0, 2.1), (-4.2 - XA0, -1.8 - XA0, 0, 2.4), (8.2 - XA0, 9.1 - XA0, 0, 2.1)])
# fundos (y = 11): banheiro masc. (-15..-9), banheiro fem. (-9..-3), rampa (-3..3), sala 104 (3..9), professores (9..15)
parede("Corredor_Parede_Fundos", (XA0, Y_C1), (XA1, Y_C1), M["parede"], C_TER,
       vaos=[(-12.6 - XA0, -11.7 - XA0, 0, 2.1), (-6.6 - XA0, -5.7 - XA0, 0, 2.1), (-2.5 - XA0, 2.5 - XA0, 0, 2.9), (5.4 - XA0, 6.3 - XA0, 0, 2.1), (11.4 - XA0, 12.3 - XA0, 0, 2.1)])
# divisorias entre as salas
for x in (-12.0, -6.0, 0.0, 6.0, 12.0):
    vaos = [(2.0, 2.9, 0, 2.1)] if x == 0.0 else []         # direcao <-> recepcao: vao da porta (y 5.0 .. 5.9)
    parede("Divisoria_Frente", (x, Y_GAL), (x, Y_C0), M["parede"], C_TER, vaos=vaos, ext=0.0)      # termina no eixo da parede vizinha
for x in (-9.0, -3.0, 3.0, 9.0):
    parede("Divisoria_Fundos", (x, Y_C1), (x, Y_FUN), M["parede"], C_TER, ext=0.0)
# pontas do corredor: portas corta-fogo fechadas (o corredor continua alem delas)
for x, s in ((XA0, -1), (XA1, 1)):
    parede("Corredor_Ponta", (x, Y_C0), (x, Y_C1), M["parede"], C_TER, vaos=[(.4, 2.6, 0, 2.2)], ext=0.0)
    box("Corredor_Porta_Corta_Fogo", (.06, 2.2, 2.2), (x, (Y_C0 + Y_C1) / 2, FZ + 1.1), M["porta_ferro"], C_TER)
    box("Corredor_Porta_Visor", (.07, .3, .5), (x, (Y_C0 + Y_C1) / 2 - .5, FZ + 1.5), M["vidro"], C_SOLTO)
    texto("Corredor_Porta_Placa", "SAÍDA DE EMERGÊNCIA" if s > 0 else "BLOCO B", .09, (x - s * .045, (Y_C0 + Y_C1) / 2, FZ + 2.05), "+x" if s < 0 else "-x", M["texto_pr"], C_SOLTO)
# forro do trecho acessivel
box("Terreo_Forro", (XA1 - XA0, Y_FUN - GAL, .02), (0, (GAL + Y_FUN) / 2, FZ + PD - .02), M["laje"], C_TER)
# rampa (marca dos CIEPs, no centro do bloco): visivel pelo vao, com grade fechada
for k in range(5):
    box("Rampa_Patamar", (5.6, .55, .12), (0, 11.85 + k * .5, FZ + .12 + k * .3), M["concreto"], C_TER)
box("Rampa_Guarda_Corpo", (.06, 2.4, 1.0), (-2.8, 12.8, FZ + 1.4), M["grade"], C_SOLTO)
r = vazio("Rampa_Grade", (0, Y_C1 + .15, FZ), C_TER)
box("Rampa_Grade_Quadro", (4.9, .05, .06), (0, 0, 2.0), M["grade"], C_SOLTO, r)
for k in range(25): box("Rampa_Grade_Barra", (.025, .025, 2.0), (-2.4 + k * .2, 0, 1.0), M["grade"], C_SOLTO, r)
box("Rampa_Grade_Colisao", (4.9, .1, 2.0), (0, Y_C1 + .15, FZ + 1.0), M["grade"], C_TER)       # bloqueia a passagem (entra na colisao)
texto("Rampa_Placa", "ACESSO AOS ANDARES · FECHADO", .1, (0, Y_C1 + .1, FZ + 2.25), "-y", M["texto_pr"], C_SOLTO)
# placas das salas
for x, y, nome, vir, z in ((-9.45, Y_C0 + .11, "SECRETARIA", "+y", 2.3), (8.65, Y_C0 + .11, "SALA 101", "+y", 2.3), (-12.15, Y_C1 - .11, "BANHEIRO MASCULINO", "-y", 2.3),
                           (-6.15, Y_C1 - .11, "BANHEIRO FEMININO", "-y", 2.3), (5.85, Y_C1 - .11, "SALA 104", "-y", 2.3), (11.85, Y_C1 - .11, "SALA DOS PROFESSORES", "-y", 2.3),
                           (-3.0, Y_C0 + .11, "RECEPÇÃO", "+y", 2.62), (-2.5, Y_GAL - .11, "ENTRADA · RECEPÇÃO", "-y", 2.62)):
    box("Placa_Sala", (len(nome) * .075 + .2, .02, .2), (x, y, FZ + z), M["branco"], C_SOLTO)
    texto("Placa_Sala_Texto", nome, .09, (x, y + (.012 if vir == "+y" else -.012), FZ + z), vir, M["texto_pr"], C_SOLTO)
texto("Placa_Direcao", "DIREÇÃO", .1, (-.12, 5.45, FZ + 2.3), "-x", M["texto_pr"], C_SOLTO)
# portas fechadas das salas sem acesso (folha simples)
for x, y in ((-9.45, Y_C0), (8.65, Y_C0), (-6.15, Y_C1), (11.85, Y_C1)):
    box("Porta_Fechada", (.9, .05, 2.08), (x, y, FZ + 1.04), M["porta_mad"], C_TER)

# ---- recepcao (x -6 .. 0, y 3 .. 8)
# balcao junto a parede oeste (o atendente fica entre o balcao e a parede); o meio da sala fica livre ate o corredor
r = vazio("Recepcao_Balcao", (-4.75, 5.5, FZ), C_MOV, PI / 2)
box("Recepcao_Balcao_Frente", (2.6, .5, 1.05), (0, 0, .525), M["mad_cl"], C_MOV, r)
box("Recepcao_Balcao_Tampo", (2.8, .65, .04), (0, .05, 1.07), M["mad_cl"], C_MOV, r)
box("Recepcao_Mural", (2.4, .03, 1.2), (-4.8, Y_GAL + .12, FZ + 1.5), M["cortica"], C_TER)
for k in range(7):
    box("Recepcao_Mural_Aviso", (rnd.uniform(.25, .4), .01, rnd.uniform(.3, .4)), (-5.8 + k * .3 + rnd.uniform(-.05, .05), Y_GAL + .14, FZ + 1.3 + (k % 2) * .4), M[("papel", "papel_am", "papel_az")[k % 3]], C_SOLTO)
texto("Recepcao_Mural_Titulo", "AVISOS", .12, (-4.8, Y_GAL + .145, FZ + 2.2), "+y", M["texto_az"], C_SOLTO)
for k in range(2):
    modelo_ph("Recepcao_Cadeira", "plastic_monobloc_chair_01", (-1.15 + k * .6, Y_GAL + .45, FZ), 0, C_SOLTO, max_tris=3000)
modelo_ph("Recepcao_Planta", "potted_plant_01", (-5.5, 7.5, FZ), 0, C_SOLTO, alt=1.1)
r = vazio("Relogio_Parede", (-3.0, Y_GAL + .12, FZ + 2.5), C_SOLTO)
cyl("Relogio_Aro", .17, .17, .04, (0, 0, 0), M["preto"], C_SOLTO, r, rot=(PI / 2, 0, 0), seg=24)
cyl("Relogio_Mostrador", .15, .15, .045, (0, 0, 0), M["branco"], C_SOLTO, r, rot=(PI / 2, 0, 0), seg=24)

# ---- sala da direcao (x 0 .. 6, y 3 .. 8)
r = vazio("Direcao_Mesa", (3.4, 6.3, FZ), C_MOV)
box("Direcao_Mesa_Tampo", (1.6, .8, .04), (0, 0, .75), M["mad_cl"], C_MOV, r)
box("Direcao_Mesa_Gaveteiro", (.45, .7, .7), (.55, 0, .37), M["mad_cl"], C_MOV, r)
box("Direcao_Mesa_Painel", (1.5, .03, .55), (0, .36, .45), M["mad_cl"], C_MOV, r)
modelo_ph("Direcao_Cadeira_Diretora", "plastic_monobloc_chair_01", (3.4, 7.1, FZ), PI, C_SOLTO, max_tris=3000)
for x in (2.8, 4.0): modelo_ph("Direcao_Cadeira_Visita", "plastic_monobloc_chair_01", (x, 5.45, FZ), 0, C_SOLTO, max_tris=3000)
modelo_ph("Direcao_Armario", "painted_wooden_cabinet", (5.55, 4.4, FZ), -PI / 2, C_MOV, alt=1.9) or box("Direcao_Armario", (.5, 1.0, 1.9), (5.6, 4.4, FZ + .95), M["porta_ferro"], C_MOV)
modelo_ph("Direcao_Estante", "wooden_bookshelf_worn", (5.6, 6.6, FZ), -PI / 2, C_MOV, alt=1.8)
box("Direcao_Quadro_Avisos", (1.6, .03, 1.0), (3.2, Y_C0 - .12, FZ + 1.6), M["cortica"], C_TER)
for k in range(5): box("Direcao_Quadro_Papel", (.3, .01, .38), (2.6 + k * .3, Y_C0 - .14, FZ + 1.55 + (k % 2) * .1), M[("papel", "papel_am")[k % 2]], C_SOLTO)
modelo_ph("Direcao_Ventilador", "ceiling_fan", (3.0, 5.5, FZ + PD - .5), 0, C_SOLTO, alt=.5)
modelo_ph("Direcao_Pasta", "binder_notebook", (2.85, 6.2, FZ + .77), .3, C_SOLTO, alt=.06)

# ---- banheiro masculino (x -15 .. -9, y 11 .. 14): pias, cabines
box("Banheiro_Azulejo_Fundo", (5.8, .03, 1.8), (-12, PROF - GAL - .12, FZ + .9), M["azulejo"], C_TER)
box("Banheiro_Azulejo_Lado", (.03, 2.8, 1.8), (-14.88, 12.5, FZ + .9), M["azulejo"], C_TER)
for k in range(3):
    x = -14.3 + k * .9
    box("Banheiro_Bancada", (.8, .5, .08), (x, 13.7, FZ + .85), M["divisoria"], C_MOV)
    box("Banheiro_Cuba", (.45, .35, .1), (x, 13.68, FZ + .82), M["pia"], C_MOV)
box("Banheiro_Espelho", (2.6, .02, .8), (-13.4, PROF - GAL - .15, FZ + 1.55), M["vidro_porta"], C_SOLTO)
for k in range(2):
    x = -10.9 + k * 1.0
    box("Banheiro_Cabine_Divisoria", (.04, 1.4, 1.9), (x - .5, 13.25, FZ + 1.05), M["divisoria"], C_TER)
    box("Banheiro_Vaso", (.4, .55, .42), (x, 13.6, FZ + .21), M["pia"], C_MOV)
box("Banheiro_Cabine_Divisoria", (.04, 1.4, 1.9), (-9.4, 13.25, FZ + 1.05), M["divisoria"], C_TER)
modelo_ph("Banheiro_Placa_Piso", "WetFloorSign_01", (-13.0, 11.8, FZ), .5, C_SOLTO, alt=.6)

# ---- sala de aula 104 (x 3 .. 9, y 11 .. 14): carteiras, quadro, mesa do professor
box("Sala_Quadro", (3.2, .04, 1.2), (6.0, PROF - GAL - .13, FZ + 1.5), M["verde_quadro"], C_TER)
box("Sala_Quadro_Moldura", (3.3, .05, .06), (6.0, PROF - GAL - .12, FZ + .87), M["mad_cl"], C_TER)
r = vazio("Sala_Mesa_Professor", (8.2, 13.35, FZ), C_MOV, PI)
box("Sala_Mesa_Professor_Tampo", (1.0, .55, .04), (0, 0, .75), M["mad_cl"], C_MOV, r)
box("Sala_Mesa_Professor_Base", (.9, .04, .7), (0, .24, .37), M["mad_cl"], C_MOV, r)
def carteira(nome, x, y):
    r = vazio(nome, (x, y, FZ), C_MOV, 0)
    box(nome + "_Tampo", (.6, .45, .03), (0, 0, .72), M["tampo"], C_MOV, r)
    box(nome + "_Assento", (.4, .38, .03), (0, -.45, .44), M["cadeira_az"], C_MOV, r)
    box(nome + "_Encosto", (.4, .03, .3), (0, -.66, .7), M["cadeira_az"], C_MOV, r)
    for sx in (-1, 1):
        barra(nome + "_Pe", (sx * .26, .15, 0), (sx * .26, .15, .71), .012, M["metal"], C_SOLTO, r, seg=6)
        barra(nome + "_Pe", (sx * .18, -.6, 0), (sx * .18, -.6, .44), .012, M["metal"], C_SOLTO, r, seg=6)
for x in (3.8, 4.9, 7.1):                                   # corredor livre na frente da porta (x 5.4 .. 6.3)
    for y in (12.15, 13.1):
        carteira("Carteira_%.0f_%.0f" % (x * 10, y * 10), x, y)
modelo_ph("Sala_Ventilador", "ceiling_fan", (6.0, 12.5, FZ + PD - .5), 0, C_SOLTO, alt=.5)
modelo_ph("Sala_Lixeira", "metal_trash_can", (3.4, 11.4, FZ), 0, C_SOLTO, alt=.6)

# ------------------------------------------------------------------ 5. passarela coberta com porticos (foto "ft ciep 02")
PW = 6.0                                                     # largura da passarela (ESTIMADA)
for y0 in range(-36, -2, 5):
    yc = y0 + 2.5
    for sx in (-1, 1):
        painel_simples("Passarela_Arco", 5.0, 5.2, 3.8, 4.3, 1.3, -.45, .45, (sx * PW / 2, yc, FZ + 2.6), M["concreto"], C_PAS, fundo_aberto=True, rz=PI / 2)
for y in range(-36, -1, 5):
    for sx in (-1, 1):
        box("Passarela_Coluna", (.49, 1.24, 5.2), (sx * PW / 2, y, FZ + 2.6), M["concreto"], C_PAS)
box("Passarela_Cobertura", (PW + .5, 34, .3), (0, -19.0, FZ + 5.35), M["concreto"], C_PAS)
box("Passarela_Piso", (PW, 34, .04), (0, -19.0, FZ + .02), M["concreto"], C_PAS)

# ------------------------------------------------------------------ 6. interativos (portas e objetos de consulta)
def porta(nome, dobradica, rz, m, larg=.88, rotulo=None, lado_rotulo=-1):
    """Folha de porta com a origem na dobradica (o site gira a raiz para abrir). rz = 0: a folha corre para +X."""
    r = vazio(nome, (dobradica[0], dobradica[1], FZ), C_INT, rz)
    box(nome + "_Folha", (larg, .045, 2.08), (larg / 2, 0, 1.04), m, C_INT, r)
    for s in (-1, 1):
        cyl(nome + "_Macaneta", .025, .025, .05, (larg - .09, s * .05, 1.02), M["metal"], C_INT, r, rot=(PI / 2, 0, 0), seg=10)
    if rotulo:
        texto(nome + "_Rotulo", rotulo, .07, (larg / 2, lado_rotulo * .026, 1.62), "-y" if lado_rotulo < 0 else "+y", M["texto_br"], C_INT, r)
    return r
porta("I_Porta_Direcao", (0.0, 5.0), PI / 2, M["porta_mad"], larg=.88)                     # recepcao <-> direcao (abre para dentro da direcao)
porta("I_Porta_Banheiro", (-12.6, Y_C1), 0, M["porta_mad"], larg=.88)
porta("I_Porta_Sala", (5.4, Y_C1), 0, M["porta_mad"], larg=.88)

def item(nome, pos, rz=0.0):
    return vazio(nome, pos, C_INT, rz)
# celular da diretora com o print (sobre a mesa)
r = item("I_Celular_Print", (3.7, 6.25, FZ + .772), .4)
box("I_Celular_Print_Corpo", (.075, .155, .009), (0, 0, .0045), M["preto"], C_INT, r, bevel=.004)
box("I_Celular_Print_Tela", (.068, .145, .002), (0, 0, .0095), M["tela"], C_INT, r)
# monitor com as cameras do patio e do corredor (DVR)
r = item("I_Monitor_Cameras", (2.85, 6.5, FZ + .77), 0)
box("I_Monitor_Cameras_Tela", (.55, .04, .34), (0, 0, .25), M["preto"], C_INT, r)
box("I_Monitor_Cameras_Pe", (.08, .08, .08), (0, 0, .04), M["preto"], C_INT, r)
quadro("I_Monitor_Cameras_Imagem", (0, .025, .25), "+y", .5, .3, M["tela"], C_INT, r)
box("I_Monitor_Cameras_DVR", (.36, .26, .06), (.45, 0, .03), M["preto"], C_INT, r)
# diario de classe / frequencia (pasta na recepcao)
r = item("I_Pasta_Frequencia", (-4.7, 6.2, FZ + 1.09), PI / 2 + .1)
box("I_Pasta_Frequencia_Capa", (.32, .24, .03), (0, 0, .015), M["c1070"], C_INT, r)
# livro de ocorrencias da escola (na mesa da direcao)
r = item("I_Livro_Ocorrencias", (3.1, 6.05, FZ + .77), -.2)
box("I_Livro_Ocorrencias_Capa", (.3, .21, .035), (0, 0, .018), M["preto"], C_INT, r)
# mochila no banheiro (vestigio: so aparece em algumas variacoes - o site decide)
r = item("I_Mochila", (-10.9, 13.15, FZ), .3)
box("I_Mochila_Corpo", (.32, .18, .42), (0, 0, .21), M["mochila"], C_INT, r, bevel=.05)
box("I_Mochila_Bolso", (.24, .05, .18), (0, -.1, .14), M["mochila2"], C_INT, r, bevel=.02)
# telefone da recepcao
r = item("I_Telefone", (-4.7, 4.75, FZ + 1.09), PI / 2)
box("I_Telefone_Base", (.2, .22, .06), (0, 0, .03), M["branco"], C_INT, r, bevel=.01)
box("I_Telefone_Fone", (.05, .2, .045), (-.05, 0, .075), M["branco"], C_INT, r, bevel=.015)

# ------------------------------------------------------------------ 7. viatura (fora do portao)
r = carro_modelo("Viatura_PM", C_VEIC, "perua", (7.5, -42.6, 0), PI, cor="#eceded", escala=1.08)
if r:
    VTR, sy_, inf = r
    giroflex(VTR, C_VEIC, -.25, inf["alt"] + .03, larg=1.05)
    faixa_lateral("Viatura_Listra_Azul", VTR, C_VEIC, sy_, -2.0, 1.68, .54, .71, M["faixa_pm"])
    for lado in (1, -1):
        v = "+y" if lado > 0 else "-y"
        texto("Adesivo_Policia_Militar", "POLÍCIA MILITAR", .085, (-.15, sy_(-.15, .89, lado) + lado * .008, .89), v, M["texto_az"], C_VEIC, VTR)
        texto("Adesivo_190", "190", .12, (-1.67, sy_(-1.67, .91, lado) + lado * .008, .91), v, M["texto_az"], C_VEIC, VTR)
        cyl("Brasao_Imagem", .09, .09, .004, (1.03, sy_(1.03, .89, lado) + lado * .006, .89), M["brasao"], C_VEIC, VTR, rot=(PI / 2, 0, 0), seg=28)
else:
    say("aviso: modelos/carros/perua.glb nao encontrado; cena sem viatura")

# ------------------------------------------------------------------ 8. luzes (dia nublado claro + lampadas tubulares internas)
sol = luz("Sol", "SUN", 3.2, "#fff2dc", (0, 0, 40), C_LUZ, angle=math.radians(2.5))
sol.rotation_euler = (math.radians(50), 0, math.radians(-35))       # sol da manha vindo da frente-esquerda do predio
def tubo(nome, x, y, watts, comp=1.2, ao_longo_x=True, col=C_TER):
    box(nome + "_Tubo", (comp, .1, .04) if ao_longo_x else (.1, comp, .04), (x, y, FZ + PD - .03), M["lamp_f"], col)
    luz(nome + "_Luz", "POINT", watts, "#eaf2ff", (x, y, FZ + PD - .35), C_LUZ, shadow_soft_size=.3)
tubo("Luz_Recepcao", -3.0, 5.4, 60); tubo("Luz_Direcao", 3.0, 5.0, 55); tubo("Luz_Direcao_B", 3.0, 7.0, 40)
for x in (-12, -6, 0, 6, 12): tubo("Luz_Corredor", x, 9.5, 45)
tubo("Luz_Banheiro", -12.0, 12.6, 35); tubo("Luz_Sala_104", 6.0, 12.4, 55); tubo("Luz_Sala_104_B", 6.0, 13.6, 40)
for x in range(-45, 50, 10): luz("Luz_Galeria", "POINT", 25, "#eaf2ff", (x, 1.5, FZ + PD - .3), C_LUZ, shadow_soft_size=.3)

# ------------------------------------------------------------------ 9. pontos do treinamento (lidos pelo site em cena.json)
ponto("Inicio", 3.0, -41.5, (-.2, 1))
ponto("Parceiro", 4.4, -41.0, (-.4, 1))
ponto("Inspetora", 3.9, -35.6, (-.3, -1))
ponto("Responsavel", -2.5, 4.4, (0, -1))
ponto("Diretora", 3.4, 7.05, (0, -1))
ponto("Aluno_Sala", 5.0, 12.0, (0, -1))
ponto("Aluno_Banheiro", -11.2, 12.4, (1, 0))
ponto("Aluno_Corredor", -7.5, 9.5, (1, 0))
ponto("Aluno_Patio", -16.0, -4.0, (1, 0))
ponto("Ferido", -6.8, 8.6, (1, 0))
ponto("Ponto_Encontro", 10.0, -20.0, (0, 1))
ponto("Porta_Direcao", -.4, 5.45, (1, 0)); ponto("Porta_Banheiro", -12.15, 10.6, (0, 1)); ponto("Porta_Sala", 5.85, 10.6, (0, 1))

# ------------------------------------------------------------------ 10. cameras, ceu, render
camera("Camera_Rua", (3.0, -41.5, FZ + 1.6), (0.0, -20.0, FZ + 3.0), 18)
camera("Camera_Patio", (-12.0, -26.0, FZ + 1.6), (2.0, 4.0, FZ + 5.0), 16)
camera("Camera_Passarela", (0.0, -34.0, FZ + 1.6), (0.0, -5.0, FZ + 1.8), 16)
camera("Camera_Recepcao", (-3.0, 1.5, FZ + 1.6), (-3.0, 7.0, FZ + 1.2), 15)
camera("Camera_Direcao", (0.8, 4.0, FZ + 1.6), (4.5, 7.5, FZ + 1.0), 14)
camera("Camera_Corredor", (-2.5, 9.5, FZ + 1.6), (-14.0, 9.5, FZ + 1.3), 15)
camera("Camera_Sala_104", (5.85, 10.2, FZ + 1.6), (7.0, 14.0, FZ + 1.0), 14)
p = camera("Camera_Planta", (0, -12, 90.0), (0, -12, 0)); p.data.type = "ORTHO"; p.data.ortho_scale = 70
p.rotation_euler = (0, 0, 0)
scene.camera = bpy.data.objects["Camera_Patio"]

world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World"); scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (*lin(hx("#a9c4e0")), 1); bg.inputs["Strength"].default_value = 1.0
scene.unit_settings.system = "METRIC"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.engine = "CYCLES"; scene.cycles.samples = 128; scene.cycles.use_denoising = True
for attr, val in (("view_transform", "AgX"), ("look", "AgX - Medium High Contrast")):
    try: setattr(scene.view_settings, attr, val)
    except Exception: pass

# medidas estimadas (registradas no .blend e no relatorio de referencias)
MEDIDAS_ESTIMADAS = {
    "comprimento_bloco_m": X1 - X0, "profundidade_bloco_m": PROF, "modulo_m": MOD, "pavimentos": 3,
    "altura_entre_pavimentos_m": PISO, "galeria_terreo_m": GAL, "corredor_central_m": Y_C1 - Y_C0,
    "janela_arredondada_m": [JW, JH, JR], "passarela_largura_m": PW, "muro_altura_m": MURO_H,
}
scene["medidas_estimadas"] = str(MEDIDAS_ESTIMADAS)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "ciep.blend"))
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for o in scene.objects:
    if o.type == "MESH":
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
say("cena salva: %d objetos, %d triangulos (antes da otimizacao)" % (len(scene.objects), tris))
say("medidas ESTIMADAS: %s" % MEDIDAS_ESTIMADAS)
