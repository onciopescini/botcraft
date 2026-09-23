import * as THREE from 'three';
import { scene, camera, renderer } from './config.js';

export const BOARD = 32;
export function xz(x, z) { return [x - BOARD / 2 + 0.5, z - BOARD / 2 + 0.5]; }

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const sun = new THREE.DirectionalLight(0xfff2d9, 0.9);
sun.position.set(20, 30, 10);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -20; sun.shadow.camera.right = 20;
sun.shadow.camera.top = 20; sun.shadow.camera.bottom = -20;
scene.add(sun);
scene.fog = new THREE.Fog(0x0b0e14, 45, 95);

{
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(BOARD, BOARD),
    new THREE.MeshStandardMaterial({ color: 0x1a2333 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.GridHelper(BOARD, BOARD, 0x33415e, 0x232f47);
  grid.position.y = 0.01;
  scene.add(grid);
}

export const totemMat = new THREE.MeshStandardMaterial({ color: 0xffc94d, emissive: 0x553a00, emissiveIntensity: 1 });
{
  const [x, z] = xz(16, 16);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.8, 2.4, 6), totemMat);
  m.position.set(x, 1.2, z);
  scene.add(m);
}

// sudden death: anello rosso sulla linea del gas
export const gasMesh = new THREE.Mesh(
  new THREE.RingGeometry(0.93, 1.0, 72),
  new THREE.MeshBasicMaterial({ color: 0xff2222, transparent: true, opacity: 0.16, side: THREE.DoubleSide }));
gasMesh.rotation.x = -Math.PI / 2;
gasMesh.visible = false;
scene.add(gasMesh);

// ping coach: diamanti colorati
const pingGeo = new THREE.OctahedronGeometry(0.5);
export const ping1 = new THREE.Mesh(pingGeo, new THREE.MeshBasicMaterial({ color: 0x4da3ff }));
export const ping2 = new THREE.Mesh(pingGeo, new THREE.MeshBasicMaterial({ color: 0xff5d5d }));
ping1.visible = ping2.visible = false;
scene.add(ping1, ping2);

export const treeGeo = new THREE.ConeGeometry(0.45, 1.4, 6);
export const treeMat = new THREE.MeshStandardMaterial({ color: 0x3fae5a });
export const rockGeo = new THREE.DodecahedronGeometry(0.4);
export const rockMat = new THREE.MeshStandardMaterial({ color: 0x9aa3b2 });
export const wallGeo = new THREE.BoxGeometry(0.9, 0.9, 0.9);
export const wallMat = new THREE.MeshStandardMaterial({ color: 0xc9a06a });
export const goldGeo = new THREE.OctahedronGeometry(0.45);
export const goldMat = new THREE.MeshStandardMaterial({ color: 0xffd700, emissive: 0x554400 });
export const dyn = new THREE.Group();
scene.add(dyn);

export function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();

// orbita touch+mouse (solo modalità orbita, gestita in app.js)
export const orbit = { theta: 0, phi: 0.28, r: 36 };
