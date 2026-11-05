# A mensagem — ocorrência em uma escola (treinamento em realidade virtual)

A direção de uma escola recebeu um print com uma suposta ameaça de ataque. O policial chega com o parceiro e encontra uma
funcionária preocupada, um responsável exaltado e relatos contraditórios. A origem, o contexto e a atualidade da mensagem
precisam ser verificados por conversas, observação e consulta a informações (print, câmeras, frequência, livro de
ocorrências, sala de operações). Quinto treinamento da série (depois de *A Casa em Silêncio*, *Operação Lei Seca*,
*Cassino clandestino* e *Busca e Apreensão*), com a mesma arquitetura.

**Status:** rascunho para validação com instrutores. Os itens marcados `validar` dependem de norma interna e de confirmação jurídica.

**Conteúdo sensível:** ameaça em escola; em uma das variações há um aluno armado e disparos. Não há cenas de violência
contra crianças: os alunos ficam abrigados nas salas, fora de cena. Situação fictícia; pessoas e mensagens inventadas.

## O que o aluno treina

1. Chegada: rádio, portaria, redução de tensão com o responsável exaltado (que pode filmar).
2. Verificação: print (data, remetente, detalhes concretos), câmeras, frequência, livro de ocorrências, consulta à central.
3. Contato com o adolescente: abordagem calma, conversa reservada com a direção, família, sem expor, sem busca ou acesso ao celular indevidos.
4. Ameaça ativa (só numa variação): comunicação, abrigamento, ir até a ameaça, ordem verbal, força proporcional, socorro, arma preservada.
5. Decisão e encerramento: conclusão compatível com os fatos verificados, registro e orientação à escola.

**Variações sorteadas** (a conduta correta muda): mensagem antiga que voltou a circular · aluno escreveu como "brincadeira" ·
aluno em sofrimento, alvo de intimidação · ameaça real com aluno armado. O responsável se acalma ou filma; na ameaça real, o
aluno obedece à ordem verbal ou aponta a arma. Nada na interface revela a variação: só os fatos que o policial verificou.

Modos: exploração (cena livre), história (4 ocorrências guiadas), treino (objetivos e dicas), avaliação (sem dicas) e
treino de ameaça ativa (começa na recepção). Relatório com nota, erros, falhas graves, fatos verificados e base legal (download em JSON).

Variações forçadas pelo endereço, para o instrutor: `?v=origem:conflito,responsavel:filma` ou `?v=origem:ameaca_real,desfecho:aponta`.

## Controles

| | Computador | Meta Quest |
|---|---|---|
| Andar / olhar | W A S D · arrastar o mouse | analógico esquerdo anda · direito gira |
| Falar, abrir, consultar | clique | gatilho |
| Menu (rádio, checklist, fatos verificados, encerrar) | T | botão Y ou B |
| Sacar ou guardar a arma | Q (com ela na mão, o clique dispara; o primeiro clique no agressor dá a ordem verbal) | botão A (gatilho direito dispara) |
| Recarregar | R | apertar o analógico direito |
| Lanterna | F | grip |

## Pastas

| Pasta | Conteúdo |
|---|---|
| `01_Cena_Render_Cycles/` | `ciep.py` **gera a cena inteira** (`ciep.blend` é refeito a cada `recriar`), `aplicar_texturas_cc0.py`, `renderizar_previa.py`, `modelos/` (viatura, Poly Haven) |
| `02_Cena_VR_Otimizada/` | `otimizar_para_vr.py`: versão para Unity/Unreal e colisão |
| `04_ThreeJS/` | `pipeline_threejs.py` (lightmaps e exportação), `texturas_cc0/`, `web/` (o site) |
| `05_Treinamento/` | `cenario_ms_01.json` (toda a mecânica), `ROTEIRO_TREINAMENTO.md`, `AMBIENTE_E_REFERENCIAS.md` |
| `06_Audio/` | sons (`brutos/`) |
| `07_Personagens/` | conversor dos avatares Rocketbox (avatares em `Desktop\leiseca\07_Personagens\rocketbox`) |
| `_referencias/` | pacote de referências do CIEP (fora do Git: os materiais têm direitos das fontes) |

## Como refazer

```
.\atualizar_tudo.ps1 recriar alta
python carimbar_versao.py      (com o Python do Blender)
```

## Publicação

O Vercel publica a pasta `04_ThreeJS/web` a cada envio ao GitHub (`vercel.json`). No projeto do Vercel, desligue
*Settings → Deployment Protection → Vercel Authentication*, senão o site pede login e não abre no Quest.

## Créditos

Ver `CREDITOS.md`.
