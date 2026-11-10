/*
  A mensagem - ocorrencia em uma escola: motor do treinamento
  Le treinamento/cenario_ms_01.json (fases, acoes, pontos, falhas graves, variacoes, falas, historia).
  Mesma arquitetura do Cassino clandestino (paineis 3D, legendas, vozes, personagens Rocketbox, arma, relatorio).

  Controles
    Computador: clique = falar / usar / botoes   T = menu   K = checklist   Q = saca ou guarda a arma (clique dispara)   R = recarrega
    Quest:      gatilho = falar / usar / botoes / teleporte   A = saca a arma (gatilho direito dispara; apertar o analogico direito recarrega)
                grip = lanterna   botao Y ou B = menu do treinamento
  Variacoes forcadas pela URL (para o instrutor):  ?v=origem:ameaca_real,desfecho:aponta,responsavel:filma
*/
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

export async function iniciar(ctx) {
  const { scene, camera, rig, renderer, CFG } = ctx;
  const HQ = p => window.__h ? window.__h(p) : p;
  const CEN = await fetch(HQ('treinamento/cenario_ms_01.json')).then(r => r.json());
  const F = CEN.falas, D = CEN.dialogos;
  const V = new THREE.Vector3(), V2 = new THREE.Vector3();

  /* ================= estado ================= */
  const S = { ativo: false, inicio: 0, fim: 0, variacao: {}, feitos: new Map(), erros: [], graves: [], log: [], modo: 'avaliacao', historia: false, fila: [], armaNaMao: false };
  let A = null;
  const HIST = [], npcs = {}, acoes = {};
  CEN.fases.forEach(f => {
    (f.acoes || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'acao' });
    (f.erros || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'erro' });
    (f.falhas_graves || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'grave' });
  });
  const cond1 = c => { const m = c.match(/variacao\.(\w+)\s*(==|!=)\s*'([^']*)'/); if (!m) return true; return m[2] === '==' ? S.variacao[m[1]] === m[3] : S.variacao[m[1]] !== m[3]; };
  const cond = c => !c || c.split('||').some(ou => ou.split('&&').every(cond1));
  const tempo = () => ((S.fim || performance.now()) - S.inicio) / 1000;
  const fmt = s => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const nAt = () => (A ? A.n : HIST.length);
  const real = () => S.variacao.origem === 'ameaca_real';
  function registrar(id, extra = '') {
    const a = acoes[id]; if (!a || !S.ativo || !A) return;
    if (a.tipo === 'acao') { if (S.feitos.has(id) || !cond(a.condicao)) return; S.feitos.set(id, tempo()); }
    else if (a.tipo === 'erro') { if (A.errosFeitos?.has(id + extra)) return; (A.errosFeitos ||= new Set()).add(id + extra); S.erros.push({ id, texto: a.texto, pontos: a.pontos, t: tempo(), extra, atendimento: nAt() }); }
    else { if (S.graves.some(g => g.id === id && g.atendimento === nAt())) return; S.graves.push({ id, texto: a.texto, pontos: a.pontos, base: a.base, t: tempo(), extra, atendimento: nAt() }); legenda('Instrutor', 'Falha grave registrada: ' + a.texto, 5); }
    S.log.push({ t: +tempo().toFixed(1), atendimento: nAt(), id, extra }); status();
  }
  const fato = t => { if (A && !A.fatos.includes(t)) A.fatos.push(t); };

  /* ================= paineis 3D (computador e Quest) ================= */
  const paineis = [];
  class Painel {
    constructor(largura = 1.1) {
      this.largura = largura; this.botoes = [];
      this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ transparent: true, depthTest: false, toneMapped: false, fog: false }));
      this.mesh.renderOrder = 1000; this.mesh.visible = false; scene.add(this.mesh); paineis.push(this);
      this.realce = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0xf0a340, transparent: true, opacity: .32, depthTest: false, toneMapped: false, fog: false }));
      this.realce.renderOrder = 1001; this.realce.visible = false; this.mesh.add(this.realce);
    }
    apontar(ray) {
      if (!this.mesh.visible) return null;
      const h = ray.intersectObject(this.mesh, false)[0]; if (!h) return null;
      const py = (1 - h.uv.y) * this.H, b = this.botoes.find(b => py >= b.y0 && py <= b.y1);
      if (b) { this.realce.position.set(0, .5 - (b.y0 + b.y1) / 2 / this.H, .001); this.realce.scale.set(1 - 2 * 56 / 1024, (b.y1 - b.y0) / this.H, 1); this.realce.visible = true; }
      return h;
    }
    // img: canvas opcional desenhado entre o titulo e o texto (print do celular, imagem das cameras)
    mostrar({ tag = '', titulo = '', texto = '', botoes = [], longe = 1.15, img = null }) {
      const W = 1024, P = 56, cv = document.createElement('canvas'), g = cv.getContext('2d');
      cv.width = W; cv.height = 2400;
      const linhas = (txt, fonte, maxW) => { g.font = fonte; const out = []; for (const par of String(txt).split('\n')) { let l = ''; for (const w of par.split(' ')) { const t = l ? l + ' ' + w : w; if (g.measureText(t).width > maxW && l) { out.push(l); l = w; } else l = t; } out.push(l); } return out; };
      const lt = titulo ? linhas(titulo, '700 46px Segoe UI, sans-serif', W - 2 * P) : [];
      const lx = texto ? linhas(texto, '400 32px Segoe UI, sans-serif', W - 2 * P) : [];
      const lb = botoes.map(b => linhas(b.label, '600 30px Segoe UI, sans-serif', W - 2 * P - 40));
      const iw = img ? Math.min(W - 2 * P, 600 * img.width / img.height) : 0, ih = img ? Math.round(iw * img.height / img.width) + 20 : 0;      // imagem com no maximo 600 px de altura
      let y = P; const H0 = P + (tag ? 40 : 0) + lt.length * 56 + ih + (lx.length ? 16 + lx.length * 44 : 0) + lb.reduce((s, l) => s + 54 + l.length * 38, 0) + P + 10;
      cv.height = Math.min(2400, H0);
      g.fillStyle = 'rgba(11,14,22,.95)'; g.beginPath(); g.roundRect(0, 0, W, cv.height, 22); g.fill();
      g.strokeStyle = 'rgba(240,163,64,.5)'; g.lineWidth = 3; g.stroke();
      if (tag) { g.fillStyle = '#f0a340'; g.font = '500 24px Consolas, monospace'; g.fillText(tag.toUpperCase(), P, y + 22); y += 40; }
      g.fillStyle = '#efe9df'; g.font = '700 46px Segoe UI, sans-serif'; lt.forEach(l => { g.fillText(l, P, y + 44); y += 56; });
      if (img) { y += 10; g.drawImage(img, (W - iw) / 2, y, iw, ih - 20); y += ih - 10; }
      if (lx.length) { y += 16; g.fillStyle = 'rgba(239,233,223,.86)'; g.font = '400 32px Segoe UI, sans-serif'; lx.forEach(l => { g.fillText(l, P, y + 32); y += 44; }); }
      y += 10; this.botoes = [];
      for (const [bi, b] of botoes.entries()) {
        y += 12; const h = 34 + lb[bi].length * 38;
        g.fillStyle = b.cor || 'rgba(240,163,64,.14)'; g.beginPath(); g.roundRect(P, y, W - 2 * P, h, 12); g.fill();
        g.strokeStyle = 'rgba(240,163,64,.55)'; g.lineWidth = 2; g.stroke();
        g.fillStyle = '#efe9df'; g.font = '600 30px Segoe UI, sans-serif';
        lb[bi].forEach((l, li) => g.fillText(l, P + 20, y + 46 + li * 38));
        this.botoes.push({ ...b, y0: y, y1: y + h }); y += h + 8;
      }
      const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
      this.mesh.material.map?.dispose(); this.mesh.material.map = tex; this.mesh.material.needsUpdate = true;
      this.H = cv.height; this.mesh.scale.set(this.largura, this.largura * cv.height / W, 1);
      camera.getWorldPosition(V); camera.getWorldDirection(V2); V2.y = 0; V2.normalize();
      const alto = this.largura * cv.height / W;                 // paineis altos ficam um pouco mais longe, para caber na vista
      this.mesh.position.copy(V).addScaledVector(V2, longe + Math.max(0, alto - .9) * .6); this.mesh.position.y = V.y - .08 - Math.max(0, alto - .9) * .25;
      this.mesh.lookAt(V.x, this.mesh.position.y, V.z); this.mesh.visible = true;
      return this;
    }
    esconder() { this.mesh.visible = false; this.realce.visible = false; }
    clique(ray) {
      if (!this.mesh.visible) return false;
      const h = ray.intersectObject(this.mesh, false)[0]; if (!h) return false;
      const py = (1 - h.uv.y) * this.H, b = this.botoes.find(b => py >= b.y0 && py <= b.y1);
      if (b && b.acao) b.acao();
      return true;
    }
  }
  const menu = new Painel(1.1), dialogo = new Painel(1.15);
  const cursorVR = new THREE.Mesh(new THREE.CircleGeometry(.012, 20), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false, toneMapped: false, fog: false }));
  cursorVR.renderOrder = 1003; cursorVR.visible = false; scene.add(cursorVR);
  function apontar(raios) {
    for (const p of paineis) p.realce.visible = false;
    let ultimo = null;
    const hs = raios.map(r => { let h = null; for (const p of paineis) h = p.apontar(r) || h; if (h) ultimo = h; return h; });
    cursorVR.visible = !!ultimo;
    if (ultimo) { cursorVR.position.copy(ultimo.point); cursorVR.quaternion.copy(ultimo.object.quaternion); cursorVR.translateZ(.002); }
    return hs;
  }
  const fecharPaineis = () => paineis.forEach(p => p.esconder());

  /* legenda presa a camera (VR) ou faixa HTML (computador) */
  const lcv = document.createElement('canvas'); lcv.width = 1400; lcv.height = 200;
  const ltex = new THREE.CanvasTexture(lcv); ltex.colorSpace = THREE.SRGBColorSpace;
  const leg = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 1.0 * 200 / 1400), new THREE.MeshBasicMaterial({ map: ltex, transparent: true, depthTest: false, toneMapped: false, fog: false }));
  leg.position.set(0, -.3, -.95); leg.renderOrder = 1001; leg.visible = false; camera.add(leg);
  let legAte = 0;
  function legenda(quem, texto, seg = 4) {
    const g = lcv.getContext('2d'); g.clearRect(0, 0, 1400, 200);
    g.fillStyle = 'rgba(5,7,12,.82)'; g.beginPath(); g.roundRect(0, 0, 1400, 200, 18); g.fill();
    g.fillStyle = '#f0a340'; g.font = '600 34px Segoe UI, sans-serif'; g.fillText(quem, 36, 54);
    g.fillStyle = '#efe9df'; g.font = '400 38px Segoe UI, sans-serif';
    let l = '', y = 108; for (const w of texto.split(' ')) { const t = l ? l + ' ' + w : w; if (g.measureText(t).width > 1330 && l) { g.fillText(l, 36, y); y += 46; l = w; } else l = t; } g.fillText(l, 36, y);
    ltex.needsUpdate = true; legAte = performance.now() + seg * 1000;
    const vr = renderer.xr.isPresenting; leg.visible = vr;
    const hl = document.getElementById('legendaHTML'); if (hl && !vr) { hl.innerHTML = `<b>${quem}:</b> ${texto}`; hl.hidden = false; }
  }

  /* ================= vozes: gravacao (catalogo vozes.falas) ou voz do navegador, sempre com legenda ================= */
  const VOZ = new Map((CEN.vozes?.falas || []).map(f => [f.texto, f.arquivo]));
  const gravacao = texto => { const a = VOZ.get(texto); return a && window.__som?.tem(a) ? a : null; };
  const espera = ms => new Promise(r => setTimeout(r, ms));
  function vozSintetica(texto, voz = 'f') {
    if (S.voz === false || !('speechSynthesis' in window)) return null;
    const vs = speechSynthesis.getVoices().filter(v => v.lang && v.lang.replace('_', '-').startsWith('pt'));
    if (!vs.length) { if (!S.avisoVoz) { S.avisoVoz = true; console.warn('Sem voz sintética em português neste navegador: só legendas.'); } return null; }
    try {
      const u = new SpeechSynthesisUtterance(texto); u.lang = 'pt-BR';
      const br = vs.filter(v => /BR/i.test(v.lang)), lista = br.length ? br : vs;
      const fem = lista.filter(v => /francisca|thalita|maria|luciana|feminin|female|google/i.test(v.name));
      const mas = lista.filter(v => /antonio|daniel|ricardo|masculin|male/i.test(v.name) && !/female/i.test(v.name));
      u.voice = (voz === 'm' || voz === 'j' ? mas[0] : fem[0]) || lista[(voz === 'm' ? 1 : 0) % lista.length];
      u.pitch = voz === 'j' ? 1.15 : voz === 'm' ? .85 : 1.05; u.rate = voz === 'm' ? 1 : .95;
      return new Promise(r => { u.onend = u.onerror = () => r(); speechSynthesis.speak(u); });
    } catch (e) { return null; }
  }
  if ('speechSynthesis' in window) speechSynthesis.getVoices();
  async function dizer(npc, quem, texto, voz = 'f', gesto = 'falando') {
    const som = window.__som, audio = gravacao(texto);
    const seg = audio ? som.duracao(audio) : Math.max(2.5, texto.length / 13);
    legenda(quem, texto, seg + .6);
    if (npc && gesto && !npc.userData.sentado && !npc.userData.caido) animar(npc, gesto, seg + 1.5);
    if (audio) {
      const med = som.tocar(audio, npc ? npc.position.clone().setY(1.55) : null, true);
      const f = npc && { medidor: typeof med === 'function' ? med : null, sintetica: typeof med !== 'function', ate: performance.now() + seg * 1000 };
      if (npc) npc.userData.fala = f;
      await espera(seg * 1000 + 350); if (npc?.userData.fala === f) npc.userData.fala = null; return;
    }
    const p = vozSintetica(texto, voz);
    const f = npc && { sintetica: true, ate: performance.now() + (p ? seg + 6 : seg) * 1000 };
    if (npc) npc.userData.fala = f;
    await (p ? Promise.race([p, espera(seg * 1000 + 1500)]) : espera(seg * 1000));
    if (npc?.userData.fala === f) npc.userData.fala = null;
    await espera(350);
  }
  const diz = (n, texto, gesto = 'falando') => n ? dizer(n, n.userData.nome, texto, n.userData.voz, gesto) : Promise.resolve();
  const BIP = () => Math.min(.8, window.__som?.duracao('radio_bip') || .4) + .15;
  async function radio(texto) {
    window.__som?.tocar('radio_bip'); await espera(BIP() * 1000);
    await dizer(null, 'Rádio · Sala de operações', texto, 'm', null);
    window.__som?.tocar('radio_bip', null, false, { vol: .35 });
  }
  const voce = (texto, seg = 3) => legenda('Você', texto, seg);

  /* ================= personagens (Rocketbox, MIT); sem o arquivo, boneco simples ================= */
  function boneco(nome, corRoupa, altura = 1.7) {
    const g = new THREE.Group(), s = altura / 1.7; g.name = 'NPC_' + nome;
    const pele = new THREE.MeshStandardMaterial({ color: 0xb98a68, roughness: .7 }), roupa = new THREE.MeshStandardMaterial({ color: corRoupa, roughness: .85 });
    const cap = (r, l, m, x, y) => { const k = new THREE.Mesh(new THREE.CapsuleGeometry(r * s, l * s, 4, 12), m); k.position.set(x * s, y * s, 0); g.add(k); return k; };
    cap(.075, .7, roupa, -.1, .44); cap(.075, .7, roupa, .1, .44); cap(.17, .4, roupa, 0, 1.14); cap(.055, .52, roupa, -.25, 1.1); cap(.055, .52, roupa, .25, 1.1);
    const cab = new THREE.Mesh(new THREE.SphereGeometry(.115 * s, 24, 16), pele); cab.position.set(0, 1.62 * s, 0); g.add(cab);
    const hit = new THREE.Mesh(new THREE.CylinderGeometry(.38, .38, altura, 8), new THREE.MeshBasicMaterial({ visible: false })); hit.position.y = altura / 2; g.add(hit);
    g.userData = { hit, nome };
    return g;
  }
  const modelos = {};
  const PAPEIS_CRISE = /^(refem_|professora|mae|negociador)/;          // so a missao "Sala 201" usa: carregam quando ela comeca
  const manifesto = fetch(HQ('personagens/manifest.json')).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const glP = new GLTFLoader();
  const carregarPapeis = filtro => manifesto.then(man => Promise.all(Object.entries(man).filter(([papel]) => filtro(papel) && !modelos[papel]).map(([papel, info]) => glP.loadAsync(HQ(info.arquivo)).then(g => { modelos[papel] = g; }).catch(() => { }))));
  const modelosProntos = carregarPapeis(p => !PAPEIS_CRISE.test(p));
  // sombra suave sob os personagens (o chao tem luz pre-calculada, entao eles nao projetam sombra): mancha radial escura
  const SOMBRA = (() => {
    const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d');
    const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(0,0,0,0.55)'); gr.addColorStop(.55, 'rgba(0,0,0,0.3)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    return { geo: new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), mat: new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }) };
  })();
  function personagem(papel, nome, cor, altura) {
    const base = modelos[papel];
    if (!base) return boneco(nome, cor, altura);
    const g = new THREE.Group(); g.name = 'NPC_' + nome;
    const m = SkeletonUtils.clone(base.scene);
    m.traverse(o => { if (o.isMesh) o.frustumCulled = false; });
    if (papel === 'aluno') m.scale.setScalar(altura / 1.78);      // sem avatar adolescente: o adulto mais jovem, um pouco menor
    g.add(m);
    const sombra = new THREE.Mesh(SOMBRA.geo, SOMBRA.mat); sombra.scale.setScalar(.75 * altura / 1.75 + .25); sombra.position.y = .015; sombra.renderOrder = 1; g.add(sombra);
    const mixer = new THREE.AnimationMixer(m), acs = {};
    for (const clip of base.animations) acs[clip.name.replace(/\.\d+$/, '')] = mixer.clipAction(clip);
    const parada = acs.parada || Object.values(acs)[0];
    if (parada) { parada.play(); parada.time = Math.random() * parada.getClip().duration; }
    const hit = new THREE.Mesh(new THREE.CylinderGeometry(.42, .42, 1, 10), new THREE.MeshBasicMaterial({ visible: false }));
    hit.scale.y = altura; hit.position.y = altura / 2; g.add(hit);
    g.userData = { hit, nome, mixer, acoes: acs, atual: parada, modelo: m, real: true, rosto: montarRosto(m), olhar: montarOlhar(m) };
    return g;
  }
  function montarRosto(m) {
    const jaw = m.getObjectByName('Bip01_MJaw'); if (!jaw) return null;
    const palp = [['Bip01_REyeBlinkTop', -1.25], ['Bip01_LEyeBlinkTop', -1.25], ['Bip01_REyeBlinkBottom', .35], ['Bip01_LEyeBlinkBottom', .35]]
      .map(([n, k]) => { const b = m.getObjectByName(n); return b && { b, base: b.position.clone(), k }; }).filter(Boolean);
    return { jaw, jawBase: jaw.quaternion.clone(), escrito: null, boca: 0, palp, piscaIni: 0, proxPisca: performance.now() + 1000 + Math.random() * 3000 };
  }
  const QZ = new THREE.Quaternion(), EIXO_Z = new THREE.Vector3(0, 0, 1);
  function montarOlhar(m) {
    let cabeca, pescoco, olhoE, olhoD;
    m.traverse(o => { if (!o.isBone) return; if (/_Head$/.test(o.name)) cabeca = o; else if (/_Neck$/.test(o.name)) pescoco = o; else if (/_LEye$/.test(o.name)) olhoE = o; else if (/_REye$/.test(o.name)) olhoD = o; });
    if (!(cabeca && olhoE && olhoD)) return null;
    const clavs = pescoco ? pescoco.children.filter(b => /Clavicle$/.test(b.name)) : [];
    const ossos = [pescoco, cabeca, ...clavs].filter(Boolean).map(b => ({ b, base: b.quaternion.clone(), escrito: null }));
    m.updateMatrixWorld(true);
    const frenteLocal = new THREE.Vector3(0, 0, 1).applyQuaternion(cabeca.getWorldQuaternion(new THREE.Quaternion()).invert());
    return { cabeca, pescoco, olhoE, olhoD, ossos, clavs, frenteLocal, peso: 0 };
  }
  const OV1 = new THREE.Vector3(), OV2 = new THREE.Vector3(), OV3 = new THREE.Vector3(), OQ1 = new THREE.Quaternion(), OQ2 = new THREE.Quaternion(), OQ3 = new THREE.Quaternion(), OQ0 = new THREE.Quaternion(), AH = new THREE.Vector3();
  function ajustarAreaClique(n) {
    const u = n.userData, cab = u.olhar?.cabeca; if (!cab || !u.hit) return;
    cab.getWorldPosition(AH); const h = Math.max(.6, AH.y - n.position.y + .2); u.hit.scale.y = h; u.hit.position.y = h / 2;
  }
  function girarNoMundo(osso, q, fracao, maxAng) {
    OQ3.copy(OQ0).slerp(q, fracao);
    const ang = 2 * Math.acos(Math.min(1, Math.abs(OQ3.w)));
    if (ang > maxAng) { const parcial = OQ3.clone(); OQ3.copy(OQ0).slerp(parcial, maxAng / ang); }
    osso.parent.getWorldQuaternion(OQ1); osso.getWorldQuaternion(OQ2);
    osso.quaternion.copy(OQ1.invert().multiply(OQ3.multiply(OQ2))); osso.updateMatrixWorld(true);
  }
  function frenteCabeca(o) { o.olhoE.getWorldPosition(OV1); o.olhoD.getWorldPosition(OV2); OV1.add(OV2).multiplyScalar(.5); return OV3.copy(o.frenteLocal).applyQuaternion(o.cabeca.getWorldQuaternion(OQ2)).normalize(); }
  function olhar(n, dt, posPolicial) {
    const o = n.userData.olhar; if (!o) return;
    const perto = n.visible && !n.userData.destino && n.position.distanceTo(OV1.copy(posPolicial).setY(n.position.y)) < 4.5;
    o.peso += ((perto ? 1 : 0) - o.peso) * Math.min(1, dt * 2.5);
    for (const x of o.ossos) { if (x.escrito && x.b.quaternion.equals(x.escrito)) x.b.quaternion.copy(x.base); else x.base.copy(x.b.quaternion); x.escrito = null; }
    if (o.peso < .01) return;
    n.updateMatrixWorld(true);
    const ombros = o.clavs.map(b => b.getWorldQuaternion(new THREE.Quaternion()));
    for (const [osso, fr, max] of [[o.pescoco, .4, .55], [o.cabeca, 1, .75]]) {
      if (!osso) continue;
      const frente = frenteCabeca(o).clone(), alvo = OV2.copy(posPolicial).sub(OV1).normalize();
      girarNoMundo(osso, OQ0.clone().setFromUnitVectors(frente, alvo), fr * o.peso, max);
    }
    if (o.pescoco) o.clavs.forEach((b, i) => { o.pescoco.getWorldQuaternion(OQ1); b.quaternion.copy(OQ1.invert().multiply(ombros[i])); b.updateMatrixWorld(true); });
    for (const x of o.ossos) x.escrito = x.b.quaternion.clone();
  }
  function animarRosto(n, dt, agora) {
    const r = n.userData.rosto; if (!r) return;
    let alvo = 0; const f = n.userData.fala;
    if (f) {
      if (agora > f.ate) n.userData.fala = null;
      else if (f.medidor) alvo = Math.pow(Math.min(1, Math.max(0, f.medidor() - .06) / .75), .8);
      else if (f.sintetica) alvo = Math.max(0, .3 + .45 * Math.sin(agora * .019) * Math.sin(agora * .0063 + 1.7));
    }
    r.boca += (alvo - r.boca) * Math.min(1, dt * (alvo > r.boca ? 28 : 14));
    const q = r.jaw.quaternion;
    if (r.escrito && q.equals(r.escrito)) q.copy(r.jawBase);
    q.multiply(QZ.setFromAxisAngle(EIXO_Z, r.boca * .17)); r.escrito = q.clone();
    if (agora > r.proxPisca) { r.piscaIni = agora; r.proxPisca = agora + 2500 + Math.random() * 4000; }
    const t = (agora - r.piscaIni) / 75, k = t < 1 ? t : t < 2 ? 2 - t : 0;
    for (const p of r.palp) { p.b.position.copy(p.base); p.b.position.x += p.k * k; }
  }
  function animar(npc, nome, segundos = 6, fade = .5) {
    const u = npc?.userData; if (!u?.real) return;
    if (u.algemado && !nome.startsWith('algemado')) nome = nome === 'andando' ? 'algemado_andando' : 'algemado';
    if (!u.acoes[nome]) return;
    u.pose = nome;
    const nova = u.acoes[nome];
    if (u.atual !== nova) { nova.reset().play(); u.atual?.crossFadeTo(nova, fade, false); u.atual = nova; }
    clearTimeout(u.volta);
    if (nome !== (u.base || 'parada')) u.volta = setTimeout(() => animar(npc, u.base || 'parada'), segundos * 1000);
  }
  function moverNPC(n, dt) {
    const u = n.userData;
    if (!u.destino && u.rota?.length) u.destino = u.rota.shift();
    if (!u.destino) return;
    V2.copy(u.destino).sub(n.position); V2.y = 0;
    const L = V2.length();
    if (L < .12) { u.destino = null; if (!u.rota?.length) { const cb = u.aoChegar; u.aoChegar = null; cb?.(); } return; }
    n.position.addScaledVector(V2.normalize(), Math.min(L, (u.vel || 1.4) * dt));
    const alvo = Math.atan2(V2.x, V2.z); let d = alvo - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
    n.rotation.y += d * Math.min(1, dt * 8);
  }

  /* objetivos (modo treino) */
  const ocv = document.createElement('canvas'); ocv.width = 640; ocv.height = 300;
  const otex = new THREE.CanvasTexture(ocv); otex.colorSpace = THREE.SRGBColorSpace;
  const objVR = new THREE.Mesh(new THREE.PlaneGeometry(.42, .42 * 300 / 640), new THREE.MeshBasicMaterial({ map: otex, transparent: true, depthTest: false, toneMapped: false, fog: false }));
  objVR.position.set(-.32, .2, -.9); objVR.renderOrder = 1002; objVR.visible = false; camera.add(objVR);
  const objHTML = document.createElement('div'); objHTML.id = 'objetivosHTML'; objHTML.hidden = true;
  Object.assign(objHTML.style, { position: 'fixed', right: '16px', top: '16px', maxWidth: 'min(340px, calc(100vw - 32px))', zIndex: 6, background: 'rgba(11,14,22,.88)', color: '#efe9df', border: '1px solid rgba(240,163,64,.5)', borderRadius: '6px', padding: '10px 14px', font: '13px/1.45 "Segoe UI", system-ui, sans-serif', pointerEvents: 'none' });
  document.body.appendChild(objHTML);
  let ultimoObj = '';
  function mostrarObjetivos() {
    const on = S.ativo && S.modo === 'treino', L = on ? objetivos() : [], chave = on + L.join('|') + renderer.xr.isPresenting;
    if (chave === ultimoObj) return; ultimoObj = chave;
    objHTML.hidden = !on || renderer.xr.isPresenting; objVR.visible = on && renderer.xr.isPresenting;
    if (!on) return;
    objHTML.innerHTML = '<b style="color:#f0a340;font:600 11px Consolas,monospace;letter-spacing:.08em">OBJETIVOS</b><br>' + L.map(t => '▸ ' + t).join('<br>');
    const g = ocv.getContext('2d'); g.clearRect(0, 0, 640, 300);
    g.fillStyle = 'rgba(11,14,22,.85)'; g.beginPath(); g.roundRect(0, 0, 640, 300, 16); g.fill();
    g.fillStyle = '#f0a340'; g.font = '600 22px Consolas, monospace'; g.fillText('OBJETIVOS', 22, 38);
    g.fillStyle = '#efe9df'; g.font = '400 25px Segoe UI, sans-serif';
    let y = 80; for (const t of L) { let l = '▸ '; for (const w of t.split(' ')) { const tt = l + w + ' '; if (g.measureText(tt).width > 600 && l.trim()) { g.fillText(l, 22, y); y += 30; l = '  '; } else l = tt; } g.fillText(l, 22, y); y += 38; if (y > 290) break; }
    otex.needsUpdate = true;
  }

  /* ================= cena: coordenadas, portas, objetos de consulta ================= */
  const B = (x, y) => new THREE.Vector3(x, .15, -y);          // planta do Blender (X, Y) -> cena web
  const olharPara = (dx, dy) => Math.atan2(dx, -dy);
  const zona = p => {                                          // onde esta um ponto da cena web
    const x = p.x, y = -p.z;
    if (p.y > 3.0) return 'pavimento1';                        // 1o andar (chega-se pela rampa)
    if (y < -38) return 'rua';
    if (y < 0) return 'patio';
    if (x > -20 && x < 20 && y > 3 && y < 19) {               // bloco administrativo do terreo
      if (y > 10 && y < 13) return 'corredor';
      if (x < -2 && x > -10 && y < 10) return 'recepcao';
      if (x > -2 && x < 6 && y < 10) return 'direcao';
      if (x < -12 && y > 13) return 'banheiro';
      if (x > 2 && x < 12 && y > 13) return 'sala';
      return 'predio';
    }
    return 'galeria';
  };
  const dentroDoPredio = z => /corredor|recepcao|direcao|banheiro|sala|predio/.test(z);
  const suave = (seg, passo) => new Promise(fim => { const t0 = performance.now(); const tic = () => { const k = Math.min(1, (performance.now() - t0) / (seg * 1000)); passo(k * k * (3 - 2 * k)); k < 1 ? setTimeout(tic, 16) : fim(); }; tic(); });
  const invisivel = () => new THREE.MeshBasicMaterial({ visible: false });

  const portas = {};
  for (const [k, nome, aberta] of [['direcao', 'I_Porta_Direcao', -1.45], ['banheiro', 'I_Porta_Banheiro', 1.45], ['sala', 'I_Porta_Sala', 1.45]]) {
    const o = ctx.cena.getObjectByName(nome); if (!o) continue;
    o.updateWorldMatrix(true, false);
    const q = o.getWorldQuaternion(new THREE.Quaternion());
    const col = new THREE.Mesh(new THREE.BoxGeometry(.9, 2.1, .16), invisivel());
    o.getWorldPosition(col.position); col.position.addScaledVector(new THREE.Vector3(1, 0, 0).applyQuaternion(q), .44); col.position.y += 1.05;
    col.quaternion.copy(q); col.userData.porta = k; col.geometry.computeBoundsTree(); scene.add(col); col.updateMatrixWorld(true);
    portas[k] = { o, base: o.rotation.y, aberta, col, ang: 0, frac: 0 };
  }
  function moverPorta(k, frac = 1, seg = .8) {
    const p = portas[k]; if (!p) return Promise.resolve();
    const cols = ctx.colisao(), i = cols.indexOf(p.col), alvo = p.aberta * frac, a0 = p.ang;
    if (frac > .5) { if (i >= 0) cols.splice(i, 1); } else if (i < 0) cols.push(p.col);
    if (seg > .3 && p.frac !== frac) window.__som?.tocar('porta_abrindo', p.col.position);
    p.frac = frac;
    return suave(seg, e => { p.ang = a0 + (alvo - a0) * e; p.o.rotation.y = p.base + p.ang; });
  }
  const ITENS = { celular: 'I_Celular_Print', cameras: 'I_Monitor_Cameras', frequencia: 'I_Pasta_Frequencia', livro: 'I_Livro_Ocorrencias', mochila: 'I_Mochila', telefone: 'I_Telefone' };
  const itens = {}, hitsItem = [];
  for (const [k, nome] of Object.entries(ITENS)) {
    const o = ctx.cena.getObjectByName(nome); if (!o) continue;
    const h = new THREE.Mesh(new THREE.SphereGeometry(k === 'cameras' || k === 'mochila' ? .32 : .2, 10, 8), invisivel());
    o.getWorldPosition(h.position); h.position.y += k === 'cameras' ? .25 : k === 'mochila' ? .2 : .04; h.userData.item = k; scene.add(h); h.updateMatrixWorld(true);
    itens[k] = { o, h }; hitsItem.push(h);
  }

  /* ================= caminhos (os personagens nao colidem: andam por uma rede de pontos livres) ================= */
  const NOS = {
    rua: [7.0, -41.0], portao: [2.5, -39.2], portao_in: [2.5, -36.5], guarita: [6.6, -35.6], pass_1: [2.5, -18.5], pass_2: [2.5, -13.5], pass_n: [2.5, -2.5],
    patio_o: [-6, -13.5], encontro: [14, -20], gal: [2.5, 1.5], gal_rec: [-7.5, 1.5], rec_porta: [-7.5, 3.3], rec: [-7.0, 5.0], rec_fundo: [-6.8, 8.6],
    direcao_porta: [-2.6, 5.45], direcao: [-1.0, 5.45], direcao_c: [0.8, 5.2], cor_c: [-6.8, 11.5], cor_o: [-11.0, 11.5], cor_bm: [-16.05, 11.5],
    ban_porta: [-16.05, 12.6], ban: [-16.05, 14.2], ban_in: [-14.5, 15.5], cor_l: [0.0, 11.5], cor_sala: [6.95, 11.5], sala_porta: [6.95, 12.6], sala: [6.95, 14.2]
  };
  const ARESTAS = [['rua', 'portao'], ['portao', 'portao_in'], ['portao_in', 'guarita'], ['portao_in', 'pass_1'], ['pass_1', 'pass_2'], ['pass_2', 'pass_n'], ['pass_2', 'patio_o'], ['pass_1', 'encontro'],
    ['pass_n', 'gal'], ['gal', 'gal_rec'], ['gal_rec', 'rec_porta'], ['rec_porta', 'rec'], ['rec', 'rec_fundo'], ['rec', 'direcao_porta'], ['direcao_porta', 'direcao'], ['direcao', 'direcao_c'],
    ['rec_fundo', 'cor_c'], ['cor_c', 'cor_o'], ['cor_o', 'cor_bm'], ['cor_bm', 'ban_porta'], ['ban_porta', 'ban'], ['ban', 'ban_in'], ['cor_c', 'cor_l'], ['cor_l', 'cor_sala'], ['cor_sala', 'sala_porta'], ['sala_porta', 'sala']];
  const VIZ = {}; for (const [a, b] of ARESTAS) { (VIZ[a] ||= []).push(b); (VIZ[b] ||= []).push(a); }
  const PORTA_NO = { direcao_porta: 'direcao', ban_porta: 'banheiro', sala_porta: 'sala' };
  const rayG = new THREE.Raycaster(); rayG.firstHitOnly = true; const GV = new THREE.Vector3(), GN = new THREE.Vector3(), GT = new THREE.Vector3();
  function visto(de, ate) { GV.copy(ate).sub(de); const d = GV.length(); rayG.set(de, GV.normalize()); rayG.far = Math.max(.01, d - .15); return !rayG.intersectObjects(ctx.colisao(), false)[0]; }
  const P3 = ([x, y]) => new THREE.Vector3(x, 1.0, -y);
  function noProximo(p) {                                      // ponto da rede mais proximo e visivel de p (cena web)
    const a = p.clone().setY(1.0); let melhor = null, dm = 1e9;
    for (const [k, xy] of Object.entries(NOS)) { const b = P3(xy), d = a.distanceTo(b); if (d < dm && (d < .6 || visto(a, b))) { dm = d; melhor = k; } }
    if (!melhor) for (const [k, xy] of Object.entries(NOS)) { const d = a.distanceTo(P3(xy)); if (d < dm) { dm = d; melhor = k; } }
    return melhor;
  }
  function caminho(de, ate) {                                  // Dijkstra na rede
    const dist = { [de]: 0 }, ant = {}, aberto = new Set([de]);
    while (aberto.size) {
      let u = null; for (const k of aberto) if (u === null || dist[k] < dist[u]) u = k;
      aberto.delete(u); if (u === ate) break;
      for (const v of VIZ[u] || []) { const d = dist[u] + Math.hypot(NOS[u][0] - NOS[v][0], NOS[u][1] - NOS[v][1]); if (dist[v] === undefined || d < dist[v]) { dist[v] = d; ant[v] = u; aberto.add(v); } }
    }
    const out = []; let k = ate; while (k !== undefined) { out.unshift(k); k = ant[k]; }
    return out[0] === de ? out : [de, ate];
  }
  // leva o personagem ate o ponto (x, y) da planta pela rede; abre as portas do caminho
  function irAte(n, xy, vel = 1.4, anim = 'andando', aoChegar) {
    const u = n.userData, ini = noProximo(n.position), fim = noProximo(B(...xy));
    const nos = caminho(ini, fim);
    for (const k of nos) if (PORTA_NO[k] && portas[PORTA_NO[k]]?.frac < .5) moverPorta(PORTA_NO[k], 1);
    const pts = nos.map(k => NOS[k]); pts.push(xy);
    u.rota = pts.map(([x, y]) => B(x, y)); u.destino = null; u.vel = vel;
    u.aoChegar = () => { animar(n, u.base || 'parada', 1e6, .3); aoChegar?.(); };
    if (u.sentado) levantar(n);
    animar(n, u.acoes?.[anim] ? anim : 'andando', 1e6, .25);
  }

  /* ================= arma do policial (mesmo modelo e mesma logica do Cassino) ================= */
  let AC = null;
  function estouro(dur, corte, vol, grave = 0) {
    try {
      AC = AC || new (window.AudioContext || window.webkitAudioContext)();
      const n = Math.floor(AC.sampleRate * dur), b = AC.createBuffer(1, n, AC.sampleRate), d = b.getChannelData(0);
      for (let i = 0; i < n; i++) { const t = i / n; d[i] = ((Math.random() * 2 - 1) * (1 - grave) + Math.sin(i / AC.sampleRate * 2 * Math.PI * 55) * grave) * Math.pow(1 - t, 3.2); }
      const s = AC.createBufferSource(); s.buffer = b; const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = corte;
      const g = AC.createGain(); g.gain.value = vol; s.connect(f).connect(g).connect(AC.destination); s.start();
    } catch (e) { }
  }
  const somTiro = pos => window.__som?.tocar('tiro_pistola', pos || null) || window.__somArquivos?.tiro_pistola || estouro(.3, 3200, .9, .25);
  const gl = new GLTFLoader();
  const arma = new THREE.Group(); arma.visible = false;
  const texFlash = (() => {
    const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d'); g.translate(64, 64);
    for (let k = 0; k < 7; k++) { g.rotate(Math.PI * 2 / 7 + (Math.random() - .5) * .3); const L = 34 + Math.random() * 28; const gr = g.createLinearGradient(0, 0, L, 0); gr.addColorStop(0, 'rgba(255,240,190,1)'); gr.addColorStop(.5, 'rgba(255,170,60,.8)'); gr.addColorStop(1, 'rgba(255,90,20,0)'); g.fillStyle = gr; g.beginPath(); g.moveTo(0, -9); g.lineTo(L, 0); g.lineTo(0, 9); g.fill(); }
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, 30); gr.addColorStop(0, 'rgba(255,255,240,1)'); gr.addColorStop(.5, 'rgba(255,200,90,.7)'); gr.addColorStop(1, 'rgba(255,120,30,0)'); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, 30, 0, 7); g.fill();
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const matFlash = new THREE.MeshBasicMaterial({ map: texFlash, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, fog: false, side: THREE.DoubleSide });
  function criarFlash(tam = .2) {
    const g = new THREE.Group(), geo = new THREE.PlaneGeometry(tam, tam);
    const a = new THREE.Mesh(geo, matFlash), b = new THREE.Mesh(geo, matFlash), c = new THREE.Mesh(geo, matFlash);
    b.rotation.y = Math.PI / 2; b.scale.x = 1.5; c.rotation.x = Math.PI / 2; c.scale.y = 1.5; g.add(a, b, c);
    const l = new THREE.PointLight(0xffc880, 0, 10, 2); g.add(l); g.userData.luz = l; g.visible = false; return g;
  }
  function acenderFlash(f) { f.rotation.z = Math.random() * 6.28; f.scale.setScalar(.75 + Math.random() * .6); f.visible = true; f.userData.luz.intensity = 9; setTimeout(() => { f.userData.luz.intensity = 3; }, 40); setTimeout(() => { f.visible = false; f.userData.luz.intensity = 0; }, 85); }
  const clarao = criarFlash(); clarao.position.set(0, 0, -.2); arma.add(clarao);
  const prep = raiz => { raiz.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => ctx.iluminar(m.clone())) : ctx.iluminar(o.material.clone()); }); return raiz; };
  const armaNPC = new THREE.Group(), armaSolta = new THREE.Group();
  for (const g of [armaNPC, armaSolta]) { g.visible = false; scene.add(g); }
  { const f = criarFlash(.24); f.position.set(0, 0, -.2); armaNPC.add(f); armaNPC.userData.flash = f; }
  const hitArma = new THREE.Mesh(new THREE.SphereGeometry(.22, 8, 6), invisivel()); hitArma.userData.item = 'arma'; armaSolta.add(hitArma);
  gl.loadAsync(HQ('modelos/arma.glb')).then(g => { const m = prep(g.scene); arma.add(m.clone()); armaNPC.add(m.clone()); armaSolta.add(m.clone()); }).catch(() => { });
  const controle = mao => (ctx.controles || []).find(c => c.userData.mao === mao);
  function sacar(on) {
    S.armaNaMao = on;
    const pai = renderer.xr.isPresenting ? (controle('right') || ctx.controles?.[0] || camera) : camera;
    pai.add(arma);
    if (pai === camera) arma.position.set(.17, -.13, -.38); else arma.position.set(0, 0, -.02);
    arma.rotation.set(0, 0, 0); arma.visible = on;
    for (const [k, g] of (ctx.grips || []).entries()) if (g.userData.mao === 'right') g.visible = !on;
    if (on && S.ativo && A && !A.ameaca && !real()) A.armaSemAmeaca = true;
    status();
  }
  const marcas = [], geoMarca = new THREE.CircleGeometry(.014, 10), matMarca = new THREE.MeshBasicMaterial({ color: 0x050505 });
  function marcar(h) { const m = marcas.length >= 40 ? marcas.shift() : new THREE.Mesh(geoMarca, matMarca); const n = h.face.normal.clone().transformDirection(h.object.matrixWorld); m.position.copy(h.point).addScaledVector(n, .004); m.lookAt(h.point.clone().add(n)); scene.add(m); marcas.push(m); }
  let ultimoTiro = 0; const CARREGADOR = 15, MIRA = new THREE.Vector3(), BOCA = new THREE.Vector3();
  function recarregar() {
    if (S.recarregando || !S.armaNaMao || (S.municao ?? CARREGADOR) >= CARREGADOR) return;
    S.recarregando = true; status();
    const som = window.__som, seg = Math.min(4, (som?.tem('recarregar_pistola') && som.duracao('recarregar_pistola')) || 1.6);
    if (!som?.tocar('recarregar_pistola')) estouro(.08, 2500, .3);
    setTimeout(() => { S.municao = CARREGADOR; S.recarregando = false; status(); }, seg * 1000);
  }
  function disparar(ray) {
    const agora = performance.now(); if (agora - ultimoTiro < 280 || S.recarregando) return true; ultimoTiro = agora;
    if ((S.municao ?? CARREGADOR) <= 0) { estouro(.03, 5000, .25); recarregar(); return true; }
    S.municao = (S.municao ?? CARREGADOR) - 1;
    if (arma.parent === camera) {
      const h0 = ray.intersectObjects(ctx.colisao(), false)[0];
      MIRA.copy(h0 ? h0.point : ray.ray.origin.clone().addScaledVector(ray.ray.direction, 30));
      arma.lookAt(MIRA); arma.rotateY(Math.PI); arma.updateMatrixWorld(true);
      clarao.getWorldPosition(BOCA); ray.set(BOCA, MIRA.clone().sub(BOCA).normalize());
    } else { arma.updateMatrixWorld(true); clarao.getWorldPosition(BOCA); ray.set(BOCA, MIRA.set(0, 0, -1).applyQuaternion(arma.getWorldQuaternion(new THREE.Quaternion())).normalize()); }
    somTiro(); acenderFlash(clarao); status(); const rx = arma.rotation.x; arma.rotation.x = rx + .22; setTimeout(() => { arma.rotation.x = rx; }, 130);
    const pessoas = Object.values(npcs).filter(n => n.visible && !n.userData.caido);
    const hn = ray.intersectObjects(pessoas.map(n => n.userData.hit), false)[0];
    const hp = ray.intersectObjects(ctx.colisao(), false)[0];
    if (hn && (!hp || hn.distance < hp.distance)) {
      const n = pessoas.find(p => p.userData.hit === hn.object);
      if (S.ativo && A) {
        if (n.userData.ameaca) {
          registrar('resposta_proporcional', 'disparo');
          if (S.modo === 'treino') legenda('Instrutor', A.ordemDada ? 'Agressão armada atual depois da ordem verbal: o disparo foi legítimo. Agora: arma, socorro e comunicação.' : 'Ele havia disparado e mantinha a arma: o disparo é defensável. Quando possível, a ordem verbal vem antes (validar).', 7);
        } else registrar('disparo_injustificado', n.userData.nome);
        A.feridos.add(n.userData.chave);
      }
      cair(n);
    } else { if (hp?.face) marcar(hp); if (S.ativo && A) registrar('disparo_sem_alvo'); }
    return true;
  }
  function cair(n) {
    const u = n.userData; u.caido = true; u.rota = []; u.destino = null; u.aoChegar = null; u.ameaca = false; u.atira = false; u.sentado = false;
    if (u.arma?.visible) { u.arma.visible = false; armaChao(n.position); }
    n.position.y = .15; const r0 = n.rotation.x;
    suave(.7, e => { n.rotation.x = r0 + (-Math.PI / 2 - r0) * e; n.position.y = .15 + .12 * e; });
    sincAmeaca(); status();
  }
  function armaChao(p) { armaSolta.position.set(p.x + .35, .17, p.z + .2); armaSolta.rotation.set(0, 1, Math.PI / 2); armaSolta.visible = true; armaSolta.updateMatrixWorld(true); }
  function seguirArmaNPC() {
    const n = npcs.aluno, g = armaNPC; if (!n || !g.visible) return;
    const mao = n.userData.modelo?.getObjectByName('Bip01_R_Hand'); if (!mao) { g.position.copy(n.position).add(new THREE.Vector3(0, 1.3, 0)); return; }
    mao.getWorldPosition(g.position);
    if (n.userData.alvo) g.lookAt(n.userData.alvo); else { camera.getWorldPosition(GT); g.lookAt(GT); }
    g.rotateY(Math.PI); g.translateZ(-.05); g.translateY(.075);
  }
  const ameacando = () => Object.values(npcs).filter(n => n.userData.ameaca && !n.userData.caido);
  function sincAmeaca() { if (A) A.ameaca = ameacando().length > 0; }
  const veu = new THREE.Mesh(new THREE.PlaneGeometry(4, 4), new THREE.MeshBasicMaterial({ color: 0xff2020, transparent: true, opacity: 0, depthTest: false, toneMapped: false, fog: false }));
  veu.position.z = -.3; veu.renderOrder = 1005; veu.visible = false; camera.add(veu);
  function veuVermelho(k = .55, seg = 1.6) { veu.visible = true; veu.material.opacity = k; suave(seg, e => { veu.material.opacity = k * (1 - e); if (e >= 1) veu.visible = false; }); }
  function policialAtingido() {
    S.vida = (S.vida ?? 3) - 1; veuVermelho();
    if (S.vida <= 0) {
      legenda('Instrutor', 'Você foi gravemente ferido. O parceiro neutralizou o agressor. Ocorrência encerrada.', 7);
      const a = npcs.aluno; if (a && !a.userData.caido) { A && A.feridos.add('aluno'); cair(a); }
      if (S.ativo) setTimeout(finalizar, 4500); else S.vida = 3;
    } else legenda('Alerta', `Você foi atingido (${S.vida} de 3). Proteja-se na parede e reaja.`, 4);
  }
  function tiroInimigo(n) {
    const g = armaNPC; somTiro(g.position.clone()); acenderFlash(g.userData.flash);
    const de = g.position.clone(); camera.getWorldPosition(GT);
    if (visto(de, GT) && Math.random() < .3) return policialAtingido();
    GV.copy(GT).sub(de).normalize(); GV.x += (Math.random() - .5) * .3; GV.y += (Math.random() - .5) * .25; GV.z += (Math.random() - .5) * .3;
    rayG.set(de, GV.normalize()); rayG.far = 30; const h = rayG.intersectObjects(ctx.colisao(), false)[0]; if (h?.face) marcar(h);
  }
  function confronto() {
    if (!A || A.fase === 'fim') return; const agora = performance.now();
    for (const n of ameacando()) { const u = n.userData; if (!u.atira) continue; if (agora > u.proxTiro) { u.proxTiro = agora + 1800 + Math.random() * 1200; tiroInimigo(n); } }
  }

  /* ================= imagens: print do celular e quadros das cameras (desenho proprio, sem marcas) ================= */
  function imagemPrint(origem) {
    const P = CEN.prints[origem], cv = document.createElement('canvas'); cv.width = 720; cv.height = 900; const g = cv.getContext('2d');
    g.fillStyle = '#e9e4dc'; g.fillRect(0, 0, 720, 900);
    g.fillStyle = '#2f3b46'; g.fillRect(0, 0, 720, 120);
    g.fillStyle = '#fff'; g.font = '600 26px Segoe UI, sans-serif'; g.fillText(P.hora, 24, 34); g.textAlign = 'right'; g.fillText('▮▮▮ 78%', 696, 34); g.textAlign = 'left';
    g.beginPath(); g.arc(56, 82, 24, 0, 7); g.fillStyle = '#7f8c99'; g.fill();
    g.fillStyle = '#fff'; g.font = '700 30px Segoe UI, sans-serif'; g.fillText(P.titulo, 94, 92);
    let y = 160;
    const quebra = (t, w, fonte) => { g.font = fonte; const out = []; for (const par of t.split('\n')) { let l = ''; for (const p of par.split(' ')) { const s = l ? l + ' ' + p : p; if (g.measureText(s).width > w && l) { out.push(l); l = p; } else l = s; } out.push(l); } return out; };
    for (const m of P.linhas) {
      const ls = m.foto ? [] : quebra(m.texto, 560, '400 27px Segoe UI, sans-serif');
      const h = 58 + ls.length * 34 + (m.foto ? 230 : 0) + (m.nota ? 34 : 0);
      g.fillStyle = '#fff'; g.beginPath(); g.roundRect(24, y, 620, h, 16); g.fill();
      g.fillStyle = '#2a6f97'; g.font = '700 23px Segoe UI, sans-serif'; g.fillText(m.de, 44, y + 32);
      if (m.foto) {                                                             // foto de um revolver (silhueta simples)
        g.fillStyle = '#5b5148'; g.fillRect(44, y + 46, 560, 220); g.fillStyle = '#7d7064'; g.fillRect(44, y + 186, 560, 80);
        g.fillStyle = '#1b1b1d'; g.beginPath(); g.moveTo(190, y + 140); g.lineTo(420, y + 140); g.lineTo(420, y + 162); g.lineTo(300, y + 162); g.lineTo(290, y + 176); g.lineTo(265, y + 176); g.lineTo(230, y + 230); g.lineTo(195, y + 222); g.lineTo(228, y + 162); g.lineTo(190, y + 162); g.closePath(); g.fill();
        g.beginPath(); g.arc(262, y + 154, 22, 0, 7); g.fill();
        g.fillStyle = 'rgba(255,255,255,.75)'; g.font = 'italic 20px Segoe UI, sans-serif'; g.fillText('foto', 52, y + 70);
      } else { g.fillStyle = '#1d1d1f'; g.font = '400 27px Segoe UI, sans-serif'; ls.forEach((l, i) => g.fillText(l, 44, y + 70 + i * 34)); }
      if (m.nota) { g.fillStyle = '#8a6d3b'; g.font = 'italic 21px Segoe UI, sans-serif'; g.fillText('📎 ' + m.nota, 44, y + h - 22); }
      g.fillStyle = '#8b8b8b'; g.font = '400 19px Segoe UI, sans-serif'; g.textAlign = 'right'; g.fillText(m.hora, 628, y + 30); g.textAlign = 'left';
      y += h + 18;
    }
    g.fillStyle = '#9a948b'; g.font = 'italic 20px Segoe UI, sans-serif'; g.fillText('captura de tela recebida pela direção às 07:10 · situação fictícia', 24, y + 14);
    const out = document.createElement('canvas'); out.width = 720; out.height = Math.min(900, y + 40);      // corta o espaco vazio
    out.getContext('2d').drawImage(cv, 0, 0); return out;
  }
  function imagemCameras() {
    const cv = document.createElement('canvas'); cv.width = 800; cv.height = 450; const g = cv.getContext('2d');
    const q = [['CAM 01 · PORTÃO', '#3d4248'], ['CAM 02 · PÁTIO', '#454a4f'], ['CAM 03 · CORREDOR', '#3a3f44'], ['CAM 04 · RECEPÇÃO', '#41464b']];
    q.forEach(([nome, cor], i) => {
      const x = (i % 2) * 400, y = Math.floor(i / 2) * 225;
      g.fillStyle = cor; g.fillRect(x, y, 400, 225);
      g.strokeStyle = 'rgba(255,255,255,.12)'; g.beginPath(); g.moveTo(x, y + 225); g.lineTo(x + 160, y + 90); g.lineTo(x + 240, y + 90); g.lineTo(x + 400, y + 225); g.stroke();
      g.fillStyle = 'rgba(0,0,0,.35)'; for (let k = 0; k < 2; k++) { g.beginPath(); g.ellipse(x + 150 + k * 90 + i * 9, y + 150, 10, 30, 0, 0, 7); g.fill(); }
      g.fillStyle = '#e8e8e8'; g.font = '600 18px Consolas, monospace'; g.fillText(nome, x + 10, y + 22); g.fillText('07:' + (12 + i * 7) + ':0' + i, x + 290, y + 22);
    });
    g.strokeStyle = '#000'; g.lineWidth = 4; g.strokeRect(0, 0, 800, 450); g.beginPath(); g.moveTo(400, 0); g.lineTo(400, 450); g.moveTo(0, 225); g.lineTo(800, 225); g.stroke();
    return cv;
  }

  /* ================= variacoes ================= */
  function derivar(v) { if (v.origem !== 'ameaca_real') v.desfecho = 'rende'; return v; }
  function sortear() {
    const forc = Object.fromEntries((new URLSearchParams(location.search).get('v') || '').split(',').filter(Boolean).map(p => p.split(':')));
    const v = {};
    for (const [k, ops] of Object.entries(CEN.variacoes)) v[k] = forc[k] && ops.includes(forc[k]) ? forc[k] : ops[Math.floor(Math.random() * ops.length)];
    return derivar(v);
  }

  /* ================= personagens ================= */
  // chave, modelo, nome, posicao na planta (x, y), para onde olha (dx, dy), voz, altura
  const ELENCO = [
    ['parceiro', 'pm_parceiro', 'Policial parceiro', [7.0, -41.0], [-.3, 1], 'm', 1.8],
    ['apoio', 'pm_apoio', 'Policial de apoio', [12.0, -41.5], [-1, 0], 'm', 1.8],
    ['inspetora', 'inspetora', 'Funcionária da portaria', [6.6, -35.6], [-.3, -1], 'f', 1.64],
    ['responsavel', 'responsavel', 'Responsável (pai de aluna)', [-6.0, 5.0], [0, -1], 'm', 1.78],
    ['diretora', 'diretora', 'Diretora', [2.4, 7.8], [0, -1], 'f', 1.66],
    ['funcionario', 'funcionario', 'Seu Jorge (inspetor de corredor)', [-9.0, 11.0], [1, 0], 'm', 1.74],
    ['aluno', 'aluno', 'Lucas (aluno, 9º ano)', [6.65, 15.9], [-1, 0], 'j', 1.68],
  ];
  const ALTURA_SENTADO = alt => .15 + .46 - .925 * (alt / 1.78);
  function limparNPCs() { Object.values(npcs).forEach(n => scene.remove(n)); for (const k in npcs) delete npcs[k]; }
  function criarNPCs(v) {
    limparNPCs(); armaNPC.visible = false; armaSolta.visible = false;
    for (const [chave, papel, nome, [x, y], [dx, dy], voz, alt] of ELENCO) {
      const n = personagem(papel, nome, /parceiro|apoio/.test(chave) ? 0x1b2a4a : 0x3d4045, alt);
      n.userData.modelo?.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => ctx.iluminar(m.clone())) : ctx.iluminar(o.material.clone()); });
      Object.assign(n.userData, { chave, voz, fig: true, giroBase: olharPara(dx, dy), altura: alt });
      n.position.copy(B(x, y)); n.rotation.y = n.userData.giroBase; scene.add(n); npcs[chave] = n;
      if (n.userData.hit) n.userData.hit.userData.npc = chave;
    }
    npcs.apoio.visible = false;
    const r = npcs.responsavel; r.userData.base = 'irritado'; animar(r, 'irritado', 1e6, 0);
    const al = npcs.aluno, ua = al.userData;
    if (v.origem === 'conflito') { al.position.copy(B(-13.6, 16.2)); al.rotation.y = ua.giroBase = olharPara(-1, 0); ua.base = 'agachado'; animar(al, 'agachado', 1e6, 0); itens.mochila && (itens.mochila.o.visible = true); }
    else if (v.origem === 'ameaca_real') { al.visible = false; itens.mochila && (itens.mochila.o.visible = false); }
    else { sentar(al); itens.mochila && (itens.mochila.o.visible = false); }
    if (itens.mochila) itens.mochila.h.visible = itens.mochila.o.visible;
  }
  function sentar(n) { const u = n.userData; u.sentado = true; u.semVirar = true; u.fig = false; u.base = 'sentado_parado'; animar(n, 'sentado_parado', 1e6, 0); n.position.y = ALTURA_SENTADO(u.altura); }
  function levantar(n) { const u = n.userData; if (!u.sentado) return; u.sentado = false; u.semVirar = false; u.fig = true; u.base = 'parada'; n.position.y = .15; n.position.x -= Math.sin(n.rotation.y) * .45; n.position.z -= Math.cos(n.rotation.y) * .45; animar(n, 'parada', 1e6, .2); }      // levanta e da um passo para tras da cadeira

  /* ================= paineis de opcoes ================= */
  const fechar = () => dialogo.esconder();
  function dica(texto, seg = 6) { if (S.modo === 'treino' && S.ativo) legenda('Dica do instrutor', texto, seg); }
  function painelOpc(tag, titulo, lista, aoEscolher, texto = '', voltar = true, img = null) {
    fecharPaineis();
    dialogo.mostrar({ tag, titulo, texto, img, botoes: [...lista.map(op => ({ label: op.fala, acao: () => {
      fechar();
      if (op.acao) registrar(op.acao);
      if (op.erro) registrar(op.erro);
      if (op.feedback && S.modo === 'treino') setTimeout(() => legenda('Instrutor', op.feedback, 7), 2600);
      aoEscolher?.(op);
    } })), ...(voltar ? [{ label: 'Voltar', acao: fechar }] : [])] });
  }
  function conversa(tag, ops) { fecharPaineis(); dialogo.mostrar({ tag, titulo: 'Conversa', botoes: [...ops, { label: 'Encerrar conversa', acao: fechar }] }); }

  /* ================= fluxo da ocorrencia ================= */
  function novaOcorrencia(v, cap) {
    S.variacao = v; S.feitos = new Map(); S.vida = 3; S.municao = CARREGADOR; S.recarregando = false;
    A = { n: HIST.length + 1, fase: 'chegada', titulo: cap?.titulo || `Ocorrência ${HIST.length + 1}`, fatos: [], feridos: new Set(), t0: performance.now() };
    criarNPCs(v); sacar(false);
    moverPorta('direcao', 1, .1); moverPorta('banheiro', 0, .1); moverPorta('sala', 0, .1);
    for (const m of marcas) scene.remove(m); marcas.length = 0;
    rig.position.copy(B(5.5, -41.5)); ctx.setYaw(Math.PI + .1);
    const abrir = () => { radio(CEN.radio.inicio).then(() => dica('Informe a chegada pelo rádio (menu: T ou botão Y/B) e fale com a funcionária no portão.')); };
    if (cap) { fecharPaineis(); menu.mostrar({ tag: 'Modo história', titulo: cap.titulo, texto: cap.texto, longe: 1.3, botoes: [{ label: 'Começar', acao: () => { menu.esconder(); abrir(); } }] }); }
    else abrir();
    status();
  }
  // --- portaria
  function menuInspetora() {
    const n = npcs.inspetora, v = S.variacao, ops = [];
    if (!A.ouviuInspetora) ops.push({ label: 'Bom dia, sou da Polícia Militar. O que aconteceu?', acao: () => { fechar(); A.ouviuInspetora = true; registrar('ouvir_inspetora'); diz(n, F.inspetora.relato, 'estressada'); } });
    if (A.ouviuInspetora && !A.entradaLucas) ops.push({ label: 'A senhora viu o aluno de quem estão falando chegar hoje?', acao: () => { fechar(); A.entradaLucas = true; fato('Portaria: ' + F.inspetora.entrada[v.origem]); diz(n, F.inspetora.entrada[v.origem]); } });
    ops.push({ label: 'Onde fica a direção?', acao: () => { fechar(); diz(n, F.inspetora.direcao); } });
    if (!A.divInspetora) ops.push({ label: 'Peço que ninguém repasse a mensagem nem o nome do aluno.', acao: () => { fechar(); A.divInspetora = true; conferirDivulgacao(); diz(n, F.inspetora.divulgar); } });
    conversa('Funcionária da portaria', ops);
  }
  function conferirDivulgacao() { if ((A.divInspetora || A.divDiretora) && (A.divResponsavel || A.responsavelLonge)) registrar('nao_divulgar'); else if (A.divDiretora && A.divResponsavel) registrar('nao_divulgar'); }
  // --- responsavel exaltado
  function gritoInicial() {
    if (!A || A.gritou) return; A.gritou = true;
    diz(npcs.responsavel, F.responsavel.inicial, 'irritado').then(() => { if (S.variacao.responsavel === 'filma' && !A.acalmou) comecarFilmar(); });
    dica('O responsável está exaltado. Ouça antes de agir.');
  }
  function comecarFilmar() { if (!A || A.filmando) return; A.filmando = true; legenda('Observação', 'O responsável pegou o celular e começou a filmar.', 4); setTimeout(() => A && diz(npcs.responsavel, F.responsavel.filma, 'irritado'), 1500); }
  function menuResponsavel() {
    const r = npcs.responsavel;
    if (!A.gritou) gritoInicial();
    if (!A.respondeu) return painelOpc('Responsável', 'Ele grita no meio da recepção', D.responsavel_inicio, op => {
      A.respondeu = true;
      if (op.id === 'acolher') { A.acalmou = true; r.userData.base = 'parada'; animar(r, 'parada', 1e6, .5); diz(r, F.responsavel.acalmou).then(() => { fato('Responsável: no grupo dos pais dizem que é o Lucas, do 9º ano, e que ele anda armado (boato, sem fonte).'); if (S.variacao.responsavel === 'filma') comecarFilmar(); }); }
      else { A.irritou = true; diz(r, F.responsavel.irritou, 'irritado').then(comecarFilmar); }
    });
    if (A.filmando && !A.filmaResolvido) return painelOpc('Responsável', 'Ele está filmando com o celular', D.responsavel_filma, op => {
      A.filmaResolvido = true;
      if (op.id === 'permitir') diz(r, F.responsavel.filma_ok); else diz(r, F.responsavel.filma_tomar, 'irritado');
    });
    if (A.irritou && !A.segundaChance) return painelOpc('Responsável', 'Ele continua nervoso', [D.responsavel_inicio[0]], () => { A.segundaChance = true; A.acalmou = true; r.userData.base = 'parada'; animar(r, 'parada', 1e6, .5); diz(r, F.responsavel.acalmou); }, 'Ainda dá para reduzir a tensão.');
    const ops = [];
    if (!A.responsavelLonge) ops.push({ label: D.responsavel_depois[0].fala, acao: () => { fechar(); registrar('separar_partes'); A.responsavelLonge = true; conferirDivulgacao(); diz(r, F.responsavel.aguardar).then(() => irAte(r, NOS.encontro, 1.3)); } });
    if (!A.divResponsavel) ops.push({ label: D.responsavel_depois[1].fala, acao: () => { fechar(); A.divResponsavel = true; conferirDivulgacao(); diz(r, F.responsavel.divulgar); } });
    conversa('Responsável', ops);
  }
  // --- direcao
  function menuDiretora() {
    const n = npcs.diretora, v = S.variacao, ops = [];
    if (!A.ouviuDiretora) ops.push({ label: 'Como essa mensagem chegou até a senhora?', acao: () => { fechar(); A.ouviuDiretora = true; registrar('ouvir_diretora'); diz(n, F.diretora.como_chegou, 'estressada'); } });
    if (!A.quem) ops.push({ label: 'Quem é o aluno citado e onde ele deveria estar agora?', acao: () => { fechar(); A.quem = true; fato('Direção: o aluno citado é Lucas, turma 901, sala 104.'); diz(n, F.diretora.quem); } });
    if (!A.hist) ops.push({ label: 'Já aconteceu alguma coisa com esse aluno antes?', acao: () => { fechar(); A.hist = true; diz(n, F.diretora.historico); } });
    if (!S.feitos.has('preservar_print')) ops.push({ label: 'Peço que guarde o print e o celular como estão, sem apagar nada.', acao: () => { fechar(); registrar('preservar_print'); diz(n, F.diretora.preservar); } });
    if (!A.divDiretora) ops.push({ label: 'Peço que a escola não repasse a mensagem nem o nome do aluno.', acao: () => { fechar(); A.divDiretora = true; conferirDivulgacao(); diz(n, F.diretora.divulgar); } });
    if (!A.chamou && !A.ameacaAtiva) ops.push({ label: 'Peço que chame o aluno e a família dele para conversarmos aqui, com a senhora presente.', acao: () => { fechar(); A.chamou = true; registrar('acionar_familia'); diz(n, F.diretora.chamar_aluno[v.origem]).then(chamarAluno); } });
    if (!A.abrigou) ops.push({ label: 'Vamos iniciar o abrigamento: trancar as salas e manter os alunos dentro.', acao: () => { fechar(); abrigamento(); } });
    if (A.conversou && !A.orientouEscola) ops.push({ label: 'Orientar a direção sobre as famílias e a rede de proteção', acao: () => painelOpc('Direção', 'Orientação à escola', D.orientacao, op => { A.orientouEscola = true; if (op.id === 'orientar') diz(n, 'Certo. Vou fazer o comunicado e ligar para o Conselho Tutelar.'); }) });
    conversa('Diretora', ops);
  }
  function abrigamento() {
    A.abrigou = true;
    const indicios = real() || A.fatos.some(f => /foto de um revólver|mochila pesada|ausente/.test(f));
    if (real()) registrar('abrigamento');
    else if (S.variacao.origem === 'corrente_antiga' && !indicios) { registrar('alarme_desproporcional'); if (S.modo === 'treino') setTimeout(() => legenda('Instrutor', 'Nada do que foi verificado indica risco concreto. Trancar a escola agora espalha pânico. Verifique primeiro (ponto a validar).', 7), 3500); }
    diz(npcs.diretora, F.diretora.abrigamento, 'estressada');
  }
  function chamarAluno() {
    const v = S.variacao, f = npcs.funcionario, al = npcs.aluno;
    if (v.origem === 'ameaca_real') { fato('Direção: o Lucas não está na sala 104.'); if (f && !A.ameacaAtiva) irAte(f, NOS.cor_o, 1.2); return; }
    if (v.origem === 'conflito') { fato('Direção: o Lucas está trancado no banheiro masculino e não quer sair.'); dica('O aluno não vem. Vá até o banheiro masculino, no corredor central.'); return; }
    diz(f, F.funcionario.traz_aluno);
    irAte(f, NOS.sala, 1.3, 'andando', () => {
      irAte(al, NOS.direcao_c, 1.0, 'andando', () => { al.userData.giroBase = olharPara(-1, 0); al.userData.naDirecao = true; registrar('localizar_aluno'); legenda('Direção', 'O Lucas chegou à direção com o seu Jorge.', 4); });
      setTimeout(() => irAte(f, [-0.8, 4.2], 1.0), 1500);
    });
  }
  // --- aluno (variacoes sem ameaca ativa)
  function menuAluno() {
    const al = npcs.aluno, u = al.userData, v = S.variacao;
    if (real()) return menuAlunoAmeaca();
    registrar('localizar_aluno');
    if (!A.abordou) return painelOpc(u.nome, 'Primeiro contato', D.aluno_abordagem, op => {
      A.abordou = true;
      if (op.id === 'calma') diz(al, F.aluno.abordagem[v.origem], v.origem === 'conflito' ? null : 'nervoso').then(() => { if (v.origem === 'conflito') { u.base = 'parada'; animar(al, 'parada', 1e6, .6); } });
      else if (op.id === 'dura') { diz(al, F.aluno.dura, null); animar(al, 'rendido', 6, .3); }
      else diz(al, F.aluno.abordagem[v.origem], 'nervoso');
      if (S.armaNaMao) registrar('arma_sem_ameaca');
    });
    const naDirecao = zona(al.position) === 'direcao', ops = [];
    for (const op of D.aluno_conversa) {
      if (op.condicao && op.condicao !== v.origem) continue;
      if (A['al_' + op.id]) continue;
      ops.push({ label: op.fala, acao: () => {
        fechar(); A['al_' + op.id] = true;
        if (op.erro) registrar(op.erro);
        if (op.feedback && op.erro && S.modo === 'treino') setTimeout(() => legenda('Instrutor', op.feedback, 7), 2600);
        if (op.id === 'mensagem') { A.conversou = true; registrar('ouvir_aluno'); if (zona(al.position) === 'direcao') registrar('conversar_reservado'); fato('Aluno: ' + F.aluno.mensagem[v.origem]); diz(al, F.aluno.mensagem[v.origem], v.origem === 'conflito' ? 'triste' : 'nervoso'); }
        else if (op.id === 'celular_pedir') { const t = F.aluno.celular[v.origem]; diz(al, t); if (v.origem !== 'conflito') fato(v.origem === 'corrente_antiga' ? 'Celular do aluno (mostrado por ele): a mensagem chegou para ele hoje, encaminhada; não há envio dele.' : 'Celular do aluno (mostrado por ele): a mensagem foi enviada por ele ontem, no grupo da turma.'); }
        else if (op.id === 'celular_pegar') diz(al, F.aluno.dura, null);
        else if (op.id === 'revistar') { revista('aluno'); diz(al, F.aluno.revista, null); }
        else if (op.id === 'algemar') { diz(al, F.aluno.dura, null); }
        else if (op.id === 'acolher') { registrar('acolher'); fato('Aluno: é alvo de intimidação repetida dos colegas (confirmado pelo livro de ocorrências).'); diz(al, 'Ninguém nunca perguntou... Tá bom. Eu vou com o senhor.', 'triste'); }
      } });
    }
    if (!naDirecao && !A.levandoAluno) ops.push({ label: 'Vamos até a direção conversar com calma.', acao: () => { fechar(); A.levandoAluno = true; diz(al, F.aluno.vai_direcao, null).then(() => irAte(al, NOS.direcao_c, 1.0, 'andando', () => { al.userData.giroBase = olharPara(-1, 0); legenda('Direção', 'O Lucas está na direção.', 3); })); } });
    conversa(u.nome, ops);
  }
  function revista(alvo) {
    const v = S.variacao;
    if (v.origem === 'corrente_antiga') { registrar('busca_sem_suspeita', alvo); if (S.modo === 'treino') setTimeout(() => legenda('Instrutor', 'Nada liga o aluno à mensagem (ela é antiga e não foi escrita por ele): não há fundada suspeita para revistar (CPP art. 244).', 7), 2600); }
    legenda('Revista', alvo === 'mochila' ? (CEN.mochila[v.origem] || CEN.mochila.outra) : 'Nada encontrado com o aluno.', 5);
    if (alvo === 'mochila') fato('Mochila: ' + (CEN.mochila[v.origem] || CEN.mochila.outra));
  }

  /* ================= ameaca ativa (variacao ameaca_real) ================= */
  function escalar(motivo) {
    if (!A || A.ameacaAtiva || !real()) return;
    A.ameacaAtiva = true; A.tAmeaca = performance.now(); A.fase = 'ameaca';
    const al = npcs.aluno, u = al.userData, f = npcs.funcionario, v = S.variacao;
    al.visible = true; u.base = 'apontando'; animar(al, 'apontando', 1e6, .1); u.ameaca = true; u.semVirar = false; u.fig = false; armaNPC.visible = true; sincAmeaca();
    if (motivo === 'banheiro') {                                // o policial chegou antes dos disparos: ele sai da cabine armado
      al.position.copy(B(-13.6, 16.2)); al.rotation.y = olharPara(-1, -1);
      legenda('Alerta', 'O aluno saiu da cabine com uma arma na mão!', 5);
    } else {
      al.position.copy(B(-14.5, 11.6)); al.rotation.y = olharPara(1, 0);
      if (A.abrigou && f) f.visible = false;                    // com o abrigamento, o inspetor entrou numa sala trancada
      if (!A.abrigou && f) { f.rota = []; f.userData.rota = []; f.userData.destino = null; f.position.copy(B(-11.0, 10.45)); f.rotation.y = olharPara(-1, 0); f.userData.base = 'agachado'; animar(f, 'agachado', 1e6, .2); f.userData.ferido = true; A.feridos.add('funcionario'); u.alvo = f.position.clone().setY(1.0); }
      const p = B(-14, 11.6).setY(1.4);
      somTiro(p); setTimeout(() => somTiro(p), 650);
      legenda('Alerta', A.abrigou ? 'Disparos no corredor central! As salas estão trancadas.' : 'Disparos no corredor central! Uma pessoa foi atingida.', 6);
      setTimeout(() => A && diz(npcs.parceiro, F.parceiro.ameaca, null), 1500);
      for (const k of ['diretora', 'inspetora']) { const n = npcs[k]; if (n && n.visible) { n.userData.base = 'nervoso'; animar(n, 'nervoso', 1e6, .3); } }
    }
    const pa = npcs.parceiro; if (pa) { pa.userData.base = 'apontando'; }
    status();
  }
  function ordemVerbal() {
    const al = npcs.aluno, u = al.userData; if (!A || !u.ameaca || A.ordemDada) return;
    A.ordemDada = true; voce('Polícia! Larga a arma no chão! Agora!', 3); registrar('ordem_verbal');
    const v = S.variacao;
    setTimeout(() => {
      if (!A || u.caido) return;
      diz(al, F.aluno.ameaca_ordem[v.desfecho], null);
      if (v.desfecho === 'rende') setTimeout(() => {
        if (!A || u.caido) return;
        u.ameaca = false; u.alvo = null; armaNPC.visible = false; armaChao(al.position); u.base = 'rendido'; animar(al, 'rendido', 1e6, .3); u.rendido = true; sincAmeaca();
        if (!A.feridos.has('aluno')) registrar('resposta_proporcional', 'sem disparo');
        legenda('Situação', 'Ele largou a arma e pôs as mãos na cabeça.', 4); status();
      }, 1800);
      else { u.alvo = null; u.atira = true; u.proxTiro = performance.now() + 2200; legenda('Alerta', 'Ele aponta a arma para você!', 3); }
    }, 900);
  }
  function menuAlunoAmeaca() {
    const al = npcs.aluno, u = al.userData;
    if (u.ameaca) return ordemVerbal();
    if (u.caido && !A.socorro) return painelOpc('Ferido', 'Lucas foi atingido', D.socorro, op => { if (op.id === 'socorrer') pedirSocorro(); });
    if (A.apreendeu) return legenda('Situação', 'Adolescente apreendido, aguardando a condução para a delegacia.', 3);
    painelOpc(u.nome, 'Ele está rendido', [
      { id: 'algemar', fala: 'Algemar e apreender (ele estava armado e disparou: há perigo)' },
      { id: 'sem', fala: 'Apreender sem algemas, com o parceiro segurando' }
    ], op => { A.apreendeu = true; if (op.id === 'algemar') { window.__som?.tocar('algemas', al.position.clone().setY(1.1)); u.algemado = true; u.base = 'algemado'; animar(al, 'algemado', 1e6, .4); } legenda('Apreensão', 'Adolescente apreendido em flagrante. A família e a delegacia especializada serão comunicadas (ECA arts. 106, 107 e 172).', 6); status(); }, '', false);
  }
  function pedirSocorro() { if (!A || A.socorro) return; A.socorro = true; registrar('socorro'); radio(CEN.radio.socorro); const f = npcs.funcionario; if (f?.userData.ferido) setTimeout(() => A && diz(f, F.funcionario.socorrido, null), 4000); status(); }
  function menuFuncionario() {
    const f = npcs.funcionario;
    if (f.userData.ferido) {
      if (!A.socorro) return painelOpc('Ferido', 'Seu Jorge foi atingido na perna', D.socorro, op => { if (op.id === 'socorrer') pedirSocorro(); }, F.funcionario.ferido);
      return legenda('Seu Jorge', 'Sangramento contido. A ambulância está a caminho.', 3);
    }
    diz(f, CEN.exploracao.funcionario);
  }

  /* ================= consulta de informacoes ================= */
  function usarItem(k) {
    const v = S.variacao;
    if (k === 'celular') {
      if (!A.ouviuDiretora && zona(itens.celular.h.position) === 'direcao' && npcs.diretora.visible) { A.ouviuDiretora = true; registrar('ouvir_diretora'); diz(npcs.diretora, F.diretora.como_chegou, 'estressada'); }
      registrar('ver_print');
      return painelOpc('Celular da diretora', 'O print recebido', [
        { id: 'detalhes', fala: 'Conferir data, hora, remetente e o que a mensagem diz de concreto' }
      ], () => { registrar('checar_detalhes'); fato('Print: ' + CEN.detalhes_print[v.origem]); legenda('Print', CEN.detalhes_print[v.origem], 10); }, '', true, imagemPrint(v.origem));
    }
    if (k === 'cameras') { registrar('consultar_cameras'); fato('Câmeras: ' + CEN.cameras[v.origem]); return painelOpc('Monitor das câmeras', 'Gravações desta manhã', [], null, CEN.cameras[v.origem], true, imagemCameras()); }
    if (k === 'frequencia') { registrar('consultar_frequencia'); fato('Frequência: ' + CEN.frequencia[v.origem]); return painelOpc('Recepção', 'Frequência de hoje', [], null, CEN.frequencia[v.origem]); }
    if (k === 'livro') { registrar('consultar_livro'); fato('Livro de ocorrências: ' + CEN.livro[v.origem]); return painelOpc('Direção', 'Livro de ocorrências da escola', [], null, CEN.livro[v.origem]); }
    if (k === 'telefone') return legenda('Recepção', 'Telefone interno: a direção usa para falar com as salas e com a portaria.', 4);
    if (k === 'mochila') return painelOpc('Banheiro', 'Mochila no chão da cabine', [
      { id: 'pedir', fala: 'Pedir ao aluno que mostre o que tem na mochila' }, { id: 'revistar', fala: 'Abrir e revistar a mochila' }
    ], op => { if (op.id === 'pedir') { const al = npcs.aluno; if (al.visible && !real()) { diz(al, F.aluno.revista, null); legenda('Mochila', CEN.mochila[v.origem] || CEN.mochila.outra, 6); fato('Mochila (mostrada pelo aluno): ' + (CEN.mochila[v.origem] || CEN.mochila.outra)); } } else revista('mochila'); });
    if (k === 'arma') { if (!armaSolta.visible) return; armaSolta.visible = false; registrar('recolher_arma'); legenda('Apreensão', 'Revólver recolhido com segurança, desmuniciado e preservado para a perícia. Local isolado.', 6); fato('Arma apreendida no corredor.'); status(); }
  }

  /* ================= radio, decisao e encerramento ================= */
  function falarRadio(tipo) {
    fecharPaineis();
    if (tipo === 'chegada') { A.chegada = true; registrar('comunicar_chegada'); radio(CEN.radio.chegada); }
    if (tipo === 'consulta') { A.consultou = true; registrar('consultar_radio'); const t = CEN.radio.consulta[S.variacao.origem === 'corrente_antiga' ? 'corrente_antiga' : 'outra']; fato('Sala de operações: ' + t.replace('Sala de operações: ', '')); radio(t); }
    if (tipo === 'ameaca') {
      A.comunicou = true; registrar('comunicar_ameaca'); radio(CEN.radio.ameaca);
      const ap = npcs.apoio; if (ap) { ap.visible = true; ap.position.copy(B(7.0, -41)); irAte(ap, NOS.pass_n, 2.6, 'correndo'); }
    }
    if (tipo === 'socorro') pedirSocorro();
    status();
  }
  function decidirFinal() {
    const v = S.variacao, certo = D.decisao_certa[v.origem];
    const fatos = A.fatos.length ? A.fatos.map(f => '• ' + f).join('\n') : 'Você ainda não verificou nada.';
    painelOpc('Rádio · encerramento', 'Qual é a conclusão da ocorrência?', D.decisao, op => {
      A.decidiu = true;
      const verificou = A.ameacaAtiva || (S.feitos.has('ver_print') && (S.feitos.has('localizar_aluno') || S.feitos.has('consultar_frequencia') || S.feitos.has('consultar_cameras')));
      if (!verificou) registrar('concluir_sem_verificar');
      if (op.id === certo) registrar('decisao_correta'); else { registrar('decisao_errada', op.id); if (real() && !A.ameacaAtiva && op.id !== 'flagrante') registrar('ignorou_ameaca'); }
      if (S.modo === 'treino') legenda('Instrutor', (op.id === certo ? 'Correto. ' : 'O adequado aqui: ') + D.decisao_explicacao[v.origem], 12);
      setTimeout(() => painelOpc('Encerramento', 'Registro da ocorrência', D.registro, () => {
        const depois = () => { radio(CEN.radio.final); setTimeout(finalizar, 5000); };
        if (!A.orientouEscola) painelOpc('Encerramento', 'Orientação à escola', D.orientacao, depois, '', false); else depois();
      }, '', false), S.modo === 'treino' ? 6000 : 500);
    }, 'Fatos que você verificou:\n' + fatos);
  }
  function finalizar() {
    if (!A || A.fase === 'fim') return;
    A.fase = 'fim'; fecharPaineis();
    if (A.feridos.size && !A.socorro) registrar('omissao_socorro');
    if (A.ameacaAtiva && !S.feitos.has('avancar_ameaca')) registrar('esperar_fora');
    sacar(false); status(); setTimeout(concluir, 1500);
  }
  function resumo() {
    const fases = [];
    for (const f of CEN.fases) {
      let fp = 0, fo = 0; const its = [];
      for (const a of f.acoes || []) { if (!cond(a.condicao) || (A.fasesAvaliadas && !A.fasesAvaliadas.includes(f.id))) continue; /* treino de ameaca ativa: so as fases treinadas */ fp += a.pontos; const ok = S.feitos.has(a.id); if (ok) fo += a.pontos; its.push({ texto: a.texto, ok, pontos: ok ? a.pontos : 0, base: a.base, validar: !!a.validar, atendimento: A.n }); }
      fases.push({ nome: f.nome, obtidos: fo, possiveis: fp, itens: its });
    }
    return { n: A.n, titulo: A.titulo, variacao: { ...S.variacao }, fases, fatos: [...A.fatos] };
  }
  function concluir() {
    if (!A) return;
    HIST.push(resumo()); A = null;
    if (!S.ativo) return;
    if (S.fila.length) { const prox = S.fila.shift(); setTimeout(() => novaOcorrencia(derivar({ ...prox.variacao }), S.historia ? prox : null), 1200); }
    else encerrar();
  }

  /* ================= tutorial de 1 minuto no portao ================= */
  // 4 passos: olhar ao redor, andar ate o circulo laranja, falar com o parceiro e abrir o menu (que ja leva ao menu principal)
  let TUT = null;
  const marcaTut = (() => {
    const g = new THREE.Group(), cor = 0xf0a340;
    const anel = new THREE.Mesh(new THREE.RingGeometry(.45, .6, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: cor, transparent: true, opacity: .9, toneMapped: false, depthWrite: false }));
    anel.position.y = .03; g.add(anel);
    const feixe = new THREE.Mesh(new THREE.CylinderGeometry(.5, .5, 2.4, 24, 1, true), new THREE.MeshBasicMaterial({ color: cor, transparent: true, opacity: .14, side: THREE.DoubleSide, toneMapped: false, depthWrite: false }));
    feixe.position.y = 1.2; g.add(feixe);
    g.position.copy(B(4.0, -36.6)); g.visible = false; scene.add(g); return g;
  })();
  const TUT_PASSOS = [
    vr => ['Olhe ao redor', vr ? 'Vire a cabeça para olhar a escola e a rua.' : 'Arraste o mouse (ou use as setas) para olhar ao redor.'],
    vr => ['Ande até o círculo laranja', vr ? 'Aponte o controle direito para o círculo no chão e aperte o gatilho para ir até lá (ou ande com o analógico).' : 'Use W A S D para andar até o círculo laranja no portão (Shift corre).'],
    vr => ['Fale com o seu parceiro', vr ? 'Aponte o controle para o policial ao seu lado e aperte o gatilho.' : 'Clique no policial ao seu lado para falar com ele.'],
    vr => ['Abra o menu', vr ? 'Aperte o botão Y ou B do controle. No menu você escolhe a ocorrência ou a missão.' : 'Aperte a tecla T. No menu você escolhe a ocorrência ou a missão.']
  ];
  function tutorial() {
    fecharPaineis(); if (S.ativo || S.crise) return;
    rig.position.copy(B(5.5, -41.5)); ctx.setYaw(Math.PI + .1);
    if (npcs.parceiro) { npcs.parceiro.position.copy(B(7.0, -41.0)); npcs.parceiro.rotation.y = npcs.parceiro.userData.giroBase; }
    TUT = { passo: -1, giro: 0, dir: null };
    passoTut(0);
  }
  function passoTut(k) {
    TUT.passo = k; marcaTut.visible = k === 1;
    const [t, x] = TUT_PASSOS[k](renderer.xr.isPresenting);
    legenda('Tutorial · ' + (k + 1) + ' de 4 · ' + t, x, 600);
  }
  function fimTut(concluiu) {
    if (!TUT) return; TUT = null; marcaTut.visible = false;
    legenda('Tutorial', concluiu ? 'Pronto! Escolha agora como quer treinar.' : 'Tutorial encerrado.', concluiu ? 5 : 2);
  }
  function eventoTut(e) {
    if (!TUT) return false;
    if (e === 'parceiro' && TUT.passo === 2) { setTimeout(() => TUT && passoTut(3), 2500); return false; }
    if (e === 'menu') {
      if (TUT.passo === 3) { fimTut(true); return false; }               // segue para o menu principal (aviso)
      menu.mostrar({ tag: 'Tutorial', titulo: 'Tutorial em andamento', texto: 'Passo ' + (TUT.passo + 1) + ' de 4.', botoes: [
        { label: 'Continuar o tutorial', acao: () => { menu.esconder(); passoTut(TUT.passo); } },
        { label: 'Sair do tutorial e ir ao menu', acao: () => { fimTut(false); aviso(); } }] });
      return true;
    }
    return false;
  }
  const TV = new THREE.Vector3(), TD = new THREE.Vector3();
  function quadroTut(dt) {
    if (!TUT) return;
    marcaTut.children[0].material.opacity = .6 + .3 * Math.sin(performance.now() / 250);
    camera.getWorldDirection(TD); const ang = Math.atan2(TD.x, TD.z);
    if (TUT.dir != null) { let d = ang - TUT.dir; d = Math.atan2(Math.sin(d), Math.cos(d)); TUT.giro += Math.abs(d); }
    TUT.dir = ang;
    if (TUT.passo === 0 && TUT.giro > 1.4) passoTut(1);
    else if (TUT.passo === 1) { camera.getWorldPosition(TV); TV.y = marcaTut.position.y; if (TV.distanceTo(marcaTut.position) < .9) passoTut(2); }
  }

  /* ================= inicio, menu e relatorio ================= */
  function aviso() {
    fecharPaineis();
    menu.mostrar({
      tag: 'Treinamento · conteúdo sensível · versão ' + (window.__versao || '?'), titulo: 'A mensagem — ocorrência em uma escola',
      texto: 'A direção de uma escola recebeu um print com ameaça de ataque. Você é policial militar e chega com o parceiro. A origem, o contexto e a atualidade da mensagem precisam ser verificados: converse, observe e consulte as informações antes de decidir.\n\n' +
        'Em algumas rodadas a ameaça é real e há um aluno armado na escola (sem cenas de violência contra crianças).\n' + CEN.aviso_ficcao + '\n' +
        'Computador: clique fala/usa · T menu · Q saca ou guarda a arma (com ela na mão, o clique dispara) · R recarrega · K checklist.\n' +
        'Quest: gatilho usa/clica · A saca a arma · Y ou B abre o menu · grip liga a lanterna.',
      botoes: [
        { label: 'Tutorial rápido (1 minuto, no portão): como olhar, andar, falar e abrir o menu', cor: 'rgba(90,170,255,.25)', acao: tutorial },
        { label: 'Modo história (4 ocorrências guiadas)', acao: () => comecar('historia') },
        { label: 'Modo treino (objetivos e dicas na tela)', acao: () => comecar('treino') },
        { label: 'Modo avaliação (sem dicas, variação sorteada)', acao: () => comecar('avaliacao') },
        { label: 'MISSÃO SALA 201 · crise com reféns (gerenciamento de crise e negociação)', cor: 'rgba(240,163,64,.3)', acao: escolherCrise },
        { label: 'Treino de ameaça ativa (direto na recepção)', acao: () => comecar('ameaca') },
        { label: S.voz === false ? 'Voz sintética: desligada (só legendas)' : 'Voz sintética: ligada', acao: () => { S.voz = S.voz === false; aviso(); } },
        { label: 'Cancelar', acao: () => menu.esconder() }
      ]
    });
  }
  async function comecar(modo) {
    fecharPaineis(); fimTut(false);
    let carregou = false; modelosProntos.then(() => { carregou = true; });
    await new Promise(r => setTimeout(r, 0));
    if (!carregou) { menu.mostrar({ tag: 'Treinamento', titulo: 'Carregando personagens…', texto: 'Aguarde alguns segundos.', botoes: [] }); await Promise.race([modelosProntos, new Promise(r => setTimeout(r, 30000))]); menu.esconder(); }
    HIST.length = 0;
    Object.assign(S, { ativo: true, inicio: performance.now(), fim: 0, erros: [], graves: [], log: [], historia: modo === 'historia', modo: modo === 'avaliacao' ? 'avaliacao' : 'treino' });
    S.fila = S.historia ? CEN.historia.slice(1) : [];
    if (ctx.hotspots) ctx.hotspots.visible = false;
    document.getElementById('relatorioHTML')?.setAttribute('hidden', '');
    if (modo === 'ameaca') {
      const v = sortear(); v.origem = 'ameaca_real'; if (!/desfecho:/.test(location.search)) v.desfecho = Math.random() < .5 ? 'rende' : 'aponta';
      novaOcorrencia(v, null); A.titulo = 'Treino de ameaça ativa'; A.fasesAvaliadas = ['ameaca', 'encerramento'];
      for (const id of ['comunicar_chegada', 'ouvir_inspetora']) registrar(id);
      A.chegada = true; A.entrouPredio = true;
      npcs.responsavel.position.copy(B(14, -20)); npcs.responsavel.userData.base = 'nervoso'; A.gritou = A.respondeu = A.acalmou = A.responsavelLonge = true;
      rig.position.copy(B(-6.8, 8.4)); ctx.setYaw(Math.PI / 2 - .35);
      npcs.parceiro.position.copy(B(-5.6, 8.0)); npcs.parceiro.rotation.y = olharPara(-1, .3);
      dica('Você está na recepção. Algo está para acontecer no corredor à esquerda.', 5);
      setTimeout(() => escalar('disparos'), 4000);
      return;
    }
    novaOcorrencia(S.historia ? derivar({ ...CEN.historia[0].variacao }) : sortear(), S.historia ? CEN.historia[0] : null);
  }
  function abrirMenu() {
    if (S.crise) return S.crise.menu();
    if (eventoTut('menu')) return;
    if (!S.ativo) return aviso();
    fecharPaineis();
    const b = [];
    if (A && !A.chegada) b.push({ label: 'Rádio: informar a chegada ao local', acao: () => falarRadio('chegada') });
    if (A && !A.consultou && !A.ameacaAtiva) b.push({ label: 'Rádio: consultar a sala de operações sobre a mensagem', acao: () => falarRadio('consulta') });
    if (A?.ameacaAtiva && !A.comunicou) b.unshift({ label: 'Rádio: disparos na escola, ameaça ativa — pedir apoio e socorro', acao: () => falarRadio('ameaca') });
    if (A?.ameacaAtiva && !A.abrigou) b.push({ label: 'Telefone da escola: mandar trancar as salas (abrigamento)', acao: () => { fecharPaineis(); abrigamento(); } });
    if (A?.ameacaAtiva && npcs.aluno?.userData.ameaca && !A.ordemDada) b.unshift({ label: 'Ordem verbal: "Polícia! Larga a arma!"', acao: () => { menu.esconder(); ordemVerbal(); } });
    if (A?.feridos.size && !A.socorro) b.push({ label: 'Rádio: pedir socorro médico', acao: () => falarRadio('socorro') });
    if (A && !A.decidiu && !(A.ameacaAtiva && ameacando().length)) b.push({ label: 'Rádio: conclusão e encerramento da ocorrência', acao: decidirFinal });
    if (S.armaNaMao) b.push({ label: `Recarregar a arma (${S.municao ?? CARREGADOR}/${CARREGADOR})`, acao: () => { menu.esconder(); recarregar(); } });
    b.push({ label: S.armaNaMao ? 'Guardar a arma no coldre' : 'Sacar a arma', acao: () => { sacar(!S.armaNaMao); menu.esconder(); } },
      { label: 'Checklist desta ocorrência', acao: abrirChecklist },
      { label: 'Fatos verificados até agora', acao: () => { fecharPaineis(); menu.mostrar({ tag: 'Anotações', titulo: 'O que você verificou', texto: A?.fatos.length ? A.fatos.map(f => '• ' + f).join('\n') : 'Nada verificado ainda.', botoes: [{ label: 'Fechar', acao: () => menu.esconder() }], longe: 1.3 }); } },
      { label: 'Encerrar e ver o relatório', cor: 'rgba(240,80,64,.22)', acao: encerrar },
      { label: 'Fechar', acao: () => menu.esconder() });
    menu.mostrar({ tag: 'Menu', titulo: 'A mensagem', texto: `Tempo: ${fmt(tempo())} · ${A ? A.titulo : 'aguardando'}`, botoes: b });
  }
  function abrirChecklist() {
    fecharPaineis();
    const linhas = CEN.fases.map(f => { const its = (f.acoes || []).filter(a => cond(a.condicao)); return its.length ? `${f.nome}: ` + its.map(a => (S.feitos.has(a.id) ? '✓ ' : '· ') + a.texto).join(' | ') : ''; }).filter(Boolean).join('\n');
    menu.mostrar({ tag: 'Checklist', titulo: 'Checklist da ocorrência', texto: (S.modo === 'avaliacao' ? 'No modo avaliação o checklist só aparece no relatório.' : linhas) + `\n\nTempo: ${fmt(tempo())}`, botoes: [{ label: 'Fechar', acao: () => menu.esconder() }], longe: 1.3 });
  }
  function encerrar() {
    if (!S.ativo) return;
    if (A) { if (A.feridos.size && !A.socorro) registrar('omissao_socorro'); HIST.push(resumo()); A = null; }
    S.fila = []; S.fim = performance.now(); S.ativo = false; fecharPaineis(); sacar(false); status();
    mostrarRelatorio(relatorio());
  }
  function relatorio() {
    let possiveis = 0, obtidos = 0; const fases = [];
    CEN.fases.forEach((f, i) => {
      const fr = { nome: f.nome, obtidos: 0, possiveis: 0, itens: [] };
      for (const h of HIST) { const x = h.fases[i]; fr.obtidos += x.obtidos; fr.possiveis += x.possiveis; fr.itens.push(...x.itens); }
      possiveis += fr.possiveis; obtidos += fr.obtidos; if (fr.possiveis) fases.push(fr);
    });
    const desc = S.erros.reduce((s, e) => s + e.pontos, 0) + S.graves.reduce((s, e) => s + e.pontos, 0);
    const nota = possiveis ? Math.max(0, Math.round((obtidos + desc) / possiveis * 100)) : 0;
    const aprovado = nota >= CEN.aprovacao.pontos_minimos && !(CEN.aprovacao.sem_falha_grave && S.graves.length);
    return { cenario: CEN.id, data: new Date().toISOString(), tempo: fmt(tempo()), modo: S.historia ? 'historia' : S.modo, nota, aprovado, obtidos, descontos: desc, possiveis,
      atendimentos: HIST.map(h => ({ n: h.n, titulo: h.titulo, variacao: h.variacao, fatos: h.fatos })), fases, erros: S.erros, falhas_graves: S.graves, linha_do_tempo: S.log };
  }
  const nomeVar = v => Object.entries(v).filter(([k]) => CEN.nomes_variacao[k] && !(k === 'desfecho' && v.origem !== 'ameaca_real')).map(([k, x]) => CEN.nomes_variacao[k][x] || x).join(' · ');
  function mostrarRelatorio(r) {
    const varios = r.atendimentos.length > 1, at = e => varios ? ` [ocorr. ${e.atendimento}]` : '';
    const txtFases = r.fases.map(f => `${f.nome}: ${f.obtidos}/${f.possiveis}`).join('\n');
    const txtErros = [...r.falhas_graves.map(g => '⚠ FALHA GRAVE: ' + g.texto + (g.base ? ` (${g.base})` : '') + at(g)), ...r.erros.map(e => `• ${e.texto} (${e.pontos})` + at(e))].join('\n') || 'Nenhum erro registrado.';
    menu.mostrar({ tag: 'Relatório', titulo: `Nota ${r.nota}/100 · ${r.aprovado ? 'APROVADO' : 'NÃO APROVADO'}`, texto: `Tempo: ${r.tempo} · Ocorrências: ${r.atendimentos.length}\n\n${txtFases}\n\n${txtErros}`,
      botoes: [{ label: 'Novo treinamento (outras variações)', acao: () => { fecharPaineis(); cenaExploracao(); aviso(); } }, { label: 'Fechar', acao: () => { menu.esconder(); cenaExploracao(); } }], longe: 1.4 });
    const el = document.getElementById('relatorioHTML');
    if (el) {
      const leis = Object.entries(CEN.base_legal).filter(([k]) => k !== '_nota').map(([k, t]) => `<li><b>${k}</b> — ${t}</li>`).join('');
      el.innerHTML = `<h2>Nota ${r.nota}/100 — ${r.aprovado ? 'aprovado' : 'não aprovado'}</h2>
        <p>Tempo ${r.tempo} · modo ${r.modo}</p>
        <ul>${r.atendimentos.map(a => `<li>${a.titulo} — <em>${nomeVar(a.variacao)}</em></li>`).join('')}</ul>
        ${r.fases.map(f => `<h3>${f.nome} <small>${f.obtidos}/${f.possiveis}</small></h3><ul>${f.itens.map(i => `<li class="${i.ok ? 'ok' : 'nao'}">${i.ok ? '✓' : '✗'} ${i.texto}${varios ? ` [ocorr. ${i.atendimento}]` : ''}${i.base ? ` <em>(${i.base})</em>` : ''}${i.validar ? ' <em>[validar]</em>' : ''}</li>`).join('')}</ul>`).join('')}
        <h3>Erros e falhas graves</h3><ul>${txtErros.split('\n').map(l => `<li>${l}</li>`).join('')}</ul>
        <h3>Fatos verificados</h3>${r.atendimentos.map(a => `<p><b>${a.titulo}</b></p><ul>${(a.fatos || []).map(f => `<li>${f}</li>`).join('') || '<li>nenhum</li>'}</ul>`).join('')}
        <h3>Base legal</h3><ul>${leis}</ul>
        <p><em>${CEN.base_legal._nota} ${CEN.aviso_ficcao}</em></p>
        <p><button type="button" id="baixarRel">Baixar relatório (JSON)</button> <button type="button" id="fecharRel">Fechar</button></p>`;
      el.hidden = false;
      document.getElementById('baixarRel').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' })); a.download = `relatorio_${r.cenario}_${Date.now()}.json`; a.click(); };
      document.getElementById('fecharRel').onclick = () => el.hidden = true;
    }
  }

  /* ================= missao "Sala 201" (crise com refens): motor em crise.js ================= */
  function escolherCrise() {
    fecharPaineis();
    menu.mostrar({ tag: 'Missão Sala 201', titulo: 'Qual é o seu papel?', texto: 'Um aluno radicalizado num grupo de Discord está armado na sala 201 com a turma. Escolha o papel que será avaliado.',
      botoes: [
        { label: 'Primeiro interventor — conter, isolar, contato inicial e passagem ao comando', acao: () => iniciarCrise('interventor', 'treino') },
        { label: 'Negociador — da passagem do comando até o desfecho', acao: () => iniciarCrise('negociador', 'treino') },
        { label: 'Completo — as duas fases, do alerta ao desfecho', acao: () => iniciarCrise('completo', 'treino') },
        { label: 'Completo em modo avaliação (sem dicas)', acao: () => iniciarCrise('completo', 'avaliacao') },
        { label: 'Voltar', acao: aviso }
      ] });
  }
  async function iniciarCrise(papel, modo) {
    fecharPaineis(); fimTut(false); menu.mostrar({ tag: 'Missão Sala 201', titulo: 'Carregando a missão…', texto: 'Personagens e equipamentos.', botoes: [] });
    await Promise.all([modelosProntos, carregarPapeis(p => PAPEIS_CRISE.test(p))]);
    const m = await import('./' + HQ('crise.js'));
    menu.esconder();
    if (A) { A = null; } S.ativo = false;
    S.crise = await m.iniciarCrise(H, { papel, modo });
  }

  /* ================= modo livre (antes de iniciar): cena montada, personagens respondem ================= */
  function cenaExploracao() {
    S.variacao = derivar({ ...CEN.historia[0].variacao }); criarNPCs(S.variacao); S.vida = 3; S.municao = CARREGADOR;
    moverPorta('direcao', 1, .1); moverPorta('banheiro', 0, .1); moverPorta('sala', 0, .1);
    npcs.parceiro.position.copy(B(7.0, -41.0));
  }
  function explorar(ray) {
    const hi = ray.intersectObjects([...hitsItem.filter(h => itens[h.userData.item]?.o.visible !== false), ...Object.values(portas).map(p => p.col)], false)[0];
    const hn = ray.intersectObjects(Object.values(npcs).filter(n => n.visible).map(n => n.userData.hit), false)[0];
    if (hn && hn.distance < 6 && (!hi || hn.distance < hi.distance)) {
      const n = Object.values(npcs).find(p => p.userData.hit === hn.object), k = n.userData.chave;
      if (k === 'parceiro') eventoTut('parceiro');
      diz(n, k === 'parceiro' ? CEN.equipe.pm_parceiro : k === 'apoio' ? CEN.equipe.pm_apoio : CEN.exploracao[k] || '...', n.userData.sentado ? null : 'falando'); return true;
    }
    if (hi && hi.distance < 4.5) {
      const u = hi.object.userData;
      if (u.porta) moverPorta(u.porta, portas[u.porta].frac > .5 ? 0 : 1);
      else legenda('Escola', { celular: 'Celular da diretora.', cameras: 'Monitor das câmeras da escola.', frequencia: 'Pasta com a frequência das turmas.', livro: 'Livro de ocorrências da escola.', mochila: 'Uma mochila.', telefone: 'Telefone interno.' }[u.item] || '', 4);
      return true;
    }
    return false;
  }

  /* ================= clique / gatilho ================= */
  function usar(ray, c) {
    for (const p of paineis) if (p.clique(ray)) return true;
    if (S.crise) return S.crise.usar(ray, c);
    if (S.armaNaMao && (!c || c.userData.mao !== 'left')) {
      // com a arma na mao, clicar no aluno armado da a ordem verbal (o primeiro clique); depois, dispara
      const al = npcs.aluno;
      if (S.ativo && A && al?.visible && al.userData.ameaca && !A.ordemDada) { const h = ray.intersectObject(al.userData.hit, false)[0]; if (h && h.distance < 25) { ordemVerbal(); return true; } }
      return disparar(ray);
    }
    if (!S.ativo) return explorar(ray);
    if (!A || A.fase === 'fim') return false;
    const hn = ray.intersectObjects(Object.values(npcs).filter(n => n.visible).map(n => n.userData.hit), false)[0];
    const hi = ray.intersectObjects([...hitsItem.filter(h => itens[h.userData.item]?.o.visible !== false), ...(armaSolta.visible ? [hitArma] : []), ...Object.values(portas).map(p => p.col)], false)[0];
    if (hn && hn.distance < (npcs.aluno?.userData.ameaca ? 25 : 5) && (!hi || hn.distance < hi.distance)) {
      const n = Object.values(npcs).find(p => p.userData.hit === hn.object), k = n.userData.chave;
      if (k === 'parceiro') diz(n, A.ameacaAtiva ? F.parceiro.cobertura : (A.fatos.length < 3 ? F.parceiro.dica_inicio : CEN.equipe.pm_parceiro), null);
      else if (k === 'apoio') diz(n, CEN.equipe.pm_apoio, null);
      else if (k === 'inspetora') menuInspetora();
      else if (k === 'responsavel') menuResponsavel();
      else if (k === 'diretora') menuDiretora();
      else if (k === 'funcionario') menuFuncionario();
      else if (k === 'aluno') menuAluno();
      return true;
    }
    if (hi && hi.distance < 4) {
      const u = hi.object.userData;
      if (u.porta) moverPorta(u.porta, portas[u.porta].frac > .5 ? 0 : 1);
      else usarItem(u.item);
      return true;
    }
    return false;
  }
  function botao(mao) { if (mao === 'right') sacar(!S.armaNaMao); }

  /* ================= objetivos (modo treino) e status ================= */
  function objetivos() {
    const L = [], v = S.variacao;
    if (!A) return ['Aguarde a próxima ocorrência'];
    if (A.fase === 'fim') return ['Ocorrência concluída'];
    if (A.ameacaAtiva) {
      if (ameacando().length) { L.push(A.ordemDada ? 'Ele não obedece e ameaça: proteja-se e reaja na medida da ameaça' : 'Vá até a ameaça com o parceiro e dê a ordem verbal (clique nele)'); }
      if (!A.comunicou) L.push('Comunique a ameaça ativa pelo rádio (menu)');
      if (!A.abrigou) L.push('Mande trancar as salas (menu)');
      if (A.feridos.size && !A.socorro) L.push('Peça socorro para o ferido');
      if (!ameacando().length && npcs.aluno?.userData.rendido && !A.apreendeu) L.push('Apreenda o adolescente (clique nele)');
      if (armaSolta.visible) L.push('Recolha a arma do chão');
      if (!ameacando().length && !A.decidiu) L.push('Encerre pelo rádio (menu)');
      return L.slice(0, 6);
    }
    if (!A.chegada) L.push('Informe a chegada pelo rádio (menu)');
    if (!A.ouviuInspetora) L.push('Fale com a funcionária no portão');
    if (!A.respondeu) L.push('Fale com o responsável na recepção');
    else if (!A.responsavelLonge) L.push('Peça ao responsável que aguarde no pátio');
    if (!S.feitos.has('ver_print')) L.push('Veja o print no celular da diretora (direção)');
    else if (!S.feitos.has('checar_detalhes')) L.push('Confira data, remetente e detalhes do print');
    if (!S.feitos.has('consultar_frequencia') && !S.feitos.has('consultar_cameras')) L.push('Consulte a frequência (recepção) e as câmeras (direção)');
    if (!A.consultou) L.push('Consulte a sala de operações pelo rádio (menu)');
    if (!real() && !S.feitos.has('localizar_aluno')) L.push('Localize o aluno citado');
    else if (!real() && !A.conversou) L.push('Converse com o aluno, com calma e em local reservado');
    if (!A.decidiu && A.fatos.length >= 4) L.push('Quando tiver informação suficiente, encerre pelo rádio (menu)');
    return L.slice(0, 6);
  }
  function status() {
    if (S.crise) return S.crise.status();
    const el = document.getElementById('statusTrein'); if (!el) return;
    el.hidden = !S.ativo || S.modo === 'treino';
    el.innerHTML = `<b>${A ? A.titulo : 'A mensagem'}</b> · ${fmt(tempo())}<br>Na mão: ${S.armaNaMao ? (S.recarregando ? 'arma (recarregando…)' : `arma · ${S.municao ?? CARREGADOR}/${CARREGADOR}`) : 'nada'} · fatos verificados: ${A ? A.fatos.length : 0}`;
    mostrarObjetivos();
  }

  /* ================= quadro ================= */
  let ultimo = performance.now(), segAntes = 0;
  const P1 = new THREE.Vector3();
  function quadro() {
    const agora = performance.now(), dt = Math.min(.1, (agora - ultimo) / 1000); ultimo = agora;
    if (agora > legAte) { leg.visible = false; const hl = document.getElementById('legendaHTML'); if (hl && !hl.hidden) hl.hidden = true; }
    confronto();
    if (S.crise) S.crise.quadro(dt);
    quadroTut(dt);
    if (vida) {                                                    // na missao, crise.js controla o patio (criseInicio/disparo/evacuar)
      if (!S.crise) { vida.normal(); vida.mostrar(!(A && A.ameacaAtiva)); } else if (!vida.emCrise()) vida.mostrar(false);
      vida.quadro(dt);
    }
    window.__som?.fase(S.crise ? 'crise' : A && A.ameacaAtiva ? 'ameaca' : 'normal');
    camera.getWorldPosition(V);
    const z = zona(V);
    if (S.ativo && A && A.fase !== 'fim') {
      if (z === 'recepcao' && !A.gritou && npcs.responsavel?.visible && V.distanceTo(npcs.responsavel.position) < 5) gritoInicial();
      if (dentroDoPredio(z) && !A.entrouPredio) { A.entrouPredio = true; A.tEntrou = agora; }
      if (real() && !A.ameacaAtiva) {
        if (z === 'banheiro' || (z === 'corredor' && V.x < -13.5)) escalar('banheiro');
        else if ((A.tEntrou && agora - A.tEntrou > (A.atrasoAmeaca ||= 70000 + Math.random() * 40000)) || agora - A.t0 > 210000) escalar('disparos');
      }
      if (A.ameacaAtiva) {
        if (!S.feitos.has('avancar_ameaca') && (z === 'corredor' || z === 'banheiro') && agora - A.tAmeaca < 90000) registrar('avancar_ameaca');
        if (!dentroDoPredio(z) && !S.feitos.has('avancar_ameaca') && agora - A.tAmeaca > 30000) registrar('esperar_fora');
      }
      if (A.armaSemAmeaca && !real() && npcs.aluno?.visible && V.distanceTo(npcs.aluno.position) < 3) { A.armaSemAmeaca = false; registrar('arma_sem_ameaca'); }
      // o parceiro acompanha o policial pela rede de caminhos
      const pa = npcs.parceiro;
      if (pa && Math.floor(agora / 1000) !== segAntes) {
        const u = pa.userData, d = pa.position.distanceTo(P1.copy(V).setY(pa.position.y));
        if (d > 3.2 && !u.rota?.length && !u.destino) {                // fica ~1,3 m atras do policial
          camera.getWorldDirection(V2); V2.y = 0; V2.normalize();
          const alvo = P1.copy(V).addScaledVector(V2, -1.3);
          if (!visto(V.clone().setY(1), alvo.clone().setY(1))) alvo.copy(V);
          irAte(pa, [alvo.x, -alvo.z], A.ameacaAtiva ? 2.6 : 1.6, A.ameacaAtiva ? 'correndo' : 'andando', () => { u.giroBase = pa.rotation.y; });
        }
      }
    }
    segAntes = Math.floor(agora / 1000);
    for (const n of Object.values(npcs)) {
      const u = n.userData;
      u.mixer?.update(dt); animarRosto(n, dt, agora);
      if (!u.caido) olhar(n, dt, V);
      ajustarAreaClique(n); moverNPC(n, dt);
      if (u.caido) continue;
      const enc = u.ameaca || (u.real && !u.destino && !u.semVirar && !u.rota?.length && V.distanceTo(n.position) < 3.2);
      if (u.alvo && u.ameaca && !u.atira) { let d = Math.atan2(u.alvo.x - n.position.x, u.alvo.z - n.position.z) - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); n.rotation.y += d * Math.min(1, dt * 4); }
      else if (enc) { let d = Math.atan2(V.x - n.position.x, V.z - n.position.z) - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); n.rotation.y += d * Math.min(1, dt * (u.ameaca ? 6 : 2.5)); }
      else if (u.fig && !u.fala && !u.destino && !u.rota?.length) { let d = u.giroBase - n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); n.rotation.y += d * Math.min(1, dt * 1.2); }
    }
    seguirArmaNPC();
    if (S.ativo && Math.floor(agora / 1000) !== Math.floor((agora - dt * 1000) / 1000)) status();
  }

  /* ================= entradas ================= */
  addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.repeat) return;
    if (e.code === 'KeyT') abrirMenu();
    if (e.code === 'KeyK' && S.ativo) abrirChecklist();
    if (e.code === 'KeyQ') sacar(!S.armaNaMao);
    if (e.code === 'KeyR') recarregar();
  });
  const bt = document.createElement('button'); bt.type = 'button'; bt.textContent = 'Iniciar treinamento'; bt.id = 'bTrein';
  bt.onclick = aviso; document.getElementById('acoes')?.prepend(bt);
  modelosProntos.then(() => { if (!S.ativo) cenaExploracao(); });
  // vida da escola (ventiladores, lampada piscando, gente no patio): vida.js
  let vida = null;
  modelosProntos.then(() => import('./' + HQ('vida.js'))).then(m => m.iniciarVida(H)).then(v => { vida = v; }).catch(e => console.warn('vida da escola nao carregou:', e));

  // pecas do motor usadas pela missao (crise.js)
  const H = { scene, camera, rig, renderer, ctx, CFG, HQ, S, npcs, menu, dialogo, Painel, fecharPaineis, legenda, diz, dizer, radio, vozSintetica, personagem, animar, irAte, NOS,
    B, olharPara, zona, visto, moverPorta, portas, sacar, disparar, armaNPC, armaSolta, somTiro, acenderFlash, veu, suave, espera, limparNPCs, ajustarAreaClique, levantar,
    fmt, aviso, cenaExploracao, carregarPapeis, estado: S, fimCrise: () => { S.crise = null; cenaExploracao(); } };
  window.__trein = {
    clique: ray => usar(ray), gatilho: (ray, c) => usar(ray, c), botao, recarregar, soltar: () => { },
    apontar, painelAberto: () => paineis.some(p => p.mesh.visible),
    menu: abrirMenu, quadro, estado: S, relatorio,
    _t: { tutorial, tut: () => TUT, comecar, encerrar, objetivos, sortear, derivar, novaOcorrencia, npcs, portas, moverPorta, itens, usarItem, sacar, disparar, falarRadio, menuInspetora, menuResponsavel, menuDiretora, menuAluno, menuFuncionario,
      decidirFinal, finalizar, escalar, ordemVerbal, usar, armaNPC, armaSolta, B, zona, irAte, caminho, noProximo, imagemPrint, imagemCameras, abrigamento, chamarAluno, pedirSocorro,
      ocorrencia: () => A, historico: HIST, botoes: () => (dialogo.mesh.visible ? dialogo : menu).botoes, painel: () => (dialogo.mesh.visible ? dialogo : menu.mesh.visible ? menu : null) }
  };
  return window.__trein;
}
