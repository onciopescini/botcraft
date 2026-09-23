import * as THREE from 'three';
import { scene, PAL } from './config.js';

const agentGeo = new THREE.CapsuleGeometry(0.4, 0.8, 4, 8);
const eyeGeo = new THREE.SphereGeometry(0.11, 8, 8);
const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffffff });
const pupilGeo = new THREE.SphereGeometry(0.05, 8, 8);
const pupilMat = new THREE.MeshStandardMaterial({ color: 0x0b0e14 });

export function dressBot(mesh, stripeColor) {
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

function mk(color) {
  const m = new THREE.Mesh(agentGeo, new THREE.MeshStandardMaterial({ color }));
  m.position.y = 0.9;
  m.castShadow = true;
  scene.add(m);
  return m;
}

export const agent1 = mk(PAL().p1);
export const agent2 = mk(PAL().p2);
export const agent1b = mk(0x9fd0ff);
export const agent1c = mk(0x2b6cb0);
export const agent2b = mk(0xffa3a3);
export const agent2c = mk(0xb02b2b);
for (const m of [agent1b, agent1c, agent2b, agent2c]) m.visible = false;
export function recolor() {
  const P = PAL();
  agent1.material.color.set(P.p1);
  agent2.material.color.set(P.p2);
  dressStripe(agent1, P.p1dark); dressStripe(agent2, P.p2dark);
  setNames(lastN1, lastN2);
}
// striscia sostituibile per daltonici (la prima resta sotto, invisibile)
function dressStripe(mesh, color) {
  if (!mesh.userData.stripe2) {
    mesh.userData.stripe2 = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.2, 0.9),
      new THREE.MeshStandardMaterial({ color }));
    mesh.userData.stripe2.position.y = -0.35;
    mesh.add(mesh.userData.stripe2);
  } else mesh.userData.stripe2.material.color.set(color);
}
dressBot(agent1, 0x1e3a5f); dressBot(agent2, 0x5f1e1e);
dressBot(agent1b, 0x1e3a5f); dressBot(agent1c, 0x1e3a5f);
dressBot(agent2b, 0x5f1e1e); dressBot(agent2c, 0x5f1e1e);

export const agentMat1 = agent1.material;
export const agentMat2 = agent2.material;

// hp mostrati (animati verso il target invece di snap)
const dispHp = new Map();
export function smoothHp(mesh, key, target) {
  const cur = dispHp.has(key) ? dispHp.get(key) : target;
  const nx = cur + (target - cur) * 0.2;
  dispHp.set(key, nx);
  mesh.scale.y = 0.4 + 0.6 * (Math.max(0, nx) / 100);
}

// etichette nomi sopra i capitani (diep.io style)
function makeLabel(text, color) {
  const cv = document.createElement('canvas');
  cv.width = 256; cv.height = 64;
  const g = cv.getContext('2d');
  g.font = 'bold 30px system-ui, sans-serif';
  g.textAlign = 'center';
  g.fillStyle = 'rgba(0,0,0,0.55)';
  const w = g.measureText(text).width + 24;
  g.fillRect(128 - w / 2, 6, w, 44);
  g.fillStyle = color;
  g.fillText(text, 128, 40);
  const tex = new THREE.CanvasTexture(cv);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  sp.scale.set(3.4, 0.85, 1);
  return sp;
}
let label1 = makeLabel('Blu', PAL().p1), label2 = makeLabel('Rosso', PAL().p2);
let lastN1 = 'Blu', lastN2 = 'Rosso';
scene.add(label1, label2);
export function setNames(n1, n2) {
  lastN1 = n1.slice(0, 14); lastN2 = n2.slice(0, 14);
  scene.remove(label1, label2);
  label1 = makeLabel(lastN1, PAL().p1);
  label2 = makeLabel(lastN2, PAL().p2);
  scene.add(label1, label2);
}
export function placeLabels(x1, z1, s1, x2, z2, s2) {
  label1.position.set(x1, 2.4 * s1 + 0.6, z1);
  label2.position.set(x2, 2.4 * s2 + 0.6, z2);
}

// feed eventi spettatore (kill feed)
export function feed(html) {
  const el = document.getElementById('feed');
  if (!el) return;
  if (el.textContent.startsWith('nessun evento')) el.textContent = '';
  const d = document.createElement('div');
  d.innerHTML = html;
  el.prepend(d);
  while (el.children.length > 12) el.lastChild.remove();
}

export const flashT = { a1: 0, a2: 0 };
export let prevHp = null;
export function setPrevHp(v) { prevHp = v; }
