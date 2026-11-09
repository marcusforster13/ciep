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

def tex_persiana_ext(S=256, seed=7):
    """Janela vista da rua (foto do Tancredo Neves): sala escura ao fundo, persianas de laminas claras
    recolhidas em alturas diferentes em cada folha, caixilho de aluminio e travessa."""
    r = np.random.default_rng(seed); yy, xx = np.mgrid[0:S, 0:S] / S        # yy = 0 no alto da abertura
    a = np.ones((S, S, 3)) * np.array(hx("#1d1f21"))
    a *= (.75 + .5 * yy)[..., None]                                      # fundo da sala: um pouco mais claro perto do peitoril
    lam = (yy * 22) % 1
    for x0, x1 in ((.0, .33), (.33, .66), (.66, 1.0)):
        desce = r.uniform(.35, 1.0)                                      # ate onde a persiana desce nesta folha
        abert = r.uniform(.25, .6)                                       # laminas mais ou menos abertas
        m = (xx >= x0) & (xx < x1) & (yy < desce)
        cor = np.array(hx("#d9dad6")) * (.62 + .38 * np.sin(np.clip(lam / (1 - abert), 0, 1) * PI) ** .5)[..., None]
        fresta = lam > (1 - abert)
        a[m & ~fresta] = cor[m & ~fresta]
        a[m & fresta] *= 1.4
    for xc in (.006, .33, .66, .994): a[np.abs(xx - xc) < .012] = hx("#a3a5a7")
    a[np.abs(yy - .5) < .01] = hx("#a3a5a7")
    a *= (.8 + .2 * yy)[..., None]                                       # sombra da verga no alto
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
    "quadro_branco": mat("Quadro_Branco", "#f3f3f0", .12), "porta_azul": mat("Porta_Azul", "#2f63a8", .45),
    "chapim": mat("Chapim_Concreto", "#a8a59e", .9), "galvanizado": mat("Aco_Galvanizado", "#9da2a6", .45, .25), "led": mat("Luminaria_LED", "#f4f7ff", .3, emit="#f4f7ff", forca=1.5), "muro_barra": mat("Muro_Barrado", "#8b8984", .9),
    "mancha": mat("Mancha_Escorrimento", "#3f3c36", .95, alpha=.35), "pvc": mat("Tubo_PVC", "#9b9d99", .45),
    "lix_azul": mat("Lixeira_Azul", "#1f5fb0", .45), "lix_verm": mat("Lixeira_Vermelha", "#c42020", .45),
    "lix_verde": mat("Lixeira_Verde", "#1f8a3a", .45), "lix_amar": mat("Lixeira_Amarela", "#e6b414", .45),
    "lix_cinza": mat("Lixeira_Cinza", "#6f726f", .5), "split": mat("Ar_Condicionado_Split", "#ecebe7", .35),
    "hidrante": mat("Caixa_Hidrante", "#b51f1f", .45), "saida": mat("Placa_Saida_Verde", "#0f8a3c", .4, emit="#18b050", forca=.6),
    "extintor_placa": mat("Placa_Extintor_Vermelha", "#c41e1e", .45), "faixa_am": mat("Demarcacao_Amarela", "#e2b21b", .6),
    "papel": mat("Papel", "#f6f3ea", .9), "papel_am": mat("Papel_Amarelo", "#efd77a", .9), "papel_az": mat("Papel_Azul", "#9cc2e6", .9),
    "tronco": mat("Tronco_Arvore", "#5c4b3c", 1), "folha": mat("Folhagem", "#3d6a35", .8), "terra": mat("Terra_Canteiro", "#5a4634", 1),
    "grama": mat("Grama", "#5f7d3a", .95),
    "texto_pr": mat("Texto_Preto", "#1a1a1a", .6), "texto_br": mat("Texto_Branco", "#f4f4f0", .6), "texto_az": mat("Texto_Azul", "#16307f", .6),
    "fita": mat("Fita_Isolamento", "#e8c21a", .5),
    "mochila": mat("Mochila_Tecido", "#2b3a55", .85), "mochila2": mat("Mochila_Detalhe", "#b3261e", .7),
    "pia": mat("Louca_Branca", "#eeede8", .25), "divisoria": mat("Divisoria_Granito", "#6b6862", .4),
    "cadeira_az": mat("Assento_Carteira_Verde", "#2f8a4f", .5), "tampo": mat("Tampo_Carteira", "#eeeeea", .4),      # foto da sala do Tancredo (2025): tampo branco, estrutura e cadeira verdes
    "estrutura_verde": mat("Estrutura_Carteira_Verde", "#2a7a47", .45, .2), "quadra": mat("Piso_Quadra", "#3f7a5a", .7), "telha": mat("Telha_Metalica", "#b9bcbd", .45, .3),
    "porta_amarela": mat("Porta_Amarela", "#e6b31e", .45),
    "pint_pm": mat("Viatura_Pintura_Branca", "#e9eaec", .3), "faixa_pm": mat("Viatura_Faixa_Azul", "#1e4fb8", .3),
    "giro_verm": mat("Giroflex_Vermelho", "#5a0a08", .2, emit="#ff1010", forca=.05),
    "giro_azul": mat("Giroflex_Azul", "#08205a", .2, emit="#1040ff", forca=.05),
    "brasao": mat("Brasao_(inserir_imagem_oficial)", "#c8cbd0", .5),
    "int_forro": mat("Interior_Forro", "#1d1f22", .9), "interior": mat("Interior_Carro", "#2a2b2e", .8),
    "tela": mat("Tela_Acesa", "#000000", .2, emit="#9fc4ff", forca=2.0),
}
M["piso"] = mat("Piso_Granilite", "#a9a7a2", .45)
M["piso_corredor"] = mat("Piso_Corredor", "#3c3e41", .45)   # corredores: piso grafite liso e gasto (foto do corredor de CIEP enviada pelo autor)          # textura CC0 granite_tile (aplicar_texturas_cc0.py)
M["azulejo"] = mat("Azulejo_Branco", "#e8e6df", .2)          # textura CC0 long_white_tiles
M["persiana"] = tela_mat("Janela_Persiana", np_image("janela_persiana", tex_persiana()), 0)
M["persiana_ext"] = tela_mat("Janela_Persiana_Externa", np_image("janela_persiana_ext", tex_persiana_ext()), 0)

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
C_BLOQ = collection("98_Bloqueios")         # caixas so de colisao (troncos, lixeiras): nao aparecem no render nem no site
def bloqueio(nome, tam, pos):
    o = box(nome, tam, pos, M["preto"], C_BLOQ); o.hide_render = True; return o

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
def muro(nome, a, b, h=MURO_H, gradil=0.0, sujeira=False):
    """Muro de escola publica: alvenaria rebocada e pintada, pilares a cada 3 m, chapim de concreto, barrado cinza
    embaixo (respingos de chuva) e manchas de escorrimento. gradil > 0: mureta de h metros com grade metalica por cima."""
    ax, ay = a; bx, by = b; horiz = abs(bx - ax) > abs(by - ay)
    L = abs(bx - ax) if horiz else abs(by - ay); sg = 1 if ((bx - ax) if horiz else (by - ay)) > 0 else -1
    P = lambda d, off=0.0: (ax + sg * d, ay + off, 0) if horiz else (ax + off, ay + sg * d, 0)
    def caixa(nm, d0, d1, esp, z0, z1, m, col, off=0.0):
        c = P((d0 + d1) / 2, off); box(nm, (d1 - d0, esp, z1 - z0) if horiz else (esp, d1 - d0, z1 - z0), (c[0], c[1], FZ + (z0 + z1) / 2), m, col)
    caixa(nome, 0, L, .15, 0, h, M["muro"], C_PAT)
    caixa(nome + "_Chapim", -.05, L + .05, .25, h, h + .06, M["chapim"], C_PAT)
    for ld in (-1, 1): caixa(nome + "_Barrado", 0, L, .012, 0, .45, M["muro_barra"], C_PAT, off=ld * .081)
    n = max(1, round(L / 3.0))
    for k in range(n + 1):
        d = min(L - .15, max(.15, L * k / n)); c = P(d)
        box(nome + "_Pilar_Muro", (.3, .3, h + (gradil + .1 if gradil else .05)), (c[0], c[1], FZ + (h + (gradil + .1 if gradil else .05)) / 2), M["muro"], C_PAT)
        if gradil: caixa(nome + "_Chapim_Pilar", d - .17, d + .17, .34, h + gradil + .1, h + gradil + .15, M["chapim"], C_PAT)
    if gradil:                                                    # grade: dois tubos horizontais e barras a cada 12 cm
        for z in (h + .12, h + gradil - .05): caixa(nome + "_Gradil_Tubo", 0, L, .04, z - .02, z + .02, M["grade"], C_SOLTO)
        for k in range(int(L / .12)):
            d = .06 + k * .12; caixa(nome + "_Gradil_Barra", d - .009, d + .009, .018, h + .06, h + gradil, M["grade"], C_SOLTO)
    if sujeira:                                                   # escorrimentos sob o chapim (decalques transparentes)
        for k in range(int(L / 2.2)):
            d = rnd.uniform(.3, L - .3); w = rnd.uniform(.25, .8); hh = rnd.uniform(.4, 1.3)
            for ld in (-1, 1): caixa(nome + "_Mancha", d - w / 2, d + w / 2, .004, h - hh, h - .02, M["mancha"], C_SOLTO, off=ld * .078)
# frente: mureta de 0,9 m com gradil de 1,6 m (deixa ver o patio da rua, comum nas escolas publicas); laterais e fundos: muro cheio
muro("Muro_Frente_O", (-56, -38), (PX - 3.0, -38), h=.9, gradil=1.6)
muro("Muro_Frente_L", (PX + 3.0, -38), (56, -38), h=.9, gradil=1.6)
muro("Muro_Lateral_O", (-56, -38), (-56, 24), sujeira=False); muro("Muro_Lateral_L", (56, -38), (56, 24), sujeira=False)
muro("Muro_Fundos", (-56, 24), (56, 24), sujeira=False)
for sx in (-1, 1):
    box("Portao_Coluna", (.5, .5, 2.9), (PX + sx * 3.25, -38, FZ + 1.45), M["muro"], C_PAT)
    box("Portao_Coluna_Chapim", (.62, .62, .06), (PX + sx * 3.25, -38, FZ + 2.93), M["chapim"], C_PAT)
