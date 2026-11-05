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
    a = np.ones((S, S, 3)) * np.array(hx("#e2e3df")) * (.7 + .3 * np.sin(lam * PI) ** .6)[..., None]      # laminas claras (foto do Tancredo Neves)
    a[lam < .1] *= .45
    for xc in (.005, .33, .66, .995): a[(np.abs(xx - xc) < .01)] = hx("#9a9c9e")       # montantes de aluminio
    a[(np.abs(yy - .5) < .012)] = hx("#9a9c9e")                                         # travessa
    a *= (.85 + .15 * yy)[..., None]                                                    # um pouco de sombra no alto da abertura
    return np.clip(a, 0, 1)

M = {
    "asfalto": mat("Asfalto", "#3a3a3c", .9), "faixa": mat("Pintura_Viaria_Branca", "#d8d6cc", .7),
    "meiofio": mat("Meio_Fio_Concreto", "#9c988f", .95),
    "concreto": mat("Concreto_Aparente", "#a6a29a", .95),
    "branco_fach": mat("Fachada_Branca", "#ecebe6", .85),      # foto do Tancredo Neves: concreto pintado de branco
    "pilotis": mat("Laje_Pilotis", "#dedcd6", .9), "piso_pilotis": mat("Piso_Pilotis", "#b9b6ae", .9),
    "peit_verm": mat("Peitoril_Vermelho", "#c81f3a", .6), "peit_preto": mat("Peitoril_Preto", "#2a2b2d", .6),
    "junta": mat("Junta_Fachada", "#b9b8b2", .9), "barra_az": mat("Barra_Azul", "#4f74a8", .55), "palmeira": mat("Folha_Palmeira", "#4f7a3a", .8),
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
M["piso"] = mat("Piso_Granilite", "#a9a7a2", .45)          # textura CC0 granite_tile (aplicar_texturas_cc0.py)
M["azulejo"] = mat("Azulejo_Branco", "#e8e6df", .2)          # textura CC0 long_white_tiles
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
# Proporcoes tiradas da foto do CIEP Tancredo Neves (Leonardo Finotti), assumindo modulo de 5 m (ESTIMADO):
#   janela 3,9 x 2,75 m, raio 0,95 m, peitoril colorido de ~0,9 m (vermelho ou preto, alternando de dois em dois);
#   piso a piso ~3,35 m; arcos do terreo 3,9 x 3,0 m; platibanda ~2 m acima da cobertura, lisa, com juntas;
#   terreo em pilotis abertos (ve-se atraves do predio) com a rampa no meio do vao; fachada de concreto pintado de branco.
# Planta (metros, ESTIMADA):
#   rua y -48 .. -40 · calcada y -40 .. -38 · muro em y = -38, portao x 0 .. 5 · patio y -38 .. 0
#   predio x -50 .. 50, y 0 .. 22 (20 modulos de 5 m). Terreo: pilotis abertos, exceto o bloco administrativo
#     bloco x -20 .. 20, y 3 .. 19 (galeria de 3 m na frente e nos fundos, sob os arcos)
#       frente  y 3 .. 10:  secretaria -20..-10 (fechada) · RECEPCAO -10..-2 · DIRECAO -2..6 · reunioes 6..20 (fechada)
#       corredor y 10 .. 13, de -20 a 20 (portas corta-fogo nas pontas)
#       fundos  y 13 .. 19: BANHEIRO MASC. -20..-12 · banheiro fem. -12..-6 · leitura -6..2 (fechadas) · SALA 104 2..12 · professores 12..20
#   rampa (marca dos CIEPs) nos pilotis, x 26 .. 34, visivel pelos arcos, como na foto
FZ = .15
PISO = 3.35
Z1, Z2, Z3 = FZ + PISO, FZ + 2 * PISO, FZ + 3 * PISO
X0, X1, PROF, MOD = -50.0, 50.0, 22.0, 5.0
PD = PISO - .35
GAL = 3.0
BX0, BX1, BY0, BY1 = -20.0, 20.0, GAL, PROF - GAL
YC0, YC1 = 10.0, 13.0
PX = 2.5                                                      # eixo do portao e da passarela (centro de um arco)

C_RUA = collection("01_Rua"); C_PAT = collection("02_Patio"); C_FAC = collection("03_Predio_Fachada")
C_TER = collection("04_Terreo_Interior"); C_PAS = collection("05_Passarela"); C_MOV = collection("06_Moveis")
C_GAL = collection("07_Pilotis"); C_INT = collection("08_Interativos"); C_LUZ = collection("09_Luzes_Cameras")
C_VEIC = collection("10_Viatura"); C_SOLTO = collection("12_Objetos_Soltos")

def parede(nome, a, b, m, col, vaos=(), h=PD, t=.2, z0=FZ, ext=None, barra=None):
    """Parede reta entre a e b com vaos [(d0, d1, zbase, ztopo)] a partir de a. barra = (material, lados, altura):
    faixa pintada na parte de baixo (lados: -1 e/ou +1, o lado da parede para onde ela aparece)."""
    ax, ay = a; bx, by = b; horiz = abs(bx - ax) > abs(by - ay)
    L = abs(bx - ax) if horiz else abs(by - ay); sg = 1 if ((bx - ax) if horiz else (by - ay)) > 0 else -1
    def trecho(d0, d1, zb, zt, suf):
        if d1 - d0 < .01 or zt - zb < .01: return
        c = (d0 + d1) / 2
        pos = (ax + sg * c, ay, z0 + (zb + zt) / 2) if horiz else (ax, ay + sg * c, z0 + (zb + zt) / 2)
        box(nome + suf, (d1 - d0, t, zt - zb) if horiz else (t, d1 - d0, zt - zb), pos, m, col)
        if barra and zb < .01:
            mb, lados, hb = barra; hh = min(hb, zt)
            for ld in lados:
                off = ld * (t / 2 + .006)
                p2 = (pos[0], pos[1] + off, z0 + hh / 2) if horiz else (pos[0] + off, pos[1], z0 + hh / 2)
                box(nome + "_Barra", (d1 - d0, .012, hh) if horiz else (.012, d1 - d0, hh), p2, mb, col)
    if ext is None: ext = t / 2 if t >= .2 else -.07
    d = -ext
    for v0, v1, zb, zt in sorted(vaos):
        trecho(d, v0, 0, h, ""); trecho(v0, v1, 0, zb, "_Mureta"); trecho(v0, v1, zt, h, "_Verga"); d = v1
    trecho(d, L + ext, 0, h, "")

def contorno_arredondado(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, PI / 2), (-w / 2 + r, -h / 2 + r, PI), (w / 2 - r, -h / 2 + r, 1.5 * PI)):
        for k in range(n + 1):
            a = a0 + PI / 2 * k / n; pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def painel_simples(nome, w, h, fw, fh, r, fcz, esp, pos, m, col, fundo_aberto=False, rz=0.0):
    """Placa w x h (plano XZ, espessura esp) com abertura fw x fh de cantos arredondados (raio r), centro a fcz do centro
    da placa; fundo_aberto = arco (os pes descem retos ate a base). Feita por fatias horizontais."""
    furo = contorno_arredondado(fw, fh, r, 8)
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
    quad(-w / 2, w / 2, top, h / 2)
    if not fundo_aberto: quad(-w / 2, w / 2, -h / 2, bot)
    def meia_larg(y):
        yy = y - fcz; hy = fh / 2 - r
        if abs(yy) <= hy or (fundo_aberto and yy < 0): return fw / 2
        d = abs(yy) - hy; return fw / 2 - r + math.sqrt(max(0, r * r - d * d))
    cortes = sorted({bot, top} | {y for y in ys if bot <= y <= top})
    for y0, y1 in zip(cortes, cortes[1:]):
        for s in (-1, 1):
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
MURO_H = 2.4
for xa, xb in ((-56, PX - 3.0), (PX + 3.0, 56)):
    box("Muro_Frente", (xb - xa, .2, MURO_H), ((xa + xb) / 2, -38, FZ + MURO_H / 2), M["muro"], C_PAT)
