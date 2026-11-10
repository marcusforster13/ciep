// A mensagem (CIEP) - gera as vozes dos personagens no ElevenLabs (mesmo esquema do Cassino clandestino).
//
//   node 06_Audio/gerar_vozes_elevenlabs.js --listar   (so lista as falas e quantos caracteres vao ser gastos)
//   node 06_Audio/gerar_vozes_elevenlabs.js            (gera so o que falta)
//
// Chave: 06_Audio/chave_elevenlabs.txt (fora do GitHub), ou a do Busca e Apreensao, ou ELEVENLABS_API_KEY.
// As falas saem do cenario (05_Treinamento/cenario_ms_01.json) e de algumas frases fixas do motor (treinamento.js).
// O site acha o audio pelo TEXTO exato da fala (catalogo vozes.falas gravado no cenario).
const fs = require('fs'), path = require('path');
const AQUI = __dirname, RAIZ = path.join(AQUI, '..');
const BRUTOS = path.join(AQUI, 'brutos'), WEB_AUDIO = path.join(RAIZ, '04_ThreeJS', 'web', 'audio');
const CENARIOS = [path.join(RAIZ, '05_Treinamento', 'cenario_ms_01.json'), path.join(RAIZ, '04_ThreeJS', 'web', 'treinamento', 'cenario_ms_01.json')];
const API = 'https://api.elevenlabs.io/v1', MODELO = 'eleven_multilingual_v2';

// rádio, parceiro e apoio: as mesmas vozes do Cassino clandestino (a equipe é a mesma na série)
const FIXAS = { funcionario: 'TY3h8ANhQUsJaa0Bga5F', radio: 'FhdOWgf0bSw3HKWefhlq', parceiro: 'czvzJwIVS2asEKnthV40', apoio: 'blPx0tvsvee8CuFd63lX',
  // missao Sala 201 (crise com refens): todas vozes brasileiras da conta, com o tom de tensao de cada papel
  lucas: 'lvkgCBi6spByiTZMPJEK', diretora_crise: '7iqXtOF3wl3pomwXFY7G', mae: 'cyD08lEy76q03ER1jZ7y', pai: 'hwnuNyWkl9DjdTFykrN6',
  negociador: 'bJrNspxJVFovUxNBQ0wh', comandante: 'Qrdut83w0Cr152Yb4Xn3', reporter: 'qPfM2laM0pRL4rrZtBGl' };
const PERFIL = {
  radio:       { nome: 'Sala de operações (rádio)', genero: 'male', idade: ['middle_aged', 'middle aged'], estilo: { stability: .7, similarity_boost: .8, style: .05 } },
  parceiro:    { nome: 'Policial parceiro', genero: 'male', idade: ['young', 'middle_aged'], estilo: { stability: .6, similarity_boost: .8, style: .1 } },
  apoio:       { nome: 'Policial de apoio', genero: 'male', idade: ['middle_aged', 'young'], estilo: { stability: .6, similarity_boost: .8, style: .1 } },
  inspetora:   { nome: 'Funcionária da portaria', genero: 'female', idade: ['middle_aged', 'middle aged', 'old'], estilo: { stability: .45, similarity_boost: .8, style: .3 } },
  diretora:    { nome: 'Diretora', genero: 'female', idade: ['middle_aged', 'middle aged'], estilo: { stability: .5, similarity_boost: .8, style: .25 } },
  responsavel: { nome: 'Responsável (pai de aluna)', genero: 'male', idade: ['middle_aged', 'middle aged'], estilo: { stability: .35, similarity_boost: .8, style: .5 } },
  aluno:       { nome: 'Lucas (aluno)', genero: 'male', idade: ['young'], estilo: { stability: .4, similarity_boost: .8, style: .4 } },
  lucas:       { nome: 'Lucas (aluno, 15 anos)', genero: 'male', idade: ['young'], estilo: { stability: .3, similarity_boost: .8, style: .55 } },          // agitado, instavel
  diretora_crise: { nome: 'Diretora', genero: 'female', idade: ['middle_aged'], estilo: { stability: .35, similarity_boost: .8, style: .45 } },        // aflita
  mae:         { nome: 'Mãe do Lucas', genero: 'female', idade: ['middle_aged'], estilo: { stability: .3, similarity_boost: .8, style: .55 } },            // desesperada
  pai:         { nome: 'Pai de aluna', genero: 'male', idade: ['middle_aged'], estilo: { stability: .3, similarity_boost: .8, style: .55 } },              // nervoso
  negociador:  { nome: 'Negociador (BOPE)', genero: 'male', idade: ['middle_aged'], estilo: { stability: .7, similarity_boost: .8, style: .05 } },         // calmo, firme
  comandante:  { nome: 'Comandante da cena (BOPE)', genero: 'male', idade: ['middle_aged'], estilo: { stability: .65, similarity_boost: .8, style: .15 } },
  reporter:    { nome: 'Repórter (TV)', genero: 'male', idade: ['middle_aged'], estilo: { stability: .55, similarity_boost: .8, style: .2 } },
  funcionario: { nome: 'Seu Jorge (inspetor de corredor)', genero: 'male', idade: ['old', 'middle_aged', 'middle aged'], estilo: { stability: .5, similarity_boost: .8, style: .25 } },
};