r = vazio("Placa_Escola", (-12, -38.6, FZ), C_SOLTO)                    # placa da escola na frente da grade, sobre dois postes
for sx in (-1, 1): cyl("Placa_Escola_Poste", .04, .04, 2.6, (sx * 1.7, 0, 1.3), M["grade"], C_SOLTO, r, seg=10)
box("Placa_Escola_Chapa", (3.8, .05, 1.0), (0, 0, 2.2), M["branco"], C_SOLTO, r)
box("Placa_Escola_Faixa", (3.8, .055, .18), (0, 0, 1.79), M["texto_az"], C_SOLTO, r)
texto("Placa_Escola_Nome", "CIEP PRESIDENTE TANCREDO NEVES", .19, (0, -.03, 2.38), "-y", M["texto_az"], C_SOLTO, r)
texto("Placa_Escola_Sub", "ESCOLA PÚBLICA", .13, (0, -.03, 2.1), "-y", M["texto_pr"], C_SOLTO, r)
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
FAIXA, JUNTA = 3.6, .13
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
bloqueio("Bloqueio_Tronco_Palmeira", (.3, .3, 2.0), (21.1, -2.8, FZ + 1.0))
# arvores: poucas, mas realistas - jacaranda (especie brasileira) do Poly Haven, reduzido para VR por modelos/preparar_arvores.py
_arv = {}
def arvore_real(nome, arquivo, x, y, rz=0.0):
    if arquivo not in _arv:
        cam = os.path.join(AQUI, "modelos", "arvores", arquivo); _arv[arquivo] = None
        if os.path.exists(cam):
            antes = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=cam)
            novos = [o for o in bpy.data.objects if o not in antes]; ob = next(o for o in novos if o.type == "MESH")
            me = ob.data.copy(); me.transform(ob.matrix_world)
            for i, m in enumerate(me.materials):
                if m: m.name = "Modelo_Arvore_" + m.name.split(".")[0]      # o pipeline mantem a UV e a imagem do modelo
            for o in novos: bpy.data.objects.remove(o, do_unlink=True)
            _arv[arquivo] = me
    if not _arv[arquivo]: return arvore(nome, x, y)
    ob = bpy.data.objects.new(nome, _arv[arquivo]); C_SOLTO.objects.link(ob); ob.location = (x, y, FZ); ob.rotation_euler = (0, 0, rz)
    bloqueio("Bloqueio_Tronco_" + nome, (.45, .45, 2.2), (x, y, FZ + 1.1))       # so o tronco bloqueia a passagem
    box(nome + "_Canteiro", (2.4, 2.4, .12), (x, y, FZ + .06), M["chapim"], C_PAT)
    box(nome + "_Canteiro_Terra", (2.1, 2.1, .02), (x, y, FZ + .12), M["terra"], C_PAT)
arvore_real("Jacaranda_1", "jacaranda.glb", -24.0, -24.0, .4)
arvore_real("Jacaranda_2", "jacaranda.glb", 24.0, -31.0, 2.1)
# (arbustos removidos a pedido do autor: so ocupavam triangulos)
for k, (x, y, rz) in enumerate(((-14, -7, 0), (-20, -7, 0), (14, -7, 0), (28, -7, 0), (-12, -22, PI / 2), (14, -22, PI / 2))):
    r = vazio("Banco_Patio", (x, y, FZ), C_PAT, rz)
    box("Banco_Patio_Tampo", (2.2, .45, .1), (0, 0, .45), M["branco_fach"], C_PAT, r)
    for sx in (-1, 1): box("Banco_Patio_Pe", (.2, .4, .4), (sx * .85, 0, .2), M["branco_fach"], C_PAT, r)

def poste_led(nome, x, y, rz, alt=8.0):
    """Poste de iluminacao comum no Brasil: coluna conica de aco galvanizado, base de concreto, braco curvo e luminaria LED."""
    r = vazio(nome, (x, y, FZ), C_SOLTO, rz)
    box(nome + "_Base", (.5, .5, .3), (0, 0, .15), M["chapim"], C_PAT, r)
    cyl(nome + "_Coluna", .1, .055, alt, (0, 0, .3 + alt / 2), M["galvanizado"], C_SOLTO, r, seg=12)
    pts = [(0, 0, alt + .25), (.15, 0, alt + .55), (.6, 0, alt + .78), (1.4, 0, alt + .88)]
    for a, b in zip(pts, pts[1:]): barra(nome + "_Braco", a, b, .035, M["galvanizado"], C_SOLTO, r, seg=8)
    box(nome + "_Luminaria", (.62, .3, .08), (1.65, 0, alt + .86), M["galvanizado"], C_SOLTO, r, rot=(0, -.08, 0), bevel=.02)
    box(nome + "_LED", (.5, .24, .01), (1.65, 0, alt + .815), M["led"], C_SOLTO, r, rot=(0, -.08, 0))
    box(nome + "_Caixa_Eletrica", (.18, .1, .3), (0, -.1, 1.6), M["galvanizado"], C_SOLTO, r)
for k, (x, y, rz) in enumerate(((-26, -3.5, PI / 2 + .3), (16, -18, PI), (-14, -18, 0), (PX + 4.5, -36.5, PI / 2))):
    poste_led("Poste_Patio_%d" % k, x, y, rz)

# ------------------------------------------------------------------ 3. predio: estrutura, fachadas e cobertura
NM = int((X1 - X0) / MOD)
JW, JH, JR = 3.9, 2.75, .95                                   # janela (foto)
AW, AH, AR = 3.9, 3.0, 1.35                                   # arco do terreo (foto)
# a laje do 1o pavimento (com o vao da rampa) fica na secao 4b
box("Laje_Cobertura", (X1 - X0, PROF, .4), ((X0 + X1) / 2, PROF / 2, Z3 - .2), M["branco_fach"], C_FAC)
# volumes fechados dos pavimentos superiores: secao 4b (o trecho x 10 .. 40 do 1o pavimento e acessivel)
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
            # vista da rua: a mesma janela com a sala escura ao fundo, 2 cm para fora (de dentro continua a persiana clara)
            quadro("Fachada_Janela_Externa", (xc, fy - lado * .08, zb + .92 + (JH - .92) / 2), "-y" if lado < 0 else "+y", JW - .1, JH - .92, M["persiana_ext"], C_SOLTO)
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

# ------------------------------------------------------------------ 4. bloco administrativo (terreo)
box("Piso_Terreo_Jogavel", (BX1 - BX0, BY1 - BY0, .15), (0, (BY0 + BY1) / 2, FZ - .073), M["piso"], C_TER)
box("Piso_Corredor_Terreo", (BX1 - BX0, YC1 - YC0, .004), (0, (YC0 + YC1) / 2, FZ + .004), M["piso_corredor"], C_TER)
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
    box("Porta_Fechada", (.9, .05, 2.08), (x, y, FZ + 1.04), M["porta_azul"], C_TER)

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
# ------------------------------------------------------------------ pecas no padrao das escolas publicas brasileiras
# Modeladas aqui (desenho proprio), com o visual das pecas comuns no Brasil: carteira padrao FNDE (tubo de aco e
# polipropileno), louca sanitaria nacional, divisorias de granito cinza, bebedouro industrial de inox, valvula de
# descarga de parede. Cada peca e montada uma vez e a malha e reaproveitada em todas as copias.
M.update({
    "granito": mat("Granito_Cinza_Andorinha", "#77736d", .35), "louca": mat("Louca_Sanitaria", "#f1f0eb", .15),
    "borda_abs": mat("Borda_ABS_Cinza", "#6c6f73", .5), "laminado_azul": mat("Laminado_Azul", "#3f6fb0", .4),
    "metal_cromo": mat("Metal_Cromado", "#c7cacd", .2, .45), "pp_preto": mat("Polipropileno_Preto", "#1f2022", .6),
    "mdf_madeira": mat("MDF_Madeirado", "#a77f55", .5),
})
C_TMP = collection("_tmp_pecas")
_pecas = {}
def peca(chave, montar):
    """Monta a peca uma vez (objetos temporarios -> uma malha so) e devolve a malha."""
    if chave in _pecas: return _pecas[chave]
    antes = set(C_TMP.objects); montar(); novos = [o for o in C_TMP.objects if o not in antes]
    bpy.context.view_layer.update()
    for o in novos:                                             # aplica modificadores (chanfros) e transformacoes
        me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); me.transform(o.matrix_world)
        o.modifiers.clear(); o.data = me; o.parent = None; o.matrix_world = Matrix.Identity(4)
    with bpy.context.temp_override(active_object=novos[0], selected_objects=novos, selected_editable_objects=novos):
        bpy.ops.object.join()
    me = novos[0].data; me.name = "Peca_" + chave
    for p in me.polygons: p.use_smooth = False
    bpy.data.objects.remove(novos[0], do_unlink=True); _pecas[chave] = me
    return me
def por(nome, chave, montar, x, y, z, rz, col):
    ob = bpy.data.objects.new(nome, peca(chave, montar)); col.objects.link(ob); ob.location = (x, y, z); ob.rotation_euler = (0, 0, rz)
    return ob
T = C_TMP
def _tb(a, b, r=.011, m=None): barra("t", a, b, r, m or M["estrutura_verde"], T, seg=6)