for sx in (-1, 1):
    box("Muro_Lateral", (.2, 62, MURO_H), (sx * 56, -7, FZ + MURO_H / 2), M["muro"], C_PAT)
    box("Portao_Coluna", (.45, .45, 2.8), (PX + sx * 3.2, -38, FZ + 1.4), M["branco_fach"], C_PAT)
box("Muro_Fundos", (112, .2, MURO_H), (0, 24.0, FZ + MURO_H / 2), M["muro"], C_PAT)
texto("Muro_Placa_Nome", "CIEP TANCREDO NEVES", .32, (-12, -38.12, FZ + 1.75), "-y", M["texto_az"], C_SOLTO)
texto("Muro_Placa_Sub", "ESCOLA PÚBLICA", .2, (-12, -38.12, FZ + 1.3), "-y", M["texto_az"], C_SOLTO)
for sx in (-1, 1):
    r = vazio("Portao_Folha", (PX + sx * 2.95, -37.85, FZ), C_PAT, sx * PI * .48 + (PI if sx < 0 else 0))
    box("Portao_Quadro_Sup", (2.9, .05, .06), (1.45, 0, 2.2), M["grade"], C_SOLTO, r)
    box("Portao_Quadro_Inf", (2.9, .05, .06), (1.45, 0, .1), M["grade"], C_SOLTO, r)
    for k in range(15): box("Portao_Barra", (.025, .025, 2.1), (.1 + k * .19, 0, 1.15), M["grade"], C_SOLTO, r)
GX, GY = 9.5, -35.6
parede("Guarita_Frente", (GX - 1.6, GY - 1.4), (GX + 1.6, GY - 1.4), M["muro"], C_PAT, vaos=[(.4, 2.8, 1.0, 2.1)], h=2.6)
parede("Guarita_Fundo", (GX - 1.6, GY + 1.4), (GX + 1.6, GY + 1.4), M["muro"], C_PAT, h=2.6)
parede("Guarita_Lado", (GX + 1.6, GY - 1.4), (GX + 1.6, GY + 1.4), M["muro"], C_PAT, h=2.6)
parede("Guarita_Porta", (GX - 1.6, GY - 1.4), (GX - 1.6, GY + 1.4), M["muro"], C_PAT, vaos=[(1.6, 2.5, 0, 2.1)], h=2.6)
box("Guarita_Laje", (3.6, 3.2, .15), (GX, GY, FZ + 2.67), M["branco_fach"], C_PAT)
box("Guarita_Vidro", (2.4, .02, 1.1), (GX, GY - 1.4, FZ + 1.55), M["vidro"], C_SOLTO)
box("Guarita_Bancada", (2.6, .5, .05), (GX, GY - 1.05, FZ + .9), M["mad_cl"], C_MOV)

# ------------------------------------------------------------------ 2. patio: placas de concreto em faixas, com juntas de grama (foto)
box("Patio_Grama", (112, 62, .1), (0, -7, FZ - .1), M["grama"], C_PAT)            # chao de grama sob tudo (aparece nas juntas)
FAIXA, JUNTA = 3.6, .32
x = -55.0
while x < 55:
    w = min(FAIXA, 55 - x)
    box("Patio_Placa", (w, 37.7, .1), (x + w / 2, -19.0, FZ - .05), M["patio"], C_PAT)
    x += w + JUNTA
for y in range(-34, 0, 6): box("Patio_Junta", (110, .025, .004), (0, y, FZ + .002), M["junta"], C_SOLTO)     # juntas transversais (serradas)
# mastros (sem bandeiras), arvores, palmeira e poste como na foto
for k, xm in enumerate((-9.0, -8.2, -7.4)):
    cyl("Mastro", .04, .05, 9.5 - k * .6, (xm, -12.5, FZ + (9.5 - k * .6) / 2), M["poste"], C_SOLTO, seg=10)
