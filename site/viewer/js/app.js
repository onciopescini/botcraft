import * as THREE from 'three';
import { canvas, renderer, scene, camera, SET, saveSet, applySettings } from './config.js';
import { xz, dyn, treeGeo, treeMat, rockGeo, rockMat, wallGeo, wallMat, goldGeo, goldMat,
         gasMesh, ping1, ping2, totemMat, resize, orbit } from './scene.js';
import { agent1, agent2, agent1b, agent1c, agent2b, agent2c, agentMat1, agentMat2,
         smoothHp, setNames, placeLabels, feed, flashT, setPrevHp } from './actors.js';
import { burst, tickParts, blip, setAudio, koFX, setSlowmo, setShake, slowmoUntil, shakeUntil } from './fx.js';

applySettings();
setAudio(!!SET.audio);

applySettings();

let frames = [];
let playing = true;
let speed = 2;
let tFloat = 0;
let prevSnap = null;
let topTick = 0;

const elTick = document.getElementById('tick');
const elLabel = document.getElementById('ticklabel');
const elStats = document.getElementById('stats');
const elPlay = document.getElementById('play');

function parseReplay(text, name) {
  frames = text.trim().split('\n').filter(Boolean).map(l => JSON.parse(l));
  tFloat = 0;
  setPrevHp(null);
  window.__prevHp = null;
  setSlowmo(0); setShake(0);
  prevSnap = null;
  document.getElementById('stats').classList.remove('loading');
  document.getElementById('src').textContent = name || 'replay caricato';
  const feedEl = document.getElementById('feed');
  if (feedEl) feedEl.textContent = 'nessun evento…';
  const qp = new URLSearchParams(location.search);
  setNames(qp.get('p1') || 'Blu', qp.get('p2') || 'Rosso');
  topTick = 0;
  let best = 0;
  const kos = [];
  for (let i = 1; i < frames.length; i++) {
    const P = frames[i - 1], Q = frames[i];
    const d = (P.p1.hp - Q.p1.hp) + (P.p2.hp - Q.p2.hp);
    if ((P.p1.hp > 0 && Q.p1.hp <= 0) || (P.p2.hp > 0 && Q.p2.hp <= 0)) {
      if (!topTick) topTick = i;
      kos.push(i);
    }
    if (d > best) { best = d; if (!topTick) topTick = i; }
  }
  document.getElementById('marks').innerHTML = kos.map(t =>
    `<i style="left:${(t / Math.max(1, frames.length - 1)) * 100}%" title="KO tick ${t}"></i>`).join('');
  elTick.max = Math.max(0, frames.length - 1);
  elTick.value = 0;
  elLabel.textContent = `tick 0/${frames.length - 1}`;
}