# --- carteira escolar padrao FNDE: mesa com porta-livros + cadeira empilhavel (aluno olha para +y; mesa em y = 0)
def _carteira():
    box("tampo", (.60, .45, .022), (0, 0, .71), M["tampo"], T, bevel=.006)
    box("borda", (.61, .46, .012), (0, 0, .697), M["borda_abs"], T, bevel=.004)
    box("portalivros", (.50, .30, .01), (0, .02, .56), M["grade"], T)
    for sx in (-1, 1):                                          # estrutura em tubo oblongo pintado
        _tb((sx * .27, -.18, 0), (sx * .27, -.18, .70)); _tb((sx * .27, .18, 0), (sx * .27, .18, .70))
        _tb((sx * .27, -.2, .015), (sx * .27, .2, .015)); _tb((sx * .27, -.18, .69), (sx * .27, .18, .69))
    _tb((-.27, .18, .55), (.27, .18, .55))
    # cadeira (atras da mesa)
    box("assento", (.40, .38, .035), (0, -.48, .43), M["cadeira_az"], T, bevel=.02, seg=1)
    box("encosto", (.38, .03, .22), (0, -.69, .72), M["cadeira_az"], T, rot=(-.12, 0, 0), bevel=.012, seg=1)
    for sx in (-1, 1):
        _tb((sx * .19, -.31, 0), (sx * .19, -.31, .42)); _tb((sx * .19, -.66, 0), (sx * .19, -.66, .42))
        _tb((sx * .19, -.66, .42), (sx * .19, -.71, .84)); _tb((sx * .19, -.31, .42), (sx * .19, -.66, .42))
        _tb((sx * .19, -.3, .03), (sx * .19, -.67, .03))
def carteira(nome, x, y, rz=PI / 2, z=None):                   # rz = PI/2: o aluno olha para -x (o quadro)
    return por(nome, "carteira_fnde", _carteira, x, y, FZ if z is None else z, rz, C_MOV)

# --- mesa do professor: estrutura metalica, tampo madeirado com borda e gaveteiro de duas gavetas
def _mesa_prof():
    box("tampo", (1.2, .6, .025), (0, 0, .75), M["mdf_madeira"], T, bevel=.006)
    box("borda", (1.21, .61, .012), (0, 0, .736), M["borda_abs"], T)
    for sx in (-1, 1):
        for sy in (-1, 1): _tb((sx * .56, sy * .26, 0), (sx * .56, sy * .26, .73), .014, M["grafite"])
        _tb((sx * .56, -.26, .05), (sx * .56, .26, .05), .012, M["grafite"])
    box("painel", (1.1, .015, .4), (0, .27, .52), M["mdf_madeira"], T)
    box("gaveteiro", (.4, .52, .36), (.32, 0, .54), M["mdf_madeira"], T, bevel=.004)
    for z in (.62, .46): box("gaveta_frente", (.38, .01, .15), (.32, -.265, z), M["mdf_madeira"], T, bevel=.003); box("puxador", (.12, .02, .015), (.32, -.275, z), M["metal_cromo"], T)
M["grafite"] = mat("Estrutura_Grafite", "#3b3d40", .45, .3)
def mesa_professor(nome, x, y, rz, z=None): return por(nome, "mesa_professor", _mesa_prof, x, y, FZ if z is None else z, rz, C_MOV)

# --- banheiro: vaso de louca com assento, valvula de descarga de parede, cuba oval em bancada de granito,
#     torneira de pressao, mictorio de louca, divisorias de granito sobre pes metalicos, portas laminadas
def _vaso():
    perfil = [(.0, .0), (.12, .0), (.125, .05), (.105, .2), (.15, .33), (.19, .38), (.2, .4), (.165, .405), (.12, .33), (.05, .28), (0, .27)]
    torno("louca", perfil, M["louca"], T, seg=24).scale = (1, 1.35, 1)
    torno("assento", [(.16, .405), (.205, .405), (.205, .425), (.16, .425), (.16, .405)], M["louca"], T, pos=(0, 0, 0), seg=24).scale = (1, 1.3, 1)
    box("caixa_ligacao", (.22, .12, .24), (0, .29, .26), M["louca"], T, bevel=.03)
def _valvula():
    box("placa", (.1, .02, .14), (0, 0, 0), M["metal_cromo"], T, bevel=.006)
    cyl("botao", .025, .025, .02, (0, -.015, .02), M["metal_cromo"], T, rot=(PI / 2, 0, 0), seg=14)
def _cuba():
    torno("cuba", [(.0, -.14), (.1, -.13), (.17, -.08), (.2, .0), (.22, .0), (.22, .01), (.2, .01)], M["louca"], T, seg=24).scale = (1, .78, 1)
    cyl("torneira_corpo", .022, .022, .12, (0, .19, .07), M["metal_cromo"], T, seg=12)
    barra("torneira_bico", (0, .19, .12), (0, .1, .1), .012, M["metal_cromo"], T)
    cyl("torneira_botao", .03, .03, .03, (0, .19, .145), M["metal_cromo"], T, seg=12)
def _mictorio():
    box("corpo", (.38, .3, .62), (0, .0, 0), M["louca"], T, bevel=.09, seg=3)
    box("bacia", (.3, .2, .3), (0, -.06, -.1), M["louca"], T, bevel=.06, seg=2)
    cyl("valvula", .03, .03, .1, (0, .06, .42), M["metal_cromo"], T, seg=12)
def _divisoria(L=1.5, h=1.8):
    box("granito", (.03, L, h), (0, 0, .15 + h / 2), M["granito"], T)
    for sy in (-1, 1): cyl("pe", .015, .015, .15, (0, sy * (L / 2 - .1), .075), M["metal_cromo"], T, seg=8)
def _porta_cabine():
    box("folha", (.6, .025, 1.6), (.3, 0, .25 + .8), M["laminado_azul"], T, bevel=.004)
    box("tranca", (.05, .04, .03), (.55, -.02, 1.05), M["metal_cromo"], T)
    for z in (.4, 1.6): box("dobradica", (.02, .03, .08), (0, 0, z), M["metal_cromo"], T)
def _bebedouro():
    box("corpo", (1.4, .5, .82), (0, 0, .41), M["inox"], T, bevel=.02)
    box("cuba", (1.36, .46, .05), (0, 0, .86), M["inox"], T)
    box("cuba_fundo", (1.2, .32, .02), (0, -.02, .83), M["metal"], T)
    box("espelho", (1.4, .06, .35), (0, .22, 1.04), M["inox"], T, bevel=.01)
    for k in range(3):
        x = -.45 + k * .45
        barra("torneira_jato", (x, .18, .95), (x, .1, 1.0), .012, M["metal_cromo"], T)
        cyl("botao", .028, .028, .04, (x, .19, 1.1), M["metal_cromo"], T, rot=(PI / 2, 0, 0), seg=12)
    box("grelha", (1.0, .02, .2), (0, -.251, .15), M["metal"], T)
    for k in range(8): box("grelha_fenda", (.015, .022, .16), (-.42 + k * .12, -.252, .15), M["preto"], T)

# ---- sala 104 (x 2 .. 12, y 13 .. 19)
QX = 2.0 + .15                                                 # quadro branco na parede oeste (as janelas ficam na parede do fundo)
box("Sala_Quadro", (.04, 3.6, 1.2), (QX, 16.2, FZ + 1.5), M["quadro_branco"], C_TER)
for zq in (.9, 2.1): box("Sala_Quadro_Moldura", (.06, 3.7, .04), (QX + .01, 16.2, FZ + zq), M["metal"], C_SOLTO)
for yq in (14.38, 18.02): box("Sala_Quadro_Moldura", (.06, .04, 1.24), (QX + .01, yq, FZ + 1.5), M["metal"], C_SOLTO)
box("Sala_Quadro_Aparador", (.1, 3.6, .03), (QX + .06, 16.2, FZ + .88), M["metal"], C_SOLTO)
mesa_professor("Sala_Mesa_Professor", 3.4, 18.0, -PI / 2)
for x in (4.6, 6.2, 7.8, 9.4, 11.0):                          # filas de frente para o quadro; faixa livre junto a porta (y 13 .. 14)
    for y in (14.7, 15.9, 17.1, 18.3):
        carteira("Carteira_%.0f_%.0f" % (x * 10, y * 10), x, y)
# ventiladores de parede: secao 6c
modelo_ph("Sala_Lixeira", "metal_trash_can", (2.5, 13.5, FZ), 0, C_SOLTO, alt=.6)
box("Sala_Mural", (.03, 2.0, 1.0), (11.86, 16.0, FZ + 1.6), M["cortica"], C_TER)

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
porta("I_Porta_Banheiro", (-16.5, YC1), 0, M["porta_azul"])
porta("I_Porta_Sala", (6.5, YC1), 0, M["porta_amarela"])      # porta amarela, como na foto da sala do Tancredo
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

# ------------------------------------------------------------------ 6b. acessorios de escola publica brasileira
def lixeira(nome, x, y, rz, m, rotulo=None, alt=.68, r=.21, col=None):
    """Lixeira plastica de 50 L com tampa basculante (vai-e-vem), como as de coleta seletiva das escolas."""
    col = col or C_SOLTO; rr = vazio(nome, (x, y, FZ), col, rz)
    torno(nome + "_Corpo", [(0, .02), (r * .86, .02), (r, alt * .92), (r * 1.06, alt * .93), (r * 1.06, alt * .97), (r * .97, alt * .97)], m, col, rr, seg=20)
    torno(nome + "_Tampa", [(r * 1.04, alt * .97), (r * 1.04, alt), (r * .7, alt + .09), (0, alt + .11)], m, col, rr, seg=20)
    box(nome + "_Tampa_Basculante", (r * 1.0, .03, .12), (0, -r * .55, alt + .05), M["preto"], col, rr, rot=(.6, 0, 0))
    if rotulo: texto(nome + "_Rotulo", rotulo, .045, (0, -r * .97, alt * .62), "-y", M["texto_br"], col, rr)
    return rr
