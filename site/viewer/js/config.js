import * as THREE from 'three';

// Impostazioni persistenti (stile surviv.io). Niente DOM qui tranne applySet.
export const SET = Object.assign({ q: 'high', shake: true, slow: true, audio: false, cb: false },
  JSON.parse(localStorage.getItem('botcraft-set') || '{}'));

// palette daltonici-safe (Okabe-Ito): blu vs vermiglio invece di blu vs rosso
export function PAL() {
  return SET.cb ? { p1: '#0072B2', p1dark: '#0a3a5c', p2: '#D55E00', p2dark: '#5c260a' }
                : { p1: '#4da3ff', p1dark: '#1e3a5f', p2: '#ff5d5d', p2dark: '#5f1e1e' };
}

export function saveSet() {
  try { localStorage.setItem('botcraft-set', JSON.stringify(SET)); } catch {}
}

export const canvas = document.getElementById('c');
export const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0e14);
export const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
camera.position.set(16, 34, 26);
camera.lookAt(16, 0, 16);

export function applySettings() {
  renderer.setPixelRatio(SET.q === 'high' ? Math.min(devicePixelRatio, 2) : 1);
  const t = (id, txt) => { const e = document.getElementById(id); if (e) e.textContent = txt; };
  t('set-q', 'qualità: ' + (SET.q === 'high' ? 'alta' : 'bassa'));
  t('set-shake', 'shake: ' + (SET.shake ? 'on' : 'off'));
  t('set-slow', 'slow-mo: ' + (SET.slow ? 'on' : 'off'));
  t('set-audio2', 'audio: ' + (SET.audio ? 'on' : 'off'));
  t('audio', 'audio: ' + (SET.audio ? 'on' : 'off'));
  const cb = document.getElementById('set-cb');
  if (cb) cb.textContent = 'daltonici: ' + (SET.cb ? 'on' : 'off');
}
