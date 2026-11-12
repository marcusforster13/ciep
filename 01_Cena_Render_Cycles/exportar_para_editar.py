"""CIEP - exporta as pecas modeladas por codigo (low poly) para o autor refazer.
Uso:  blender -b ciep.blend --python exportar_para_editar.py      (nao salva a cena)
Saida: 08_Para_Editar/<peca>.glb  (cada peca centrada em X/Y, base no chao, na orientacao em que esta na escola)
Para devolver: salve a versao nova com o MESMO nome em 01_Cena_Render_Cycles/modelos/<peca>_realista.glb,
mesmo tamanho, mesma frente e base no chao."""
import bpy, os
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(AQUI, "..", "08_Para_Editar")); os.makedirs(OUT, exist_ok=True)

# arquivo: (como achar, raio do grupo em metros)
#   "data:<nome>"  = pecas instanciadas (a malha compartilhada)  |  "pre:<inicio do nome>" = objetos pelo nome
PECAS = {
    "carteira_fnde": ("data:Peca_carteira_fnde", 0),
    "mesa_professor": ("data:Peca_mesa_professor", 0),
    "vaso_sanitario": ("data:Peca_vaso", 0),
    "mictorio": ("data:Peca_mictorio", 0),
    "cuba_torneira": ("data:Peca_cuba_torneira", 0),
    "valvula_descarga": ("data:Peca_valvula", 0),
    "divisoria_banheiro": ("data:Peca_divisoria", 0),
    "porta_cabine": ("data:Peca_porta_cabine", 0),
    "bebedouro_inox": ("data:Peca_bebedouro", 0),
    "armario_aco": ("pre:Direcao_Armario", 2.0),
    "estante_sala": ("pre:Sala_201_Estante", 2.5),
    "contentor_lixo": ("pre:Contentor_Lixo", .5),
    "coleta_seletiva": ("pre:Coleta_Seletiva_Patio", 1.5),
    "banco_patio": ("pre:Banco_Patio", 1.4),
    "mural_avisos": ("pre:Mural_Entrada", 1.5),
    "balcao_recepcao": ("pre:Recepcao_Balcao", 1.6),
    "extintor": ("pre:Extintor_Pav1", .8),
    "regador": ("pre:Horta_Regador", .5),
    "papeleira_higienica": ("pre:Banheiro_Papeleira_Higienica", .2),
    "detector_fumaca": ("pre:Corredor_Terreo_Detector_Fumaca", .2),
    "luminaria_regua_led": ("pre:Pav1_Corredor_12_Luz", .9),
    "quadro_branco": ("pre:Sala_201_Quadro", 2.2),
    "porta_corredor": ("pre:Porta_Fechada", .8),
    "poste_led": ("pre:Poste_Patio_0", 7.0),
    "mochila_chao": ("pre:Sala_201_Mochila_Chao", .3), "mochila_item": ("pre:I_Mochila", .5),
    "caderno": ("pre:Sala_201_Caderno", .15), "lapis": ("pre:Sala_201_Lapis", .1),
    "quadro_verde": ("pre:Sala_201_Quadro_Verde", .8), "cesto_lixo_sala": ("pre:Cesto_Sala", .4),
    "cartaz_corredor": ("pre:Corredor_Frente_Cartaz", .4), "mural_corredor": ("pre:Corredor_Frente_Mural", 1.0),
    "lixeira_corredor_cheia": ("pre:Corredor_Lixeira_Cheia", .5), "placa_saida": ("pre:Placa_Saida", .5),
    "telefone": ("pre:I_Telefone", .3), "livro_ocorrencias": ("pre:I_Livro_Ocorrencias", .3),
    "pasta_frequencia": ("pre:I_Pasta_Frequencia", .3), "celular": ("pre:I_Celular_Print", .15),
    "gravador_cameras": ("pre:I_Monitor_Cameras_DVR", .3), "mesa_diretora": ("pre:Direcao_Mesa", 1.2),
    "quadro_avisos_direcao": ("pre:Direcao_Quadro", .8), "espelho_banheiro": ("pre:Banheiro_Espelho", 1.5),
    "saboneteira": ("pre:Banheiro_Saboneteira", .1), "papeleira_toalha": ("pre:Banheiro_Papeleira_Toalha", .2),
    "alcool_gel": ("pre:Banheiro_Alcool_Gel", .15), "lixeira_pedal_banheiro": ("pre:Lixeira_Pedal_Banheiro", .4),
    "tambor_lixo": ("pre:Tambor", .6), "hidrante": ("pre:Hidrante_Caixa", .6), "placa_escola": ("pre:Placa_Escola", 2.5),
    "horta_canteiro": ("pre:Horta_Canteiro_0", 2.0), "placa_horta": ("pre:Horta_Placa", .8),
    "mesa_refeitorio": ("pre:Refeitorio_Mesa", 1.5), "bandeja": ("pre:Refeitorio_Bandeja", .3),
    "cardapio_refeitorio": ("pre:Refeitorio_Cardapio", 1.0), "fogao": ("pre:Cozinha_Fogao", 1.0),
    "geladeira": ("pre:Cozinha_Geladeira", 1.0), "caldeirao": ("pre:Cozinha_Caldeirao", .6), "panela": ("pre:Cozinha_Panela", .3),
    "tabela_basquete": ("pre:Ginasio_Basquete", 2.5), "trave_futsal": ("pre:Ginasio_Trave", 2.5),
}