function drawFrame(a, b, alpha) {
  const lerp = (p, q) => p + (q - p) * alpha;
  const [x1, z1] = xz(lerp(a.p1.x, b.p1.x), lerp(a.p1.y, b.p1.y));
  const [x2, z2] = xz(lerp(a.p2.x, b.p2.x), lerp(a.p2.y, b.p2.y));
  agent1.position.x = x1; agent1.position.z = z1;
  agent2.position.x = x2; agent2.position.z = z2;
  smoothHp(agent1, 'a1', a.p1.hp);
  smoothHp(agent2, 'a2', a.p2.hp);
  placeLabels(x1, z1, agent1.scale.y, x2, z2, agent2.scale.y);
  const prev = window.__prevHp || null;
  if (prev && a.p1.hp < prev[0]) flashT.a1 = performance.now();
  if (prev && a.p2.hp < prev[1]) flashT.a2 = performance.now();
  window.__prevHp = [a.p1.hp, a.p2.hp];
  const nowF = performance.now();
  agentMat1.emissive = new THREE.Color(nowF - flashT.a1 < 180 ? 0xffffff : (a.p1.sword ? 0x003a88 : 0x000000));
  agentMat2.emissive = new THREE.Color(nowF - flashT.a2 < 180 ? 0xffffff : (a.p2.sword ? 0x881100 : 0x000000));
  if (prevSnap) {
    const res = (P, Q) => [Q.wood - P.wood, Q.stone - P.stone, (Q.gold || 0) - (P.gold || 0)];
    const [dw1, ds1, dg1] = res(prevSnap.p1, a.p1);
    const [dw2, ds2, dg2] = res(prevSnap.p2, a.p2);
    if (dw1 > 0) { burst(agent1.position.x, agent1.position.z, 0x3fae5a, 8); blip(660); }
    if (ds1 > 0) { burst(agent1.position.x, agent1.position.z, 0x9aa3b2, 8); blip(520); }
    if (dg1 > 0) { burst(agent1.position.x, agent1.position.z, 0xffd700, 12); blip(880); }
    if (dw2 > 0) { burst(agent2.position.x, agent2.position.z, 0x3fae5a, 8); blip(660); }
    if (ds2 > 0) { burst(agent2.position.x, agent2.position.z, 0x9aa3b2, 8); blip(520); }
    if (dg2 > 0) { burst(agent2.position.x, agent2.position.z, 0xffd700, 12); blip(880); }
    for (const [P, Q, mesh, nm] of [[prevSnap.p1, a.p1, agent1, 'Blu'], [prevSnap.p2, a.p2, agent2, 'Rosso']]) {
      if (P.hp > Q.hp) blip(180, 0.09);
      if (!P.sword && Q.sword) feed(`tick ${a.tick}: <b>${nm}</b> costruisce la spada`);
      if (P.hp > 0 && Q.hp <= 0) {
        burst(mesh.position.x, mesh.position.z, 0xff7a00, 40, 5);
        blip(90, 0.25, 0.12);
        feed(`tick ${a.tick}: <b style="color:#ff5d5d">KO!</b> ${nm} cade`);
        koFX();
      }
    }
  }
  prevSnap = JSON.parse(JSON.stringify({ p1: a.p1, p2: a.p2 }));
  const squad = Array.isArray(a.t1) && Array.isArray(a.t2);
  const bSquad = b && Array.isArray(b.t1) && Array.isArray(b.t2);
  for (const m of [agent1b, agent1c, agent2b, agent2c]) m.visible = !!squad;
  if (squad) {
    const put = (mesh, P, Q) => {
      const [x, z] = xz(lerp(P.x, Q.x), lerp(P.y, Q.y));
      mesh.position.x = x; mesh.position.z = z;
    };
    put(agent1b, a.t1[1], (bSquad ? b : a).t1[1]);
    put(agent1c, a.t1[2], (bSquad ? b : a).t1[2]);
    put(agent2b, a.t2[1], (bSquad ? b : a).t2[1]);
    put(agent2c, a.t2[2], (bSquad ? b : a).t2[2]);
    smoothHp(agent1b, 'a1b', a.t1[1].hp); smoothHp(agent1c, 'a1c', a.t1[2].hp);
    smoothHp(agent2b, 'a2b', a.t2[1].hp); smoothHp(agent2c, 'a2c', a.t2[2].hp);
  }

  while (dyn.children.length) dyn.remove(dyn.children[0]);
  for (const [tx, ty] of (a.trees || [])) {
    const [x, z] = xz(tx, ty);
    const m = new THREE.Mesh(treeGeo, treeMat);
    m.position.set(x, 0.7, z);
    dyn.add(m);
  }
  for (const [rx, ry] of (a.rocks || [])) {
    const [x, z] = xz(rx, ry);
    const m = new THREE.Mesh(rockGeo, rockMat);
    m.position.set(x, 0.4, z);
    dyn.add(m);
  }
  for (const [gx, gy] of (a.golds || [])) {
    const [x, z] = xz(gx, gy);
    const m = new THREE.Mesh(goldGeo, goldMat);
    m.position.set(x, 0.5, z);
    dyn.add(m);
  }
  for (const key of (a.walls || [])) {
    const [wx, wy] = key.split(',').map(Number);
    const [x, z] = xz(wx, wy);
    const m = new THREE.Mesh(wallGeo, wallMat);
    m.position.set(x, 0.45, z);
    dyn.add(m);
  }
  const gas = (typeof a.gas === 'number') ? a.gas : 99;
  if (gas < 90) {
    const [tx, tz] = xz(16, 16);
    gasMesh.visible = true;
    gasMesh.position.set(tx, 0.06, tz);
    gasMesh.scale.set(gas, gas, 1);
  } else gasMesh.visible = false;
  const showPing = (mesh, c, tick) => {
    if (c && typeof c.x === 'number' && tick >= c.tick) {
      const [x, z] = xz(c.x, c.y);
      mesh.visible = true;
      mesh.position.set(x, 0.6 + 0.2 * Math.sin(performance.now() / 300), z);
      mesh.rotation.y += 0.05;
    } else mesh.visible = false;
  };
  showPing(ping1, a.c1, a.tick);
  showPing(ping2, a.c2, a.tick);
  const g1 = a.p1.gold || 0, g2 = a.p2.gold || 0;
  document.getElementById('hp1').style.width = Math.max(0, a.p1.hp) + '%';
  document.getElementById('hp2').style.width = Math.max(0, a.p2.hp) + '%';
  const msg = (a.m1 || a.m2) ? `\nmsg P1:"${a.m1 || ''}" P2:"${a.m2 || ''}"` : '';
  elStats.textContent =
    `P1 blu hp=${a.p1.hp} legna=${a.p1.wood} pietra=${a.p1.stone} gold=${g1} spada=${a.p1.sword ? 'si' : 'no'} [${a.a1}]\n` +
    `P2 rosso hp=${a.p2.hp} legna=${a.p2.wood} pietra=${a.p2.stone} gold=${g2} spada=${a.p2.sword ? 'si' : 'no'} [${a.a2}]${msg}`;
  drawMini(a);
  drawGraph();
}

