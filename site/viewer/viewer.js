import * as THREE from 'three';

// Botcraft S2 viewer — stupido per design: legge replay.jsonl, non conosce le regole.
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0e14);
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
// vista isometrica-like sulla 32x32
camera.position.set(16, 34, 26);
camera.lookAt(16, 0, 16);

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(20, 30, 10);
scene.add(sun);

const BOARD = 32;
function xz(x, z) { return [x - BOARD / 2 + 0.5, z - BOARD / 2 + 0.5]; }

// pavimento + griglia
{
  const [cx, cz] = [0, 0];
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(BOARD, BOARD),
    new THREE.MeshStandardMaterial({ color: 0x1a2333 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(cx, 0, cz);
  scene.add(floor);
  const grid = new THREE.GridHelper(BOARD, BOARD, 0x33415e, 0x232f47);
  grid.position.y = 0.01;
  scene.add(grid);
}
// totem centrale (16,16) con glow pulsante
const totemMat = new THREE.MeshStandardMaterial({ color: 0xffc94d, emissive: 0x553a00, emissiveIntensity: 1 });
{
  const [x, z] = xz(16, 16);
  const m = new THREE.Mesh(
    new THREE.CylinderGeometry(0.6, 0.8, 2.4, 6),
    totemMat
  );
  m.position.set(x, 1.2, z);
  scene.add(m);
}

const agentGeo = new THREE.CapsuleGeometry(0.4, 0.8, 4, 8);
// occhi + striscia team: figli della capsula così seguono il movimento
const eyeGeo = new THREE.SphereGeometry(0.11, 8, 8);
const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
const pupilGeo = new THREE.SphereGeometry(0.05, 8, 8);
const pupilMat = new THREE.MeshStandardMaterial({ color: 0x0b0e14 });
function dressBot(mesh, stripeColor) {
  const stripe = new THREE.Mesh(
    new THREE.BoxGeometry(0.86, 0.18, 0.86),
    new THREE.MeshStandardMaterial({ color: stripeColor })
  );
  stripe.position.y = -0.35;
  mesh.add(stripe);
  for (const sx of [-0.16, 0.16]) {
    const e = new THREE.Mesh(eyeGeo, eyeMat);
    e.position.set(sx, 0.45, 0.34);
    const p = new THREE.Mesh(pupilGeo, pupilMat);
    p.position.set(sx, 0.45, 0.44);
    mesh.add(e, p);
  }
}
const agentMat1 = new THREE.MeshStandardMaterial({ color: 0x4da3ff });
const agentMat2 = new THREE.MeshStandardMaterial({ color: 0xff5d5d });
const agent1 = new THREE.Mesh(agentGeo, agentMat1);
const agent2 = new THREE.Mesh(agentGeo, agentMat2);
agent1.position.y = agent2.position.y = 0.9;
scene.add(agent1, agent2);
// squad S2: altri 2 cloni per team (tonalità chiare), nascosti nei replay v1
const agentMat1b = new THREE.MeshStandardMaterial({ color: 0x9fd0ff });
const agentMat1c = new THREE.MeshStandardMaterial({ color: 0x2b6cb0 });
const agentMat2b = new THREE.MeshStandardMaterial({ color: 0xffa3a3 });
const agentMat2c = new THREE.MeshStandardMaterial({ color: 0xb02b2b });
const agent1b = new THREE.Mesh(agentGeo, agentMat1b);
const agent1c = new THREE.Mesh(agentGeo, agentMat1c);
const agent2b = new THREE.Mesh(agentGeo, agentMat2b);
const agent2c = new THREE.Mesh(agentGeo, agentMat2c);
for (const m of [agent1b, agent1c, agent2b, agent2c]) { m.position.y = 0.9; m.visible = false; scene.add(m); }
dressBot(agent1, 0x1e3a5f); dressBot(agent2, 0x5f1e1e);
dressBot(agent1b, 0x1e3a5f); dressBot(agent1c, 0x1e3a5f);
dressBot(agent2b, 0x5f1e1e); dressBot(agent2c, 0x5f1e1e);
// flash hit: timestamp ultimo danno per capitano (bianco per 180ms)
const flashT = { a1: 0, a2: 0 };
let prevHp = null;

// pool dinamico per alberi/rocce/muri (ricreati per tick, max ~100 oggetti: ok per S0)
const dyn = new THREE.Group();
scene.add(dyn);
const treeGeo = new THREE.ConeGeometry(0.45, 1.4, 6);
const treeMat = new THREE.MeshStandardMaterial({ color: 0x3fae5a });
const rockGeo = new THREE.DodecahedronGeometry(0.4);
const rockMat = new THREE.MeshStandardMaterial({ color: 0x9aa3b2 });
const wallGeo = new THREE.BoxGeometry(0.9, 0.9, 0.9);
const wallMat = new THREE.MeshStandardMaterial({ color: 0xc9a06a });
const goldGeo = new THREE.OctahedronGeometry(0.45);
const goldMat = new THREE.MeshStandardMaterial({ color: 0xffd700, emissive: 0x554400 });
// particelle leggere: pool di cubetti riusati (gather verde/grigio/oro, KO arancione)
const partGeo = new THREE.BoxGeometry(0.16, 0.16, 0.16);
const parts = [];
function burst(wx, wz, color, n = 10, up = 3) {
  for (let i = 0; i < n; i++) {
    let p = parts.find(q => q.life <= 0);
    if (!p) {
      if (parts.length >= 140) return;
      p = { mesh: new THREE.Mesh(partGeo, new THREE.MeshBasicMaterial({ color: 0xffffff })), vel: new THREE.Vector3(), life: 0 };
      scene.add(p.mesh);
      parts.push(p);
    }
    p.mesh.material.color = new THREE.Color(color);
    p.mesh.position.set(wx + (Math.random() - 0.5) * 0.5, 0.8, wz + (Math.random() - 0.5) * 0.5);
    p.vel.set((Math.random() - 0.5) * 3, up * (0.6 + Math.random() * 0.8), (Math.random() - 0.5) * 3);
    p.life = 0.7 + Math.random() * 0.4;
  }
}
function tickParts(dt) {
  for (const p of parts) {
    if (p.life <= 0) { p.mesh.visible = false; continue; }
    p.life -= dt;
    p.mesh.visible = p.life > 0;
    p.vel.y -= 6 * dt;
    p.mesh.position.addScaledVector(p.vel, dt);
    if (p.mesh.position.y < 0.05) p.mesh.position.y = 0.05;
  }
}
let slowmoUntil = 0;
let prevSnap = null;
let topTick = 0; // top-moment auto: primo KO o danno max

let frames = [];
let playing = true;
let speed = 2; // ticks/sec base 2 * speed
let tFloat = 0;

const elTick = document.getElementById('tick');
const elLabel = document.getElementById('ticklabel');
const elStats = document.getElementById('stats');
const elPlay = document.getElementById('play');

function parseReplay(text) {
  frames = text.trim().split('\n').filter(Boolean).map(l => JSON.parse(l));
  tFloat = 0;
  prevHp = null;
  prevSnap = null;
  slowmoUntil = 0;
  // top-moment: primo KO, altrimenti tick del danno singolo max
  topTick = 0;
  let best = 0;
  for (let i = 1; i < frames.length; i++) {
    const P = frames[i - 1], Q = frames[i];
    const d = (P.p1.hp - Q.p1.hp) + (P.p2.hp - Q.p2.hp);
    if ((P.p1.hp > 0 && Q.p1.hp <= 0) || (P.p2.hp > 0 && Q.p2.hp <= 0)) { topTick = i; break; }
    if (d > best) { best = d; topTick = i; }
  }
  elTick.max = Math.max(0, frames.length - 1);
  elTick.value = 0;
  elLabel.textContent = `tick 0/${frames.length - 1}`;
}

function drawFrame(a, b, alpha) {
  // interpola posizioni agenti tra frame a e b
  const lerp = (p, q) => p + (q - p) * alpha;
  const [x1, z1] = xz(lerp(a.p1.x, b.p1.x), lerp(a.p1.y, b.p1.y));
  const [x2, z2] = xz(lerp(a.p2.x, b.p2.x), lerp(a.p2.y, b.p2.y));
  agent1.position.x = x1; agent1.position.z = z1;
  agent2.position.x = x2; agent2.position.z = z2;
  // altezza = hp (feedback visivo), spada = emissive, flash bianco sul danno
  agent1.scale.y = 0.4 + 0.6 * (a.p1.hp / 100);
  agent2.scale.y = 0.4 + 0.6 * (a.p2.hp / 100);
  if (prevHp && a.p1.hp < prevHp[0]) flashT.a1 = performance.now();
  if (prevHp && a.p2.hp < prevHp[1]) flashT.a2 = performance.now();
  prevHp = [a.p1.hp, a.p2.hp];
  const nowF = performance.now();
  agentMat1.emissive = new THREE.Color(nowF - flashT.a1 < 180 ? 0xffffff : (a.p1.sword ? 0x003a88 : 0x000000));
  agentMat2.emissive = new THREE.Color(nowF - flashT.a2 < 180 ? 0xffffff : (a.p2.sword ? 0x881100 : 0x000000));
  // eventi: gather (risorse aumentate) -> puff colorato; KO -> esplosione + slow-mo 0.25x per 2s
  if (prevSnap) {
    const res = (P, Q) => [Q.wood - P.wood, Q.stone - P.stone, (Q.gold || 0) - (P.gold || 0)];
    const [dw1, ds1, dg1] = res(prevSnap.p1, a.p1);
    const [dw2, ds2, dg2] = res(prevSnap.p2, a.p2);
    if (dw1 > 0) burst(agent1.position.x, agent1.position.z, 0x3fae5a, 8);
    if (ds1 > 0) burst(agent1.position.x, agent1.position.z, 0x9aa3b2, 8);
    if (dg1 > 0) burst(agent1.position.x, agent1.position.z, 0xffd700, 12);
    if (dw2 > 0) burst(agent2.position.x, agent2.position.z, 0x3fae5a, 8);
    if (ds2 > 0) burst(agent2.position.x, agent2.position.z, 0x9aa3b2, 8);
    if (dg2 > 0) burst(agent2.position.x, agent2.position.z, 0xffd700, 12);
    for (const [P, Q, mesh] of [[prevSnap.p1, a.p1, agent1], [prevSnap.p2, a.p2, agent2]]) {
      if (P.hp > 0 && Q.hp <= 0) {
        burst(mesh.position.x, mesh.position.z, 0xff7a00, 40, 5);
        slowmoUntil = performance.now() + 2000;
      }
    }
  }
  prevSnap = JSON.parse(JSON.stringify({ p1: a.p1, p2: a.p2 }));
  // S2: 6 unità se replay v2
  const squad = Array.isArray(a.t1) && Array.isArray(a.t2);
  const bSquad = b && Array.isArray(b.t1) && Array.isArray(b.t2);
  for (const m of [agent1b, agent1c, agent2b, agent2c]) m.visible = !!squad;
  if (squad) {
    const put = (mesh, P, Q) => {
      const [x, z] = xz(lerp(P.x, Q.x), lerp(P.y, Q.y));
      mesh.position.x = x; mesh.position.z = z;
      mesh.scale.y = 0.4 + 0.6 * (P.hp / 100);
    };
    put(agent1b, a.t1[1], (bSquad ? b : a).t1[1]);
    put(agent1c, a.t1[2], (bSquad ? b : a).t1[2]);
    put(agent2b, a.t2[1], (bSquad ? b : a).t2[1]);
    put(agent2c, a.t2[2], (bSquad ? b : a).t2[2]);
  }

  // risorse del frame A (se replay vecchio senza trees, mostra solo agenti)
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
  const g1 = a.p1.gold || 0, g2 = a.p2.gold || 0;
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
    // cursore tick corrente
    const cx = Math.floor(tFloat) / (frames.length - 1) * 160;
    graph.fillStyle = '#fff'; graph.fillRect(cx, 0, 1, 128);
  };
  line('p1', '#4da3ff'); line('p2', '#ff5d5d');
}

function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();

let last = performance.now();
function loop(now) {
  requestAnimationFrame(loop);
  const dt = (now - last) / 1000;
  last = now;
  if (frames.length && playing) {
    const eff = performance.now() < slowmoUntil ? 0.25 : 1; // slow-mo KO
    tFloat += dt * 2 * speed * eff;
    if (tFloat >= frames.length - 1) tFloat = 0; // loop
    elTick.value = Math.floor(tFloat);
    const tag = performance.now() < slowmoUntil ? ' (slow-mo KO!)' : '';
    elLabel.textContent = `tick ${Math.floor(tFloat)}/${frames.length - 1}${tag}`;
  }
  if (frames.length) {
    const i = Math.min(frames.length - 2, Math.floor(tFloat));
    drawFrame(frames[i], frames[i + 1], tFloat - i);
    if (camMode === 'follow') {
      // punto medio dei capitani (o delle 6 unità se v2)
      const f = frames[Math.floor(tFloat)];
      const pts = (Array.isArray(f.t1) && Array.isArray(f.t2)) ? [...f.t1, ...f.t2] : [f.p1, f.p2];
      const mx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
      const mz = pts.reduce((s, p) => s + p.y, 0) / pts.length;
      const [wx, wz] = xz(mx, mz);
      camera.position.set(wx, 18, wz + 14);
      camera.lookAt(wx, 0, wz);
    } else {
      camera.position.set(16, 34, 26);
      camera.lookAt(16, 0, 16);
    }
  }
  tickParts(dt);
  totemMat.emissiveIntensity = 0.8 + 0.4 * Math.sin(now / 500); // glow pulsante
  renderer.render(scene, camera);
}
requestAnimationFrame(loop);
let camMode = 'orbit';

document.getElementById('file').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  if (f) parseReplay(await f.text());
});
document.getElementById('demo').addEventListener('click', async () => {
  // funziona se servi la root: python -m http.server
  const candidates = ['../matches/1/replay.jsonl', './demo.jsonl'];
  for (const u of candidates) {
    try {
      const r = await fetch(u);
      if (r.ok) { parseReplay(await r.text()); return; }
    } catch {}
  }
  alert('demo non trovata: avvia `python -m http.server` nella root oppure carica un replay.jsonl a mano');
});
elPlay.addEventListener('click', () => {
  playing = !playing;
  elPlay.textContent = playing ? '⏸ pausa' : '▶ play';
});
document.getElementById('speed').addEventListener('change', (e) => { speed = Number(e.target.value); });
elTick.addEventListener('input', () => { tFloat = Number(elTick.value); });
document.getElementById('top').addEventListener('click', () => {
  if (frames.length) {
    tFloat = Math.max(0, topTick - 4); // 2s prima del momento per contesto
    elTick.value = Math.floor(tFloat);
  }
});
document.getElementById('cam').addEventListener('click', (e) => {  camMode = camMode === 'orbit' ? 'follow' : 'orbit';
  e.target.textContent = camMode === 'orbit' ? 'camera: orbita' : 'camera: follow';
});
document.getElementById('clip').addEventListener('click', (e) => {
  // registra 15s di canvas in webm, pronta per Discord/X. Muto default: niente audio.
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
      btn.textContent = 'registra clip 15s';
    };
    rec.start();
    btn.textContent = 'registro… 15s';
    setTimeout(() => rec.state !== 'inactive' && rec.stop(), 15000);
  } catch (err) {
    btn.textContent = 'clip non supportata qui';
    setTimeout(() => btn.textContent = 'registra clip 15s', 2000);
  }
});
document.getElementById('share').addEventListener('click', () => {  navigator.clipboard.writeText(location.href);
  document.getElementById('share').textContent = 'link copiato!';
  setTimeout(() => document.getElementById('share').textContent = 'copia share link', 1500);
});
// share link ?match=ladder-4|1|demo — prova API /replays poi demo locale
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
      if (r.ok) { parseReplay(await r.text()); return; }
    } catch {}
  }
})();