function falasDoCenario() {
  const c = JSON.parse(fs.readFileSync(CENARIOS[0], 'utf8')), F = c.falas, E = c.exploracao, lista = [];
  const add = (quem, t, quando) => { if (typeof t === 'string' && t) lista.push({ quem, texto: t, quando }); };
  const todos = (quem, obj, quando) => Object.values(obj || {}).forEach(t => typeof t === 'string' ? add(quem, t, quando) : todos(quem, t, quando));
  for (const [k, t] of Object.entries(c.radio)) typeof t === 'string' ? add('radio', t, 'Rádio: ' + k) : todos('radio', t, 'Rádio: ' + k);
  add('parceiro', c.equipe.pm_parceiro, 'Conversa'); todos('parceiro', F.parceiro, 'Parceiro');
  add('apoio', c.equipe.pm_apoio, 'Conversa');
  for (const k of ['inspetora', 'diretora', 'responsavel', 'aluno', 'funcionario']) { add(k, E[k], 'Modo livre'); todos(k, F[k], k); }
  add('diretora', 'Certo. Vou fazer o comunicado e ligar para o Conselho Tutelar.', 'Orientação à escola');      // frases fixas do motor
  add('aluno', 'Ninguém nunca perguntou... Tá bom. Eu vou com o senhor.', 'Acolhimento');
  // missao Sala 201: so falas de personagens (as do participante sao dele, sem voz gravada)
  const cr = JSON.parse(fs.readFileSync(path.join(RAIZ, '05_Treinamento', 'cenario_crise_01.json'), 'utf8')), FC = cr.falas;
  for (const [k, t] of Object.entries(cr.radio)) add('radio', t, 'Crise · rádio: ' + k);
  const quem = { diretora: 'diretora_crise', parceiro: 'parceiro', pai: 'pai', comandante: 'comandante', negociador: 'negociador', mae: 'mae', imprensa: 'reporter', lucas: 'lucas', bope: 'comandante' };
  for (const [k, t] of Object.entries(FC)) { const pre = k.split('_')[0]; if (quem[pre]) add(quem[pre], t, 'Crise · ' + k); }
  for (const t of Object.values(cr.respostas_porta || {})) add('lucas', t, 'Crise · porta');
  for (const l of Object.values(cr.negociacao.aberturas_lucas)) l.forEach(t => add('lucas', t, 'Crise · negociação'));
  for (const e of Object.values(cr.negociacao.exigencias)) add('lucas', e.lucas, 'Crise · exigência');
  add('diretora_crise', 'Policial! Aqui! É na 201!', 'Crise · chegada');
  return lista;
}
function montarFalas() {
  const cont = {}, visto = new Set(), saida = [];
  for (const f of falasDoCenario()) {
    if (visto.has(f.texto)) continue; visto.add(f.texto);
    cont[f.quem] = (cont[f.quem] || 0) + 1;
    saida.push({ ...f, arquivo: `fala_${f.quem}_${String(cont[f.quem]).padStart(2, '0')}`, personagem: PERFIL[f.quem].nome });
  }
  return saida;
}
function chave() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY.trim();
  for (const f of [path.join(AQUI, 'chave_elevenlabs.txt'), 'C:/Users/marcus.leite/Desktop/buscaeapreensao/06_Audio/chave_elevenlabs.txt'])
    if (fs.existsSync(f)) return fs.readFileSync(f, 'utf8').trim();
  console.error('Falta a chave: crie 06_Audio/chave_elevenlabs.txt.'); process.exit(1);
}
let KEY = null;
async function api(rota, op = {}) {
  const r = await fetch(API + rota, { ...op, headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json', ...(op.headers || {}) } });
  if (!r.ok) throw new Error(`${rota}: ${r.status} ${(await r.text()).slice(0, 300)}`);
  return r;
}
async function escolherVozes(quem) {
  const arq = path.join(AQUI, 'vozes_elevenlabs.json');
  const salvas = { ...FIXAS, ...(fs.existsSync(arq) ? JSON.parse(fs.readFileSync(arq, 'utf8')) : {}) };
  if (!quem.every(k => salvas[k])) {
    const { voices } = await (await api('/voices')).json();
    const lab = v => v.labels || {}, br = v => /brazil|portug|pt-br|brasil/i.test(JSON.stringify(lab(v)) + ' ' + (v.name || '') + ' ' + (v.description || ''));
    const usadas = new Set(Object.values(salvas));
    for (const k of quem) {
      if (salvas[k]) continue; const p = PERFIL[k];
      const nota = v => (lab(v).gender === p.genero ? 10 : 0) + (p.idade.includes(lab(v).age) ? 4 - p.idade.indexOf(lab(v).age) : 0) + (br(v) ? 100 : 0) + (usadas.has(v.voice_id) ? -8 : 0);
      const m = [...voices].sort((a, b) => nota(b) - nota(a))[0];
      salvas[k] = m.voice_id; usadas.add(m.voice_id);
      console.log(`  ${k.padEnd(12)} -> ${m.name} (${[lab(m).gender, lab(m).age, lab(m).accent].filter(Boolean).join(', ')})`);
    }
  }
  fs.writeFileSync(arq, JSON.stringify(salvas, null, 1));
  return salvas;
}
(async () => {
  const falas = montarFalas();
  const faltam = falas.filter(f => !fs.existsSync(path.join(BRUTOS, f.arquivo + '.mp3')));
  const chars = faltam.reduce((a, f) => a + f.texto.length, 0);
  if (process.argv.includes('--listar')) {
    for (const f of falas) console.log(`${f.arquivo.padEnd(22)} ${f.texto}`);
    console.log(`\n${falas.length} falas; faltam ${faltam.length}, que gastam ${chars} caracteres.`); return;
  }
  KEY = chave(); fs.mkdirSync(BRUTOS, { recursive: true }); fs.mkdirSync(WEB_AUDIO, { recursive: true });
  console.log(`${falas.length} falas; faltam ${faltam.length} (${chars} caracteres).`);
  const vozes = await escolherVozes([...new Set(falas.map(f => f.quem))]);
  let feitas = 0, erro = null;
  for (const f of falas) {
    const destino = path.join(BRUTOS, f.arquivo + '.mp3');
    if (!fs.existsSync(destino) && !erro) {
      try {
        const r = await api(`/text-to-speech/${vozes[f.quem]}?output_format=mp3_44100_128`, { method: 'POST', headers: { Accept: 'audio/mpeg' },
          body: JSON.stringify({ text: f.texto, model_id: MODELO, language_code: 'pt', voice_settings: { ...PERFIL[f.quem].estilo, use_speaker_boost: true } }) });
        fs.writeFileSync(destino, Buffer.from(await r.arrayBuffer())); feitas++; console.log(`  ${f.arquivo}: ${f.texto.slice(0, 60)}`);
      } catch (e) { erro = e; }                              // (cota acabou etc.): para de gerar, mas cataloga o que ja existe
    }
    if (fs.existsSync(destino)) fs.copyFileSync(destino, path.join(WEB_AUDIO, f.arquivo + '.mp3'));
  }
  falas.splice(0, falas.length, ...falas.filter(f => fs.existsSync(path.join(BRUTOS, f.arquivo + '.mp3'))));      // so as gravadas entram no catalogo
  const man = path.join(WEB_AUDIO, 'manifest.json');
  const lista = new Set(fs.existsSync(man) ? JSON.parse(fs.readFileSync(man, 'utf8')) : []);
  for (const f of falas) lista.add(f.arquivo + '.mp3');
  fs.writeFileSync(man, JSON.stringify([...lista].sort()));
  for (const c of CENARIOS) {
    const cen = JSON.parse(fs.readFileSync(c, 'utf8'));
    cen.vozes = { _nota: 'Gerado por 06_Audio/gerar_vozes_elevenlabs.js. O site acha o áudio pelo texto exato da fala.', falas: falas.map(f => ({ arquivo: f.arquivo, personagem: f.personagem, quando: f.quando || '', texto: f.texto })) };
    fs.writeFileSync(c, JSON.stringify(cen, null, 2) + '\n');
  }
  console.log(`Pronto: ${feitas} audios novos; ${falas.length} falas gravadas no catalogo.` + (erro ? `\nParou antes do fim: ${erro.message.slice(0, 200)}` : ''));
})().catch(e => { console.error('Erro:', e.message); process.exit(1); });
