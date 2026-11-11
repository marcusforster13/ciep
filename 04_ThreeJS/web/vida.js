/*
  Vida da escola (so no site, sem bake):
  - ventiladores de parede das salas girando e oscilando (a chapa de fixacao vem do bake; motor, grade e helice daqui)
  - lampada fluorescente do corredor do 1o andar (perto da Sala 201) piscando de leve
  - modo normal: alunos de uniforme andando e conversando no patio, criancas correndo na quadra,
    e uma professora passando pela galeria. Somem na missao Sala 201 e quando a ameaca fica ativa.
  Coordenadas: planta do Blender (x, y, z) -> cena web (x, z, -y).
*/
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export async function iniciarVida(H) {
  const { scene, ctx, personagem, animar, B, olharPara } = H;
  const ilum = m => (ctx?.iluminar ? ctx.iluminar(m) : m);
  const P1Z = 3.5;                                                // piso do 1o andar (FZ + 3,35)

  /* ---------------- ventiladores de parede ----------------
     Leve para o Quest: as pecas de cada ventilador viram 2 malhas (cabeca e helice), e os bracos de todos viram 1. */
  const mVent = ilum(new THREE.MeshStandardMaterial({ color: 0x232427, roughness: .5, metalness: .25, side: THREE.DoubleSide }));
  const junta = (pecas) => mergeGeometries(pecas.map(([g, pos, rot]) => { g = g.toNonIndexed(); g.deleteAttribute('uv');
    return g.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3(...pos), new THREE.Quaternion().setFromEuler(new THREE.Euler(...rot)), new THREE.Vector3(1, 1, 1))); }));
  const centro = -.27, Q = Math.PI / 2;
  const pecasCab = [[new THREE.CylinderGeometry(.085, .095, .2, 14), [-.08, 0, 0], [0, 0, Q]], [new THREE.CylinderGeometry(.04, .04, .02, 12), [centro - .065, 0, 0], [0, 0, Q]]];
  // grade fechada: faixa lateral em volta, aros concentricos e raios na frente e atras (como a grade de um ventilador de verdade)
  pecasCab.push([new THREE.CylinderGeometry(.262, .262, .1, 40, 1, true), [centro, 0, 0], [0, 0, Q]]);
  for (const dx of [-.06, .06]) {
    pecasCab.push([new THREE.TorusGeometry(.262, .007, 6, 40), [centro + dx, 0, 0], [0, Q, 0]]);
    for (const r of [.085, .17]) pecasCab.push([new THREE.TorusGeometry(r, .0035, 4, 28), [centro + dx * 1.08, 0, 0], [0, Q, 0]]);
    for (let k = 0; k < 16; k++) { const a = k / 16 * Math.PI * 2; pecasCab.push([new THREE.BoxGeometry(.004, .25, .004), [centro + dx * 1.1, Math.cos(a) * .135, Math.sin(a) * .135], [a, 0, 0]]); }
  }
  const GEO_CAB = junta(pecasCab);
  const pecasHel = [[new THREE.CylinderGeometry(.035, .035, .05, 10), [0, 0, 0], [0, 0, Q]]];
  for (let k = 0; k < 3; k++) { const a = k / 3 * Math.PI * 2; pecasHel.push([new THREE.BoxGeometry(.01, .2, .09), [0, Math.cos(a) * .12, Math.sin(a) * .12], [a, .35, 0]]); }
  const GEO_HEL = junta(pecasHel);
  const ventiladores = [], bracos = [];
  function ventilador(xParede, yb, zb) {                         // parede em x = xParede, ventilador virado para -x (a sala)
    const base = new THREE.Group(); base.position.set(xParede - .12, zb, -yb); scene.add(base);
    bracos.push([new THREE.BoxGeometry(.1, .05, .05), [xParede - .07, zb, -yb], [0, 0, 0]]);
    const osc = new THREE.Group(); base.add(osc);                // oscila de um lado para o outro (eixo vertical)
    const cab = new THREE.Mesh(GEO_CAB, mVent); cab.rotation.z = .25; osc.add(cab);      // inclinado para baixo, para os alunos
    const helice = new THREE.Mesh(GEO_HEL, mVent); helice.position.x = centro; cab.add(helice);
    ventiladores.push({ osc, helice, fase: Math.random() * 6, vel: 22 + Math.random() * 6 });
  }
  for (const [x1, y0, y1] of [[20, .5, 9.5], [30, .5, 9.5], [40, .5, 9.5], [20, 12.5, 21.5]]) for (const y of [y0 + .9, y1 - .9]) ventilador(x1, y, P1Z + 2.55);
  for (const y of [13.9, 18.1]) ventilador(12, y, .15 + 2.55);   // sala 104 (terreo)
  scene.add(new THREE.Mesh(junta(bracos), mVent));

  /* ---------------- lampada piscando (corredor do 1o andar, perto da Sala 201) ---------------- */
  const mTubo = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
  const tubo = new THREE.Mesh(new THREE.BoxGeometry(1.24, .05, .12), mTubo); tubo.position.set(17, P1Z + 3.0 - .055, -11); scene.add(tubo);
  const COR_ON = new THREE.Color(0xeef4ff).multiplyScalar(1.6), COR_OFF = new THREE.Color(0x3a3d44);
  let piscaAte = 0, proxPisca = performance.now() + 3000;

  /* ---------------- gente no patio (modo normal) ---------------- */
  const pessoas = [];
  let uniformizar = null, cabeloCor = null;
  try { ({ uniformizar, cabeloCor } = await import('./' + H.HQ('crise.js'))); } catch (e) { }
  await H.carregarPapeis?.(p => /^refem_|^professora$/.test(p));
  // o piso da quadra fica 9 cm acima do patio (planta: x 33,5..51, y -36,2..-11,3): sem isso os pes afundavam
  const pisar = n => { const x = n.position.x, z = n.position.z; n.position.y = (x > 33.5 && x < 51 && z > 11.3 && z < 36.2) ? .239 : .15; };
  function pessoa(papel, nome, alt, rota, { vel = 1.1, anim = 'andando', pausa = [2, 5], uniforme = true, cabelo = null, fixo = null } = {}) {
    const n = personagem(papel, nome, 0x3d4045, alt);
    n.userData.modelo?.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => ilum(m.clone())) : ilum(o.material.clone()); });
    if (uniforme && uniformizar && /^refem_/.test(papel)) uniformizar(n, papel);
    if (cabelo && cabeloCor) cabeloCor(n, cabelo, papel);
    const p = { n, rota: rota.map(([x, y]) => B(x, y)), i: 1, vel, anim, pausa, espera: Math.random() * 3, fixo };
    n.position.copy(p.rota[0]); pisar(n);
    if (fixo) { n.rotation.y = fixo.giro; animar(n, fixo.anim || 'parada', 1e6, 0); n.userData.base = fixo.anim || 'parada'; }
    if (n.userData.acoes?.[anim]) n.userData.acoes[anim].timeScale = anim === 'correndo' ? 1 : vel / 1.2;
    scene.add(n); pessoas.push(p); return p;
  }
  // alunos caminhando pelo patio (longe da passarela e dos bancos)
  pessoa('refem_menino_a', 'Aluno', 1.55, [[-30, -10], [-13, -16], [-24, -18]], { vel: 1.1 });
  pessoa('refem_menina_b', 'Aluna', 1.5, [[11, -13.5], [30, -15], [33, -11]], { vel: 1.0, cabelo: '#2b1d14' });
  pessoa('refem_menina_a', 'Aluna', 1.48, [[31, -12.5], [12, -12], [9, -16]], { vel: 1.05 });
  // dois conversando perto dos mastros
  pessoa('refem_menino_b', 'Aluno', 1.52, [[-11.4, -9.6]], { fixo: { giro: olharPara(1, -.3), anim: 'parada' } });
  pessoa('refem_menina_b', 'Aluna', 1.47, [[-10.5, -9.85]], { fixo: { giro: olharPara(-1, .3), anim: 'parada' }, cabelo: '#5a3b22' });
  // futebol na quadra: so estes dois meninos (um ataca, o outro fica no gol); animacoes do Mixamo (fut_*, gol_*)
  pessoa('refem_menino_a', 'Aluno', 1.45, [[42.25, -21]], { fixo: { giro: olharPara(0, -1), anim: 'fut_parado' } });
  pessoa('refem_menino_b', 'Aluno', 1.47, [[42.25, -34.2]], { fixo: { giro: olharPara(0, 1), anim: 'gol_parado' } });
  // professora passando pela galeria do predio
  pessoa('professora', 'Professora', 1.64, [[-16, 1.5], [16, 1.5]], { vel: .95, pausa: [4, 9], uniforme: false });


  /* ---------------- futebol na quadra ----------------
     O atacante conduz a bola, as vezes para e domina, e chuta no gol; o goleiro acompanha a bola, defende (e segura)
     ou toma o gol, e repoe com a mao para o atacante, que domina e recomeca. A bola tem fisica simples (rola, quica). */
  const atac = pessoas[5], gole = pessoas[6];
  const ZG = 34.3, XG = 42.25, RB = .11, CHAO_B = .239 + RB;     // linha do gol (cena web) e altura da bola na quadra
  const texBola = (() => {
    const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const g = cv.getContext('2d');
    g.fillStyle = '#f4f4f0'; g.fillRect(0, 0, 256, 128); g.fillStyle = '#18191b';
    for (let i = 0; i < 12; i++) { const x = (i % 6) * 43 + (i < 6 ? 0 : 21), y = i < 6 ? 34 : 94; g.beginPath();
      for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2 - Math.PI / 2; g.lineTo(x + 11 * Math.cos(a), y + 13 * Math.sin(a)); } g.fill(); }
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const bola = new THREE.Mesh(new THREE.SphereGeometry(RB, 18, 12), ilum(new THREE.MeshStandardMaterial({ map: texBola, roughness: .5 })));
  bola.position.set(XG, CHAO_B, 21.5); scene.add(bola);
  const J = { estado: 'conduz', t: 0, vel: new THREE.Vector3(), vy: 0, alvo: new THREE.Vector3(), reagiu: false, pega: false, recebe: new THREE.Vector3(), mira: new THREE.Vector3() };
  const JV = new THREE.Vector3(), JF = new THREE.Vector3(), EIXO = new THREE.Vector3(), GOL = new THREE.Vector3(XG, 0, ZG);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const dur = (p, n) => p.n.userData.acoes?.[n]?.getClip().duration || 1;
  const anima = (p, n) => { if (p.n.userData.pose !== n) animar(p.n, n, 1e6, .2); };
  function virar(p, alvo, dt, k = 7) {
    JV.copy(alvo).sub(p.n.position); let d = Math.atan2(JV.x, JV.z) - p.n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); p.n.rotation.y += d * Math.min(1, dt * k);
  }
  function andar(p, alvo, vel, dt) {                        // anda ate o alvo (no chao); devolve a distancia que falta
    JV.copy(alvo).sub(p.n.position); JV.y = 0; const L = JV.length();
    if (L > .05) { p.n.position.addScaledVector(JV.normalize(), Math.min(L, vel * dt)); pisar(p.n); virar(p, alvo, dt); }
    return L;
  }
  const frente = p => JF.set(Math.sin(p.n.rotation.y), 0, Math.cos(p.n.rotation.y));
  function novoAlvo() { J.alvo.set(rnd(39, 45.5), 0, rnd(23, 28.5)); }
  function lancar(destino, vel, vy) { JV.copy(destino).sub(bola.position); JV.y = 0; J.vel.copy(JV.normalize().multiplyScalar(vel)); J.vy = vy; }
  function rolar(v, dt) { const s = Math.hypot(v.x, v.z); if (s > .01) { EIXO.set(v.z, 0, -v.x).normalize(); bola.rotateOnWorldAxis(EIXO, s * dt / RB); } }
  function fisica(dt) {
    bola.position.addScaledVector(J.vel, dt);
    J.vy -= 9.8 * dt; bola.position.y += J.vy * dt;
    if (bola.position.y < CHAO_B) { bola.position.y = CHAO_B; J.vy = Math.abs(J.vy) > 1.2 ? -J.vy * .45 : 0; J.vel.multiplyScalar(1 - Math.min(1, 1.1 * dt)); }
    const b = bola.position;                                   // laterais e fundo da quadra
    if (b.x < 35.6 || b.x > 48.9) { b.x = THREE.MathUtils.clamp(b.x, 35.6, 48.9); J.vel.x *= -.5; }
    if (b.z < 13) { b.z = 13; J.vel.z *= -.5; }
    if (b.z > ZG + 1.1) { b.z = ZG + 1.1; J.vel.multiplyScalar(.15); }       // rede do gol
    rolar(J.vel, dt);
  }
  function naFrente(p, d = .45) { frente(p); bola.position.set(p.n.position.x + JF.x * d, CHAO_B, p.n.position.z + JF.z * d); }
  function jogo(dt) {
    J.t += dt; const t = J.t;
    const ir = e => { J.estado = e; J.t = 0; };
    // goleiro: acompanha a bola de lado, no gol (salvo quando segura, repoe ou busca a bola na rede)
    if (!['segura', 'repoe', 'gol'].includes(J.estado)) {
      const gx = THREE.MathUtils.clamp(bola.position.x, XG - 1.4, XG + 1.4);
      gole.n.position.x += (gx - gole.n.position.x) * Math.min(1, dt * 2.2); gole.n.position.z = ZG - .1; pisar(gole.n);
      virar(gole, bola.position, dt, 5);
    }
    switch (J.estado) {
      case 'conduz': {                                        // atacante conduz a bola ate o ponto
        anima(atac, 'fut_trote'); if (gole.n.userData.pose !== 'gol_pega' || t > 1.5) anima(gole, 'gol_parado');
        const L = andar(atac, J.alvo, 2.1, dt); naFrente(atac); rolar(JV.copy(frente(atac)).multiplyScalar(2.1), dt);
        if (L < .35 || t > 4.5) ir(Math.random() < .3 ? 'domina' : 'mira');
        break; }
      case 'domina':                                          // para e domina a bola
        anima(atac, 'fut_dominar'); virar(atac, GOL, dt, 3); naFrente(atac, .32);
        if (t > Math.min(2.6, dur(atac, 'fut_dominar'))) ir('mira');
        break;
      case 'mira':                                            // ajeita o corpo para o gol e chuta
        if (t === dt || t < dt * 1.5) J.mira.set(XG + rnd(-1.3, 1.3), 0, ZG + .8);
        anima(atac, 'fut_parado'); virar(atac, J.mira, dt, 10); naFrente(atac);
        if (t > .35) { anima(atac, 'fut_chute'); ir('chute'); }
        break;
      case 'chute':
        naFrente(atac, .45 + t * .4);
        if (t > dur(atac, 'fut_chute') * .45) {
          lancar(J.mira, rnd(10, 13), rnd(.5, 3.2)); J.reagiu = false; J.pega = Math.random() < .62;
          J.recebe.set(rnd(39.5, 45), 0, rnd(21, 25)); ir('voo');
        }
        break;
      case 'voo': {
        fisica(dt);
        if (t > .4) { if (andar(atac, J.recebe, 1.6, dt) > .3) anima(atac, 'fut_trote'); else { anima(atac, 'fut_parado'); virar(atac, bola.position, dt, 4); } }
        if (!J.reagiu && ZG - bola.position.z < 4) { J.reagiu = true; anima(gole, 'gol_pega'); }
        JV.copy(bola.position).sub(gole.n.position); JV.y = 0;
        if (J.pega && JV.length() < 1.1 && bola.position.y < 1.9) { ir('segura'); break; }
        if (bola.position.z > ZG + .35) { ir('gol'); break; }
        if (Math.hypot(J.vel.x, J.vel.z) < .3 && bola.position.y <= CHAO_B + .01) { ir('busca'); }
        break; }
      case 'gol':                                             // bola na rede: o goleiro vai buscar
        fisica(dt);
        if (andar(atac, J.recebe, 1.6, dt) < .3) { anima(atac, 'fut_parado'); virar(atac, gole.n.position, dt, 3); } else anima(atac, 'fut_trote');
        if (t < 1.2) anima(gole, 'gol_parado');
        else { anima(gole, 'fut_trote'); if (andar(gole, bola.position, 1.4, dt) < .55) ir('segura'); }
        break;
      case 'busca':                                           // bola parou longe: o atacante busca e recomeca
        anima(atac, 'fut_trote'); if (andar(atac, bola.position, 2.2, dt) < .5) { novoAlvo(); ir('conduz'); }
        break;
      case 'segura': {                                        // goleiro com a bola nas maos, volta para o gol
        J.vel.set(0, 0, 0); J.vy = 0; frente(gole);
        bola.position.set(gole.n.position.x + JF.x * .28, gole.n.position.y + 1.0, gole.n.position.z + JF.z * .28);
        const longe = andar(gole, JV.set(gole.n.position.x, 0, ZG - .1), 1.2, dt);
        anima(gole, longe > .2 ? 'fut_trote' : 'gol_parado'); virar(gole, atac.n.position, dt, 4);
        if (andar(atac, J.recebe, 1.6, dt) < .3) { anima(atac, 'fut_parado'); virar(atac, gole.n.position, dt, 4); } else anima(atac, 'fut_trote');
        if (t > 1.6 && longe < .2) { anima(gole, 'gol_repoe'); ir('repoe'); }
        break; }
      case 'repoe':                                           // reposicao com a mao para o atacante
        frente(gole); bola.position.set(gole.n.position.x + JF.x * .25, gole.n.position.y + 1.0 + Math.min(.6, t), gole.n.position.z + JF.z * .25);
        if (t > dur(gole, 'gol_repoe') * .5) { lancar(atac.n.position, rnd(7.5, 9), 3.2); ir('volta'); }
        break;
      case 'volta': {                                         // a bola volta; o atacante domina
        fisica(dt); if (t > 1) anima(gole, 'gol_parado');
        JV.copy(bola.position).sub(atac.n.position); JV.y = 0; const L = JV.length();
        if (bola.position.y < .9 && L > .6) { anima(atac, 'fut_trote'); andar(atac, bola.position, 2.0, dt); }
        else if (L >= .6) { anima(atac, 'fut_parado'); virar(atac, bola.position, dt, 5); }
        if (L < .6 && bola.position.y < .9) { anima(atac, 'fut_receber'); J.vel.set(0, 0, 0); J.vy = 0; ir('recebe'); }
        if (t > 6) ir('busca');
        break; }
      case 'recebe':
        naFrente(atac, .4);
        if (t > Math.min(1.1, dur(atac, 'fut_receber'))) { novoAlvo(); ir('conduz'); }
        break;
    }
  }
  function resetJogo() { J.estado = 'conduz'; J.t = 0; J.vel.set(0, 0, 0); J.vy = 0; novoAlvo(); bola.position.set(XG, CHAO_B, 21.5); }
  novoAlvo();

  const V = new THREE.Vector3();
  let visivel = true, modo = 'normal';
  function mostrar(v) { if (v === visivel) return; visivel = v; for (const p of pessoas) p.n.visible = v && !p.fora; }

  /* ---------------- missao Sala 201: o patio no inicio da crise ----------------
     criseInicio(): todos no patio, parados. disparo(): gritos de criancas no 1o andar (sem tiro); quem anda ou joga na quadra sai correndo
     pelo portao da frente; os outros se agacham com medo. evacuar(): quando o policial manda tirar o patio (pela diretora),
     os que ficaram correm para os pilotis do lado oeste, longe da rampa. Ninguem e ferido. */
  const CORREM = [0, 1, 2, 5, 6];
  const saidaFrente = p => {
    const x = p.n.position.x, y = -p.n.position.z, r = [];
    if (x > 34) r.push([35.5, y]);                               // sai da quadra pela lateral (o alambrado fica nas pontas)
    if (x < -5) r.push([-6, -17]); else if (x > 5) r.push(y < -24 ? [8, -26] : [8, -20]);
    return [...r, [2.5, -30], [2.5, -37.8], [1.5, -48]].map(([a, b]) => B(a, b));
  };
  function reset() {
    for (const p of pessoas) {
      p.fuga = null; p.fora = false; p.n.visible = visivel; p.n.position.copy(p.rota[0]); pisar(p.n); p.i = 1; p.espera = Math.random() * 2;
      if (p.fixo) p.n.rotation.y = p.fixo.giro;
      animar(p.n, p.fixo?.anim || 'parada', 1e6, .2);
    }
  }
  function criseInicio() { modo = 'crise'; visivel = true; reset(); resetJogo(); }
  function disparo() {
    if (modo !== 'crise') return;
    pessoas.forEach((p, k) => {
      if (p.fora || p.fuga) return;
      if (CORREM.includes(k)) {
        p.fuga = saidaFrente(p); p.velF = 3.1 + Math.random() * .7;
        if (p.n.userData.acoes?.correndo) p.n.userData.acoes.correndo.timeScale = 1;
        setTimeout(() => animar(p.n, 'correndo', 1e6, .15), Math.random() * 500);
      } else {
        const a = p.n.userData.acoes?.agachado ? 'agachado' : 'nervoso';
        setTimeout(() => { p.n.userData.base = a; animar(p.n, a, 1e6, .25); }, 200 + Math.random() * 700);
      }
    });
  }
  function evacuar() {
    if (modo !== 'crise') return;
    for (const p of pessoas) {
      if (p.fora || p.fuga) continue;
      const y = -p.n.position.z;
      p.fuga = [[-34, y > -2 ? 1.5 : y], [-34, 12]].map(([a, b]) => B(a, b)); p.velF = 2.8 + Math.random() * .5;
      animar(p.n, 'correndo', 1e6, .2);
    }
  }
  function normal() { if (modo === 'normal') return; modo = 'normal'; reset(); resetJogo(); }
  function fugir(p, dt) {                                        // segue a rota de fuga e some ao chegar
    const alvo = p.fuga[0]; V.copy(alvo).sub(p.n.position); V.y = 0;
    const L = V.length();
    if (L < .3) { p.fuga.shift(); if (!p.fuga.length) { p.fuga = null; p.fora = true; p.n.visible = false; } return; }
    p.n.position.addScaledVector(V.normalize(), Math.min(L, p.velF * dt)); pisar(p.n);
    let d = Math.atan2(V.x, V.z) - p.n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
    p.n.rotation.y += d * Math.min(1, dt * 8);
  }

  function quadro(dt) {
    const t = performance.now();
    for (const f of ventiladores) {
      f.helice.rotation.x -= f.vel * dt;
      f.osc.rotation.y = Math.sin(t / 1000 * .45 + f.fase) * .6;
    }
    if (t > proxPisca) { piscaAte = t + 250 + Math.random() * 900; proxPisca = t + 4000 + Math.random() * 9000; }
    const off = t < piscaAte && Math.sin(t * .09) * Math.sin(t * .023) > -.1;
    mTubo.color.copy(off ? COR_OFF : COR_ON);
    bola.visible = visivel && modo === 'normal';
    if (!visivel) return;
    if (modo === 'crise') {
      for (const p of pessoas) { if (p.fora) continue; p.n.userData.mixer?.update(dt); if (p.fuga) fugir(p, dt); }
      return;
    }
    jogo(dt);
    for (const p of pessoas) {
      p.n.userData.mixer?.update(dt);
      if (p.fixo || p.rota.length < 2) continue;
      if (p.espera > 0) { p.espera -= dt; if (p.espera <= 0) animar(p.n, p.anim, 1e6, .3); continue; }
      const alvo = p.rota[p.i]; V.copy(alvo).sub(p.n.position); V.y = 0;
      const L = V.length();
      if (L < .15) {
        p.i = (p.i + 1) % p.rota.length; p.espera = THREE.MathUtils.randFloat(...p.pausa);
        animar(p.n, 'parada', 1e6, .35); continue;
      }
      p.n.position.addScaledVector(V.normalize(), Math.min(L, p.vel * dt)); pisar(p.n);
      let d = Math.atan2(V.x, V.z) - p.n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
      p.n.rotation.y += d * Math.min(1, dt * 6);
    }
  }
  const api = { J, bola, quadro, mostrar, criseInicio, disparo, evacuar, normal, emCrise: () => modo === 'crise' };
  window.__vida = { ...api, pessoas, ventiladores };
  return api;
}