def torno(name, perfil, mats, col, parent=None, pos=(0, 0, 0), rot=(0, 0, 0), seg=24):
    bm = bmesh.new(); aneis = []
    for k in range(seg):
        a = 2 * PI * k / seg; aneis.append([bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)) for rr, z in perfil])
    for k in range(seg):
        A, Bn = aneis[k], aneis[(k + 1) % seg]
        for i in range(len(perfil) - 1):
            try: bm.faces.new((A[i], Bn[i], Bn[i + 1], A[i + 1]))
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, pos, mats, col, parent, rot, smooth=True)
def coleta_seletiva(nome, x, y, rz):
    """Conjunto de 4 lixeiras de coleta seletiva (papel, plastico, vidro, metal) num suporte de tubo metalico."""
    r = vazio(nome, (x, y, FZ), C_SOLTO, rz)
    for k, (m, rot) in enumerate((("lix_azul", "PAPEL"), ("lix_verm", "PLÁSTICO"), ("lix_verde", "VIDRO"), ("lix_amar", "METAL"))):
        lx = (k - 1.5) * .5
        rr = lixeira(nome + "_" + rot, 0, 0, 0, M[m], rot); rr.parent = r; rr.location = (lx, 0, 0)
    for sx in (-1, 1): box(nome + "_Suporte_Pe", (.04, .04, .8), (sx * 1.02, .12, .4), M["metal"], C_SOLTO, r)
    box(nome + "_Suporte_Barra", (2.08, .03, .03), (0, .12, .55), M["metal"], C_SOLTO, r)
    bloqueio("Bloqueio_" + nome, (2.1, .5, .8), (x, y, FZ + .4))          # uma caixa so para a colisao (fica dentro das lixeiras)
coleta_seletiva("Coleta_Seletiva_Patio", 12.5, -1.7, 0)
coleta_seletiva("Coleta_Seletiva_Portao", -3.5, -36.6, 0)
coleta_seletiva("Coleta_Seletiva_Pilotis", -24.0, 1.6, 0)
for nome, x, y, rz, m in (("Cesto_Sala", 2.5, 13.45, 0, "lix_cinza"), ("Cesto_Direcao", 5.6, 9.5, 0, "lix_cinza"), ("Cesto_Recepcao", -2.5, 3.45, 0, "lix_azul")):
    lixeira(nome, x, y, rz, M[m], alt=.42, r=.15)
lixeira("Lixeira_Pedal_Banheiro", -19.6, 17.8, PI / 2, M["branco"], alt=.48, r=.16)
# tambor de 200 L pintado, usado como lixeira no patio
for k, (x, y) in enumerate(((-8.0, -2.2), (20.0, -1.8))):
    torno("Tambor_%d" % k, [(0, .01), (.29, .01), (.29, .88), (.27, .9), (0, .9)], M["lix_azul"], C_SOLTO, pos=(x, y, FZ))
    for z in (.3, .6): torno("Tambor_%d_Aro" % k, [(.295, z - .015), (.3, z), (.295, z + .015)], M["lix_azul"], C_SOLTO, pos=(x, y, FZ))
    texto("Tambor_%d_Texto" % k, "LIXO", .09, (x, y - .3, FZ + .55), "-y", M["texto_br"], C_SOLTO)
# extintores: na parede, com placa vermelha e demarcacao no piso (vermelho com borda amarela, como nas escolas)
def extintor(nome, x, y, virado):
    du = {"-y": (0, -1), "+y": (0, 1), "-x": (-1, 0), "+x": (1, 0)}[virado]
    rz = {"-y": 0, "+y": PI, "-x": -PI / 2, "+x": PI / 2}[virado]
    modelo_ph(nome, "korean_fire_extinguisher_01", (x + du[0] * .12, y + du[1] * .12, FZ + .95), rz + PI, C_SOLTO, alt=.55) or cyl(nome, .08, .08, .5, (x + du[0] * .12, y + du[1] * .12, FZ + 1.2), M["hidrante"], C_SOLTO)
    box(nome + "_Placa", (.3 if du[1] else .012, .012 if du[1] else .3, .4), (x + du[0] * .01, y + du[1] * .01, FZ + 1.95), M["extintor_placa"], C_SOLTO)
    texto(nome + "_Placa_Texto", "EXTINTOR", .045, (x + du[0] * .02, y + du[1] * .02, FZ + 1.95), virado, M["texto_br"], C_SOLTO)
    cx, cy = x + du[0] * .5, y + du[1] * .5
    box(nome + "_Piso_Borda", (1.0, 1.0, .004), (cx, cy, FZ + .003), M["faixa_am"], C_SOLTO)
    box(nome + "_Piso", (.8, .8, .006), (cx, cy, FZ + .004), M["extintor_placa"], C_SOLTO)
extintor("Extintor_Corredor_A", -3.5, YC1 - .13, "-y")
extintor("Extintor_Corredor_B", 14.0, YC0 + .13, "+y")
extintor("Extintor_Recepcao", -9.87, 8.6, "+x")
extintor("Extintor_Pilotis", -32.5, 10.7, "-y")
# caixa de hidrante no corredor
box("Hidrante_Caixa", (.8, .2, .95), (-0.2, YC1 - .2, FZ + 1.35), M["hidrante"], C_SOLTO)
box("Hidrante_Vidro", (.6, .02, .6), (-0.2, YC1 - .31, FZ + 1.4), M["vidro"], C_SOLTO)
texto("Hidrante_Texto", "INCÊNDIO", .07, (-0.2, YC1 - .33, FZ + 1.75), "-y", M["texto_br"], C_SOLTO)
# placas de saida (verdes) sobre as portas corta-fogo e a entrada
for x, y, vir in ((BX0 + .15, (YC0 + YC1) / 2, "+x"), (BX1 - .15, (YC0 + YC1) / 2, "-x"), (-7.5, BY0 + .15, "+y")):
    du = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1)}[vir]
    box("Placa_Saida", (.42 if du[1] else .02, .02 if du[1] else .42, .16), (x, y, FZ + 2.45), M["saida"], C_SOLTO)
    texto("Placa_Saida_Texto", "SAÍDA", .07, (x + du[0] * .012, y + du[1] * .012, FZ + 2.45), vir, M["texto_br"], C_SOLTO)
# cameras de seguranca
for k, (x, y, z, rz) in enumerate(((-7.5, .7, PD - .15, PI), (BX0 + .3, 11.5, PD - .15, -PI / 2), (BX1 - .3, 11.5, PD - .15, PI / 2), (PX + 3.25, -38.0, 2.95, 0))):
    modelo_ph("Camera_Seguranca_%d" % k, "security_camera_01", (x, y, FZ + z - .25), rz, C_SOLTO, alt=.25)
# ar-condicionado split (direcao, recepcao, sala 104)
for k, (x, y, rz) in enumerate(((3.5, YC0 - .2, 0), (-6.0, YC0 - .2, 0), (11.75, 16.0, PI / 2))):
    r = vazio("Split_%d" % k, (x, y, FZ + 2.55), C_SOLTO, rz)
    box("Split_%d_Corpo" % k, (.9, .22, .3), (0, 0, 0), M["split"], C_SOLTO, r, bevel=.03)
    box("Split_%d_Saida" % k, (.75, .02, .04), (0, -.11, -.11), M["preto"], C_SOLTO, r)
    barra("Split_%d_Dreno" % k, (.4, 0, -.15), (.4, 0, -.9), .008, M["branco"], C_SOLTO, r, seg=6)
# bebedouro industrial de inox (4 torneiras) na galeria, junto a parede do bloco
# --- banheiro masculino (x -20 .. -12, y 13 .. 19): azulejo ate 1,8 m, bancada de granito com 3 cubas, mictorios, 3 cabines
box("Banheiro_Azulejo_Fundo", (7.8, .03, 1.8), (-16, BY1 - .14, FZ + .9), M["azulejo"], C_TER)
box("Banheiro_Azulejo_Lado", (.03, 5.8, 1.8), (-19.86, 16.0, FZ + .9), M["azulejo"], C_TER)
# bancada de granito com recorte para cuba de embutir (pedra em faixas em volta dos recortes)
box("Banheiro_Bancada", (.165, 2.7, .03), (-19.7725, 15.0, FZ + .84), M["granito"], C_MOV)
box("Banheiro_Bancada", (.165, 2.7, .03), (-19.3875, 15.0, FZ + .84), M["granito"], C_MOV)
for ya, yb in ((13.65, 13.96), (14.24, 14.86), (15.14, 15.76), (16.04, 16.35)):
    box("Banheiro_Bancada", (.22, yb - ya, .03), (-19.58, (ya + yb) / 2, FZ + .84), M["granito"], C_MOV)
box("Banheiro_Bancada_Rodabanca", (.02, 2.7, .1), (-19.845, 15.0, FZ + .9), M["granito"], C_MOV)
box("Banheiro_Bancada_Saia", (.03, 2.7, .12), (-19.3, 15.0, FZ + .78), M["granito"], C_MOV)
for k in range(3): por("Banheiro_Cuba", "cuba_torneira", _cuba, -19.58, 14.1 + k * .9, FZ + .84, PI / 2, C_MOV)
box("Banheiro_Espelho", (.02, 2.6, .8), (-19.83, 15.0, FZ + 1.55), M["vidro_porta"], C_SOLTO)
box("Banheiro_Espelho_Moldura", (.025, 2.64, .84), (-19.845, 15.0, FZ + 1.55), M["metal"], C_SOLTO)
box("Banheiro_Saboneteira", (.08, .1, .18), (-19.8, 16.7, FZ + 1.2), M["branco"], C_SOLTO, bevel=.01)
box("Banheiro_Papeleira_Toalha", (.1, .3, .38), (-19.78, 17.2, FZ + 1.25), M["branco"], C_SOLTO, bevel=.015)
for k in range(2): por("Banheiro_Mictorio", "mictorio", _mictorio, -17.6 + k * .7, YC1 + .3, FZ + .85, PI, C_MOV)
for k in range(3):                                              # cabines: vaso, valvula de descarga, divisorias e porta
    x = -15.6 + k * 1.2
    por("Banheiro_Vaso", "vaso", _vaso, x, 18.5, FZ, 0, C_MOV)
    por("Banheiro_Valvula", "valvula", _valvula, x, BY1 - .17, FZ + 1.05, 0, C_SOLTO)
    por("Banheiro_Divisoria", "divisoria", _divisoria, x - .6, 18.2, FZ, 0, C_TER)
    por("Banheiro_Porta_Cabine", "porta_cabine", _porta_cabine, x - .57, 17.45, FZ, -.6, C_SOLTO)       # porta entreaberta
    box("Banheiro_Cabine_Frente", (.52, .03, 1.8), (x + .32, 17.45, FZ + 1.05), M["granito"], C_TER)