const mini = document.getElementById('mini').getContext('2d');
const graph = document.getElementById('graph').getContext('2d');
function drawMini(a) {
  mini.fillStyle = '#0b0e14'; mini.fillRect(0, 0, 128, 128);
  const px = v => Math.floor(v / 32 * 128);
  mini.fillStyle = '#3fae5a';
  for (const [x, y] of (a.trees || [])) mini.fillRect(px(x), px(y), 3, 3);
  mini.fillStyle = '#9aa3b2';
  for (const [x, y] of (a.rocks || [])) mini.fillRect(px(x), px(y), 3, 3);
  mini.fillStyle = '#ffd700';
  for (const [x, y] of (a.golds || [])) mini.fillRect(px(x), px(y), 4, 4);
  mini.fillStyle = '#ffc94d'; mini.fillRect(px(16), px(16), 5, 5);
  if (Array.isArray(a.t1) && Array.isArray(a.t2)) {
    mini.fillStyle = '#4da3ff';
    for (const u of a.t1) mini.fillRect(px(u.x), px(u.y), 4, 4);
    mini.fillStyle = '#ff5d5d';
    for (const u of a.t2) mini.fillRect(px(u.x), px(u.y), 4, 4);
  } else {
    mini.fillStyle = '#4da3ff'; mini.fillRect(px(a.p1.x), px(a.p1.y), 5, 5);
    mini.fillStyle = '#ff5d5d'; mini.fillRect(px(a.p2.x), px(a.p2.y), 5, 5);
  }
}
function drawGraph() {
  graph.fillStyle = '#0b0e14'; graph.fillRect(0, 0, 160, 128);
  if (frames.length < 2) return;
  const line = (key, color) => {
    graph.strokeStyle = color; graph.beginPath();
    frames.forEach((f, i) => {
      const x = i / (frames.length - 1) * 160;
      const y = 128 - (f[key === 'p1' ? 'p1' : 'p2'].hp / 100) * 128;
      i ? graph.lineTo(x, y) : graph.moveTo(x, y);
    });
    graph.stroke();
    const cx = Math.floor(tFloat) / (frames.length - 1) * 160;
    graph.fillStyle = '#fff'; graph.fillRect(cx, 0, 1, 128);
  };
  line('p1', '#4da3ff'); line('p2', '#ff5d5d');
}

let last = performance.now();
let camMode = 'orbit';
function loop(now) {
  requestAnimationFrame(loop);
  const dt = (now - last) / 1000;
  last = now;
  if (frames.length && playing) {
    const eff = (SET.slow && performance.now() < slowmoUntil) ? 0.25 : 1;
    tFloat += dt * 2 * speed * eff;
    if (tFloat >= frames.length - 1) tFloat = 0;
    elTick.value = Math.floor(tFloat);
    const tag = (SET.slow && performance.now() < slowmoUntil) ? ' (slow-mo KO!)' : '';
    elLabel.textContent = `tick ${Math.floor(tFloat)}/${frames.length - 1}${tag}`;
  }
  if (frames.length) {
    const i = Math.min(frames.length - 2, Math.floor(tFloat));
    drawFrame(frames[i], frames[i + 1], tFloat - i);
    if (camMode === 'follow') {
      const f = frames[Math.floor(tFloat)];
      const pts = (Array.isArray(f.t1) && Array.isArray(f.t2)) ? [...f.t1, ...f.t2] : [f.p1, f.p2];
      const mx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
      const mz = pts.reduce((s, p) => s + p.y, 0) / pts.length;
      const [wx, wz] = xz(mx, mz);
      camera.position.set(wx, 18, wz + 14);
      camera.lookAt(wx, 0, wz);
    } else {
      const cx = 0, cz = 0;
      camera.position.set(
        cx + orbit.r * Math.sin(orbit.phi) * Math.sin(orbit.theta),
        orbit.r * Math.cos(orbit.phi),
        cz + orbit.r * Math.sin(orbit.phi) * Math.cos(orbit.theta));
      camera.lookAt(cx, 0, cz);
    }
    const nowS = performance.now();
    if (SET.shake && nowS < shakeUntil) {
      const k = (shakeUntil - nowS) / 450;
      camera.position.x += (Math.random() - 0.5) * 2.4 * k;
      camera.position.y += (Math.random() - 0.5) * 1.6 * k;
    }
  }
  tickParts(dt);
  totemMat.emissiveIntensity = 0.8 + 0.4 * Math.sin(now / 500);
  renderer.render(scene, camera);
}
requestAnimationFrame(loop);

