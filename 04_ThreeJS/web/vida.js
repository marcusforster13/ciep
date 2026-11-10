/*
  Vida da escola (so no site, sem bake):
  - ventiladores de parede das salas girando e oscilando (a chapa de fixacao vem do bake; motor, grade e helice daqui)
  - lampada fluorescente do corredor do 1o andar (perto da Sala 201) piscando de leve
  - modo normal: alunos de uniforme andando e conversando no patio, criancas correndo na quadra,
    uma professora passando pela galeria e uma servente varrendo. Somem na missao Sala 201 e quando a ameaca fica ativa.
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
  const mVent = ilum(new THREE.MeshStandardMaterial({ color: 0x232427, roughness: .5, metalness: .25 }));
  const junta = (pecas) => mergeGeometries(pecas.map(([g, pos, rot]) => { g = g.toNonIndexed(); g.deleteAttribute('uv');
    return g.applyMatrix4(new THREE.Matrix4().compose(new THREE.Vector3(...pos), new THREE.Quaternion().setFromEuler(new THREE.Euler(...rot)), new THREE.Vector3(1, 1, 1))); }));
  const centro = -.27, Q = Math.PI / 2;
  const pecasCab = [[new THREE.CylinderGeometry(.085, .095, .2, 14), [-.08, 0, 0], [0, 0, Q]], [new THREE.CylinderGeometry(.04, .04, .02, 12), [centro - .065, 0, 0], [0, 0, Q]]];
  for (const dx of [-.06, .06]) pecasCab.push([new THREE.TorusGeometry(.26, .006, 6, 36), [centro + dx, 0, 0], [0, Q, 0]]);     // grade: dois aros e raios
  for (let k = 0; k < 12; k++) { const a = k / 12 * Math.PI * 2; pecasCab.push([new THREE.BoxGeometry(.004, .26, .004), [centro - .06, Math.cos(a) * .13, Math.sin(a) * .13], [a, 0, 0]]); }
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
  await H.carregarPapeis?.(p => /^refem_|^professora$|^mae$/.test(p));
  function pessoa(papel, nome, alt, rota, { vel = 1.1, anim = 'andando', pausa = [2, 5], uniforme = true, cabelo = null, fixo = null } = {}) {
    const n = personagem(papel, nome, 0x3d4045, alt);
    n.userData.modelo?.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => ilum(m.clone())) : ilum(o.material.clone()); });
    if (uniforme && uniformizar && /^refem_/.test(papel)) uniformizar(n, papel);
    if (cabelo && cabeloCor) cabeloCor(n, cabelo, papel);
    const p = { n, rota: rota.map(([x, y]) => B(x, y)), i: 1, vel, anim, pausa, espera: Math.random() * 3, fixo };
    n.position.copy(p.rota[0]);
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
  // criancas correndo na quadra
  pessoa('refem_menino_a', 'Aluno', 1.45, [[40, -30], [41, -17]], { vel: 3.2, anim: 'correndo', pausa: [.3, 1.5] });
  pessoa('refem_menino_b', 'Aluno', 1.47, [[44.5, -17.5], [43.5, -30.5]], { vel: 3.0, anim: 'correndo', pausa: [.5, 2] });
  // professora passando pela galeria do predio
  pessoa('professora', 'Professora', 1.64, [[-16, 1.5], [16, 1.5]], { vel: .95, pausa: [4, 9], uniforme: false });
  // servente varrendo perto do jacaranda
  const servente = pessoa('mae', 'Servente', 1.62, [[-21.5, -17], [-19, -17.3], [-16.5, -17], [-19, -16.7]], { vel: .5, pausa: [5, 9], uniforme: false });
  const vassoura = new THREE.Group();
  const mCabo = ilum(new THREE.MeshStandardMaterial({ color: 0xc9b07a, roughness: .7 })), mCerda = ilum(new THREE.MeshStandardMaterial({ color: 0x2f6b34, roughness: .8 }));
  const cabo = new THREE.Mesh(new THREE.CylinderGeometry(.013, .013, 1.3, 6), mCabo); cabo.position.y = .65; vassoura.add(cabo);
  const cerda = new THREE.Mesh(new THREE.BoxGeometry(.32, .07, .06), mCerda); cerda.position.y = .03; vassoura.add(cerda);
  const pivo = new THREE.Group(); pivo.position.set(.12, 0, .55); pivo.add(vassoura); vassoura.rotation.x = -.45; servente.n.add(pivo);

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
      p.fuga = null; p.fora = false; p.n.visible = visivel; p.n.position.copy(p.rota[0]); p.i = 1; p.espera = Math.random() * 2;
      if (p.fixo) p.n.rotation.y = p.fixo.giro;
      animar(p.n, p.fixo?.anim || 'parada', 1e6, .2);
    }
  }
  function criseInicio() { modo = 'crise'; visivel = true; reset(); }
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
  function normal() { if (modo === 'normal') return; modo = 'normal'; reset(); }
  function fugir(p, dt) {                                        // segue a rota de fuga e some ao chegar
    const alvo = p.fuga[0]; V.copy(alvo).sub(p.n.position); V.y = 0;
    const L = V.length();
    if (L < .3) { p.fuga.shift(); if (!p.fuga.length) { p.fuga = null; p.fora = true; p.n.visible = false; } return; }
    p.n.position.addScaledVector(V.normalize(), Math.min(L, p.velF * dt));
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
    if (!visivel) return;
    if (modo === 'crise') {
      for (const p of pessoas) { if (p.fora) continue; p.n.userData.mixer?.update(dt); if (p.fuga) fugir(p, dt); }
      pivo.rotation.y = 0; return;
    }
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
      p.n.position.addScaledVector(V.normalize(), Math.min(L, p.vel * dt));
      let d = Math.atan2(V.x, V.z) - p.n.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
      p.n.rotation.y += d * Math.min(1, dt * 6);
    }
    // vassoura: vai e volta enquanto a servente esta parada
    const parada = servente.espera > 0;
    pivo.rotation.y = parada ? Math.sin(t / 1000 * 3.2) * .5 : 0;
  }
  const api = { quadro, mostrar, criseInicio, disparo, evacuar, normal, emCrise: () => modo === 'crise' };
  window.__vida = { ...api, pessoas, ventiladores };
  return api;
}