por("Banheiro_Divisoria", "divisoria", _divisoria, -12.6, 18.2, FZ, 0, C_TER)
lixeira("Banheiro_Lixeira", -13.0, 13.4, 0, M["branco"], alt=.45, r=.15)
modelo_ph("Banheiro_Placa_Piso", "WetFloorSign_01", (-17.5, 14.6, FZ), .5, C_SOLTO, alt=.6)
por("Bebedouro", "bebedouro", _bebedouro, -12.5, BY0 - .35, FZ, 0, C_MOV)
# grades nas janelas do terreo do bloco (muito comuns em escolas publicas)
for y, divs in ((BY0, (-10.0, -2.0, 6.0)), (BY1, (-12.0, -6.0, 2.0, 12.0))):
    for v0, v1, zb, zt in janelas_frente(BX0, BX1, None, divs):
        if zb < .5: continue
        xa = BX0 + v0; off = -.16 if y == BY0 else .16
        for k in range(int((v1 - v0) / .15) + 1):
            box("Janela_Gradil_Barra", (.016, .016, zt - zb), (xa + k * .15, y + off, FZ + (zb + zt) / 2), M["grade"], C_SOLTO)
        for z in (zb + .05, zt - .05): box("Janela_Gradil_Tubo", (v1 - v0, .03, .03), (xa + (v1 - v0) / 2, y + off, FZ + z), M["grade"], C_SOLTO)
# tubos de descida de agua na fachada e manchas de escorrimento (foto do Tancredo Neves em 2025)
for k in (2, 6, 10, 14, 18):
    for fy, sgy in ((0.0, -1), (PROF, 1)):
        x = X0 + MOD * k + .45
        cyl("Tubo_Descida", .05, .05, Z3 + PL_H - .3 - FZ, (x, fy + sgy * .36, (FZ + Z3 + PL_H - .3) / 2), M["pvc"], C_SOLTO, seg=10)

# ------------------------------------------------------------------ 4b. rampa e 1o pavimento (acessivel)
# Rampa em zigue-zague nos pilotis (marca dos CIEPs): dois lancos de 10 m e patamar, inclinacao ~17% (adaptada para VR;
# a norma pede rampas mais suaves - medidas ESTIMADAS). Chega ao 1o pavimento por um vao na laje, com guarda-corpo.
# 1o pavimento (projeto-padrao, PRO192-ALB-107.03): corredor central y 9,5 .. 12,5; salas de 10 x 9 m (~90 m2, o desenho
# anota "aulas 87,5 m2"). Trecho acessivel x 10 .. 40: salas 201, 202, 203 na frente, sala 204 nos fundos e o hall da rampa.
C_PAV = collection("11_Pavimento_1")
P1Z = Z1                                       # piso do 1o pavimento
PD1 = PISO - .35                               # pe-direito livre
PX0, PX1 = 10.0, 40.0                          # trecho acessivel
PC0, PC1 = 9.5, 12.5                           # corredor
RX0, RX1, RY0, RY1 = 24.5, 34.5, 13.0, 19.0    # rampa: lancos de x 24,5 a 34,5; patamar em x 34,5 .. 36,3
HX0, HX1, HY0, HY1 = 24.5, 36.3, 12.7, 19.4    # vao na laje
ang = math.atan((PISO / 2) / (RX1 - RX0))
def prisma(nome, x0, x1, y0, y1, zb0, zb1, zt0, zt1, m, col):
    """Parede com base e topo inclinados (pontas verticais): guarda-corpo e parede central que acompanham a rampa."""
    v = [(x0, y0, zb0), (x1, y0, zb1), (x1, y1, zb1), (x0, y1, zb0), (x0, y0, zt0), (x1, y0, zt1), (x1, y1, zt1), (x0, y1, zt0)]
    malha(nome, v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)], m, col)
MEIO = (RY0 + RY1) / 2                                          # parede central entre os lancos (y 15,9 .. 16,1)
LA0, LA1, LB0, LB1 = RY0, MEIO - .1, MEIO + .1, RY1              # lanco A (sobe para +x) e lanco B (sobe para -x), 2,9 m cada
def z_a(x): return FZ + (x - RX0) / (RX1 - RX0) * PISO / 2       # piso do lanco A
def z_b(x): return FZ + PISO / 2 + (RX1 - x) / (RX1 - RX0) * PISO / 2
def lanco(nome, y0, y1, sobe_x):
    zc = FZ + (PISO / 4 if sobe_x else 3 * PISO / 4)
    box(nome, ((RX1 - RX0) / math.cos(ang), y1 - y0, .2), ((RX0 + RX1) / 2, (y0 + y1) / 2, zc - .1 / math.cos(ang)), M["piso_pilotis"], C_GAL, rot=(0, -ang if sobe_x else ang, 0))
lanco("Rampa_Lanco_A", LA0, LA1, True)
lanco("Rampa_Lanco_B", LB0, LB1, False)
T_GC = .12                                                      # guarda-corpo de concreto, 1,10 m acima do piso
prisma("Rampa_Guarda_Corpo_A", RX0, RX1, LA0 - T_GC, LA0, z_a(RX0) - .25, z_a(RX1) - .25, z_a(RX0) + 1.1, z_a(RX1) + 1.1, M["parede_az"], C_GAL)
prisma("Rampa_Guarda_Corpo_B", RX0, RX1, LB1, LB1 + T_GC, z_b(RX0) - .25, z_b(RX1) - .25, z_b(RX0) + 1.1, z_b(RX1) + 1.1, M["parede_az"], C_GAL)
# entre os lances: cada lance tem o proprio guarda-corpo, 1,10 m acima do seu piso (como nas rampas de CIEP); entre os dois fica aberto
prisma("Rampa_Guarda_Corpo_Centro_A", RX0, RX1, LA1, LA1 + T_GC, FZ, FZ, z_a(RX0) + 1.1, z_a(RX1) + 1.1, M["parede_az"], C_GAL)
prisma("Rampa_Guarda_Corpo_Centro_B", RX0, RX1, LB0 - T_GC, LB0, z_b(RX0) - .25, z_b(RX1) - .25, z_b(RX0) + 1.1, z_b(RX1) + 1.1, M["parede_az"], C_GAL)
for k in (1, 2):                                                # pilares sob o lanco B (ele fica alto perto do 1o andar)
    xp = RX0 + k * (RX1 - RX0) / 3
    box("Rampa_Lanco_B_Coluna", (.3, .3, z_b(xp) - .25 - FZ), (xp, (LB0 + LB1) / 2, FZ + (z_b(xp) - .25 - FZ) / 2), M["branco_fach"], C_GAL)
ZP = FZ + PISO / 2                                              # patamar: piso e guarda-corpo continuo em U (sul, leste, norte)
box("Rampa_Patamar", (HX1 - RX1, RY1 - RY0, .25), ((RX1 + HX1) / 2, MEIO, ZP - .125), M["piso_pilotis"], C_GAL)
box("Rampa_Patamar_Guarda_Corpo", (T_GC, RY1 - RY0 + 2 * T_GC, 1.35), (HX1 + T_GC / 2, MEIO, ZP + 1.1 - .675), M["parede_az"], C_GAL)
for nome, y in (("Rampa_Patamar_Guarda_Corpo_Sul", RY0 - T_GC / 2), ("Rampa_Patamar_Guarda_Corpo_Norte", RY1 + T_GC / 2)):
    box(nome, (HX1 - RX1, T_GC, 1.35), ((RX1 + HX1) / 2, y, ZP + 1.1 - .675), M["parede_az"], C_GAL)
# como nas fotos de rampas de CIEP: paredes pintadas na cor da barra, corrimao tubular pintado dos dois lados de cada lanco
# (a ~0,85 m do piso, preso na parede por suportes) e faixa amarela de seguranca no inicio e no fim da rampa
M["corrimao"] = mat("Corrimao_Pintado", "#24508f", .4, .3)
for nome, yw, sgn, zf_ in (("A_Sul", LA0, 1, z_a), ("A_Centro", LA1, -1, z_a), ("B_Centro", LB0, 1, z_b), ("B_Norte", LB1, -1, z_b)):
    yr = yw + sgn * .07
    barra("Rampa_Corrimao_" + nome, (RX0 + .15, yr, zf_(RX0 + .15) + .85), (RX1 - .15, yr, zf_(RX1 - .15) + .85), .022, M["corrimao"], C_SOLTO, seg=8)
    for k in range(6):
        x = RX0 + .4 + k * (RX1 - RX0 - .8) / 5
        box("Rampa_Corrimao_Suporte", (.03, .07, .03), (x, yw + sgn * .035, zf_(x) + .85), M["corrimao"], C_SOLTO)
M["faixa_seg"] = M.get("faixa_am") or mat("Faixa_Seguranca_Amarela", "#e2b62a", .6)
box("Rampa_Faixa_Seguranca", (.3, LA1 - LA0, .006), (RX0 - .2, (LA0 + LA1) / 2, FZ + .003), M["faixa_seg"], C_SOLTO)
box("Rampa_Faixa_Seguranca", (.3, LB1 - LB0, .006), (RX0 - .2, (LB0 + LB1) / 2, P1Z + .028), M["faixa_seg"], C_SOLTO)
box("Rampa_Patamar_Pilar", (.4, .4, PISO / 2 - .25), (HX1 - .3, MEIO, FZ + (PISO / 2 - .25) / 2), M["branco_fach"], C_GAL)
# laje do 1o pavimento com o vao da rampa (substitui a laje inteira)
for nome, x0, x1, y0, y1 in (("Laje_1_O", X0, HX0, 0, PROF), ("Laje_1_L", HX1, X1, 0, PROF), ("Laje_1_M_Frente", HX0, HX1, 0, HY0), ("Laje_1_M_Fundos", HX0, HX1, HY1, PROF)):
    box(nome, (x1 - x0, y1 - y0, .35), ((x0 + x1) / 2, (y0 + y1) / 2, Z1 - .175), M["pilotis"], C_FAC)
