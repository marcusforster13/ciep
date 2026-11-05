# Ambiente: o que veio de onde

## Da unidade Tancredo Neves (foto de Leonardo Finotti, Arquitectura Viva) — referência principal da aparência

| Elemento no modelo | Como aparece na foto |
|---|---|
| Fachada de concreto pintado de **branco**, lisa | toda a fachada |
| Janelas em arco arredondado, uma por módulo, com persianas claras por dentro | dois pavimentos de janelas |
| Peitoril **vermelho** ou **preto**, alternando de dois em dois | parte de baixo de cada abertura |
| Térreo com arcos abertos (pilotis): vê-se através do prédio | arcos do térreo |
| Rampa no vão do térreo, visível por um dos arcos | terceiro arco da foto |
| Platibanda lisa com juntas verticais e junta horizontal na altura da cobertura | faixa alta da fachada |
| Pátio em placas de concreto claras, em faixas, separadas por juntas de grama; palmeira; poste alto | primeiro plano |

## Do projeto-padrão dos CIEPs (acervo da Fundação Oscar Niemeyer; não é levantamento do Tancredo Neves)

| Elemento | Referência |
|---|---|
| Bloco longo de 3 pavimentos, malha de pilares em módulos | PRO192-ALB-107.03 |
| Área de direção e pedagogia no térreo | PRO192-ALB-107.03 ("área destinada à direção e pedagogia") |
| Corredor com barra azul 1070; colunas e paredes conforme o desenho de cores | PRO192-ALB-254.02 (tom do azul estimado) |
| Passarela coberta com pórticos em arco | foto "ft ciep 02" (outra unidade) |

A Figura 28 da dissertação da UFAL (plantas do Tancredo Neves) **não estava no pacote**: a distribuição do bloco
administrativo (recepção, direção, corredor, banheiro, sala 104) é uma **proposta de produção**.

## Medidas — todas ESTIMADAS (nenhuma é oficial)

Medidas tiradas das proporções da foto do Tancredo Neves, assumindo **módulo de 5 m** (o desenho do projeto-padrão anota "100" no comprimento e "5" nos módulos).

| Medida | Valor no modelo |
|---|---|
| Comprimento do bloco | 100 m (20 módulos de 5 m) |
| Profundidade do bloco | 22 m |
| Altura entre pavimentos | 3,35 m |
| Janela | 3,9 × 2,75 m, cantos com raio de 0,95 m; peitoril colorido de 0,92 m |
| Arco do térreo | 3,9 × 3,0 m, raio 1,35 m |
| Platibanda | 2,0 m acima da cobertura |
| Bloco administrativo do térreo | 40 × 16 m, com galerias de 3 m sob os arcos |
| Recepção · direção | 8 × 7 m cada |
| Corredor central | 3 m de largura, 40 m de comprimento |
| Sala 104 · banheiro masculino | 10 × 6 m · 8 × 6 m |
| Passarela | 6 m de largura, pórticos a cada 5 m |
| Muro | 2,4 m |

Os valores estão em `ciep.py` (constantes no início da seção "CIEP" e `MEDIDAS_ESTIMADAS`, gravadas no `.blend`).

## Texturas (CC0, Poly Haven)

white_stucco (fachada, paredes, peitoris tingidos), granite_tile (piso de granilite), concrete_wall_008 (placas do pátio e
piso dos pilotis), leafy_grass (grama), long_white_tiles (azulejo do banheiro), além das do Cassino clandestino (asfalto,
reboco do muro, madeiras, metal pintado, casca de árvore). As fotos de referência **não** são usadas como textura.

## Área jogável e desempenho em VR

Rua, portão e portaria, pátio, passarela, pilotis (com a rampa), galeria, recepção, direção, corredor central de 40 m,
banheiro masculino e sala 104. Os pavimentos superiores e as demais salas são só volume.
