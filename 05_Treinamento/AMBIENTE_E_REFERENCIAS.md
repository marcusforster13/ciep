# Ambiente: o que veio de onde

## Do projeto-padrão dos CIEPs (não é levantamento do Tancredo Neves)

| Elemento no modelo | Referência |
|---|---|
| Bloco principal longo, 3 pavimentos, malha de pilares em módulos | PRO192-ALB-107.03 (plantas do 1º e 2º pavimentos) |
| Corredor central com salas dos dois lados; área de direção e pedagogia no térreo | PRO192-ALB-107.03 ("área destinada à direção e pedagogia") |
| Janelas em arco arredondado, uma por módulo, com peitoril pintado | PRO192-ALB-254.02 e foto "ft ciep 02" |
| Sequência de cores dos peitoris (1006, 1038, 1070, 1035) | PRO192-ALB-254.02 ("cores concretina"); **os tons são estimados** |
| Paredes de alvenaria do corredor em azul 1070; colunas em concreto aparente | PRO192-ALB-254.02 (anotação manuscrita); tom estimado |
| Arcadas no térreo | foto "ft ciep 02" |
| Passarela coberta com pórticos em arco | foto "ft ciep 02" |
| Rampa no centro do bloco | PRO192-ALB-107.03 (marcação central); modelada só como volume, com acesso fechado |
| Platibanda com nervuras verticais | foto "ft ciep 02" |

## Da unidade Tancredo Neves

| Elemento | Referência |
|---|---|
| Aparência geral da fachada, pátio aberto, letreiro com o nome sobre o térreo | foto de Leonardo Finotti (Arquitectura Viva), identificada como desta unidade |

A Figura 28 da dissertação da UFAL (plantas do Tancredo Neves) **não estava no pacote**: a distribuição interna do térreo
(recepção, direção, banheiro, sala 104) é uma **proposta de produção**, não a configuração real da unidade.

## Medidas — todas ESTIMADAS (nenhuma é oficial)

| Medida | Valor no modelo | Como foi estimada |
|---|---|---|
| Comprimento do bloco | 100 m (20 módulos de 5 m) | o desenho anota "100" junto à planta; módulo de 5 m pelas cotas "5 · 5" |
| Profundidade do bloco | 17 m | proporção da planta |
| Altura entre pavimentos | 3,8 m | proporção da foto |
| Galeria do térreo | 3 m | proporção |
| Corredor central | 3 m | proporção da planta |
| Janela arredondada | 3,9 × 2,55 m, raio 0,75 m | ~78% do módulo, pela foto |
| Passarela | 6 m de largura, pórticos a cada 5 m | foto |
| Muro | 2,4 m | adotado |

Os valores estão em `ciep.py` (bloco `MEDIDAS_ESTIMADAS`) e gravados no `.blend`. Trocar por medidas confirmadas é só mudar as constantes no início da seção "CIEP".

## Área jogável e desempenho em VR

Acessíveis: rua, portão e portaria, pátio, passarela, galeria, recepção, sala da direção, trecho de 30 m do corredor central,
banheiro masculino e sala 104. O resto do prédio é só volume externo (interiores fechados com portas e blocos escuros).
Cena otimizada: cerca de 100 mil triângulos, 30 malhas, colisão por caixas, iluminação pré-calculada por área.