def centro(o): return sum((o.matrix_world @ Vector(c) for c in o.bound_box), Vector()) / 8
feitos = []
for arq, (regra, raio) in PECAS.items():
    tipo, chave = regra.split(":", 1)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if tipo == "data":
        sel = [o for o in meshes if o.data.name.split(".")[0] == chave][:1]
    else:
        cands = [o for o in meshes if o.name.startswith(chave)]
        if not cands: print("[PARA_EDITAR] nao achei", arq); continue
        c0 = centro(cands[0]); sel = [o for o in cands if (centro(o) - c0).length < raio]
    if not sel: print("[PARA_EDITAR] nao achei", arq); continue
    for o in bpy.data.objects: o.select_set(False)
    pts = [o.matrix_world @ Vector(c) for o in sel for c in o.bound_box]
    desl = Vector(((min(p.x for p in pts) + max(p.x for p in pts)) / 2, (min(p.y for p in pts) + max(p.y for p in pts)) / 2, min(p.z for p in pts)))
    copias = []
    for o in sel:                                           # copias soltas (sem pai), na posicao certa, centradas
        c = o.copy(); c.data = o.data.copy(); bpy.context.scene.collection.objects.link(c)
        c.parent = None; c.matrix_world = o.matrix_world.copy(); c.matrix_world.translation -= desl
        c.select_set(True); copias.append(c)
    bpy.context.view_layer.objects.active = copias[0]
    dst = os.path.join(OUT, arq + ".glb")
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=True, export_apply=True)
    for c in copias: bpy.data.objects.remove(c, do_unlink=True)
    tam = max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts), max(p.z for p in pts) - min(p.z for p in pts)
    feitos.append((arq, len(sel), tam)); print("[PARA_EDITAR] %s: %d pecas, %.2f x %.2f x %.2f m" % (arq, len(sel), *tam))
with open(os.path.join(OUT, "LEIA-ME.txt"), "w", encoding="utf-8") as f:
    f.write("Pecas do CIEP para refazer (exportadas do ciep.blend).\n\n"
            "Como devolver: salve com o mesmo nome + _realista, por exemplo carteira_fnde_realista.glb,\n"
            "mantendo o mesmo tamanho, a mesma frente (como veio) e a base no chao (z = 0), centrada em X e Y.\n"
            "Pode usar texturas embutidas no .glb. Mande as que ficarem prontas, nao precisa ser todas.\n\n")
    for arq, n, t in feitos: f.write("%-24s %2d pecas   %.2f x %.2f x %.2f m (largura x profundidade x altura)\n" % (arq + ".glb", n, *t))
print("[PARA_EDITAR] %d arquivos em %s" % (len(feitos), OUT))
