/*
  Missao "Sala 201" - crise com refens na escola (gerenciamento de crise e negociacao)
  Le treinamento/cenario_crise_01.json. Usa as pecas do motor (treinamento.js) recebidas em H.
  Papeis: 'interventor' (fase 1), 'negociador' (fase 2) ou 'completo' (as duas).
  Doutrina: conter, isolar, contato sem concessoes; quem negocia nao comanda; criterios de acao; agressor ativo -> intervencao imediata.
  Variacoes forcadas pela URL (instrutor): ?v=arma:faca,motivo:vinganca,pressao:mae,virada:ataque
*/
import * as THREE from 'three';

export async function iniciarCrise(H, { papel, modo }) {
  const { scene, camera, rig, renderer, ctx, menu, dialogo, legenda, diz, radio, personagem, animar, B, olharPara, npcs } = H;
  const CEN = await fetch(H.HQ('treinamento/cenario_crise_01.json')).then(r => r.json());
  const F = CEN.falas, NG = CEN.negociacao;
  const V = new THREE.Vector3(), V2 = new THREE.Vector3();
  const P1 = 3.5;                                               // piso do 1o andar na cena web (FZ + 3,35)
  const B1 = (x, y) => new THREE.Vector3(x, P1, -y);
  const espera = ms => new Promise(r => setTimeout(r, ms));
  const treino = modo !== 'avaliacao';
  const dica = (t, s = 7) => { if (treino) legenda('Dica do instrutor', t, s); };

  /* ---------------- variacao ---------------- */
  const forc = Object.fromEntries((new URLSearchParams(location.search).get('v') || '').split(',').filter(Boolean).map(p => p.split(':')));
  const v = {}; for (const [k, ops] of Object.entries(CEN.variacoes)) v[k] = forc[k] && ops.includes(forc[k]) ? forc[k] : ops[Math.floor(Math.random() * ops.length)];

  /* ---------------- estado e pontuacao ---------------- */
  const C = { papel, modo, v, fase: 'chegada', t0: performance.now(), tensao: 70, vinculo: 5, feitos: new Map(), erros: [], graves: [], log: [], fatos: {}, refens: 10,
    turno: 0, live: v.motivo === 'notoriedade', espectadores: 380, mensagens: [], exig: null, contato: false, bopeChegou: false, acionou: false, fim: false, fila: 0 };
  const acoes = {};
  CEN.fases.forEach(f => {
    (f.acoes || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'acao', modo: f.modo });
    (f.erros || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'erro' });
    (f.falhas_graves || []).forEach(a => acoes[a.id] = { ...a, fase: f.id, tipo: 'grave' });
  });
  const tempo = () => (performance.now() - C.t0) / 1000;
  const condOk = c => { if (!c) return true; const m = c.match(/variacao\.(\w+)\s*(==|!=)\s*'([^']*)'/); return !m || (m[2] === '==' ? v[m[1]] === m[3] : v[m[1]] !== m[3]); };
  function registrar(id, extra = '') {
    const a = acoes[id]; if (!a || C.fim) return;
    if (a.tipo === 'acao') { if (C.feitos.has(id) || !condOk(a.condicao)) return; C.feitos.set(id, tempo()); }
    else if (a.tipo === 'erro') { if (C.erros.some(e => e.id === id)) return; C.erros.push({ id, texto: a.texto, pontos: a.pontos, t: tempo() }); }
    else { if (C.graves.some(e => e.id === id)) return; C.graves.push({ id, texto: a.texto, pontos: a.pontos, base: a.base, t: tempo() }); legenda('Instrutor', 'Falha grave: ' + a.texto, 5); }
    C.log.push({ t: +tempo().toFixed(1), id, extra }); status();
  }
  const ajusta = ([dt, dv]) => { C.tensao = Math.max(0, Math.min(100, C.tensao + dt)); C.vinculo = Math.max(0, Math.min(100, C.vinculo + dv)); status(); conferirTensao(); };

  /* ---------------- personagens ---------------- */
  H.limparNPCs(); H.armaNPC.visible = false; H.armaSolta.visible = false;
  const ilum = n => n.userData.modelo?.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => ctx.iluminar(m.clone())) : ctx.iluminar(o.material.clone()); });
  function npc(chave, papel, nome, pos, olha, voz = 'm', alt = 1.75, visivel = true) {
    const n = personagem(papel, nome, 0x3d4045, alt); ilum(n);
    Object.assign(n.userData, { chave, voz, fig: true, giroBase: olha, altura: alt });
    n.position.copy(pos); n.rotation.y = olha; n.visible = visivel; scene.add(n); npcs[chave] = n; if (n.userData.hit) n.userData.hit.userData.npc = chave;
    return n;
  }
  // roupa diferente para cada crianca: recolore so o que nao e pele (uniforme branco e cores variadas)
  const cacheRoupa = {};
  function variarRoupa(n, cor, chaveCache) {
    n.userData.modelo?.traverse(o => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) {
        const img = m.map?.image; if (!img || !/body/i.test(m.name + (m.map.name || ''))) continue;
        const k = chaveCache + '|' + cor; let tex = cacheRoupa[k];
        if (!tex) {
          const cv = document.createElement('canvas'); cv.width = img.width; cv.height = img.height; const g = cv.getContext('2d'); g.drawImage(img, 0, 0);
          const d = g.getImageData(0, 0, cv.width, cv.height), p = d.data, alvo = new THREE.Color(cor);
          for (let i = 0; i < p.length; i += 4) {
            const r = p[i], gg = p[i + 1], b = p[i + 2];
            const pele = r > 90 && gg > 40 && b > 20 && r > gg && r > b && r - Math.min(gg, b) > 15 && Math.abs(r - gg) > 12;
            if (pele) continue;
            const l = (r * .3 + gg * .59 + b * .11) / 255, f = .35 + .9 * l;
            p[i] = Math.min(255, alvo.r * 255 * f); p[i + 1] = Math.min(255, alvo.g * 255 * f); p[i + 2] = Math.min(255, alvo.b * 255 * f);
          }
          g.putImageData(d, 0, 0); tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = m.map.flipY; cacheRoupa[k] = tex;
        }
        m.map = tex; m.needsUpdate = true;
      }
    });
  }
  // uniforme da rede municipal: camiseta branca com faixa azul-marinho no peito e filete azul-claro (sem logo oficial),
  // bermuda/calca azul-marinho; o tenis fica com a cor original.
  // Separa por altura de cada triangulo do corpo (pose de bind): pinta uma mascara no espaco UV e recolore a textura
  // preservando o sombreado (dobras) e pulando a pele.
  const cacheUniforme = {};
  function uniformizar(n, chaveCache) {
    n.userData.modelo?.traverse(o => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) {
        const img = m.map?.image; if (!img || !/body/i.test(m.name + (m.map.name || ''))) continue;
        let tex = cacheUniforme[chaveCache];
        if (!tex) {
          const W = img.width, Hh = img.height, g = o.geometry, pos = g.attributes.position, uv = g.attributes.uv, idx = g.index;
          if (!uv) continue;
          let y0 = 1e9, y1 = -1e9; for (let i = 0; i < pos.count; i++) { const y = pos.getY(i); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
          const mk = document.createElement('canvas'); mk.width = W; mk.height = Hh; const mg = mk.getContext('2d');
          const tri = idx ? idx.count / 3 : pos.count / 3, vy = v => m.map.flipY ? (1 - uv.getY(v)) * Hh : uv.getY(v) * Hh;
          // altura h (0 = pe, 1 = pescoco) e posicao lateral xn (em alturas) interpoladas pixel a pixel: em cada triangulo
          // sao afins no plano UV, entao um gradiente linear do canvas reproduz o valor exato (sem serrilhado).
          const mkX = document.createElement('canvas'); mkX.width = W; mkX.height = Hh; const mx = mkX.getContext('2d');
          const pintar = (ctx, P, val) => {
            const ax = P[1][0] - P[0][0], ay = P[1][1] - P[0][1], bx = P[2][0] - P[0][0], by = P[2][1] - P[0][1], det = ax * by - ay * bx;
            let fill = `rgb(${Math.round(val[0] * 255)},0,0)`;
            if (Math.abs(det) > 1e-6) {
              const d1 = val[1] - val[0], d2 = val[2] - val[0], ga = (d1 * by - d2 * ay) / det, gb = (ax * d2 - bx * d1) / det, g2 = ga * ga + gb * gb;
              if (g2 > 1e-12) {
                const k0 = -val[0] / g2, k1 = (1 - val[0]) / g2;
                fill = ctx.createLinearGradient(P[0][0] + ga * k0, P[0][1] + gb * k0, P[0][0] + ga * k1, P[0][1] + gb * k1);
                fill.addColorStop(0, 'rgb(0,0,0)'); fill.addColorStop(1, 'rgb(255,0,0)');
              }
            }
            ctx.fillStyle = fill; ctx.strokeStyle = fill; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]); ctx.lineTo(P[1][0], P[1][1]); ctx.lineTo(P[2][0], P[2][1]); ctx.closePath(); ctx.fill(); ctx.stroke();
          };
          const ALT = y1 - y0;
          for (let t = 0; t < tri; t++) {
            const vi = [0, 1, 2].map(j => idx ? idx.getX(3 * t + j) : 3 * t + j), P = vi.map(v => [uv.getX(v) * W, vy(v)]);
            pintar(mg, P, vi.map(v => (pos.getY(v) - y0) / ALT));
            pintar(mx, P, vi.map(v => Math.min(1, Math.max(0, pos.getX(v) / ALT / 1.2 + .5))));   // xn de -0,6 a +0,6
          }
          const mp = mg.getImageData(0, 0, W, Hh).data, mq = mx.getImageData(0, 0, W, Hh).data;
          // tom de pele da propria crianca (media dos pixels de pele do rosto) para os antebracos da manga curta
          let pr = 0, pg = 0, pb = 0, pn = 0;
          n.traverse(q => { if (q.isMesh && /head/i.test([].concat(q.material)[0].name)) { const hi = [].concat(q.material)[0].map?.image; if (!hi) return;
            const c2 = document.createElement('canvas'); c2.width = 128; c2.height = 128; const x2 = c2.getContext('2d'); x2.drawImage(hi, 0, 0, 128, 128);
            const dd = x2.getImageData(32, 40, 64, 48).data;
            for (let i = 0; i < dd.length; i += 4) { const r = dd[i], g2 = dd[i + 1], b2 = dd[i + 2]; if (r > g2 && g2 > b2 && r - b2 > 15) { pr += r; pg += g2; pb += b2; pn++; } } } });
          const PELE = pn ? [pr / pn, pg / pn, pb / pn] : [190, 140, 110];
          const cv = document.createElement('canvas'); cv.width = W; cv.height = Hh; const cg = cv.getContext('2d'); cg.drawImage(img, 0, 0);
          const d = cg.getImageData(0, 0, W, Hh), p = d.data;
          // sombreado suave do tecido (dobras) sem a estampa original: luminancia da textura borrada
          const cb = document.createElement('canvas'); cb.width = W; cb.height = Hh; const bg = cb.getContext('2d'); bg.filter = 'blur(10px)'; bg.drawImage(img, 0, 0);
          const pb_ = bg.getImageData(0, 0, W, Hh).data;
          const BR = [244, 244, 240], AZ = [28, 40, 78], FAIXA = [22, 58, 112], FILETE = [70, 170, 225];
          const TRONCO = .15, OMBRO = [.15, .86], MANGA = .13, FX = chaveCache === 'aluno' ? [.74, .79] : [.82, .875];   // faixa: adulto tem o peito mais baixo                       // em fracoes da altura ate o pescoco
          for (let i = 0; i < p.length; i += 4) {
            if (mp[i + 3] < 40) continue;                                             // fora da malha
            const r = p[i], gg = p[i + 1], bb = p[i + 2], h = mp[i] / 255, xn = Math.abs(mq[i] / 255 * 1.2 - .6);
            const sat = r - bb, gr_ = gg / Math.max(1, r);
            const noTronco = xn <= TRONCO && h >= .5 && h < .93;                      // tronco coberto pela camiseta: ali nao ha pele
            const naCoxa = xn <= .2 && h >= .3 && h < .5;                                 // coxa coberta pela bermuda: tambem nao
            const pele = !noTronco && !naCoxa && r > 60 && r > gg && gg > bb && sat > 15 && sat < 140 && gr_ > .55 && gr_ < .92;
            if (pele || h < .07) continue;                                            // pele e tenis ficam como estao
            const l = (r * .3 + gg * .59 + bb * .11) / 255, lb = (pb_[i] * .3 + pb_[i + 1] * .59 + pb_[i + 2] * .11) / 255;
            let alvo;
            if (xn > TRONCO && h > .45) {                                             // braco: manga curta e antebraco de pele
              if (Math.hypot(xn - OMBRO[0], h - OMBRO[1]) < MANGA) alvo = BR;
              else { const f = .85 + .3 * (l - .5); p[i] = Math.min(255, PELE[0] * f); p[i + 1] = Math.min(255, PELE[1] * f); p[i + 2] = Math.min(255, PELE[2] * f); continue; }
            } else if (h < .5) { if (xn > .2) continue; alvo = AZ; }                   // calca (maos ficam)
            else alvo = (h > FX[0] && h < FX[1]) ? FAIXA : (h > FX[0] - .015 && h <= FX[0]) ? FILETE : BR;   // camiseta com faixa no peito
            const f = alvo === AZ ? .45 + .9 * l : .8 + .3 * (lb - .5);                 // camiseta/faixa: so as dobras, sem a estampa
            p[i] = Math.min(255, alvo[0] * f); p[i + 1] = Math.min(255, alvo[1] * f); p[i + 2] = Math.min(255, alvo[2] * f);
          }
          cg.putImageData(d, 0, 0); tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = m.map.flipY; cacheUniforme[chaveCache] = tex;
        }
        m.map = tex; m.needsUpdate = true;
      }
    });
  }
  // cabelo: o pacote so tem uma menina sem hijab; cada uma ganha um tom de cabelo (pinta a regiao do cabelo na textura da cabeca:
  // triangulos do alto e da parte de tras da cabeca; a testa e o rosto, virados para a frente, ficam de fora)
  function cabeloCor(n, cor, chave) {
    n.userData.modelo?.traverse(o => {
      if (!o.isMesh) return;
      const m0 = [].concat(o.material)[0]; if (!/head/i.test(m0.name) || !m0.map?.image) return;
      const k = chave + '|' + cor; let tex = cacheUniforme[k];
      if (!tex) {
        const img = m0.map.image, W = img.width, Hh = img.height, g = o.geometry, pos = g.attributes.position, nor = g.attributes.normal, uv = g.attributes.uv, idx = g.index;
        let y0 = 1e9, y1 = -1e9; for (let i = 0; i < pos.count; i++) { y0 = Math.min(y0, pos.getY(i)); y1 = Math.max(y1, pos.getY(i)); }
        const mk = document.createElement('canvas'); mk.width = W; mk.height = Hh; const mg = mk.getContext('2d'); mg.fillStyle = '#fff';
        const vy = v => m0.map.flipY ? (1 - uv.getY(v)) * Hh : uv.getY(v) * Hh, tri = idx ? idx.count / 3 : pos.count / 3;
        for (let t = 0; t < tri; t++) {
          const vi = [0, 1, 2].map(j => idx ? idx.getX(3 * t + j) : 3 * t + j);
          const h = vi.reduce((a, v) => a + (pos.getY(v) - y0) / (y1 - y0), 0) / 3, nz = vi.reduce((a, v) => a + nor.getZ(v), 0) / 3;
          if (!(h > .8 || (nz < .35 && h > .3))) continue;                  // alto da cabeca, ou laterais/nuca
          mg.beginPath(); vi.forEach((v, j) => j ? mg.lineTo(uv.getX(v) * W, vy(v)) : mg.moveTo(uv.getX(v) * W, vy(v))); mg.closePath(); mg.fill();
        }
        const mp = mg.getImageData(0, 0, W, Hh).data, cv = document.createElement('canvas'); cv.width = W; cv.height = Hh; const cg = cv.getContext('2d'); cg.drawImage(img, 0, 0);
        const d = cg.getImageData(0, 0, W, Hh), p = d.data, alvo = new THREE.Color(cor);
        for (let i = 0; i < p.length; i += 4) {
          if (mp[i + 3] < 128) continue;
          if (p[i] > 140 && p[i + 2] / p[i] > .62) continue;                    // pele clara (orelha, bochecha) fica
          const l = (p[i] * .3 + p[i + 1] * .59 + p[i + 2] * .11) / 255, f = .35 + 1.3 * l;
          p[i] = Math.min(255, alvo.r * 255 * f); p[i + 1] = Math.min(255, alvo.g * 255 * f); p[i + 2] = Math.min(255, alvo.b * 255 * f);
        }
        cg.putImageData(d, 0, 0); tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = m0.map.flipY; cacheUniforme[k] = tex;
      }
      const m = m0.clone(); m.map = tex; if (Array.isArray(o.material)) { o.material = o.material.slice(); o.material[0] = m; } else o.material = m;
    });
  }
  // Sala 201: a professora sentada a frente do quadro, sob a ameaca do Lucas (revolver apontado para a cabeca dela, ou faca
  // na mao, atras dela, sem encostar); a turma agachada no canto da frente, visivel da porta por cima das carteiras.
  const PROF = [11.75, 4.4], FR = [1, .15], FL = Math.hypot(...FR), fx = FR[0] / FL, fy = FR[1] / FL;   // para onde ela olha (a sala)
  const cadeiraProf = (() => {
    const gC = new THREE.Group(), mv = new THREE.MeshStandardMaterial({ color: 0x2f8a4f, roughness: .55 }), me = new THREE.MeshStandardMaterial({ color: 0x1f5a34, roughness: .5, metalness: .2 });
    const bx = (w, h, d, x, y, z, m) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); gC.add(o); };
    bx(.42, .035, .4, 0, .44, 0, mv); bx(.4, .26, .03, 0, .72, -.2, mv);
    for (const sx of [-.19, .19]) for (const sz of [-.17, .17]) bx(.022, .44, .022, sx, .22, sz, me);
    for (const sx of [-.19, .19]) bx(.022, .44, .022, sx, .66, -.2, me);
    gC.position.copy(B1(...PROF)); gC.rotation.y = olharPara(fx, fy); scene.add(gC); return gC;
  })();
  const posLucas = [PROF[0] - fx * .2 - fy * .78, PROF[1] - fy * .2 + fx * .78];                             // ao lado dela, um pouco atras
  const lucas = npc('lucas', 'aluno', 'Lucas (aluno, 15 anos)', B1(...posLucas), olharPara(PROF[0] - posLucas[0] + fx * .05, PROF[1] - posLucas[1] + fy * .05), 'j', 1.66);
  // revolver ou faca apontados para a cabeca dela (sem gestos de ocioso)
  lucas.userData.base = 'apontando'; lucas.userData.fig = false; animar(lucas, lucas.userData.base, 1e6, 0); lucas.userData.semVirar = true;
  uniformizar(lucas, 'aluno');                                                     // ele tambem e aluno da 901: de uniforme
  const faca = new THREE.Mesh(new THREE.BoxGeometry(.025, .22, .012), new THREE.MeshStandardMaterial({ color: 0xc9ccd0, metalness: .5, roughness: .3 }));
  faca.visible = v.arma === 'faca'; scene.add(faca);
  if (v.arma === 'revolver') { H.armaNPC.visible = true; lucas.userData.arma = H.armaNPC; }
  const PAPEIS_KIDS = ['refem_menino_a', 'refem_menina_a', 'refem_menino_b', 'refem_menina_b'];
  const CORES = ['#f2f2ee', '#f2f2ee', '#2f5f9e', '#f2f2ee', '#7a7f86', '#f2f2ee', '#3d7a4a', '#f2f2ee', '#8a2a2a', '#f2f2ee'];
  const kids = [];
  for (let k = 0; k < 10; k++) {
    const papelK = PAPEIS_KIDS[k % 4], x = 10.75 + (k % 2) * .75 + (Math.random() - .5) * .08, y = .95 + Math.floor(k / 2) * .58;
    const n = npc('refem_' + k, papelK, k === 8 ? 'Bia (aluna ferida)' : 'Aluno da 901', B1(x, y), olharPara(1, .35 + Math.random() * .2), /menina/.test(papelK) ? 'f' : 'j', 1.42 + Math.random() * .16);
    n.userData.base = 'agachado'; n.userData.semVirar = true; n.userData.fig = false; animar(n, 'agachado', 1e6, 0);
    if (n.userData.acoes?.agachado) n.userData.acoes.agachado.time = Math.random() * 2;
    uniformizar(n, papelK);
    if (/menina/.test(papelK)) { const tons = ['#2b1d14', '#141010', '#5a3b22', '#7a5634', null], tom = tons[(k >> 1) % tons.length]; if (tom) cabeloCor(n, tom, papelK); }
    kids.push(n);
  }
  const professora = npc('professora', 'professora', 'Professora Cláudia', B1(...PROF), olharPara(fx, fy), 'f', 1.64);
  const poseProf = professora.userData.acoes?.sentada_nervosa ? 'sentada_nervosa' : professora.userData.acoes?.sentado_parado ? 'sentado_parado' : 'agachado';
  professora.userData.base = poseProf; professora.userData.semVirar = true; animar(professora, poseProf, 1e6, 0);
  if (poseProf !== 'agachado') { professora.position.y += .46 - .925 * (1.64 / 1.78); professora.userData.sentado = true; }   // assento da cadeira (mesma regra do aluno sentado)
  lucas.rotation.order = 'YXZ'; lucas.rotation.x = .14;                                        // inclinado para a frente: a arma na altura da cabeca dela
  const diretora = npc('diretora', 'diretora', 'Diretora', B(PX(1.5), -35.8), olharPara(0, -1), 'f', 1.66);
  const parceiro = npc('parceiro', 'pm_parceiro', 'Policial parceiro', B(7.0, -41.0), olharPara(-.3, 1), 'm', 1.8);
  const pai = npc('pai', 'responsavel', v.pressao === 'pai' ? 'Pai de aluna' : 'Pai de aluno', B(PX(-1.2), -36.4), olharPara(0, 1), 'm', 1.78);
  pai.userData.base = 'irritado'; animar(pai, 'irritado', 1e6, 0);
  const comandante = npc('comandante', 'pm_apoio', 'Comandante da cena (BOPE)', B(9.0, -29.5), olharPara(-1, 0), 'm', 1.8, false);
  const negociador = npc('negociador', 'negociador', 'Negociador (BOPE)', B(10.5, -29.0), olharPara(-1, 0), 'm', 1.8, false);
  const mae = npc('mae', 'mae', 'Mãe do Lucas', B(PX(1.0), -39.5), olharPara(0, 1), 'f', 1.62, false);
  function PX(dx) { return 2.5 + dx; }

  /* ---------------- objetos da missao (sem novo bake: criados aqui) ---------------- */
  const grupo = new THREE.Group(); scene.add(grupo);
  const matB = (cor, r = .7) => ctx.iluminar(new THREE.MeshStandardMaterial({ color: cor, roughness: r }));
  const caixa = (tam, pos, m, pai = grupo) => { const o = new THREE.Mesh(new THREE.BoxGeometry(...tam), m); o.position.copy(pos); pai.add(o); return o; };
  // porta da sala 201, trancada, com visor de vidro; e a barricada de carteiras por dentro
  const porta = new THREE.Group(); porta.position.copy(B1(14.5, 9.5)); grupo.add(porta);
  caixa([.9, 2.08, .045], new THREE.Vector3(.45, 1.04, 0), matB(0xe6b31e, .45), porta);
  const visor = caixa([.22, .5, .05], new THREE.Vector3(.62, 1.45, 0), new THREE.MeshStandardMaterial({ color: 0x9fb5bd, transparent: true, opacity: .25, roughness: .05 }), porta);
  const colPorta = new THREE.Mesh(new THREE.BoxGeometry(.95, 2.1, .2), new THREE.MeshBasicMaterial({ visible: false })); colPorta.position.copy(B1(14.95, 9.5)).add(new THREE.Vector3(0, 1.05, 0));
  colPorta.geometry.computeBoundsTree?.(); scene.add(colPorta); colPorta.updateMatrixWorld(true); ctx.colisao().push(colPorta);
  for (let k = 0; k < 4; k++) caixa([.6, .03, .45], B1(14.8 + (k % 2) * .25, 8.9 - (k > 1 ? .3 : 0)).add(new THREE.Vector3(0, .72 + k * .3, 0)), matB(0xeeeeea), grupo).rotation.set(.2 * k, .5 * k, .15);
  // posto de comando, viaturas, ambulancia e fita de isolamento (aparecem quando acionados)
  const posto = new THREE.Group(); posto.visible = false; grupo.add(posto);
  const viatura = ctx.cena.getObjectByName('Viatura_PM');
  if (viatura) {
    const bope = viatura.clone(true); bope.position.copy(B(8.0, -33.0)); bope.rotation.y = Math.PI / 2;
    const pinta = m => { const c = m.clone(); if (!/vidro|glass|pneu|wheel|tire|optic/i.test(c.name)) c.color?.setHex(0x1d1f22); return c; };
    bope.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(pinta) : pinta(o.material); });
    posto.add(bope);
    const amb = viatura.clone(true); amb.position.copy(B(14.0, -34.5)); amb.rotation.y = Math.PI / 2; posto.add(amb);
  }
  caixa([1.8, .05, .8], B(9.6, -28.0).add(new THREE.Vector3(0, .75, 0)), matB(0xd8d8d0), posto);
  for (const [dx, dz] of [[-.8, -.35], [.8, -.35], [-.8, .35], [.8, .35]]) caixa([.04, .75, .04], B(9.6 + dx, -28.0 - dz).add(new THREE.Vector3(0, .37, 0)), matB(0x555555), posto);
  caixa([.28, .02, .2], B(9.4, -28.0).add(new THREE.Vector3(0, .79, 0)), new THREE.MeshBasicMaterial({ color: 0x3a6fb0 }), posto);
  const texFita = (() => { const cv = document.createElement('canvas'); cv.width = 256; cv.height = 32; const g = cv.getContext('2d'); for (let k = 0; k < 16; k++) { g.fillStyle = k % 2 ? '#111' : '#f2c81e'; g.beginPath(); g.moveTo(k * 16, 0); g.lineTo(k * 16 + 16, 0); g.lineTo(k * 16, 32); g.lineTo(k * 16 - 16, 32); g.fill(); } const t = new THREE.CanvasTexture(cv); t.wrapS = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; return t; })();
  function fita(a, b, y = 1.0, pai = grupo) {
    const d = b.clone().sub(a), L = Math.hypot(d.x, d.z), t = texFita.clone(); t.repeat.set(L / 1.2, 1); t.needsUpdate = true;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(L, .08), new THREE.MeshBasicMaterial({ map: t, side: THREE.DoubleSide }));
    m.position.copy(a).add(b).multiplyScalar(.5); m.position.y = a.y + y; m.rotation.y = -Math.atan2(d.z, d.x); pai.add(m);
    for (const p of [a, b]) { const c = new THREE.Mesh(new THREE.ConeGeometry(.17, .7, 12), matB(0xe8500e, .55)); c.position.copy(p).add(new THREE.Vector3(0, .35, 0)); pai.add(c); }
    return m;
  }
  const fitaPortao = new THREE.Group(); fitaPortao.visible = false; grupo.add(fitaPortao);
  fita(B(PX(-4.5), -37.2), B(PX(4.5), -37.2), 1.0, fitaPortao); fita(B(PX(-4.5), -37.2), B(PX(-4.5), -33.5), 1.0, fitaPortao);
  const fitaCorredor = new THREE.Group(); fitaCorredor.visible = false; grupo.add(fitaCorredor);
  fita(B1(19.6, 9.6), B1(19.6, 12.4), 1.0, fitaCorredor); fita(B1(29.0, 9.6), B1(29.0, 12.4), 1.0, fitaCorredor);
  // drone (aparece depois do acionamento) e drone da TV (variacao imprensa)
  function fazerDrone(cor) {
    const d = new THREE.Group(); caixa([.32, .08, .32], new THREE.Vector3(), matB(cor, .4), d);
    for (const [x, z] of [[-.25, -.25], [.25, -.25], [-.25, .25], [.25, .25]]) { caixa([.2, .01, .2], new THREE.Vector3(x, .05, z), new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: .5 }), d); }
    d.visible = false; grupo.add(d); return d;
  }
  const drone = fazerDrone(0x2a2d31), droneTV = fazerDrone(0xd8d8d8);

  /* ---------------- tablet: dossie, cameras, drone, mensagens, live ---------------- */
  const rt = new THREE.WebGLRenderTarget(640, 360);
  const camCorredor = new THREE.PerspectiveCamera(70, 16 / 9, .1, 60); camCorredor.position.copy(B1(19.5, 11.0)).add(new THREE.Vector3(0, 2.6, 0)); camCorredor.lookAt(B1(10.5, 10.8).add(new THREE.Vector3(0, 1.2, 0)));
  const camDrone = new THREE.PerspectiveCamera(75, 16 / 9, .1, 40); camDrone.position.copy(B1(15.5, .75)).add(new THREE.Vector3(0, 2.2, 0)); camDrone.lookAt(B1(13.0, 6.0).add(new THREE.Vector3(0, .8, 0)));
  function foto(cam, rotulo) {
    const xr = renderer.xr.enabled; renderer.xr.enabled = false;
    renderer.setRenderTarget(rt); renderer.render(scene, cam); renderer.setRenderTarget(null); renderer.xr.enabled = xr;
    const px = new Uint8Array(640 * 360 * 4); renderer.readRenderTargetPixels(rt, 0, 0, 640, 360, px);
    const cv = document.createElement('canvas'); cv.width = 640; cv.height = 360; const g = cv.getContext('2d'), im = g.createImageData(640, 360);
    for (let y = 0; y < 360; y++) im.data.set(px.subarray((359 - y) * 640 * 4, (360 - y) * 640 * 4), y * 640 * 4);
    g.putImageData(im, 0, 0);
    if (rotulo === 'drone') { g.globalCompositeOperation = 'saturation'; g.fillStyle = 'hsl(0,0%,50%)'; g.fillRect(0, 0, 640, 360); g.globalCompositeOperation = 'source-over'; }
    g.fillStyle = 'rgba(0,0,0,.55)'; g.fillRect(0, 0, 640, 28); g.fillStyle = '#e8e8e8'; g.font = '600 16px Consolas, monospace';
    g.fillText((rotulo === 'drone' ? 'DRONE · PELA JANELA DA 201' : 'CAM 07 · CORREDOR 1º ANDAR') + '  ' + new Date().toLocaleTimeString('pt-BR'), 10, 19);
    g.strokeStyle = 'rgba(255,60,60,.9)'; g.beginPath(); g.arc(620, 14, 6, 0, 7); g.fillStyle = '#e33'; g.fill();
    return cv;
  }
  function telaDossie() {
    const cv = document.createElement('canvas'); cv.width = 720; cv.height = 420; const g = cv.getContext('2d');
    g.fillStyle = '#313338'; g.fillRect(0, 0, 720, 420); g.fillStyle = '#2b2d31'; g.fillRect(0, 0, 170, 420);
    g.fillStyle = '#949ba4'; g.font = '600 15px Segoe UI'; ['# geral', '# hoje', '# arquivo', '# live'].forEach((c, i) => g.fillText(c, 18, 40 + i * 30));
    g.fillStyle = '#404249'; g.fillRect(8, 52, 154, 28); g.fillStyle = '#fff'; g.fillText('# hoje', 18, 70);
    g.beginPath(); g.arc(205, 60, 18, 0, 7); g.fillStyle = '#5865f2'; g.fill();
    g.fillStyle = '#f2f3f5'; g.font = '700 16px Segoe UI'; g.fillText('Lucas_901', 232, 56); g.fillStyle = '#949ba4'; g.font = '13px Segoe UI'; g.fillText('hoje às 07:33', 320, 56);
    g.fillStyle = '#dbdee1'; g.font = '16px Segoe UI'; g.fillText('hoje é na 201', 232, 80);
    g.fillStyle = '#4a3f36'; g.fillRect(232, 92, 300, 200); g.fillStyle = '#2a4a8a'; g.fillRect(262, 120, 240, 160); g.fillStyle = '#1a1a1a';
    if (v.arma === 'faca') { g.fillRect(330, 190, 120, 10); g.fillStyle = '#c9ccd0'; g.fillRect(450, 190, 40, 8); } else { g.fillRect(320, 180, 110, 20); g.fillRect(340, 200, 22, 40); }
    g.fillStyle = 'rgba(255,255,255,.7)'; g.font = 'italic 13px Segoe UI'; g.fillText('foto: mochila escolar', 240, 286);
    g.fillStyle = '#949ba4'; g.font = '13px Segoe UI'; g.fillText('servidor monitorado pelo núcleo de inteligência · situação fictícia', 190, 408);
    return cv;
  }
  function telaMensagens() {
    const cv = document.createElement('canvas'); cv.width = 640; cv.height = 420; const g = cv.getContext('2d');
    g.fillStyle = '#e9e4dc'; g.fillRect(0, 0, 640, 420); g.fillStyle = '#2f3b46'; g.fillRect(0, 0, 640, 56); g.fillStyle = '#fff'; g.font = '700 22px Segoe UI'; g.fillText('Profª Cláudia (sala 201)', 20, 36);
    let y = 80; for (const m of C.mensagens.slice(-4)) { const L = []; let l = ''; g.font = '18px Segoe UI'; for (const w of m.split(' ')) { const t = l ? l + ' ' + w : w; if (g.measureText(t).width > 540 && l) { L.push(l); l = w; } else l = t; } L.push(l);
      g.fillStyle = '#fff'; g.beginPath(); g.roundRect(20, y, 580, 20 + L.length * 24, 12); g.fill(); g.fillStyle = '#1d1d1f'; L.forEach((t, i) => g.fillText(t, 34, y + 26 + i * 24)); y += 34 + L.length * 24; }
    if (!C.mensagens.length) { g.fillStyle = '#777'; g.font = 'italic 18px Segoe UI'; g.fillText('Nenhuma mensagem ainda.', 20, 100); }
    return cv;
  }
  function telaLive() {
    const cv = document.createElement('canvas'); cv.width = 640; cv.height = 360; const g = cv.getContext('2d');
    g.fillStyle = '#18191c'; g.fillRect(0, 0, 640, 360); g.fillStyle = C.live ? '#e33' : '#666'; g.fillRect(16, 16, 70, 26); g.fillStyle = '#fff'; g.font = '700 15px Segoe UI'; g.fillText(C.live ? 'AO VIVO' : 'ENCERRADA', 22, 35);
    g.fillText(C.live ? `${C.espectadores} assistindo` : 'transmissão derrubada pela plataforma', 100, 35);
    g.fillStyle = '#ccc'; g.font = '15px Segoe UI';
    const coments = C.live ? ['faz logo', 'lenda', 'kkkkkk', 'isso é real??', 'chama a polícia', 'ele vai entrar pra história'] : ['—'];
    coments.forEach((t, i) => g.fillText('• ' + t, 24, 90 + i * 34));
    g.fillStyle = '#888'; g.font = 'italic 13px Segoe UI'; g.fillText('monitoramento da sala de operações · situação fictícia', 16, 345);
    return cv;
  }
  function tablet() {
    H.fecharPaineis();
    const b = [{ label: 'Dossiê do alerta (Discord)', acao: () => { registrar('ler_dossie'); fato('dossie'); dialogo.mostrar({ tag: 'Tablet', titulo: 'Dossiê do alerta', texto: CEN.dossie.join('\n'), img: telaDossie(), botoes: [{ label: 'Voltar', acao: tablet }] }); } },
      { label: 'Câmera do corredor (1º andar)', acao: () => { usouTec(); dialogo.mostrar({ tag: 'Tablet', titulo: 'Câmera do corredor', img: foto(camCorredor, 'cam'), texto: 'Imagem de agora. A porta da 201 está fechada.', botoes: [{ label: 'Atualizar', acao: () => menuTabletItem('cam') }, { label: 'Voltar', acao: tablet }] }); } }];
    if (C.droneNoAr) b.push({ label: 'Drone (pela janela da 201)', acao: () => menuTabletItem('drone') });
    b.push({ label: `Mensagens de uma aluna (${C.mensagens.length})`, acao: () => { usouTec(); if (C.mensagens.length) fato('mensagens'); dialogo.mostrar({ tag: 'Tablet', titulo: 'Mensagens de dentro da sala', img: telaMensagens(), botoes: [{ label: 'Voltar', acao: tablet }] }); } });
    if (v.motivo === 'notoriedade' || C.liveVista) b.push({ label: 'Transmissão ao vivo dele', acao: () => { usouTec(); C.liveVista = true; dialogo.mostrar({ tag: 'Tablet', titulo: 'Live no Discord', img: telaLive(), botoes: [...(C.live ? [{ label: 'Pedir à sala de operações que a plataforma derrube a transmissão', acao: derrubarLive }] : []), { label: 'Voltar', acao: tablet }] }); } });
    b.push({ label: 'Fechar', acao: () => dialogo.esconder() });
    dialogo.mostrar({ tag: 'Tablet tático', titulo: 'Informações da crise', texto: resumoFatos(), botoes: b });
  }
  function menuTabletItem(q) {
    usouTec();
    if (q === 'cam') dialogo.mostrar({ tag: 'Tablet', titulo: 'Câmera do corredor', img: foto(camCorredor, 'cam'), botoes: [{ label: 'Atualizar', acao: () => menuTabletItem('cam') }, { label: 'Voltar', acao: tablet }] });
    else { fato('drone'); fato('arma'); fato('refens'); dialogo.mostrar({ tag: 'Tablet', titulo: 'Drone', img: foto(camDrone, 'drone'), texto: `Vê-se o Lucas perto do quadro com ${v.arma === 'faca' ? 'uma faca' : 'um revólver'} na mão e cerca de ${C.refens} crianças e a professora no chão, junto às janelas.`, botoes: [{ label: 'Atualizar', acao: () => menuTabletItem('drone') }, { label: 'Voltar', acao: tablet }] }); }
  }
  function usouTec() { C.tec = (C.tec || 0) + 1; if (C.tec >= 2 && emNegociacao()) registrar('uso_tecnologia'); }
  function derrubarLive() { H.fecharPaineis(); C.live = false; usouTec(); registrar('uso_tecnologia'); radio(CEN.radio.live_derrubada); if (v.motivo === 'notoriedade') { ajusta([10, 0]); setTimeout(() => { if (!C.fim) { lucasDiz('Derrubaram minha live! Ninguém mais tá vendo...'); ajusta([-18, 4]); } }, 6000); } }

  /* ---------------- informacoes levantadas (para a passagem ao comando) ---------------- */
  function fato(k) { C.fatos[k] = true; if (C.fatos.arma && C.fatos.refens && (C.fatos.ferida || C.fatos.mensagens)) registrar('levantar_informacoes'); }
  function resumoFatos() {
    const L = [];
    L.push('Arma: ' + (C.fatos.arma ? (v.arma === 'faca' ? 'faca (confirmada)' : 'revólver (confirmado)') : 'não confirmada'));
    L.push('Reféns: ' + (C.fatos.refens ? `${C.refens} alunos e a professora` : 'turma da 901 (número não confirmado)'));
    L.push('Ferida: ' + (C.fatos.ferida ? 'uma aluna com corte no braço' : 'sem informação'));
    L.push('Estado dele: ' + (C.contato ? 'muito agitado, fala de ' + ({ notoriedade: 'audiência e live', vinganca: 'intimidação sofrida', suicida: 'morrer' })[v.motivo] : 'sem contato ainda'));
    L.push(`Tensão estimada: ${C.tensao > 70 ? 'alta' : C.tensao > 40 ? 'média' : 'baixa'} · vínculo: ${C.vinculo > 60 ? 'bom' : C.vinculo > 30 ? 'em construção' : 'fraco'}`);
    return L.join('\n');
  }

  /* ---------------- fala do Lucas pela porta ---------------- */
  const lucasDiz = t => diz(lucas, t, null);
  const emNegociacao = () => C.fase === 'negociacao';
  function conferirTensao() {
    if (C.fim) return;
    if (C.tensao >= 100) { if (emNegociacao()) registrar('neg_provocou_ataque'); desfecho('ataque_provocado'); }
  }

  /* ---------------- fluxo ---------------- */
  const BOPE_ATE = treino ? 75000 : 120000;
  function iniciarFase1() {
    C.fase = 'chegada'; rig.position.copy(B(5.5, -41.5)); ctx.setYaw(Math.PI + .1);
    radio(CEN.radio.inicio).then(() => dica('Leia o dossiê no tablet (menu: T ou Y/B) e informe a chegada pelo rádio. A diretora está no portão.'));
  }
  function iniciarFase2() {
    C.fase = 'negociacao'; C.papelAtual = 'negociador';
    posto.visible = true; fitaPortao.visible = true; fitaCorredor.visible = true; drone.visible = true; C.droneNoAr = true; C.bopeChegou = true;
    comandante.visible = true; negociador.visible = papel === 'completo';
    if (papel === 'negociador') {                               // comeca ja com a passagem feita (resumo pronto)
      C.fatos = { dossie: true, arma: true, refens: true }; C.contato = true; C.tensao = 72; C.vinculo = 8;
      rig.position.copy(B1(13.7, 10.7)); ctx.setYaw(-Math.PI / 2 - .4); pai.visible = false; diretora.position.copy(B(PX(4), -31));
      menu.mostrar({ tag: 'Missão Sala 201 · negociador', titulo: 'Passagem do primeiro interventor', texto: 'Você é o negociador da equipe do BOPE. O comandante assumiu no pátio.\n\n' + resumoFatos() + '\n\nO contato é pela porta da 201, de posição abrigada. Lembre: quem negocia não comanda.', longe: 1.3,
        botoes: [{ label: 'Começar a negociação', acao: () => { menu.esconder(); proximoTurno(); } }] });
    } else {
      legenda('Negociador', CEN.falas.negociador_chegada, 4);
      setTimeout(() => { menu.mostrar({ tag: 'Missão Sala 201 · fase 2', titulo: 'Agora você é o negociador', texto: 'A equipe do BOPE assumiu. Você passa a conduzir a negociação pela porta da 201. O comandante decide as alternativas táticas; você negocia.', longe: 1.3, botoes: [{ label: 'Começar a negociação', acao: () => { menu.esconder(); proximoTurno(); } }] }); }, 1500);
    }
    status();
  }

  // contato inicial (fase 1)
  function contatoPorta() {
    if (!perto(B1(14.95, 10.4), 4.0)) return legenda('Contato', 'Aproxime-se da porta da 201 pelo corredor (de lado, fora da linha da porta).', 4);
    if (emNegociacao()) return proximoTurno();
    const lista = !C.contato ? CEN.contato_porta.abertura : CEN.contato_porta.seguir;
    H.fecharPaineis();
    dialogo.mostrar({ tag: 'Porta da sala 201', titulo: !C.contato ? 'Primeiro contato' : 'Manter o contato', texto: C.ultimaFala ? 'Lucas: ' + C.ultimaFala : '',
      botoes: [...lista.map(op => ({ label: op.fala, acao: () => {
        H.fecharPaineis(); legenda('Você', op.fala, 4); C.contato = true; C.contatoT = C.contatoT || performance.now();
        if (op.acao) registrar(op.acao); if (op.erro) registrar(op.erro);
        if (!op.erro && op.id !== 'concessao') C.semConcessao = (C.semConcessao || 0) + 1; if (C.semConcessao >= 2 && !C.erros.some(e => e.id === 'promessa_indevida')) registrar('contato_sem_concessao');
        if (op.id === 'info') { fato('ferida'); fato('refens'); }
        ajusta(op.efeito || [0, 0]);
        setTimeout(() => { const r = CEN.respostas_porta[op.id]; if (r && !C.fim) { C.ultimaFala = r; lucasDiz(r); } }, 2600);
      } })), { label: 'Voltar', acao: () => dialogo.esconder() }] });
  }

  // turnos da negociacao (fase 2)
  function proximoTurno() {
    if (C.fim || C.saindo) return;
    if (!perto(B1(14.95, 10.4), 4.5)) return legenda('Negociação', 'Vá até o ponto de contato, ao lado da porta da 201.', 4);
    C.turno++;
    const linhas = NG.aberturas_lucas[v.motivo];
    // eventos com o passar dos turnos
    if (C.turno === 2 && !C.exig) C.exig = v.virada === 'prazo' ? 'prazo' : v.motivo === 'notoriedade' ? 'live' : v.motivo === 'vinganca' ? 'rafa' : null;
    if (C.turno === 3 && !C.msgBia) { C.msgBia = true; C.mensagens.push(F.professora_mensagem); fato('ferida'); legenda('Tablet', 'Nova mensagem de uma aluna, de dentro da sala.', 4); }
    if (C.turno === 4 && !C.pressaoFeita) { C.pressaoFeita = true; pressaoExterna(); }
    if (v.virada === 'ataque' && C.turno >= 5 && C.vinculo < 70 && !C.ataque) return ataqueEmCurso();
    const fala = C.exig && !C.exigRespondida ? NG.exigencias[C.exig].lucas : linhas[(C.turno - 1) % linhas.length];
    C.ultimaFala = fala; lucasDiz(fala);
    setTimeout(() => painelNegociacao(fala), Math.max(2200, fala.length * 55));
  }
  function painelNegociacao(fala) {
    if (C.fim) return;
    const ops = [];
    if (C.exig && !C.exigRespondida) {
      const E = NG.exigencias[C.exig];
      ops.push({ label: E.ok, acao: () => { C.exigRespondida = true; registrar('gestao_exigencias'); ajusta([-8, 8]); depois('Você... tá falando sério? Tá. Eu escuto.'); } });
      ops.push({ label: E.nega, acao: () => { C.exigRespondida = true; ajusta([16, -10]); depois('Então vocês não ligam mesmo!'); } });
      ops.push({ label: E.aceita, acao: () => { C.exigRespondida = true; if (C.exig === 'live') registrar('neg_arma'); else registrar('neg_concessao_gratis'); ajusta([-4, 2]); depois('Isso. Agora sim.'); } });
    } else {
      const boas = NG.tecnicas.filter(t => !t.erro).sort(() => Math.random() - .5).slice(0, 2), ruins = NG.tecnicas.filter(t => t.erro).sort(() => Math.random() - .5).slice(0, 2);
      for (const t of [...boas, ...ruins].sort(() => Math.random() - .5)) ops.push({ label: t.modelos[v.motivo], acao: () => {
        if (t.acao) { C.boas = (C.boas || 0) + 1; if (C.boas >= 3) registrar('escuta_ativa'); }
        if (t.erro) registrar(t.erro);
        ajusta(t.efeito); if (C.vinculo >= 40 && C.tensao < 60) registrar('vinculo');
        depois(C.tensao > 75 ? ['Você não entende nada!', 'Para de falar desse jeito comigo!', 'Ninguém nunca entende.'][C.turno % 3] : C.tensao > 45 ? ['...é. É isso.', 'Ninguém nunca me perguntou isso.', 'Tá... continua.'][C.turno % 3] : ['Eu tô cansado.', 'Eu não queria que fosse assim.', 'E agora? O que acontece comigo?'][C.turno % 3]);
      } });
      for (const tr of NG.trocas) if (!C['troca_' + tr.id] && C.refens > 0 && C.vinculo >= tr.requer_vinculo) ops.push({ label: 'Troca: ' + tr.fala, acao: () => troca(tr) });
      if (C.tensao < 40 && C.vinculo >= 65) for (const r of NG.rendicao) ops.push({ label: 'Rendição: ' + r.fala, acao: () => { if (r.erro) { registrar(r.erro); ajusta([20, -15]); depois('Não! Ninguém me dá ordem!'); } else rendicao(); } });
    }
    H.fecharPaineis();
    dialogo.mostrar({ tag: `Negociação · turno ${C.turno}`, titulo: 'Lucas: ' + fala, texto: treino ? `Tensão: ${barra(C.tensao)}   Vínculo: ${barra(C.vinculo)}` : '', botoes: ops.map(o => ({ label: o.label, acao: () => { H.fecharPaineis(); legenda('Você', o.label.replace(/^(Troca|Rendição): /, ''), 5); setTimeout(o.acao, 300); } })) });
  }
  const barra = x => '▮'.repeat(Math.round(x / 10)) + '▯'.repeat(10 - Math.round(x / 10));
  function depois(resposta) { setTimeout(() => { if (C.fim) return; lucasDiz(resposta); setTimeout(proximoTurno, Math.max(3000, resposta.length * 60)); }, 2500); }
  function troca(tr) {
    C['troca_' + tr.id] = true; registrar('troca_refens'); ajusta([-6, 6]);
    const n = Math.min(tr.libera, C.refens); C.refens -= n;
    setTimeout(() => { lucasDiz(n >= 99 || C.refens <= 0 ? 'Tá. Podem sair. Todo mundo.' : 'Tá... só eles. Rápido.'); liberar(n); setTimeout(proximoTurno, 6000); }, 2400);
  }
  function liberar(n) {
    const ordem = [kids[8], ...kids.filter(k => k !== kids[8])].filter(k => k.visible && !k.userData.saiu);
    const quem = n >= 99 ? [...ordem, professora] : ordem.slice(0, n);
    abrirPorta(.5);
    quem.forEach((k, i) => setTimeout(() => { const u = k.userData; u.saiu = true; u.semVirar = false; u.base = 'parada';
      u.rota = [B1(14.95, 8.0), B1(14.95, 10.9), B1(19.0, 11.0), B1(23.6, 11.0), B1(23.6, 14.0)].map(p => p.clone()); u.destino = null; u.vel = 1.8;
      u.aoChegar = () => { k.visible = false; }; animar(k, k.userData.acoes?.correndo ? 'correndo' : 'andando', 1e6, .2); }, i * 700));
    setTimeout(() => { if (!C.fim && !C.saindo) abrirPorta(0); }, quem.length * 700 + 4000);
    legenda('Situação', n >= 99 ? 'Os reféns que restavam e a professora estão saindo.' : `${quem.length} ${quem.length === 1 ? 'refém saiu' : 'reféns saíram'}. A equipe recebe no corredor.`, 5);
  }
  function abrirPorta(frac) { const a0 = porta.rotation.y, a1 = -1.4 * frac; H.suave(.8, e => { porta.rotation.y = a0 + (a1 - a0) * e; }); const cols = ctx.colisao(), i = cols.indexOf(colPorta); if (frac > .3 && i >= 0) cols.splice(i, 1); if (frac <= .3 && i < 0) cols.push(colPorta); }
  function pressaoExterna() {
    if (v.pressao === 'mae') {
      mae.visible = true; legenda('Situação', 'A mãe do Lucas chegou ao portão e quer falar com ele.', 5);
      setTimeout(() => { if (C.fim) return; diz(mae, F.mae_chegada, 'estressada'); setTimeout(() => painelMae(), 5000); }, 1500);
    } else if (v.pressao === 'imprensa') {
      droneTV.visible = true; legenda('Imprensa', F.imprensa, 6);
      if (!C.live) C.live = true, C.espectadores = 2400, C.liveVista = true;
      setTimeout(() => dica('Ele pode estar acompanhando a cobertura. Considere pedir o afastamento do drone da TV e o controle da transmissão pela sala de operações.', 8), 2500);
    } else { legenda('Situação', 'Um pai furou o perímetro e está subindo a rampa!', 5); pai.visible = true; pai.position.copy(B(30, 9)); setTimeout(() => dica('Ele precisa ser retirado pelo apoio, sem chamar a atenção de quem está na 201.', 6), 2000); }
  }
  function painelMae() {
    H.fecharPaineis();
    dialogo.mostrar({ tag: 'Mãe do Lucas', titulo: 'Ela insiste em falar com o filho', botoes: NG.mae.map(op => ({ label: op.fala, acao: () => {
      H.fecharPaineis(); legenda('Você', op.fala, 4); if (op.acao) registrar(op.acao); if (op.erro) registrar(op.erro);
      if (op.id === 'avaliar') { setTimeout(() => diz(mae, F.mae_info, 'triste'), 2500); fato('mae'); NG.tecnicas.push({ tipo: 'thor', rotulo: '', modelos: { notoriedade: 'Sua mãe me contou do Thor. Ele tá te esperando em casa.', vinganca: 'Sua mãe me contou do Thor. Ele tá te esperando em casa.', suicida: 'Sua mãe me contou do Thor. Quem vai cuidar dele?' }, efeito: [-12, 14], acao: 'escuta_ativa' }); }
      else { ajusta([25, -10]); setTimeout(() => lucasDiz('Manda ela embora! Ela nunca ligou! Manda ela embora!'), 2500); }
    } })) });
  }

  // desfechos
  function rendicao() {
    if (C.fim || C.saindo) return; registrar('rendicao'); registrar('vinculo'); C.saindo = true;
    setTimeout(() => { lucasDiz(F.lucas_rendicao); faca.visible = false; H.armaNPC.visible = false; abrirPorta(1);
      lucas.rotation.x = 0; const u = lucas.userData; u.semVirar = false; u.base = 'rendido'; u.rota = [B1(14.95, 8.0), B1(14.95, 10.6)].map(p => p.clone()); u.destino = null; u.vel = 1.0; u.aoChegar = () => { animar(lucas, 'rendido', 1e6, .3); };
      animar(lucas, 'andando', 1e6, .2);
      setTimeout(() => liberar(99), 5000);
      setTimeout(() => apreensao(), 9000);
    }, 2200);
  }
  function apreensao() {
    if (C.fim) return; H.fecharPaineis();
    dialogo.mostrar({ tag: 'Desfecho', titulo: 'Ele saiu com as mãos vazias', botoes: [
      { label: 'Apreender sem violência, algemar (portava arma: há perigo) e conduzir sem expor o rosto', acao: () => { registrar('apreensao_correta'); registrar('vidas_preservadas'); desfecho('rendicao'); } },
      { label: 'Derrubá-lo no chão com força e mostrar à imprensa', acao: () => { registrar('vidas_preservadas'); desfecho('rendicao'); } }
    ] });
  }
  function ataqueEmCurso() {
    C.ataque = true; H.fecharPaineis(); legenda('Alerta', 'Gritos dentro da sala! Ele avançou contra os colegas!', 5);
    animar(lucas, lucas.userData.base === 'apontando' ? 'apontando' : 'irritado', 1e6, .1); kids.forEach(k => animar(k, k.userData.acoes?.nervoso ? 'nervoso' : 'parada', 1e6, .2));
    setTimeout(() => dialogo.mostrar({ tag: 'Agressão em curso', titulo: 'O que fazer agora?', texto: 'Há um ataque acontecendo do outro lado da porta.', botoes: [
      { label: 'Entrada imediata com a equipe: agressão ativa em curso', acao: () => { registrar('intervencao_correta'); desfecho('ataque_contencao'); } },
      { label: 'Continuar falando e esperar o comandante', acao: () => { desfecho('ataque_provocado'); } }
    ] }), 1500);
  }
  function forcarPorta() {
    if (C.ataque) { registrar('intervencao_correta'); return desfecho('ataque_contencao'); }
    registrar('invasao_precipitada'); desfecho('invasao_precipitada');
  }
  function desfecho(tipo) {
    if (C.fim) return; C.fim = true; C.resultado = tipo; H.fecharPaineis();
    if ((tipo === 'rendicao' || tipo === 'passagem') && !C.graves.some(g => g.id === 'invasao_precipitada')) registrar('manter_contencao');
    if (tipo === 'passagem' && !C.ataque) registrar('vidas_preservadas');
    const veu = H.veu; veu.material.color.set(0x000000); veu.visible = true; H.suave(1.5, e => { veu.material.opacity = .92 * e; });
    setTimeout(() => {
      menu.mostrar({ tag: 'Desfecho', titulo: { rendicao: 'Crise encerrada: rendição negociada', passagem: 'Passagem ao comando', ataque_contencao: 'Intervenção imediata', ataque_provocado: 'A crise escalou', invasao_precipitada: 'Invasão precipitada' }[tipo], texto: CEN.narracoes[tipo], longe: 1.3,
        botoes: [{ label: 'Ver o relatório', acao: relatorio }] });
    }, 1800);
  }

  /* ---------------- passagem ao comando (fim da fase 1) ---------------- */
  function bopeChega() {
    if (C.bopeChegou) return; C.bopeChegou = true; posto.visible = true; comandante.visible = true; negociador.visible = true; drone.visible = true; C.droneNoAr = true;
    radio(CEN.radio.bope_chegou).then(() => radio(CEN.radio.drone));
    if (pai.visible && !C.isolouPortao) registrar('curiosos_no_perimetro');
    dica('Vá ao posto de comando no pátio (perto do portão) e passe a ocorrência ao comandante.', 8);
  }
  function briefing() {
    H.fecharPaineis();
    const perguntas = [
      { t: 'Arma', ops: [['Faca', v.arma === 'faca'], ['Revólver', v.arma === 'revolver'], ['Não confirmada', !C.fatos.arma]] },
      { t: 'Reféns', ops: [['10 alunos e a professora', !!C.fatos.refens], ['Turma inteira, número não confirmado', !C.fatos.refens], ['Ninguém, ele está sozinho', false]] },
      { t: 'Feridos', ops: [['Uma aluna com corte no braço', !!C.fatos.ferida], ['Sem informação de feridos', !C.fatos.ferida], ['Vários feridos graves', false]] }
    ];
    let certas = 0, i = 0;
    const pergunta = () => {
      if (i >= perguntas.length) {
        if (certas === perguntas.length) registrar('passagem_completa'); else registrar('passagem_errada');
        diz(comandante, F.comandante_assume, 'falando');
        if (papel === 'interventor') return setTimeout(() => desfecho('passagem'), 4000);
        return setTimeout(iniciarFase2, 4500);
      }
      const P = perguntas[i++];
      dialogo.mostrar({ tag: 'Passagem ao comandante', titulo: P.t + '?', texto: 'Informe só o que você confirmou.', botoes: P.ops.map(([l, ok]) => ({ label: l, acao: () => { if (ok) certas++; pergunta(); } })) });
    };
    diz(comandante, F.comandante_chegada, 'falando').then(pergunta);
  }

  /* ---------------- menu da missao ---------------- */
  function menuCrise() {
    H.fecharPaineis();
    const b = [];
    if (!C.chegada && C.fase !== 'negociacao') b.push({ label: 'Rádio: informar a chegada e confirmar a crise', acao: () => { H.fecharPaineis(); C.chegada = true; registrar('comunicar_chegada'); radio(CEN.radio.chegada); } });
    if (!C.acionou && C.fase !== 'negociacao') b.push({ label: 'Rádio: acionar BOPE e negociação, SAMU e apoio', acao: () => { H.fecharPaineis(); C.acionou = true; registrar('acionar_especializada'); radio(CEN.radio.acionamento); setTimeout(bopeChega, BOPE_ATE); } });
    b.push({ label: 'Tablet tático (dossiê, câmeras, drone, mensagens)', acao: tablet });
    if (perto(B(PX(0), -37.5), 9) && !C.isolouPortao) b.push({ label: 'Isolar o portão: afastar pais e curiosos para fora da fita', acao: isolarPortao });
    if (perto(B1(14.95, 10.4), 5) && !C.fim) {
      b.push({ label: emNegociacao() ? 'Falar com ele (negociação)' : 'Falar com ele pela porta', acao: contatoPorta });
      b.push({ label: 'Forçar a porta e entrar', cor: 'rgba(240,80,64,.22)', acao: forcarPorta });
    }
    if (podeParceiro()) b.push({ label: 'Parceiro: fechar a outra ponta do corredor', acao: pedirParceiro });
    if (C.bopeChegou && C.fase !== 'negociacao' && perto(B(9.6, -28), 8)) b.push({ label: 'Passar a ocorrência ao comandante', acao: briefing });
    b.push({ label: H.S.armaNaMao ? 'Guardar a arma' : 'Sacar a arma', acao: () => { H.sacar(!H.S.armaNaMao); menu.esconder(); } },
      { label: 'Encerrar a missão e ver o relatório', cor: 'rgba(240,80,64,.22)', acao: relatorio },
      { label: 'Fechar', acao: () => menu.esconder() });
    menu.mostrar({ tag: 'Missão Sala 201', titulo: { interventor: 'Primeiro interventor', negociador: 'Negociador', completo: 'Missão completa' }[papel], texto: `Tempo: ${H.fmt(tempo())} · ${resumoCurto()}`, botoes: b });
  }
  const resumoCurto = () => `reféns na sala: ${C.refens} · ${C.bopeChegou ? 'BOPE no local' : C.acionou ? 'BOPE a caminho' : 'BOPE não acionado'}`;
  const podeParceiro = () => C.fase !== 'negociacao' && !C.parceiroNoCorredor && camera.getWorldPosition(V).y > 2.5;
  function pedirParceiro() {
    H.fecharPaineis(); C.parceiroNoCorredor = true; diz(parceiro, F.parceiro_fila, null); H.irAte(parceiro, [26.5, 11.0], 1.6); fitaCorredor.visible = true;
    if (C.isolouPortao) registrar('isolar_perimetro');
  }
  function isolarPortao() {
    H.fecharPaineis(); C.isolouPortao = true; fitaPortao.visible = true; legenda('Você', 'Senhores, preciso que fiquem do lado de fora da fita. É para a segurança dos seus filhos.', 5);
    setTimeout(() => { diz(pai, F.pai_afastado, null); pai.position.copy(B(PX(-1.5), -39.2)); }, 2500);
    if (C.parceiroNoCorredor) registrar('isolar_perimetro');
  }
  function falarDiretora() {
    H.fecharPaineis();
    const ops = [];
    if (!C.ouviuDiretora) ops.push({ label: 'O que aconteceu? Onde ele está e com quantas pessoas?', acao: () => { C.ouviuDiretora = true; registrar('ouvir_diretora'); diz(diretora, F.diretora_chegada, 'estressada').then(() => diz(diretora, F.diretora_info)); } });
    if (!C.protecao) {
      ops.push({ label: 'Mande as salas do 1º andar trancarem as portas e ficarem longe delas; tire o térreo e o pátio pelo portão dos fundos, longe da rampa.', acao: () => { C.protecao = true; registrar('proteger_demais'); diz(diretora, F.diretora_abrigo).then(() => diz(diretora, F.diretora_evacua)); } });
      ops.push({ label: 'Tire todas as turmas do 1º andar agora, pelo corredor.', acao: () => { C.protecao = true; registrar('evacuar_corredor_crise'); if (treino) setTimeout(() => legenda('Instrutor', 'Passar turmas pelo corredor da 201 expõe todo mundo à crise. Abrigar onde estão é mais seguro.', 7), 2500); } });
    }
    ops.push({ label: 'Encerrar', acao: () => dialogo.esconder() });
    dialogo.mostrar({ tag: 'Diretora', titulo: 'Conversa', botoes: ops });
  }

  /* ---------------- clique / quadro / status ---------------- */
  function perto(p, r) { camera.getWorldPosition(V); return Math.hypot(V.x - p.x, V.z - p.z) < r && Math.abs(V.y - (p.y + 1.5)) < 2.2; }
  function usar(ray, c) {
    if (C.fim) return false;
    if (H.S.armaNaMao && (!c || c.userData.mao !== 'left')) { if (!C.ataque) registrar('invasao_precipitada', 'disparo'); return H.disparar(ray); }
    const hn = ray.intersectObjects(Object.values(npcs).filter(n => n.visible).map(n => n.userData.hit), false)[0];
    if (hn && hn.distance < 6) {
      const k = hn.object.userData.npc;
      if (k === 'diretora') return falarDiretora(), true;
      if (k === 'parceiro') { if (podeParceiro()) pedirParceiro(); else diz(parceiro, 'Tô contigo.', null); return true; }
      if (k === 'pai') { if (!C.isolouPortao) isolarPortao(); else diz(pai, F.pai_afastado, null); if (v.pressao === 'pai' && emNegociacao()) { pai.visible = false; legenda('Apoio', 'O apoio retirou o pai do prédio, em silêncio.', 4); } return true; }
      if (k === 'comandante') { if (C.fase !== 'negociacao') briefing(); else diz(comandante, 'Negociador, a decisão tática é minha. Continue o contato.', null); return true; }
      if (k === 'mae') { if (emNegociacao()) painelMae(); return true; }
      if (k === 'lucas' && perto(B1(14.95, 10.4), 5)) return contatoPorta(), true;
    }
    const hp = ray.intersectObject(colPorta, false)[0];
    if (hp && hp.distance < 3) { contatoPorta(); return true; }
    return false;
  }
  let ultimoS = 0;
  function quadro(dt) {
    const agora = performance.now();
    // faca na mao do Lucas
    if (faca.visible) { const mao = lucas.userData.modelo?.getObjectByName('Bip01_R_Hand'); if (mao) { mao.getWorldPosition(faca.position); faca.position.y -= .1; } }
    if (H.armaNPC.visible) { const mao = lucas.userData.modelo?.getObjectByName('Bip01_R_Hand'); if (mao) { mao.getWorldPosition(H.armaNPC.position); H.armaNPC.lookAt(B1(14.95, 9.5).add(new THREE.Vector3(0, 1.4, 0))); H.armaNPC.rotateY(Math.PI); } }
    // drones pairando
    const t = agora / 1000;
    if (drone.visible) drone.position.copy(B1(15.5, -2.5)).add(new THREE.Vector3(Math.sin(t * .7) * .3, 2.4 + Math.sin(t * 1.3) * .15, 0));
    if (droneTV.visible) droneTV.position.copy(B(-4, -6)).add(new THREE.Vector3(Math.sin(t * .5) * 2, 9 + Math.sin(t) * .4, 0));
    if (C.live) C.espectadores += Math.random() < .2 ? Math.floor(Math.random() * 9) : 0;
    if (Math.floor(agora / 1000) === ultimoS) return; ultimoS = Math.floor(agora / 1000);
    if (C.fim) return;
    camera.getWorldPosition(V);
    // posicao do policial no corredor: abrigado (ao lado da porta) ou exposto (na linha da porta)
    if (V.y > 2.5 && Math.abs(-V.z - 11.0) < 1.6 && V.x > 10 && V.x < 30) {
      const naLinha = V.x > 14.3 && V.x < 15.6 && -V.z < 12.4;
      C.tLinha = naLinha ? (C.tLinha || 0) + 1 : 0;
      if (C.tLinha >= 3 && v.arma === 'revolver') registrar('linha_porta');
      if (!naLinha && Math.abs(V.x - 14.95) < 3.5) { C.tAbrigado = (C.tAbrigado || 0) + 1; if (C.tAbrigado >= 4) { registrar('conter_corredor'); if (C.fase === 'chegada') C.fase = 'contencao'; } }
    }
    // diretora vem ao encontro na chegada
    if (!C.diretoraFalou && Math.hypot(V.x - diretora.position.x, V.z - diretora.position.z) < 6) { C.diretoraFalou = true; diz(diretora, 'Policial! Aqui! É na 201!', 'estressada'); }
    // parceiro acompanha
    if (!C.parceiroNoCorredor && C.fase !== 'negociacao') {
      const u = parceiro.userData, d = parceiro.position.distanceTo(V2.copy(V).setY(parceiro.position.y));
      if (d > 3.5 && !u.rota?.length && !u.destino) { camera.getWorldDirection(V2); V2.y = 0; V2.normalize(); const a = V.clone().addScaledVector(V2, -1.3); H.irAte(parceiro, [a.x, -a.z], 1.7, 'andando'); }
    }
    // o Lucas fala sozinho de vez em quando durante a contencao; tensao sobe devagar se ninguem fala com ele
    if (C.contato && C.fase !== 'negociacao' && !C.bopeChegou && agora - (C.tFala || 0) > 22000) { C.tFala = agora; const L = NG.aberturas_lucas[v.motivo]; C.ultimaFala = L[(C.fila++) % L.length]; lucasDiz(C.ultimaFala); }
    if (C.contato && agora - (C.tSobe || 0) > 10000) { C.tSobe = agora; if (!emNegociacao()) ajusta([2, 0]); }
    // variacao "ataque" na fase 1: o ataque acontece antes da equipe chegar
    if (papel !== 'negociador' && v.virada === 'ataque' && C.contatoT && !C.ataque && !emNegociacao() && agora - C.contatoT > 70000 && (C.tensao > 30 || C.vinculo < 60)) ataqueEmCurso();
    // mensagens de dentro da sala (fase 1)
    if (C.contatoT && !C.msgBia && agora - C.contatoT > 30000) { C.msgBia = true; C.mensagens.push(F.professora_mensagem); legenda('Tablet', 'Mensagem de uma aluna, de dentro da sala.', 4); }
    status();
  }
  function objetivos() {
    if (C.fim) return ['Missão encerrada'];
    const L = [];
    if (emNegociacao()) {
      L.push('Fale com ele pela porta (clique na porta)');
      if (C.exig && !C.exigRespondida) L.push('Responda à exigência sem aceitar nem negar de forma seca');
      if (C.refens > 0) L.push('Construa vínculo e troque pequenas concessões por reféns');
      if (C.live) L.push('A live dá plateia a ele: use o tablet');
      if (v.pressao === 'mae' && mae.visible && !C.feitos.has('terceiros_avaliados')) L.push('Avalie a mãe antes de qualquer contato dela com ele');
      return L;
    }
    if (!C.feitos.has('ler_dossie')) L.push('Leia o dossiê no tablet (menu)');
    if (!C.chegada) L.push('Informe a chegada pelo rádio (menu)');
    if (!C.acionou) L.push('Acione BOPE/negociação, SAMU e apoio (menu)');
    if (!C.ouviuDiretora) L.push('Fale com a diretora no portão');
    else if (!C.protecao) L.push('Decida como proteger as outras turmas (diretora)');
    if (!C.isolouPortao) L.push('Isole o portão e afaste os pais (menu, perto do portão)');
    if (!C.feitos.has('conter_corredor')) L.push('Suba a rampa e contenha o corredor do 1º andar, ao lado da porta da 201');
    else if (!C.parceiroNoCorredor) L.push('Peça ao parceiro para fechar a outra ponta do corredor (menu)');
    if (!C.contato) L.push('Faça o contato inicial pela porta, sem concessões');
    if (C.bopeChegou) L.push('Passe a ocorrência ao comandante no posto de comando (pátio)');
    return L.slice(0, 6);
  }
  function status() {
    const el = document.getElementById('statusTrein');
    if (el) { el.hidden = false; el.innerHTML = `<b>Missão Sala 201</b> · ${H.fmt(tempo())}<br>reféns: ${C.refens} · ${C.bopeChegou ? 'BOPE no local' : C.acionou ? 'BOPE a caminho' : 'BOPE não acionado'}${treino ? `<br>tensão ${Math.round(C.tensao)} · vínculo ${Math.round(C.vinculo)}` : ''}`; }
    const ob = document.getElementById('objetivosHTML');
    if (ob) { ob.hidden = !treino || renderer.xr.isPresenting; if (treino) ob.innerHTML = '<b style="color:#f0a340;font:600 11px Consolas,monospace;letter-spacing:.08em">OBJETIVOS</b><br>' + objetivos().map(t => '▸ ' + t).join('<br>'); }
  }

  /* ---------------- relatorio ---------------- */
  function relatorio() {
    H.fecharPaineis(); H.veu.visible = false;
    const modos = papel === 'completo' ? ['interventor', 'negociador', 'todos'] : [papel, 'todos'];
    let pos = 0, obt = 0; const fases = [];
    for (const f of CEN.fases) {
      if (!modos.includes(f.modo)) continue;
      if (papel === 'completo' && f.modo === 'negociador' && C.papelAtual !== 'negociador') continue;   // a crise terminou antes da fase de negociacao: nao cobra o que nao pode ser feito
      const vale = a => condOk(a.condicao) && !(papel === 'interventor' && a.id === 'apreensao_correta');
      const its = (f.acoes || []).filter(vale).map(a => { pos += a.pontos; const ok = C.feitos.has(a.id); if (ok) obt += a.pontos; return { texto: a.texto, ok, base: a.base, validar: a.validar }; });
      fases.push({ nome: f.nome, itens: its, obtidos: its.filter(i => i.ok).reduce((s, i) => s + (acoes[Object.keys(acoes).find(k => acoes[k].texto === i.texto)]?.pontos || 0), 0), possiveis: (f.acoes || []).filter(vale).reduce((s, a) => s + a.pontos, 0) });
    }
    const desc = C.erros.reduce((s, e) => s + e.pontos, 0) + C.graves.reduce((s, e) => s + e.pontos, 0);
    const nota = pos ? Math.max(0, Math.round((obt + desc) / pos * 100)) : 0, aprovado = nota >= CEN.aprovacao.pontos_minimos && !C.graves.length;
    const varTxt = Object.entries(v).map(([k, x]) => CEN.nomes_variacao[k][x]).join(' · ');
    menu.mostrar({ tag: 'Relatório · Missão Sala 201', titulo: `Nota ${nota}/100 · ${aprovado ? 'APROVADO' : 'NÃO APROVADO'}`, texto: `Papel: ${papel} · tempo ${H.fmt(tempo())}\nDesfecho: ${C.resultado || 'encerrada pelo participante'}\n\n` + fases.map(f => `${f.nome}: ${f.obtidos}/${f.possiveis}`).join('\n') + '\n\n' + ([...C.graves.map(g => '⚠ ' + g.texto), ...C.erros.map(e => `• ${e.texto} (${e.pontos})`)].join('\n') || 'Nenhum erro registrado.'), longe: 1.4,
      botoes: [{ label: 'Nova missão (outra variação)', acao: () => { encerrar(); H.aviso(); } }, { label: 'Fechar', acao: () => { encerrar(); menu.esconder(); } }] });
    const el = document.getElementById('relatorioHTML');
    if (el) {
      const leis = Object.entries(CEN.base_legal).filter(([k]) => k !== '_nota').map(([k, t]) => `<li><b>${k}</b> — ${t}</li>`).join('');
      el.innerHTML = `<h2>Missão Sala 201 — nota ${nota}/100 (${aprovado ? 'aprovado' : 'não aprovado'})</h2><p>Papel: ${papel} · modo ${modo} · tempo ${H.fmt(tempo())}<br><em>${varTxt}</em><br>Desfecho: ${C.resultado || '—'}</p>
        ${fases.map(f => `<h3>${f.nome} <small>${f.obtidos}/${f.possiveis}</small></h3><ul>${f.itens.map(i => `<li class="${i.ok ? 'ok' : 'nao'}">${i.ok ? '✓' : '✗'} ${i.texto}${i.base ? ` <em>(${i.base})</em>` : ''}${i.validar ? ' <em>[validar]</em>' : ''}</li>`).join('')}</ul>`).join('')}
        <h3>Erros e falhas graves</h3><ul>${[...C.graves.map(g => `<li>⚠ FALHA GRAVE: ${g.texto}${g.base ? ` (${g.base})` : ''}</li>`), ...C.erros.map(e => `<li>${e.texto} (${e.pontos})</li>`)].join('') || '<li>nenhum</li>'}</ul>
        <h3>Linha do tempo</h3><ul>${C.log.map(l => `<li>${H.fmt(l.t)} · ${acoes[l.id]?.texto || l.id}</li>`).join('')}</ul>
        <h3>Base doutrinária e legal</h3><ul>${leis}</ul><p><em>${CEN.base_legal._nota} ${CEN.aviso}</em></p>
        <p><button type="button" id="baixarRel">Baixar relatório (JSON)</button> <button type="button" id="fecharRel">Fechar</button></p>`;
      el.hidden = false;
      document.getElementById('baixarRel').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify({ missao: CEN.id, papel, modo, variacao: v, nota, aprovado, desfecho: C.resultado, feitos: [...C.feitos.keys()], erros: C.erros, falhas_graves: C.graves, linha_do_tempo: C.log }, null, 2)], { type: 'application/json' })); a.download = `relatorio_sala201_${Date.now()}.json`; a.click(); };
      document.getElementById('fecharRel').onclick = () => el.hidden = true;
    }
  }
  function encerrar() {
    C.fim = true; scene.remove(grupo); scene.remove(faca); const cols = ctx.colisao(), i = cols.indexOf(colPorta); if (i >= 0) cols.splice(i, 1); scene.remove(colPorta);
    H.veu.visible = false; H.veu.material.color.set(0xff2020); H.fimCrise();
  }

  /* ---------------- inicio ---------------- */
  const api = { usar, menu: menuCrise, quadro, status, objetivos, relatorio, estado: C, _t: { kids, animar, B1, contatoPorta, proximoTurno, briefing, bopeChega, tablet, forcarPorta, ataqueEmCurso, rendicao, liberar, isolarPortao, falarDiretora, foto: () => foto(camDrone, 'drone') } };
  const intro = { interventor: 'Você é o primeiro interventor. Contenha, isole, proteja e faça o contato inicial sem concessões. Não negocie no lugar da equipe especializada.', negociador: 'Você é o negociador do BOPE. Escute, construa vínculo, troque pequenas concessões por reféns e conduza a rendição. O comandante decide as ações táticas.', completo: 'Você começa como primeiro interventor e, quando a equipe chegar, assume a negociação.' }[papel];
  menu.mostrar({ tag: 'Missão Sala 201 · ' + (treino ? 'treino' : 'avaliação'), titulo: 'Crise com reféns na escola', texto: CEN.aviso + '\n\n' + intro + '\n\nComputador: clique fala/usa · T menu (rádio, tablet) · Q arma. Quest: gatilho usa · Y/B menu · A arma.', longe: 1.3,
    botoes: [{ label: 'Começar', acao: () => { menu.esconder(); if (papel === 'negociador') iniciarFase2(); else iniciarFase1(); } }] });
  status();
  return api;
}