# guarda-corpo em volta do vao (fica aberto onde o lanco B chega, x = 24,5, y 16,1 .. 19)
for nome, tam, pos in (("Vao_Guarda_Corpo_Frente", (HX1 - HX0, .12, 1.1), ((HX0 + HX1) / 2, HY0 - .06, P1Z + .55)),
                       ("Vao_Guarda_Corpo_Fundos", (HX1 - HX0, .12, 1.1), ((HX0 + HX1) / 2, HY1 + .06, P1Z + .55)),
                       ("Vao_Guarda_Corpo_Leste", (.12, HY1 - HY0, 1.1), (HX1 + .06, (HY0 + HY1) / 2, P1Z + .55)),
                       ("Vao_Guarda_Corpo_Oeste", (.12, MEIO + .1 - HY0, 1.1), (HX0 - .06, (HY0 + MEIO + .1) / 2, P1Z + .55))):
    box(nome, tam, pos, M["parede_az"], C_PAV)
# piso e forro do trecho acessivel (2 mm acima da laje: lightmap proprio)
for nome, x0, x1, y0, y1 in (("Piso_Pav1_A", PX0, HX0, .17, PROF - .17), ("Piso_Pav1_B", HX1, PX1, .17, PROF - .17), ("Piso_Pav1_C", HX0, HX1, .17, HY0), ("Piso_Pav1_D", HX0, HX1, HY1, PROF - .17)):
    box(nome, (x1 - x0, y1 - y0, .02), ((x0 + x1) / 2, (y0 + y1) / 2, P1Z + .011), M["piso"], C_PAV)
box("Piso_Corredor_Pav1", (PX1 - PX0, PC1 - PC0, .004), ((PX0 + PX1) / 2, (PC0 + PC1) / 2, P1Z + .023), M["piso_corredor"], C_PAV)
box("Forro_Pav1", (PX1 - PX0, PROF - .34, .02), ((PX0 + PX1) / 2, PROF / 2, Z2 - .35 - .02), M["laje"], C_PAV)
# paredes do 1o pavimento
BAR1 = (M["barra_az"], (1,), 1.4); BAR1n = (M["barra_az"], (-1,), 1.4)
portas_f = [(14.5, 15.4), (24.5, 25.4), (34.5, 35.4)]
parede("Pav1_Corredor_Frente", (PX0, PC0), (PX1, PC0), M["parede"], C_PAV, vaos=[(a - PX0, b - PX0, 0, 2.1) for a, b in portas_f], h=PD1, z0=P1Z, barra=BAR1)
parede("Pav1_Corredor_Fundos", (PX0, PC1), (20.0, PC1), M["parede"], C_PAV, vaos=[(14.5 - PX0, 15.4 - PX0, 0, 2.1)], h=PD1, z0=P1Z, barra=BAR1n)
for x in (20.0, 30.0):
    parede("Pav1_Divisoria_Frente", (x, .17), (x, PC0), M["parede"], C_PAV, h=PD1, z0=P1Z, ext=0.0)
parede("Pav1_Divisoria_Fundos", (20.0, PC1), (20.0, PROF - .17), M["parede"], C_PAV, h=PD1, z0=P1Z, ext=0.0)
for x in (PX0, PX1):
    parede("Pav1_Ponta", (x, .17), (x, PROF - .17), M["parede"], C_PAV, vaos=[(PC0 + .4 - .17, PC1 - .4 - .17, 0, 2.2)], h=PD1, z0=P1Z, t=.25)
    box("Pav1_Porta_Corta_Fogo", (.06, 2.2, 2.2), (x, (PC0 + PC1) / 2, P1Z + 1.1), M["porta_ferro"], C_PAV)
for (a, b), nome in zip(portas_f, ("SALA 201", "SALA 202", "SALA 203")):

    box("Pav1_Placa", (.8, .02, .2), ((a + b) / 2, PC0 + .11, P1Z + 2.3), M["branco"], C_SOLTO)
    texto("Pav1_Placa_Texto", nome, .09, ((a + b) / 2, PC0 + .122, P1Z + 2.3), "+y", M["texto_pr"], C_SOLTO)
box("Pav1_Placa", (.8, .02, .2), (14.95, PC1 - .11, P1Z + 2.3), M["branco"], C_SOLTO)
texto("Pav1_Placa_Texto", "SALA 204", .09, (14.95, PC1 - .122, P1Z + 2.3), "-y", M["texto_pr"], C_SOLTO)
# salas: carteiras viradas para o quadro (parede lateral), mesa do professor, ventiladores, quadro branco
def sala_aula(nome, x0, x1, y0, y1, frente_y):
    """Sala com quadro na parede x0 e carteiras viradas para ele."""
    qx = x0 + .14; yc = (y0 + y1) / 2
    box(nome + "_Quadro", (.04, 3.6, 1.2), (qx, yc, P1Z + 1.5), M["quadro_branco"], C_PAV)
    for zq in (.9, 2.1): box(nome + "_Quadro_Moldura", (.06, 3.7, .04), (qx + .01, yc, P1Z + zq), M["metal"], C_SOLTO)
    mesa_professor(nome + "_Mesa_Professor", x0 + 1.4, yc + 2.2, -PI / 2, z=P1Z)
    ys = [y0 + 1.6 + k * 1.25 for k in range(int((y1 - y0 - 2.4) / 1.25) + 1)]
    for x in [x0 + 2.8 + k * 1.5 for k in range(5)]:
        for y in ys:
            carteira(nome + "_Carteira", x, y, z=P1Z)
    # ventiladores de parede (detalhes_sala), como na foto do Tancredo
    for x in (x0 + 3.3, x0 + 6.7):
        for y in (y0 + 2.2, y1 - 2.2):
            box(nome + "_Luz_Tubo", (1.2, .1, .04), (x, y, P1Z + PD1 - .05), M["lamp_f"], C_PAV)
            luz(nome + "_Luz", "POINT", 38, "#eaf2ff", (x, y, P1Z + PD1 - .4), C_LUZ, shadow_soft_size=.3)
    modelo_ph(nome + "_Lixeira", "metal_trash_can", (x1 - .5, frente_y, P1Z), 0, C_SOLTO, alt=.55)
sala_aula("Sala_201", 10.0, 20.0, .5, PC0, PC0 - .4)
sala_aula("Sala_202", 20.0, 30.0, .5, PC0, PC0 - .4)
sala_aula("Sala_203", 30.0, 40.0, .5, PC0, PC0 - .4)
sala_aula("Sala_204", 10.0, 20.0, PC1, PROF - .5, PC1 + .4)
for x in range(12, 40, 5):
    box("Pav1_Corredor_Luz_Tubo", (1.2, .1, .04), (x, (PC0 + PC1) / 2, P1Z + PD1 - .05), M["lamp_f"], C_PAV)
    luz("Pav1_Corredor_Luz", "POINT", 30, "#eaf2ff", (x, (PC0 + PC1) / 2, P1Z + PD1 - .4), C_LUZ, shadow_soft_size=.3)
extintor("Extintor_Pav1", 22.0, PC0 + .13, "+y")
# volume fechado do restante dos pavimentos superiores (fora do trecho acessivel)
box("Pav1_Volume_O", (PX0 - X0 - .4, PROF - 1.6, PISO - .6), ((X0 + .2 + PX0 - .2) / 2, PROF / 2, (Z1 + Z2) / 2), M["escuro"], C_FAC)
box("Pav1_Volume_L", (X1 - PX1 - .4, PROF - 1.6, PISO - .6), ((PX1 + .2 + X1 - .2) / 2, PROF / 2, (Z1 + Z2) / 2), M["escuro"], C_FAC)
box("Pav2_Volume", (X1 - X0 - .8, PROF - 1.6, PISO - .6), ((X0 + X1) / 2, PROF / 2, (Z2 + Z3) / 2), M["escuro"], C_FAC)

# ------------------------------------------------------------------ 6c. fidelidade ao CIEP real (fotos da Agencia Brasil, 2025)
# --- vigas pre-moldadas aparentes no teto dos pilotis e das galerias (nervuras a cada 1,25 m)
for k in range(int((X1 - X0) / 1.25) + 1):
    x = X0 + k * 1.25
    trechos = [(0.3, PROF - .3)] if not (BX0 - .1 < x < BX1 + .1) else [(0.3, BY0 - .1), (BY1 + .1, PROF - .3)]   # sobre o bloco fechado ha forro
    if HX0 - .2 < x < HX1 + .2: trechos = [(a, min(b, HY0 - .2)) for a, b in trechos if a < HY0 - .2] + [(max(a, HY1 + .2), b) for a, b in trechos if b > HY1 + .2]
    for y0, y1 in trechos:
        if y1 - y0 > .5: box("Pilotis_Viga", (.22, y1 - y0, .38), (x, (y0 + y1) / 2, Z1 - .35 - .19), M["pilotis"], C_GAL)
# --- fachada envelhecida: escorrimentos com textura (transparencia em degrade), sob os peitoris e sob a platibanda
def tex_escorrimento(S=256, H=512, seed=3):
    r = np.random.default_rng(seed); a = np.zeros((H, S)); yy = np.linspace(0, 1, H)[:, None]
    for _ in range(26):                                          # filetes verticais de largura e comprimento variados
        x0 = r.integers(0, S); w = r.integers(2, 14); L = r.uniform(.25, 1.0); f = r.uniform(.25, .8)
        xs = np.clip(np.arange(x0 - w, x0 + w), 0, S - 1)
        perfil = np.exp(-((np.arange(len(xs)) - w) / (w * .6)) ** 2)
        queda = np.clip(1 - yy / L, 0, 1) ** 1.6
        a[:, xs] = np.maximum(a[:, xs], f * queda * perfil[None, :])
    a = np.clip(a + .12 * np.clip(1 - yy / .15, 0, 1), 0, 1) * (.85 + .15 * r.random((H, S))) * .55
    rgba = np.zeros((H, S, 4), np.float32); rgba[..., 0], rgba[..., 1], rgba[..., 2] = .23, .21, .18; rgba[..., 3] = a
    img = bpy.data.images.new("escorrimento_fachada", S, H, alpha=True); img.pixels.foreach_set(np.flipud(rgba).ravel()); img.pack()
    return img
