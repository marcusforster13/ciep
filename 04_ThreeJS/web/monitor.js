/*
  Monitoramento pelo instrutor (portal XPTO VR).
  So e carregado quando o endereco tem ?monitor=1 (aluno transmite) ou ?espectador=1 (tela do instrutor, dentro do portal).
  Sem esses parametros o treinamento funciona exatamente como antes: este arquivo nem e baixado.

  aluno      : abre uma conexao direta (WebRTC, PeerJS) com o codigo mostrado na tela; envia so DADOS
               (pose da cabeca, personagens, estado do treinamento). Nao muda nada no jogo; se cair, o treino segue.
               Recebe do instrutor apenas mensagens de texto, mostradas como legenda.
  espectador : recebe esses dados do portal (postMessage) e redesenha a cena: visao do aluno ou camera de ombro.
*/
import * as THREE from 'three';

const ORIGENS_PORTAL = [/^https:\/\/portalxptovr(-[\w-]+)?\.vercel\.app$/, /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/, /^null$/, /^file:/];

export async function iniciar(ctx) {
  return ctx.modo === 'espectador' ? espectador(ctx) : aluno(ctx);
}

const trein = () => new Promise(res => { const t = () => window.__trein?._t?.H ? res(window.__trein) : setTimeout(t, 300); t(); });

/* ====================================================================== aluno */
async function aluno({ camera, scene, renderer, fase }) {
  const { Peer } = await import('https://cdn.jsdelivr.net/npm/peerjs@1.5.4/+esm');
  const T = await trein(), H = T._t.H, S = T.estado;

  // catalogo das acoes (textos, pontos, base legal) dos cenarios do site
  const catalogo = {}, nomesVar = {};
  for (const arq of ['treinamento/cenario_ms_01.json', 'treinamento/cenario_crise_01.json']) {
    try {
      const c = await fetch(window.__h ? window.__h(arq) : arq).then(r => r.json());
      Object.assign(nomesVar, c.nomes_variacao || {});
      for (const f of c.fases || []) for (const [lista, tipo] of [['acoes', 'acao'], ['erros', 'erro'], ['falhas_graves', 'grave']])
        for (const a of f[lista] || []) catalogo[a.id] = { texto: a.texto, pontos: a.pontos, base: a.base || '', tipo, fase: f.nome || f.id };
    } catch (e) { }
  }

  // selo na tela (2D) com o codigo
  const selo = document.createElement('div');
  selo.style.cssText = 'position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:9999;font:600 15px Segoe UI,sans-serif;color:#e8edf7;background:rgba(5,7,15,.85);border:1px solid #00d4e6;border-radius:999px;padding:8px 18px;letter-spacing:.04em;pointer-events:none';
  document.body.append(selo);
  const conexoes = new Set();
  let codigo = '', peer = null;
  const atualizarSelo = () => selo.innerHTML = `<span style="color:#ff5a5a">●</span> Monitoramento · código <b style="color:#5cf0ff;letter-spacing:.15em">${codigo}</b> · ${conexoes.size ? 'instrutor conectado' : 'aguardando instrutor'}`;
  const avisarVR = (t, s = 7, quem = 'Monitoramento') => { try { H.legenda(quem, t, s); } catch (e) { } };

  function abrir() {
    codigo = String(Math.floor(10000 + Math.random() * 90000));
    peer = new Peer('xptovr-' + codigo, { debug: 0 });
    peer.on('open', () => { atualizarSelo(); avisarVR(`Código para o instrutor: ${codigo}`, 10); });
    peer.on('error', e => { if (e.type === 'unavailable-id') { peer.destroy(); abrir(); } else console.warn('monitor:', e.type); });
    peer.on('disconnected', () => { try { peer.reconnect(); } catch (e) { } });
    peer.on('connection', c => {
      c.on('open', () => {
        conexoes.add(c); atualizarSelo(); avisarVR('Instrutor conectado.', 4);
        c.send({ tipo: 'ola', fase, titulo: document.title, url: location.origin + location.pathname, catalogo, nomesVar });
        enviarEstado(true);
      });
      c.on('data', m => {
        if (m?.tipo === 'mensagem' && typeof m.texto === 'string') avisarVR(m.texto.slice(0, 220), Math.min(14, 4 + m.texto.length / 18), 'Instrutor');
      });
      c.on('close', () => { conexoes.delete(c); atualizarSelo(); });
    });
  }
  abrir();
  renderer.xr.addEventListener('sessionstart', () => setTimeout(() => avisarVR(conexoes.size ? 'Monitoramento ativo.' : `Código para o instrutor: ${codigo}`, 8), 1500));

  const enviar = m => { for (const c of conexoes) if (c.open) try { c.send(m); } catch (e) { } };

  // pose da cabeca: 20 por segundo
  const P = new THREE.Vector3(), Q = new THREE.Quaternion();
  const r3 = v => Math.round(v * 1000) / 1000;
  setInterval(() => {
    if (!conexoes.size) return;
    const cam = renderer.xr.isPresenting ? renderer.xr.getCamera() : camera;
    cam.getWorldPosition(P); cam.getWorldQuaternion(Q);
    enviar({ tipo: 'pose', p: [r3(P.x), r3(P.y), r3(P.z)], q: [r3(Q.x), r3(Q.y), r3(Q.z), r3(Q.w)], vr: renderer.xr.isPresenting, arma: !!S.armaNaMao });
  }, 50);

  // personagens: 10 por segundo
  setInterval(() => {
    if (!conexoes.size) return;
    const lista = [];
    for (const n of scene.children) {
      if (!n.name?.startsWith('NPC_') || !n.visible || !n.userData?.real) continue;
      const u = n.userData;
      lista.push({ k: n.uuid, papel: u.papel, nome: u.nome, alt: r3(u.hit?.scale?.y || 1.7), p: [r3(n.position.x), r3(n.position.y), r3(n.position.z)], r: r3(n.rotation.y), a: u.pose || u.atual?.getClip?.().name?.replace(/\.\d+$/, '') || 'parada' });
    }
    enviar({ tipo: 'npcs', lista });
  }, 100);

  // estado do treinamento: 2 por segundo (e na hora em que algo e registrado)
  let nLog = -1, fimEnviado = 0;
  function enviarEstado(forcar) {
    if (!conexoes.size) return;
    const A = T._t.ocorrencia?.();
    if (!forcar && S.log.length === nLog && !(S.fim && S.fim !== fimEnviado)) { enviar({ tipo: 'relogio', ativo: S.ativo, t: S.ativo ? (performance.now() - S.inicio) / 1000 : null }); return; }
    nLog = S.log.length;
    const est = {
      tipo: 'estado', ativo: S.ativo, modo: S.historia ? 'historia' : S.modo, t: S.inicio ? ((S.fim || performance.now()) - S.inicio) / 1000 : 0,
      variacao: S.variacao, ocorrencia: A ? { titulo: A.titulo, n: A.n, fatos: A.fatos || [] } : null,
      feitos: [...S.feitos.entries()], erros: S.erros.map(e => ({ id: e.id, texto: e.texto, pontos: e.pontos, t: e.t })),
      graves: S.graves.map(g => ({ id: g.id, texto: g.texto, pontos: g.pontos, base: g.base, t: g.t })), log: S.log.slice(-200)
    };
    if (S.fim && S.fim !== fimEnviado) { fimEnviado = S.fim; try { est.relatorio = T.relatorio(); } catch (e) { } }
    enviar(est);
  }
  setInterval(() => enviarEstado(false), 500);
}

