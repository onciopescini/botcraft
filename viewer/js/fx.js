import * as THREE from 'three';
import { scene, SET } from './config.js';

// particelle leggere: pool di cubetti riusati (gather verde/grigio/oro, KO arancione)
const partGeo = new THREE.BoxGeometry(0.16, 0.16, 0.16);
const parts = [];
export function burst(wx, wz, color, n = 10, up = 3) {
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
export function tickParts(dt) {
  for (const p of parts) {
    if (p.life <= 0) { p.mesh.visible = false; continue; }
    p.life -= dt;
    p.mesh.visible = p.life > 0;
    p.vel.y -= 6 * dt;
    p.mesh.position.addScaledVector(p.vel, dt);
    if (p.mesh.position.y < 0.05) p.mesh.position.y = 0.05;
  }
}

export let slowmoUntil = 0;
export let shakeUntil = 0;
export function koFX() {
  slowmoUntil = performance.now() + 2000;
  shakeUntil = performance.now() + 450;
}
export function setSlowmo(v) { slowmoUntil = v; }
export function setShake(v) { shakeUntil = v; }

// audio WebAudio, muto default (rispetta SET)
let AC = null;
export let audioOn = !!SET.audio;
export function setAudio(v) { audioOn = v; }
export function blip(freq, dur = 0.06, vol = 0.08) {
  if (!audioOn) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    const o = AC.createOscillator(), g = AC.createGain();
    o.frequency.value = freq; o.type = 'sine';
    g.gain.setValueAtTime(vol, AC.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, AC.currentTime + dur);
    o.connect(g).connect(AC.destination);
    o.start(); o.stop(AC.currentTime + dur);
  } catch {}
}