M["escorre"] = bpy.data.materials.new("Img_Mancha_Escorrimento")
_nt = M["escorre"].node_tree; _b = _nt.nodes.get("Principled BSDF"); _t = _nt.nodes.new("ShaderNodeTexImage"); _t.image = tex_escorrimento()
_nt.links.new(_t.outputs["Color"], _b.inputs["Base Color"]); _nt.links.new(_t.outputs["Alpha"], _b.inputs["Alpha"]); _b.inputs["Roughness"].default_value = .95
for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
    try: setattr(M["escorre"], attr, val)
    except Exception: pass
for fy, vir, sgy in ((-.176, "-y", -1), (PROF + .176, "+y", 1)):
    for k in range(NM):
        for z0 in (Z1, Z2):
            if rnd.random() < .25:
                xc = X0 + MOD * (k + .5) + rnd.uniform(-.6, .6); w = rnd.uniform(1.2, 2.4); hh = rnd.uniform(.4, .8)
                zb = z0 + PISO / 2 - .05 - JH / 2
                quadro("Fachada_Escorrimento", (xc, fy, zb - hh / 2 + .05), vir, w, hh, M["escorre"], C_SOLTO)
        quadro("Platibanda_Escorrimento", (X0 + MOD * (k + .5) + rnd.uniform(-1, 1), fy - sgy * .05, Z3 + PL_H - .2 - .7), vir, rnd.uniform(2.5, 4.8), 1.4, M["escorre"], C_SOLTO)
# --- salas como a foto atual do Tancredo: ventilador de parede, eletrodutos aparentes, forro modular, estante branca
def ventilador_parede(nome, x, y, z, rz):
    r = vazio(nome, (x, y, z), C_SOLTO, rz)
    box(nome + "_Suporte", (.08, .12, .08), (0, .04, 0), M["preto"], C_SOLTO, r)
    cyl(nome + "_Motor", .09, .09, .2, (0, -.1, 0), M["preto"], C_SOLTO, r, rot=(PI / 2, 0, 0), seg=14)
    cyl(nome + "_Grade", .26, .26, .1, (0, -.26, -.02), M["grade"], C_SOLTO, r, rot=(PI / 2 + .25, 0, 0), seg=24)
def eletrodutos(nome, x0, x1, y, z, n=2):
    for k in range(n): cyl(nome, .02, .02, x1 - x0, ((x0 + x1) / 2, y, z - k * .06), M["pvc"], C_SOLTO, rot=(0, PI / 2, 0), seg=8)
def forro_modular(nome, x0, x1, y0, y1, z, passo=.625):
    for k in range(int((x1 - x0) / passo) + 1): box(nome, (.02, y1 - y0, .01), (x0 + k * passo, (y0 + y1) / 2, z - .006), M["junta"], C_SOLTO)
    for k in range(int((y1 - y0) / passo) + 1): box(nome, (x1 - x0, .02, .01), ((x0 + x1) / 2, y0 + k * passo, z - .006), M["junta"], C_SOLTO)
def estante(nome, x, y, rz, larg=3.6, zf=FZ):
    r = vazio(nome, (x, y, zf), C_MOV, rz); cores = ("papel_am", "lix_azul", "lix_verm", "papel", "lix_verde")
    box(nome + "_Fundo", (larg, .02, 1.8), (0, .18, .9), M["branco"], C_MOV, r)
    for z in (.05, .45, .85, 1.25, 1.65): box(nome + "_Prateleira", (larg, .38, .025), (0, 0, z), M["branco"], C_MOV, r)
    for xs in (-larg / 2, -larg / 6, larg / 6, larg / 2): box(nome + "_Lateral", (.025, .38, 1.7), (xs, 0, .87), M["branco"], C_MOV, r)
    for k in range(14):
        z = (.07, .47, .87, 1.27)[k % 4] + .1
        box(nome + "_Material", (rnd.uniform(.15, .35), .28, rnd.uniform(.12, .3)), (rnd.uniform(-larg / 2 + .2, larg / 2 - .2), 0, z), M[cores[k % 5]], C_SOLTO, r)
def detalhes_sala(nome, x0, x1, y0, y1, zf, qx, porta_y):
    """Detalhes da foto: quadro verde pequeno ao lado do branco, ventiladores de parede, eletrodutos, forro modular, estante."""
    yc = (y0 + y1) / 2
    box(nome + "_Quadro_Verde", (.04, 1.2, 1.0), (qx, yc + 2.55, zf + 1.5), M["verde_quadro"], C_SOLTO)
    for y in (y0 + .9, y1 - .9): ventilador_parede(nome + "_Ventilador_Parede", x1 - .12, y, zf + 2.55, PI / 2)
    eletrodutos(nome + "_Eletroduto", x0 + .2, x1 - .2, y0 + .12 if porta_y > yc else y1 - .12, zf + PD - .15)
    forro_modular(nome + "_Forro_Grade", x0 + .1, x1 - .1, y0 + .1, y1 - .1, zf + PD - .03)
    estante(nome + "_Estante", x1 - 2.2, y0 + .3 if porta_y > yc else y1 - .3, 0 if porta_y > yc else PI, zf=zf)
detalhes_sala("Sala_104", 2.0, 12.0, YC1, BY1, FZ, 2.0 + .15, YC1)
for nome, x0, x1, y0, y1, py in (("Sala_201", 10.0, 20.0, .5, PC0, PC0), ("Sala_202", 20.0, 30.0, .5, PC0, PC0), ("Sala_203", 30.0, 40.0, .5, PC0, PC0), ("Sala_204", 10.0, 20.0, PC1, PROF - .5, PC1)):
    detalhes_sala(nome, x0, x1, y0, y1, P1Z, x0 + .14, py)
# --- ginasio coberto (o segundo volume dos CIEPs): cobertura em arco sobre pilares e quadra poliesportiva escolar
# Padrao das quadras de escola publica (memoriais FNDE / prefeituras): piso de concreto com pintura acrilica ou epoxi,
# area de jogo verde e faixa externa vermelho-oxido; linhas de 5 cm por modalidade (futsal branco, basquete amarelo,
# volei azul); arquibancada em placas de concreto sobre estrutura de concreto. Medidas da quadra (14 x 22 m) ESTIMADAS.
M.update({"quadra": mat("Piso_Quadra", "#2f6a4b", .55), "quadra_borda": mat("Piso_Quadra_Borda", "#93453a", .55),
          "linha_br": mat("Linha_Quadra_Branca", "#e9e9e4", .5), "linha_am": mat("Linha_Quadra_Amarela", "#e3b52c", .5),
          "linha_az": mat("Linha_Quadra_Azul", "#2d5fa8", .5), "tabela": mat("Tabela_Basquete", "#f1f1ee", .4),
          "aro": mat("Aro_Basquete", "#d2541f", .4, .5), "rede": mat("Rede_Trave", "#f2f2f2", .8, alpha=.35)})
GX0, GX1, GY0, GY1 = 33.0, 55.0, -36.5, -11.0
QX, QY, QW, QL = 42.25, -23.75, 14.0, 22.0                     # centro, largura (x) e comprimento (y) da area de jogo
ZQ = FZ + .085                                                  # topo do piso da quadra
box("Ginasio_Piso", (GX1 - GX0, GY1 - GY0, .12), ((GX0 + GX1) / 2, (GY0 + GY1) / 2, FZ + .02), M["piso_pilotis"], C_PAT)
box("Ginasio_Piso_Borda", (17.5, 24.9, .004), (QX, QY, ZQ + .002), M["quadra_borda"], C_PAT)
box("Ginasio_Piso_Jogo", (QW, QL, .004), (QX, QY, ZQ + .004), M["quadra"], C_PAT)
def faixa(nome, pts, m, w=.05, z=ZQ + .007, fechado=False):
    """Linha pintada no piso: fita de largura w ao longo de uma polilinha."""
    if fechado: pts = list(pts) + [pts[0]]
    vs, fs = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L * w / 2, dx / L * w / 2
        vs += [(x + nx, y + ny, z), (x - nx, y - ny, z)]
        if i: fs.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    malha(nome, vs, fs, m, C_SOLTO)
def arco_pts(cx, cy, r, a0, a1, n=24): return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
qx0, qx1, qy0, qy1 = QX - QW / 2, QX + QW / 2, QY - QL / 2, QY + QL / 2
# futsal (branco): limites, linha central, circulo central, areas de meta e marcas de penalti
faixa("Ginasio_Linha_Futsal", [(qx0, qy0), (qx1, qy0), (qx1, qy1), (qx0, qy1)], M["linha_br"], fechado=True)
faixa("Ginasio_Linha_Futsal", [(qx0, QY), (qx1, QY)], M["linha_br"])
faixa("Ginasio_Linha_Futsal", arco_pts(QX, QY, 2.5, 0, 2 * PI, 40), M["linha_br"])
for s, yl in ((1, qy0), (-1, qy1)):
    a_esq = (PI / 2, PI) if s > 0 else (PI, 1.5 * PI)
    a_dir = (0, PI / 2) if s > 0 else (1.5 * PI, 2 * PI)
    faixa("Ginasio_Linha_Futsal", arco_pts(QX - 1.5, yl, 4.0, *a_esq), M["linha_br"])
    faixa("Ginasio_Linha_Futsal", arco_pts(QX + 1.5, yl, 4.0, *a_dir), M["linha_br"])
    faixa("Ginasio_Linha_Futsal", [(QX - 1.5, yl + s * 4.0), (QX + 1.5, yl + s * 4.0)], M["linha_br"])
    torno("Ginasio_Marca_Penalti", [(0, ZQ + .007), (.1, ZQ + .007)], M["linha_br"], C_SOLTO, pos=(QX, yl + s * 5.0, 0), seg=12)