/* ================================================================= espectador */
async function espectador({ camera, scene, renderer, rig }) {
  // tela limpa: so a cena
  const canvas = renderer.domElement;
  const limpar = () => { for (const el of document.body.children) if (el !== canvas && !el.contains(canvas) && el.tagName !== 'SCRIPT') el.style.display = 'none'; };
  limpar(); setTimeout(limpar, 2000); setTimeout(limpar, 6000);
  window.__som?.mudo?.(true);

  const T = await trein(), H = T._t.H;
  let uniformizar = null;
  try { ({ uniformizar } = await import('./' + (window.__h ? window.__h('crise.js') : 'crise.js'))); } catch (e) { }

  // avatar do aluno (aparece na camera de ombro)
  const corpo = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0x0a2a3a, emissive: 0x00d4e6, emissiveIntensity: .35, roughness: .5 });
  const tronco = new THREE.Mesh(new THREE.CapsuleGeometry(.22, .9, 6, 12), mat); tronco.position.y = -.85; corpo.add(tronco);
  const cabeca = new THREE.Mesh(new THREE.SphereGeometry(.13, 16, 12), mat); corpo.add(cabeca);
  const visor = new THREE.Mesh(new THREE.BoxGeometry(.2, .08, .08), new THREE.MeshBasicMaterial({ color: 0x5cf0ff })); visor.position.set(0, .01, -.12); cabeca.add(visor);
  const anel = new THREE.Mesh(new THREE.RingGeometry(.45, .52, 40), new THREE.MeshBasicMaterial({ color: 0x00d4e6, transparent: true, opacity: .8, side: THREE.DoubleSide }));
  anel.rotation.x = -Math.PI / 2; scene.add(anel); scene.add(corpo);

  let vista = 'aluno', alvoP = null, alvoQ = null;
  const pos = new THREE.Vector3(), quat = new THREE.Quaternion(), E = new THREE.Euler(0, 0, 0, 'YXZ');
  const espelhos = new Map(); let listaNPC = [];

  addEventListener('message', ev => {
    if (!ORIGENS_PORTAL.some(r => r.test(ev.origin))) return;
    const m = ev.data; if (!m || typeof m !== 'object') return;
    if (m.tipo === 'pose') { alvoP = new THREE.Vector3(...m.p); alvoQ = new THREE.Quaternion(...m.q); }
    else if (m.tipo === 'npcs') listaNPC = m.lista || [];
    else if (m.tipo === 'vista') vista = m.vista;
  });
  parent !== window && parent.postMessage({ tipo: 'espectador-pronto' }, '*');

  // espelha os personagens do aluno; esconde os que o espectador criou sozinho
  const criando = new Set();
  async function sincronizar() {
    const vivos = new Set(listaNPC.map(n => n.k));
    for (const [k, e] of espelhos) if (!vivos.has(k)) { scene.remove(e.n); espelhos.delete(k); }
    for (const d of listaNPC) {
      let e = espelhos.get(d.k);
      if (!e && !criando.has(d.k)) {
        criando.add(d.k);
        H.carregarPapeis(p => p === d.papel).then(() => {
          const n = H.personagem(d.papel, d.nome, 0x3d4045, d.alt);
          n.name = 'ESP_' + d.nome; n.position.set(...d.p); n.rotation.y = d.r;
          if (/^refem_/.test(d.papel) && uniformizar) try { uniformizar(n, d.papel); } catch (er) { }
          scene.add(n); espelhos.set(d.k, { n, d, anim: null }); criando.delete(d.k);
        }).catch(() => criando.delete(d.k));
        continue;
      }
      if (e) e.d = d;
    }
    for (const n of scene.children) if (n.name?.startsWith('NPC_')) n.visible = false;
  }
  setInterval(sincronizar, 150);

  const relogio = new THREE.Clock(), V = new THREE.Vector3(), atras = new THREE.Vector3();
  const anterior = scene.onBeforeRender;
  scene.onBeforeRender = (...args) => {
    anterior?.(...args);
    const dt = Math.min(relogio.getDelta(), .1), k = 1 - Math.exp(-dt * 14);
    for (const e of espelhos.values()) {
      const { n, d } = e;
      n.position.lerp(V.set(...d.p), k);
      let dr = d.r - n.rotation.y; dr = Math.atan2(Math.sin(dr), Math.cos(dr)); n.rotation.y += dr * k;
      if (e.anim !== d.a) { e.anim = d.a; try { H.animar(n, d.a, 1e6, .35); } catch (er) { } }
      n.userData.mixer?.update(dt);
      n.updateMatrixWorld(true);
    }
    if (!alvoP) return;
    pos.lerp(alvoP, k); quat.slerp(alvoQ, k);
    if (pos.lengthSq() === 0) { pos.copy(alvoP); quat.copy(alvoQ); }
    E.setFromQuaternion(quat);
    corpo.position.copy(pos); corpo.rotation.set(0, E.y, 0); cabeca.rotation.set(E.x, 0, 0);
    tronco.position.y = -.85; anel.position.set(pos.x, Math.max(0, pos.y - 1.58), pos.z);
    rig.rotation.set(0, 0, 0); rig.position.set(0, 0, 0);
    if (vista === 'aluno') {
      corpo.visible = false; anel.visible = false;
      camera.position.copy(pos); camera.quaternion.copy(quat);
    } else {
      corpo.visible = true; anel.visible = true;
      atras.set(Math.sin(E.y), 0, Math.cos(E.y)).multiplyScalar(2.2);
      camera.position.set(pos.x + atras.x, pos.y + .7, pos.z + atras.z);
      camera.lookAt(pos.x - atras.x * .8, pos.y - .25, pos.z - atras.z * .8);
    }
    rig.updateMatrixWorld(true); corpo.updateMatrixWorld(true); anel.updateMatrixWorld(true);
  };
}