box("Mastro_Base", (2.6, 1.0, .3), (-8.2, -12.5, FZ + .15), M["branco_fach"], C_PAT)
def arvore(nome, x, y, alt=5.5, copa=2.2):
    cyl(nome + "_Tronco", .14, .2, alt * .55, (x, y, FZ + alt * .275), M["tronco"], C_PAT, seg=10)
    for k in range(5):
        a = k * 1.3; esfera(nome + "_Copa", copa * rnd.uniform(.7, 1.0), (x + math.cos(a) * copa * .5, y + math.sin(a) * copa * .5, FZ + alt * .62 + rnd.uniform(0, 1.2)), M["folha"], C_SOLTO, sub=2, esc=(1, 1, .75))
def palmeira(nome, x, y, alt=9.0):
    """Palmeira (desenho proprio): tronco levemente curvo e folhas compridas e arqueadas."""
    n = 8
    for k in range(n):
        z0, z1 = alt * k / n, alt * (k + 1) / n; dx = .25 * math.sin(k / n * 2)
        cyl(nome + "_Tronco", .17 - .05 * k / n, .17 - .05 * (k + 1) / n, z1 - z0, (x + dx, y, FZ + (z0 + z1) / 2), M["tronco"], C_PAT, seg=10)
    topo = Vector((x + .25 * math.sin(2), y, FZ + alt))
    for k in range(16):
        a = 2 * PI * k / 16 + rnd.uniform(-.1, .1); L = rnd.uniform(2.4, 3.2); inc = rnd.uniform(.1, .6)
        vs, fs = [], []
        for i in range(7):
            t = i / 6; d = L * t; zc = math.sin(inc + .9) * d * (1 - t) * .8 - (t ** 2) * 1.2
            lw = .32 * math.sin(PI * min(1, t * 1.15 + .05))
            c = topo + Vector((math.cos(a) * d, math.sin(a) * d, zc)); pr = Vector((-math.sin(a), math.cos(a), 0)) * lw
            vs += [tuple(c - pr), tuple(c + pr)]
        for i in range(6): fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
        malha(nome + "_Folha", vs, fs, M["palmeira"], C_SOLTO)
palmeira("Palmeira", 21.0, -2.8)
palmeira("Palmeira_2", -31.0, -3.2, 8.2)
for k, (x, y) in enumerate(((-30, -28), (-22, -22), (24, -26), (36, -31), (-46, -14), (46, -16))):
    arvore("Arvore_%d" % k, x, y)
for k, (x, y, rz) in enumerate(((-14, -7, 0), (-20, -7, 0), (14, -7, 0), (28, -7, 0), (-12, -22, PI / 2), (14, -22, PI / 2))):
    r = vazio("Banco_Patio", (x, y, FZ), C_PAT, rz)
    box("Banco_Patio_Tampo", (2.2, .45, .1), (0, 0, .45), M["branco_fach"], C_PAT, r)
    for sx in (-1, 1): box("Banco_Patio_Pe", (.2, .4, .4), (sx * .85, 0, .2), M["branco_fach"], C_PAT, r)
for x, y in ((-3.5, -2.0), (8.5, -2.0), (-1.5, -30.0)):
    modelo_ph("Lixeira_Patio", "metal_trash_can", (x, y, FZ), 0, C_SOLTO, alt=.9)
for x, y in ((-26, -3.5), (16, -18), (-14, -18)):
    modelo_ph("Poste_Patio", "street_lamp_01", (x, y, FZ), 0, C_SOLTO, alt=7.5) or cyl("Poste_Patio", .07, .1, 7.5, (x, y, FZ + 3.75), M["poste"], C_SOLTO)

# ------------------------------------------------------------------ 3. predio: estrutura, fachadas e cobertura
NM = int((X1 - X0) / MOD)
JW, JH, JR = 3.9, 2.75, .95                                   # janela (foto)
AW, AH, AR = 3.9, 3.0, 1.35                                   # arco do terreo (foto)
box("Laje_1", (X1 - X0, PROF, .35), ((X0 + X1) / 2, PROF / 2, Z1 - .175), M["pilotis"], C_FAC)
box("Laje_Cobertura", (X1 - X0, PROF, .4), ((X0 + X1) / 2, PROF / 2, Z3 - .2), M["branco_fach"], C_FAC)
box("Pavimentos_Superiores_Volume", (X1 - X0 - .8, PROF - 1.6, Z3 - Z1 - .6), ((X0 + X1) / 2, PROF / 2, (Z1 + Z3) / 2), M["escuro"], C_FAC)
PL_H = 2.0
for y in (-.05, PROF + .05):
    box("Platibanda", (X1 - X0 + .3, .3, PL_H), ((X0 + X1) / 2, y, Z3 + PL_H / 2 - .2), M["branco_fach"], C_FAC)
for x in (X0 - .1, X1 + .1):
    box("Platibanda_Lateral", (.3, PROF + .3, PL_H), (x, PROF / 2, Z3 + PL_H / 2 - .2), M["branco_fach"], C_FAC)
    box("Empena", (.3, PROF + .2, Z3 - Z1), (x, PROF / 2, (Z1 + Z3) / 2), M["branco_fach"], C_FAC)
# juntas da fachada (linhas finas da foto): horizontal na altura da cobertura e verticais na platibanda, a cada modulo
for y, ld in ((-.21, -1), (PROF + .21, 1)):
    box("Junta_Horizontal", (X1 - X0, .01, .025), ((X0 + X1) / 2, y, Z3 - .1), M["junta"], C_SOLTO)
    for k in range(NM + 1):
        box("Junta_Vertical", (.02, .01, PL_H - .1), (X0 + MOD * k, y, Z3 + PL_H / 2 - .2), M["junta"], C_SOLTO)