# basquete (amarelo): garrafao, lance livre e linha de 3 pontos (reduzida, quadra escolar)
for s, yl in ((1, qy0), (-1, qy1)):
    faixa("Ginasio_Linha_Basquete", [(QX - 1.8, yl), (QX - 1.8, yl + s * 4.6), (QX + 1.8, yl + s * 4.6), (QX + 1.8, yl)], M["linha_am"])
    faixa("Ginasio_Linha_Basquete", arco_pts(QX, yl + s * 4.6, 1.8, 0, PI) if s > 0 else arco_pts(QX, yl + s * 4.6, 1.8, PI, 2 * PI), M["linha_am"])
    tres = arco_pts(QX, yl + s * 1.2, 6.0, PI, 0, 30) if s > 0 else arco_pts(QX, yl + s * 1.2, 6.0, PI, 2 * PI, 30)
    faixa("Ginasio_Linha_Basquete", [(QX - 6.0, yl)] + tres + [(QX + 6.0, yl)], M["linha_am"])
faixa("Ginasio_Linha_Basquete", arco_pts(QX, QY, 1.8, 0, 2 * PI, 32), M["linha_am"])
# volei (azul): 9 x 18 centrada, linhas de ataque a 3 m da rede
vx0, vx1, vy0, vy1 = QX - 4.5, QX + 4.5, QY - 9.0, QY + 9.0
faixa("Ginasio_Linha_Volei", [(vx0, vy0), (vx1, vy0), (vx1, vy1), (vx0, vy1)], M["linha_az"], z=ZQ + .006, fechado=True)
for dy in (-3.0, 3.0): faixa("Ginasio_Linha_Volei", [(vx0, QY + dy), (vx1, QY + dy)], M["linha_az"], z=ZQ + .006)
for sx in (-1, 1):                                              # postes de volei (sem rede, encaixados no piso)
    cyl("Ginasio_Poste_Volei", .045, .045, 2.55, (QX + sx * 5.2, QY, ZQ + 1.275), M["metal"], C_SOLTO, seg=10)
# traves de futsal com rede e tabelas de basquete atras do fundo
for s, yl in ((1, qy0), (-1, qy1)):
    for dx in (-1.5, 1.5):
        box("Ginasio_Trave", (.08, .08, 2.0), (QX + dx, yl, ZQ + 1.0), M["branco"], C_SOLTO)
        barra("Ginasio_Trave_Fundo", (QX + dx, yl, ZQ + 2.0), (QX + dx, yl - s * .9, ZQ), .015, M["metal"], C_SOLTO, seg=6)
    box("Ginasio_Trave_Travessao", (3.08, .08, .08), (QX, yl, ZQ + 2.0), M["branco"], C_SOLTO)
    malha("Ginasio_Rede", [(QX - 1.5, yl, ZQ + 2.0), (QX + 1.5, yl, ZQ + 2.0), (QX + 1.5, yl - s * .9, ZQ), (QX - 1.5, yl - s * .9, ZQ)], [(0, 1, 2, 3)], M["rede"], C_SOLTO)
    yp = yl - s * 1.25                                          # poste da tabela, fora da area de jogo
    box("Ginasio_Basquete_Poste", (.18, .18, 3.5), (QX, yp, ZQ + 1.75), M["grafite"], C_SOLTO)
    box("Ginasio_Basquete_Braco", (.12, 1.1, .12), (QX, yp + s * .55, ZQ + 3.3), M["grafite"], C_SOLTO)
    box("Ginasio_Basquete_Tabela", (1.8, .04, 1.05), (QX, yp + s * 1.1, ZQ + 3.38), M["tabela"], C_SOLTO)
    for zq in (3.15, 3.63): box("Ginasio_Basquete_Quadro", (.59, .045, .03), (QX, yp + s * 1.1, ZQ + zq), M["preto"], C_SOLTO)
    for dx in (-.28, .28): box("Ginasio_Basquete_Quadro", (.03, .045, .48), (QX + dx, yp + s * 1.1, ZQ + 3.39), M["preto"], C_SOLTO)
    torno("Ginasio_Basquete_Aro", [(.225, 3.05), (.245, 3.05), (.245, 3.07), (.225, 3.07), (.225, 3.05)], M["aro"], C_SOLTO, pos=(QX, yp + s * 1.1 + s * .26, ZQ), seg=20)
# arquibancada de concreto (4 degraus de 0,45 x 0,80) ao longo do lado leste, com escada lateral e guarda-corpo
for k in range(4):
    box("Ginasio_Arquibancada", (.8, 18.0, .45 * (k + 1)), (51.7 + .8 * k + .4, QY, FZ + .45 * (k + 1) / 2), M["concreto"], C_PAT)
for k in range(8): box("Ginasio_Arquibancada_Escada", (.4, 1.0, .225 * (k + 1)), (51.7 + .4 * k + .2, QY + 9.5, FZ + .225 * (k + 1) / 2), M["concreto"], C_PAT)
barra("Ginasio_Arquibancada_Guarda_Corpo", (54.9, QY - 9.0, FZ + 2.9), (54.9, QY + 10.0, FZ + 2.9), .025, M["grafite"], C_SOLTO, seg=8)
for k in range(8): barra("Ginasio_Arquibancada_Montante", (54.9, QY - 9.0 + k * 2.7, FZ + 1.8), (54.9, QY - 9.0 + k * 2.7, FZ + 2.9), .02, M["grafite"], C_SOLTO, seg=6)
bloqueio("Bloqueio_Arquibancada", (3.3, 19.0, 1.8), (53.35, QY + .5, FZ + .9))
H_G = 6.5                                                        # altura dos pilares (ESTIMADA)
for k in range(6):
    y = GY0 + k * (GY1 - GY0) / 5
    for x in (GX0, GX1): box("Ginasio_Pilar", (.5, .5, H_G), (x, y, FZ + H_G / 2), M["branco_fach"], C_PAT)
    box("Ginasio_Viga", (GX1 - GX0, .4, .5), ((GX0 + GX1) / 2, y, FZ + H_G - .25), M["branco_fach"], C_PAT)
n_arco = 14                                                      # cobertura em arco (telha metalica), em faixas
for i in range(n_arco):
    a0, a1 = PI * i / n_arco, PI * (i + 1) / n_arco; R = (GX1 - GX0) / 2
    xa, za = (GX0 + GX1) / 2 - R * math.cos(a0), H_G + 2.2 * math.sin(a0); xb, zb = (GX0 + GX1) / 2 - R * math.cos(a1), H_G + 2.2 * math.sin(a1)
    corda = math.hypot(xb - xa, zb - za)                         # placa com espessura (plano simples saia preto no lightmap)
    box("Ginasio_Cobertura", (corda + .02, GY1 - GY0 + 1.2, .06), ((xa + xb) / 2, (GY0 + GY1) / 2, FZ + (za + zb) / 2), M["telha"], C_PAT, rot=(0, -math.atan2(zb - za, xb - xa), 0))
box("Ginasio_Mureta", (.2, GY1 - GY0, 1.0), (GX0, (GY0 + GY1) / 2, FZ + .5), M["branco_fach"], C_PAT)
# --- biblioteca (terceiro volume): predio OCTOGONAL de um pavimento (o decreto de tombamento cita "as bibliotecas octogonais"), faixa de janelas e beiral
BXc, BYc, BR = -44.0, -27.0, 6.5
torno("Biblioteca_Parede", [(BR, FZ), (BR, FZ + 1.0)], M["branco_fach"], C_PAT, pos=(BXc, BYc, 0), seg=8)
torno("Biblioteca_Janelas", [(BR - .05, FZ + 1.0), (BR - .05, FZ + 2.6)], M["vidro"], C_SOLTO, pos=(BXc, BYc, 0), seg=8)
torno("Biblioteca_Parede_Alta", [(BR, FZ + 2.6), (BR, FZ + 3.6)], M["branco_fach"], C_PAT, pos=(BXc, BYc, 0), seg=8)
for k in range(8):
    a = 2 * PI * k / 8; box("Biblioteca_Montante", (.12, .25, 1.6), (BXc + BR * math.cos(a), BYc + BR * math.sin(a), FZ + 1.8), M["branco_fach"], C_SOLTO, rot=(0, 0, a))
torno("Biblioteca_Laje", [(0, FZ + 3.6), (BR + 1.2, FZ + 3.6), (BR + 1.2, FZ + 3.9), (0, FZ + 3.9)], M["branco_fach"], C_PAT, pos=(BXc, BYc, 0), seg=8)
torno("Biblioteca_Interior", [(BR - .4, FZ + .1), (BR - .4, FZ + 3.5)], M["escuro"], C_PAT, pos=(BXc, BYc, 0), seg=8)
box("Biblioteca_Porta", (.06, 1.8, 2.2), (BXc + BR * math.cos(PI / 8) + .03, BYc, FZ + 1.1), M["porta_ferro"], C_PAT)
texto("Biblioteca_Placa", "BIBLIOTECA", .22, (BXc + BR * math.cos(PI / 8) + .08, BYc, FZ + 3.1), "+x", M["texto_az"], C_SOLTO)
bloqueio("Bloqueio_Biblioteca", (BR * 1.6, BR * 1.6, 3.6), (BXc, BYc, FZ + 1.8))

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
else:
    say("aviso: modelos/carros/perua.glb nao encontrado; cena sem viatura")

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
ponto("Aluno_Sala", 6.65, 15.9, (-1, 0)); ponto("Aluno_Banheiro", -13.6, 16.2, (1, 0)); ponto("Aluno_Corredor", -14.5, 11.6, (1, 0))
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
camera("Camera_Rampa", (22.0, 14.0, FZ + 1.6), (34.0, 14.0, FZ + 2.6), 16)
camera("Camera_Pav1", (11.5, 11.0, Z1 + 1.6), (38.0, 11.0, Z1 + 1.2), 15)
camera("Camera_Sala_201", (19.4, 8.8, Z1 + 1.6), (10.5, 3.0, Z1 + 1.0), 14)
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
bpy.data.collections.remove(C_TMP)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "ciep.blend"))
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in scene.objects if o.type == "MESH")
say("cena salva: %d objetos, %d triangulos (antes da otimizacao)" % (len(scene.objects), tris))
say("medidas ESTIMADAS: %s" % MEDIDAS_ESTIMADAS)