{
  let lastP = null, pinch = 0;
  canvas.style.touchAction = 'none';
  const pos = e => ({ x: e.clientX ?? e.touches?.[0]?.clientX, y: e.clientY ?? e.touches?.[0]?.clientY });
  canvas.addEventListener('pointerdown', e => { lastP = pos(e); canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    if (!lastP || camMode !== 'orbit') return;
    const p = pos(e);
    orbit.theta -= (p.x - lastP.x) * 0.006;
    orbit.phi = Math.min(1.35, Math.max(0.15, orbit.phi - (p.y - lastP.y) * 0.004));
    lastP = p;
  });
  const end = () => { lastP = null; pinch = 0; };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('touchmove', e => {
    if (e.touches.length === 2 && camMode === 'orbit') {
      e.preventDefault();
      const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      if (pinch) orbit.r = Math.min(70, Math.max(14, orbit.r * (pinch / d)));
      pinch = d;
    }
  }, { passive: false });
}

document.getElementById('file').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (f) parseReplay(await f.text(), f.name);
});
document.getElementById('demo').addEventListener('click', async () => {
  const candidates = ['../matches/1/replay.jsonl', './demo.jsonl'];
  for (const u of candidates) {
    try {
      const r = await fetch(u);
      if (r.ok) { parseReplay(await r.text(), 'demo seed 1'); return; }
    } catch {}
  }
  document.getElementById('stats').textContent = 'demo non trovata: avvia `python -m http.server` nella root oppure carica un replay.jsonl a mano';
});
elPlay.addEventListener('click', () => {
  playing = !playing;
  elPlay.textContent = playing ? 'pausa' : 'play';
});
document.getElementById('speed').addEventListener('change', (e) => { speed = Number(e.target.value); });
elTick.addEventListener('input', () => { tFloat = Number(elTick.value); });
document.getElementById('top').addEventListener('click', () => {
  if (frames.length) {
    tFloat = Math.max(0, topTick - 4);
    elTick.value = Math.floor(tFloat);
  }
});
document.getElementById('cam').addEventListener('click', (e) => {
  camMode = camMode === 'orbit' ? 'follow' : 'orbit';
  e.target.textContent = camMode === 'orbit' ? 'camera: orbita' : 'camera: follow';
});
document.getElementById('full').addEventListener('click', async (e) => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {}
});
function toggleAudio() {
  SET.audio = !SET.audio; setAudio(SET.audio); saveSet(); applySettings();
  if (SET.audio) blip(440, 0.08);
}
document.getElementById('audio').addEventListener('click', toggleAudio);
document.getElementById('set-audio2').addEventListener('click', toggleAudio);
document.getElementById('set-q').addEventListener('click', () => {
  SET.q = SET.q === 'high' ? 'low' : 'high'; saveSet(); applySettings(); resize();
});
document.getElementById('set-shake').addEventListener('click', () => {
  SET.shake = !SET.shake; saveSet(); applySettings();
});
document.getElementById('set-slow').addEventListener('click', () => {
  SET.slow = !SET.slow; saveSet(); applySettings();
});
document.getElementById('clip').addEventListener('click', (e) => {
  const btn = e.target;
  try {
    const stream = canvas.captureStream(30);
    const rec = new MediaRecorder(stream, { mimeType: 'video/webm', videoBitsPerSecond: 4_000_000 });
    const chunks = [];
    rec.ondataavailable = ev => ev.data.size && chunks.push(ev.data);
    rec.onstop = () => {
      const url = URL.createObjectURL(new Blob(chunks, { type: 'video/webm' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `botcraft-${Date.now()}.webm`;
      a.click();
      btn.textContent = 'clip 15s';
    };
    rec.start();
    btn.textContent = 'registro… 15s';
    setTimeout(() => rec.state !== 'inactive' && rec.stop(), 15000);
  } catch (err) {
    btn.textContent = 'clip non supportata qui';
    setTimeout(() => btn.textContent = 'clip 15s', 2000);
  }
});
document.getElementById('share').addEventListener('click', () => {
  navigator.clipboard.writeText(location.href);
  document.getElementById('share').textContent = 'link copiato!';
  setTimeout(() => document.getElementById('share').textContent = 'copia share link', 1500);
});
(async () => {
  const q = new URLSearchParams(location.search).get('match');
  if (!q) return;
  const candidates = [
    `../matches/${q}/replay.jsonl`,
    `/replays/${q}/replay.jsonl`,
    `https://botcraft-6tjh.onrender.com/replays/${q}/replay.jsonl`,
    './demo.jsonl',
  ];
  for (const u of candidates) {
    try {
      const r = await fetch(u);
      if (r.ok) { parseReplay(await r.text(), 'match ' + q); return; }
    } catch {}
  }
  document.getElementById('stats').textContent = `replay ${q} non trovato qui: aprilo da ladder o caricalo a mano`;
})();