# fachadas dos pavimentos superiores: uma janela arredondada por modulo; peitoril vermelho ou preto, de dois em dois
for fy, rz, lado in ((0.0, 0.0, -1), (PROF, PI, 1)):
    for a, z0 in enumerate((Z1, Z2)):
        for k in range(NM):
            xc = X0 + MOD * (k + .5); zc = z0 + PISO / 2
            painel_simples("Fachada_Painel", MOD, PISO, JW, JH, JR, -.05, .34, (xc, fy, zc), M["branco_fach"], C_FAC, rz=rz)
            verm = ((k // 2) + a) % 2 == (0 if a == 1 else 1)
            zb = zc - .05 - JH / 2
            box("Fachada_Peitoril_Cor", (JW - .04, .14, .92), (xc, fy - lado * .03, zb + .46), M["peit_verm" if verm else "peit_preto"], C_FAC)
            quadro("Fachada_Janela", (xc, fy - lado * .1, zb + .92 + (JH - .92) / 2), "-y" if lado < 0 else "+y", JW - .1, JH - .92, M["persiana"], C_SOLTO)
# terreo: arcos na frente e nos fundos (pilotis)
for fy, rz in ((0.0, 0.0), (PROF, PI)):
    for k in range(NM):
        xc = X0 + MOD * (k + .5)
        painel_simples("Arcada_Arco", MOD, PD, AW, AH, AR, -(PD - AH) / 2, .55, (xc, fy, FZ + PD / 2), M["branco_fach"], C_FAC, fundo_aberto=True, rz=rz)
    for k in range(NM + 1):
        box("Arcada_Coluna", (MOD - AW + .04, .59, PD), (X0 + MOD * k, fy, FZ + PD / 2), M["branco_fach"], C_FAC)
    box("Arcada_Viga", (X1 - X0, .55, Z1 - FZ - PD), ((X0 + X1) / 2, fy, (FZ + PD + Z1) / 2), M["branco_fach"], C_FAC)
texto("Fachada_Letreiro", "CIEP TANCREDO NEVES", .5, (-27.5, -.35, Z1 - .17), "-y", M["texto_pr"], C_SOLTO)
# pilotis: piso, pilares internos (linha do meio) e a rampa
box("Piso_Pilotis", (X1 - X0, PROF, .15), ((X0 + X1) / 2, PROF / 2, FZ - .075), M["piso_pilotis"], C_GAL)
for k in range(NM + 1):
    x = X0 + MOD * k
    if BX0 - .5 <= x <= BX1 + .5: continue
    box("Pilotis_Coluna", (.6, .6, PD), (x, PROF / 2, FZ + PD / 2), M["branco_fach"], C_GAL)
# rampa em zigue-zague (dois lancos e patamar), vista pelos arcos como na foto; termina na laje (acesso fechado no topo)
RX0, RX1 = 26.0, 34.0
for k in range(10):
    z = FZ + .15 + k * (PD / 10)
    box("Rampa_Lanco_A", (.8, 2.4, .2), (RX0 + .4 + k * .8, 8.0, z), M["branco_fach"], C_GAL)
    box("Rampa_Lanco_B", (.8, 2.4, .2), (RX1 - .4 - k * .8, 13.0, z + PD * .5), M["branco_fach"], C_GAL)
for y in (6.8, 9.2, 11.8, 14.2):
    box("Rampa_Guarda_Corpo", (RX1 - RX0, .12, 1.1), ((RX0 + RX1) / 2, y, FZ + PD * .45), M["branco_fach"], C_GAL)
box("Rampa_Bloqueio", (RX1 - RX0 + 1, 9, 1.1), ((RX0 + RX1) / 2, 10.5, FZ + .55), M["branco_fach"], C_GAL)      # base fechada (colisao)

# ------------------------------------------------------------------ 4. bloco administrativo (terreo)
box("Piso_Terreo_Jogavel", (BX1 - BX0, BY1 - BY0, .15), (0, (BY0 + BY1) / 2, FZ - .073), M["piso"], C_TER)
box("Terreo_Forro", (BX1 - BX0, BY1 - BY0, .02), (0, (BY0 + BY1) / 2, FZ + PD - .02), M["laje"], C_TER)
def janelas_frente(xa, xb, entrada=None, divisorias=()):
    vaos = []
    for k in range(NM):
        xc = X0 + MOD * (k + .5)
        if not (xa < xc < xb): continue
        if any(abs(xc - d) < 1.6 for d in divisorias): continue          # a janela cruzaria a parede entre duas salas
        if entrada and entrada[0] < xc < entrada[1]: vaos.append((xc - xa - 1.0, xc - xa + 1.0, 0, 2.3))
        else: vaos.append((xc - xa - 1.5, xc - xa + 1.5, 1.0, 2.4))
    return vaos
for y, nome, entrada, divs in ((BY0, "Bloco_Parede_Frente", (-10, -5), (-10.0, -2.0, 6.0)), (BY1, "Bloco_Parede_Fundos", None, (-12.0, -6.0, 2.0, 12.0))):
    vaos = janelas_frente(BX0, BX1, entrada, divs)
    parede(nome, (BX0, y), (BX1, y), M["parede"], C_TER, vaos=vaos, t=.25)
    for v0, v1, zb, zt in vaos:
        xc = BX0 + (v0 + v1) / 2
        if zb < .5:
            box(nome + "_Porta_Vidro_Caixilho", (v1 - v0, .06, .06), (xc, y, FZ + 2.3), M["esquadria"], C_SOLTO); continue
        box(nome + "_Janela_Vidro", (v1 - v0, .03, zt - zb), (xc, y, FZ + (zb + zt) / 2), M["vidro"], C_SOLTO)
        box(nome + "_Janela_Montante", (.05, .05, zt - zb), (xc, y, FZ + (zb + zt) / 2), M["esquadria"], C_SOLTO)
        aberta = (y == BY0 and -10 < xc < 6) or (y == BY1 and (-20 < xc < -12 or 2 < xc < 12))
        if not aberta: box(nome + "_Janela_Fundo", (v1 - v0, .05, zt - zb), (xc, y + (.6 if y == BY0 else -.6), FZ + (zb + zt) / 2), M["escuro"], C_SOLTO)
for x in (BX0, BX1):                                            # laterais do bloco: porta corta-fogo no corredor
    parede("Bloco_Lateral", (x, BY0), (x, BY1), M["parede"], C_TER, vaos=[(YC0 - BY0 + .4, YC1 - BY0 - .4, 0, 2.2)], t=.25)
    box("Corredor_Porta_Corta_Fogo", (.06, 2.2, 2.2), (x, (YC0 + YC1) / 2, FZ + 1.1), M["porta_ferro"], C_TER)
    box("Corredor_Porta_Visor", (.08, .3, .5), (x, (YC0 + YC1) / 2 - .5, FZ + 1.5), M["vidro"], C_SOLTO)
    texto("Corredor_Porta_Placa", "SAÍDA" if x > 0 else "SAÍDA · PILOTIS", .09, (x - (.045 if x > 0 else -.045), (YC0 + YC1) / 2, FZ + 2.05), "-x" if x > 0 else "+x", M["texto_pr"], C_SOLTO)
BARRA = (M["barra_az"], (1,), 1.4)
# corredor: parede da frente (y = 10) e dos fundos (y = 13), barra azul 1070 do lado do corredor
parede("Corredor_Parede_Frente", (BX0, YC0), (BX1, YC0), M["parede"], C_TER, barra=(M["barra_az"], (1,), 1.4),
       vaos=[(-15.4 - BX0, -14.5 - BX0, 0, 2.1), (-8.2 - BX0, -5.4 - BX0, 0, 2.4), (12.5 - BX0, 13.4 - BX0, 0, 2.1)])
parede("Corredor_Parede_Fundos", (BX0, YC1), (BX1, YC1), M["parede"], C_TER, barra=(M["barra_az"], (-1,), 1.4),
       vaos=[(-16.5 - BX0, -15.6 - BX0, 0, 2.1), (-9.5 - BX0, -8.6 - BX0, 0, 2.1), (-2.5 - BX0, -1.6 - BX0, 0, 2.1), (6.5 - BX0, 7.4 - BX0, 0, 2.1), (16.0 - BX0, 16.9 - BX0, 0, 2.1)])
for x in (-10.0, -2.0, 6.0):
    vaos = [(2.0, 2.9, 0, 2.1)] if x == -2.0 else []           # direcao <-> recepcao (y 5.0 .. 5.9)
    parede("Divisoria_Frente", (x, BY0), (x, YC0), M["parede"], C_TER, vaos=vaos, ext=0.0)
for x in (-12.0, -6.0, 2.0, 12.0):
    parede("Divisoria_Fundos", (x, YC1), (x, BY1), M["parede"], C_TER, ext=0.0)
# barra azul tambem na recepcao (parede da galeria, por dentro)
box("Recepcao_Barra", (1.4, .012, 1.4), (-9.3, BY0 + .137, FZ + .7), M["barra_az"], C_TER)      # dos dois lados da porta de entrada (x -8.5 .. -6.5)
box("Recepcao_Barra", (4.4, .012, 1.4), (-4.3, BY0 + .137, FZ + .7), M["barra_az"], C_TER)
# placas das salas
for x, y, nome, vir, z in ((-14.95, YC0 + .11, "SECRETARIA", "+y", 2.3), (12.95, YC0 + .11, "SALA DE REUNIÕES", "+y", 2.3), (-6.8, YC0 + .11, "RECEPÇÃO", "+y", 2.62),
                           (-16.05, YC1 - .11, "BANHEIRO MASCULINO", "-y", 2.3), (-9.05, YC1 - .11, "BANHEIRO FEMININO", "-y", 2.3), (-2.05, YC1 - .11, "SALA DE LEITURA", "-y", 2.3),
                           (6.95, YC1 - .11, "SALA 104", "-y", 2.3), (16.45, YC1 - .11, "SALA DOS PROFESSORES", "-y", 2.3), (-7.5, BY0 - .14, "ENTRADA · RECEPÇÃO", "-y", 2.62)):
    box("Placa_Sala", (len(nome) * .075 + .2, .02, .2), (x, y, FZ + z), M["branco"], C_SOLTO)
    texto("Placa_Sala_Texto", nome, .09, (x, y + (.012 if vir == "+y" else -.012), FZ + z), vir, M["texto_pr"], C_SOLTO)
texto("Placa_Direcao", "DIREÇÃO", .1, (-2.14, 5.45, FZ + 2.35), "-x", M["texto_pr"], C_SOLTO)
for x, y in ((-14.95, YC0), (12.95, YC0), (-9.05, YC1), (-2.05, YC1), (16.45, YC1)):
    box("Porta_Fechada", (.9, .05, 2.08), (x, y, FZ + 1.04), M["porta_mad"], C_TER)

# ---- recepcao (x -10 .. -2, y 3 .. 10)
r = vazio("Recepcao_Balcao", (-9.0, 6.4, FZ), C_MOV, PI / 2)
box("Recepcao_Balcao_Frente", (2.8, .5, 1.05), (0, 0, .525), M["mad_cl"], C_MOV, r)
box("Recepcao_Balcao_Tampo", (3.0, .65, .04), (0, .05, 1.07), M["mad_cl"], C_MOV, r)
modelo_ph("Recepcao_Cadeira_Atendente", "plastic_monobloc_chair_01", (-9.6, 6.4, FZ), -PI / 2, C_SOLTO, max_tris=3000)
box("Recepcao_Mural", (2.4, .03, 1.2), (-3.4, BY0 + .15, FZ + 1.95), M["cortica"], C_TER)
for k in range(7):
    box("Recepcao_Mural_Aviso", (rnd.uniform(.25, .4), .01, rnd.uniform(.3, .4)), (-4.4 + k * .3 + rnd.uniform(-.05, .05), BY0 + .17, FZ + 1.75 + (k % 2) * .4), M[("papel", "papel_am", "papel_az")[k % 3]], C_SOLTO)
texto("Recepcao_Mural_Titulo", "AVISOS", .12, (-3.4, BY0 + .175, FZ + 2.65), "+y", M["texto_az"], C_SOLTO)
for k in range(4):
    modelo_ph("Recepcao_Cadeira", "plastic_monobloc_chair_01", (-4.6 + k * .6, BY0 + .5, FZ), 0, C_SOLTO, max_tris=3000)
modelo_ph("Recepcao_Planta", "potted_plant_01", (-9.4, 9.4, FZ), 0, C_SOLTO, alt=1.1)
r = vazio("Relogio_Parede", (-6.0, YC0 - .14, FZ + 2.6), C_SOLTO)
cyl("Relogio_Aro", .17, .17, .04, (0, 0, 0), M["preto"], C_SOLTO, r, rot=(PI / 2, 0, 0), seg=24)
cyl("Relogio_Mostrador", .15, .15, .045, (0, 0, 0), M["branco"], C_SOLTO, r, rot=(PI / 2, 0, 0), seg=24)
# ---- direcao (x -2 .. 6, y 3 .. 10)
r = vazio("Direcao_Mesa", (2.4, 7.0, FZ), C_MOV)
box("Direcao_Mesa_Tampo", (1.7, .85, .04), (0, 0, .75), M["mad_cl"], C_MOV, r)
box("Direcao_Mesa_Gaveteiro", (.45, .75, .7), (.6, 0, .37), M["mad_cl"], C_MOV, r)
box("Direcao_Mesa_Painel", (1.6, .03, .55), (0, .38, .45), M["mad_cl"], C_MOV, r)
modelo_ph("Direcao_Cadeira_Diretora", "plastic_monobloc_chair_01", (2.4, 7.85, FZ), PI, C_SOLTO, max_tris=3000)
for x in (1.8, 3.0): modelo_ph("Direcao_Cadeira_Visita", "plastic_monobloc_chair_01", (x, 6.1, FZ), 0, C_SOLTO, max_tris=3000)
modelo_ph("Direcao_Armario", "painted_wooden_cabinet", (5.55, 4.2, FZ), -PI / 2, C_MOV, alt=1.9)
modelo_ph("Direcao_Estante", "wooden_bookshelf_worn", (5.6, 8.6, FZ), -PI / 2, C_MOV, alt=1.8)
box("Direcao_Quadro_Avisos", (1.6, .03, 1.0), (2.4, YC0 - .14, FZ + 1.6), M["cortica"], C_TER)
for k in range(5): box("Direcao_Quadro_Papel", (.3, .01, .38), (1.8 + k * .3, YC0 - .16, FZ + 1.55 + (k % 2) * .1), M[("papel", "papel_am")[k % 2]], C_SOLTO)
modelo_ph("Direcao_Ventilador", "ceiling_fan", (2.0, 6.0, FZ + PD - .5), 0, C_SOLTO, alt=.5)
modelo_ph("Direcao_Pasta", "binder_notebook", (1.85, 6.85, FZ + .77), .3, C_SOLTO, alt=.06)
modelo_ph("Direcao_Planta", "potted_plant_01", (-1.4, 9.4, FZ), 0, C_SOLTO, alt=1.0)
# ---- banheiro masculino (x -20 .. -12, y 13 .. 19)
box("Banheiro_Azulejo_Fundo", (7.8, .03, 1.8), (-16, BY1 - .14, FZ + .9), M["azulejo"], C_TER)
box("Banheiro_Azulejo_Lado", (.03, 5.8, 1.8), (-19.86, 16.0, FZ + .9), M["azulejo"], C_TER)
for k in range(4):
    yb = 14.2 + k * .9
    box("Banheiro_Bancada", (.5, .8, .08), (-19.6, yb, FZ + .85), M["divisoria"], C_MOV)
    box("Banheiro_Cuba", (.35, .45, .1), (-19.58, yb, FZ + .82), M["pia"], C_MOV)
box("Banheiro_Espelho", (.02, 3.4, .8), (-19.83, 15.55, FZ + 1.55), M["vidro_porta"], C_SOLTO)
for k in range(3):
    x = -15.6 + k * 1.2
    box("Banheiro_Cabine_Divisoria", (.04, 1.5, 1.9), (x - .6, 18.2, FZ + 1.05), M["divisoria"], C_TER)
    box("Banheiro_Vaso", (.4, .55, .42), (x, 18.6, FZ + .21), M["pia"], C_MOV)
box("Banheiro_Cabine_Divisoria", (.04, 1.5, 1.9), (-12.6, 18.2, FZ + 1.05), M["divisoria"], C_TER)
modelo_ph("Banheiro_Placa_Piso", "WetFloorSign_01", (-17.5, 13.8, FZ), .5, C_SOLTO, alt=.6)
# ---- sala 104 (x 2 .. 12, y 13 .. 19)
box("Sala_Quadro", (3.6, .04, 1.2), (7.0, BY1 - .15, FZ + 1.5), M["verde_quadro"], C_TER)
box("Sala_Quadro_Moldura", (3.7, .06, .06), (7.0, BY1 - .14, FZ + .87), M["mad_cl"], C_TER)
r = vazio("Sala_Mesa_Professor", (10.2, 18.0, FZ), C_MOV, PI)
box("Sala_Mesa_Professor_Tampo", (1.2, .6, .04), (0, 0, .75), M["mad_cl"], C_MOV, r)
box("Sala_Mesa_Professor_Base", (1.1, .04, .7), (0, .26, .37), M["mad_cl"], C_MOV, r)
def carteira(nome, x, y):
    r = vazio(nome, (x, y, FZ), C_MOV, 0)
    box(nome + "_Tampo", (.6, .45, .03), (0, 0, .72), M["tampo"], C_MOV, r)
    box(nome + "_Assento", (.4, .38, .03), (0, -.45, .44), M["cadeira_az"], C_MOV, r)
    box(nome + "_Encosto", (.4, .03, .3), (0, -.66, .7), M["cadeira_az"], C_MOV, r)
    for sx in (-1, 1):
        barra(nome + "_Pe", (sx * .26, .15, 0), (sx * .26, .15, .71), .012, M["metal"], C_SOLTO, r, seg=6)
        barra(nome + "_Pe", (sx * .18, -.6, 0), (sx * .18, -.6, .44), .012, M["metal"], C_SOLTO, r, seg=6)
for x in (3.6, 4.8, 9.2, 10.4):                               # corredor livre no meio (x 5.5 .. 8.5), em frente a porta
    for y in (14.6, 15.8, 17.0):
        carteira("Carteira_%.0f_%.0f" % (x * 10, y * 10), x, y)
modelo_ph("Sala_Ventilador", "ceiling_fan", (5.0, 16.0, FZ + PD - .5), 0, C_SOLTO, alt=.5)
modelo_ph("Sala_Ventilador_2", "ceiling_fan", (9.5, 16.0, FZ + PD - .5), 0, C_SOLTO, alt=.5)
modelo_ph("Sala_Lixeira", "metal_trash_can", (2.5, 13.5, FZ), 0, C_SOLTO, alt=.6)
box("Sala_Mural", (2.0, .03, 1.0), (2.14, 16.0, FZ + 1.6), M["cortica"], C_TER, rot=(0, 0, PI / 2))

# ------------------------------------------------------------------ 5. passarela coberta com porticos (projeto-padrao, foto "ft ciep 02")
PW = 6.0
for y0 in range(-36, -2, 5):
    for sx in (-1, 1):
        painel_simples("Passarela_Arco", 5.0, 4.6, 3.8, 3.9, 1.3, -.35, .45, (PX + sx * PW / 2, y0 + 2.5, FZ + 2.3), M["branco_fach"], C_PAS, fundo_aberto=True, rz=PI / 2)
for y in range(-36, -1, 5):
    for sx in (-1, 1):
        box("Passarela_Coluna", (.49, 1.24, 4.6), (PX + sx * PW / 2, y, FZ + 2.3), M["branco_fach"], C_PAS)
box("Passarela_Cobertura", (PW + .5, 34, .3), (PX, -19.0, FZ + 4.75), M["branco_fach"], C_PAS)

# ------------------------------------------------------------------ 6. interativos
def porta(nome, dobradica, rz, m, larg=.88):
    r = vazio(nome, (dobradica[0], dobradica[1], FZ), C_INT, rz)
    box(nome + "_Folha", (larg, .045, 2.08), (larg / 2, 0, 1.04), m, C_INT, r)
    for s in (-1, 1):
        cyl(nome + "_Macaneta", .025, .025, .05, (larg - .09, s * .05, 1.02), M["metal"], C_INT, r, rot=(PI / 2, 0, 0), seg=10)
    return r
porta("I_Porta_Direcao", (-2.0, 5.0), PI / 2, M["porta_mad"])
porta("I_Porta_Banheiro", (-16.5, YC1), 0, M["porta_mad"])
porta("I_Porta_Sala", (6.5, YC1), 0, M["porta_mad"])
def item(nome, pos, rz=0.0): return vazio(nome, pos, C_INT, rz)
r = item("I_Celular_Print", (2.75, 6.95, FZ + .772), .4)
box("I_Celular_Print_Corpo", (.075, .155, .009), (0, 0, .0045), M["preto"], C_INT, r, bevel=.004)
box("I_Celular_Print_Tela", (.068, .145, .002), (0, 0, .0095), M["tela"], C_INT, r)
r = item("I_Monitor_Cameras", (1.85, 7.2, FZ + .77), 0)
box("I_Monitor_Cameras_Tela", (.55, .04, .34), (0, 0, .25), M["preto"], C_INT, r)
box("I_Monitor_Cameras_Pe", (.08, .08, .08), (0, 0, .04), M["preto"], C_INT, r)
quadro("I_Monitor_Cameras_Imagem", (0, .025, .25), "+y", .5, .3, M["tela"], C_INT, r)
box("I_Monitor_Cameras_DVR", (.36, .26, .06), (.45, 0, .03), M["preto"], C_INT, r)
r = item("I_Pasta_Frequencia", (-8.95, 7.2, FZ + 1.09), PI / 2 + .1)
box("I_Pasta_Frequencia_Capa", (.32, .24, .03), (0, 0, .015), M["peit_verm"], C_INT, r)
r = item("I_Livro_Ocorrencias", (2.15, 6.75, FZ + .77), -.2)
box("I_Livro_Ocorrencias_Capa", (.3, .21, .035), (0, 0, .018), M["preto"], C_INT, r)
r = item("I_Mochila", (-13.4, 18.3, FZ), .3)
box("I_Mochila_Corpo", (.32, .18, .42), (0, 0, .21), M["mochila"], C_INT, r, bevel=.05)
box("I_Mochila_Bolso", (.24, .05, .18), (0, -.1, .14), M["mochila2"], C_INT, r, bevel=.02)
r = item("I_Telefone", (-8.95, 5.6, FZ + 1.09), PI / 2)
box("I_Telefone_Base", (.2, .22, .06), (0, 0, .03), M["branco"], C_INT, r, bevel=.01)
box("I_Telefone_Fone", (.05, .2, .045), (-.05, 0, .075), M["branco"], C_INT, r, bevel=.015)

# ------------------------------------------------------------------ 7. viatura
r = carro_modelo("Viatura_PM", C_VEIC, "perua", (10.0, -42.6, 0), PI, cor="#eceded", escala=1.08)
if r:
    VTR, sy_, inf = r
    giroflex(VTR, C_VEIC, -.25, inf["alt"] + .03, larg=1.05)
    faixa_lateral("Viatura_Listra_Azul", VTR, C_VEIC, sy_, -2.0, 1.68, .54, .71, M["faixa_pm"])
    for lado in (1, -1):
        v = "+y" if lado > 0 else "-y"
        texto("Adesivo_Policia_Militar", "POLÍCIA MILITAR", .085, (-.15, sy_(-.15, .89, lado) + lado * .008, .89), v, M["texto_az"], C_VEIC, VTR)
        texto("Adesivo_190", "190", .12, (-1.67, sy_(-1.67, .91, lado) + lado * .008, .91), v, M["texto_az"], C_VEIC, VTR)
        cyl("Brasao_Imagem", .09, .09, .004, (1.03, sy_(1.03, .89, lado) + lado * .006, .89), M["brasao"], C_VEIC, VTR, rot=(PI / 2, 0, 0), seg=28)

# ------------------------------------------------------------------ 8. luzes
sol = luz("Sol", "SUN", 3.6, "#fff2dc", (0, 0, 40), C_LUZ, angle=math.radians(2.0))
sol.rotation_euler = (math.radians(48), 0, math.radians(-35))
def tubo(nome, x, y, watts, comp=1.2, col=C_TER):
    box(nome + "_Tubo", (comp, .1, .04), (x, y, FZ + PD - .05), M["lamp_f"], col)
    luz(nome + "_Luz", "POINT", watts, "#eaf2ff", (x, y, FZ + PD - .4), C_LUZ, shadow_soft_size=.3)
for x, y in ((-7.5, 5.0), (-4.5, 5.0), (-7.5, 8.2), (-4.5, 8.2)): tubo("Luz_Recepcao", x, y, 45)
for x, y in ((0.5, 5.0), (3.8, 5.0), (0.5, 8.2), (3.8, 8.2)): tubo("Luz_Direcao", x, y, 40)
for x in range(-17, 20, 5): tubo("Luz_Corredor", x, 11.5, 35)
for x, y in ((-17.5, 15.0), (-14.5, 17.0)): tubo("Luz_Banheiro", x, y, 30)
for x, y in ((4.5, 14.8), (9.5, 14.8), (4.5, 17.6), (9.5, 17.6)): tubo("Luz_Sala_104", x, y, 40)
for x in range(-45, 50, 10):
    for y in (1.5, PROF - 1.5): luz("Luz_Pilotis", "POINT", 20, "#eaf2ff", (x, y, FZ + PD - .3), C_LUZ, shadow_soft_size=.3)

# ------------------------------------------------------------------ 9. pontos do treinamento (cena.json)
ponto("Inicio", PX + 3.0, -41.5, (-.2, 1)); ponto("Parceiro", PX + 4.5, -41.0, (-.4, 1)); ponto("Inspetora", PX + 4.1, -35.6, (-.3, -1))
ponto("Responsavel", -6.0, 5.0, (0, -1)); ponto("Diretora", 2.4, 7.8, (0, -1))
ponto("Aluno_Sala", 4.8, 15.35, (0, 1)); ponto("Aluno_Banheiro", -13.6, 16.2, (1, 0)); ponto("Aluno_Corredor", -14.5, 11.6, (1, 0))
ponto("Ferido", -11.0, 10.45, (1, 0)); ponto("Ponto_Encontro", 14.0, -20.0, (0, 1))

# ------------------------------------------------------------------ 10. cameras, ceu, render
camera("Camera_Rua", (PX + 3.0, -41.5, FZ + 1.6), (PX, -20.0, FZ + 3.0), 18)
camera("Camera_Patio", (-6.0, -26.0, FZ + 1.6), (2.0, 4.0, FZ + 5.0), 16)
camera("Camera_Passarela", (PX, -34.0, FZ + 1.6), (PX, -5.0, FZ + 1.8), 16)
camera("Camera_Recepcao", (-7.5, 1.5, FZ + 1.6), (-5.0, 8.0, FZ + 1.2), 15)
camera("Camera_Direcao", (-1.2, 4.0, FZ + 1.6), (3.5, 8.5, FZ + 1.0), 14)
camera("Camera_Corredor", (-6.8, 11.5, FZ + 1.6), (-19.0, 11.5, FZ + 1.3), 15)
camera("Camera_Sala_104", (6.95, 13.6, FZ + 1.6), (8.0, 18.5, FZ + 1.0), 14)
camera("Camera_Pilotis", (22.5, -4.0, FZ + 1.6), (30.0, 12.0, FZ + 1.5), 16)
p = camera("Camera_Planta", (0, -8, 90.0), (0, -8, 0)); p.data.type = "ORTHO"; p.data.ortho_scale = 70
p.rotation_euler = (0, 0, 0)
scene.camera = bpy.data.objects["Camera_Patio"]
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World"); scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (*lin(hx("#9fbcd8")), 1); bg.inputs["Strength"].default_value = 1.0
scene.unit_settings.system = "METRIC"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.engine = "CYCLES"; scene.cycles.samples = 128; scene.cycles.use_denoising = True
for attr, val in (("view_transform", "AgX"), ("look", "AgX - Medium High Contrast")):
    try: setattr(scene.view_settings, attr, val)
    except Exception: pass
MEDIDAS_ESTIMADAS = {
    "comprimento_bloco_m": X1 - X0, "profundidade_bloco_m": PROF, "modulo_m": MOD, "pavimentos": 3, "altura_entre_pavimentos_m": PISO,
    "janela_m": [JW, JH, JR], "arco_terreo_m": [AW, AH, AR], "platibanda_m": PL_H, "corredor_central_m": YC1 - YC0,
    "recepcao_m": [8, 7], "direcao_m": [8, 7], "sala_104_m": [10, 6], "banheiro_m": [8, 6], "passarela_largura_m": PW, "muro_altura_m": MURO_H,
}
scene["medidas_estimadas"] = str(MEDIDAS_ESTIMADAS)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "ciep.blend"))
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in scene.objects if o.type == "MESH")
say("cena salva: %d objetos, %d triangulos (antes da otimizacao)" % (len(scene.objects), tris))
say("medidas ESTIMADAS: %s" % MEDIDAS_ESTIMADAS)
