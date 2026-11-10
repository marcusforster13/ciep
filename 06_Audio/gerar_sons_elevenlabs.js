// Sons de ambiente e de efeito gerados no ElevenLabs (Sound Effects). Uso: node 06_Audio/gerar_sons_elevenlabs.js
// Pula os arquivos que ja existem em 06_Audio/brutos (retomavel). A chave nunca e impressa.
const fs = require('fs'), path = require('path');
const AQUI = __dirname, DST = path.join(AQUI, 'brutos');
let KEY = process.env.ELEVENLABS_API_KEY || '';
for (const f of [path.join(AQUI, 'chave_elevenlabs.txt'), 'C:/Users/marcus.leite/Desktop/buscaeapreensao/06_Audio/chave_elevenlabs.txt'])
  if (!KEY && fs.existsSync(f)) KEY = fs.readFileSync(f, 'utf8').trim();
if (!KEY) { console.error('Falta a chave.'); process.exit(1); }

const SONS = [
  ['amb_patio_escola', 22, true, 'Distant school playground ambience during recess, many children playing, laughing and chatting far away outdoors, light breeze, birds, no music, no speech in focus'],
  ['amb_tensao_crise', 22, true, 'Tense quiet empty school building room tone, distant muffled city traffic, low electrical hum, occasional faint creak, very sparse, no music'],
  ['ventilador_parede', 12, true, 'Old oscillating wall fan running steadily, soft motor hum and air whoosh, slight rattle of the metal grille, indoor'],
  ['choro_crianca_baixo', 14, true, 'Muffled quiet sobbing and frightened whispering of several children heard through a closed classroom door, distant and soft'],
  ['sinal_escola', 6, false, 'Electric school bell ringing in a concrete corridor, continuous loud ring for a few seconds then stops'],
  ['gritos_criancas_susto', 6, false, 'Sudden frightened screams of a group of children heard from an upper floor classroom of a school, short panicked yelling then running footsteps, distant and reverberant, no words'],
  ['sirene_longe', 14, false, 'Police car siren approaching from far away in a city, getting closer and louder, Brazilian two-tone siren'],
];

(async () => {
  fs.mkdirSync(DST, { recursive: true });
  for (const [nome, dur, loop, texto] of SONS) {
    const arq = path.join(DST, nome + '.mp3');
    if (fs.existsSync(arq)) { console.log('ja existe', nome); continue; }
    const corpo = { text: texto, duration_seconds: dur, prompt_influence: .45 };
    if (loop) Object.assign(corpo, { loop: true, model_id: 'eleven_text_to_sound_v2' });
    let r = await fetch('https://api.elevenlabs.io/v1/sound-generation', { method: 'POST', headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) });
    if (!r.ok && loop) {                                           // conta sem o modelo com loop: gera sem loop
      console.log(nome, 'sem loop:', r.status, (await r.text()).slice(0, 160));
      r = await fetch('https://api.elevenlabs.io/v1/sound-generation', { method: 'POST', headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json' }, body: JSON.stringify({ text: texto, duration_seconds: dur, prompt_influence: .45 }) });
    }
    if (!r.ok) { console.log('ERRO', nome, r.status, (await r.text()).slice(0, 200)); continue; }
    fs.writeFileSync(arq, Buffer.from(await r.arrayBuffer()));
    console.log('ok', nome, fs.statSync(arq).size, 'bytes');
  }
})();
