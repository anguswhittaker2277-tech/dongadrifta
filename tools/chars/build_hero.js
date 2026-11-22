const L = require('./lib2.js'); const fs = require('fs'), path = require('path');
const U = path.join(__dirname, 'models/ubc');
(async () => {
  const { browser, page, logs } = await L.start({ w: 600, h: 400 });
  await page.route('**/__u/*', r => { let k = decodeURIComponent(r.request().url().split('/__u/')[1]); if (!fs.existsSync(path.join(U, k))) k = k.replace('_png.png', '.png'); r.fulfill({ body: fs.readFileSync(path.join(U, k)), contentType: k.endsWith('png') ? 'image/png' : k.endsWith('gltf') ? 'model/gltf+json' : 'application/octet-stream' }); });
  await L.run(page, 1);
  const b64 = await page.evaluate(async () => { const G = __game, T = G.THREE; const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js'); const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
    const gl = new GLTFLoader(), load = u => new Promise((res, rej) => gl.load(u, res, undefined, rej));
    const g = await load('/__u/Superhero_Male_FullBody.gltf'), o = g.scene; let body = null; o.traverse(m => { if (m.isSkinnedMesh && /Superhero/.test(m.material.name)) body = m; });
    const img = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = '/__u/T_Superhero_Male_Light.png'; });
    const S = 1024, cv = document.createElement('canvas'); cv.width = cv.height = S; const cx = cv.getContext('2d'); cx.drawImage(img, 0, 0, S, S);
    // grey gym shorts over the briefs: the triangles between the hips and just above the knee
    const gm = body.geometry, P = gm.attributes.position, UV = gm.attributes.uv, I = gm.index; gm.computeBoundingBox(); const bb = gm.boundingBox, H = bb.max.y - bb.min.y;
    cx.fillStyle = cx.strokeStyle = '#4a4e55'; cx.lineWidth = 1.5; const n = I ? I.count : P.count;
    for (let k = 0; k < n; k += 3) { const ids = I ? [I.getX(k), I.getX(k + 1), I.getX(k + 2)] : [k, k + 1, k + 2]; let y = 0, x = 0; for (const id of ids) { y += P.getY(id); x += P.getX(id); } const h = (y / 3 - bb.min.y) / H;
      if (h > 0.335 && h < 0.53 && Math.abs(x / 3) / H < 0.13) { cx.beginPath(); ids.forEach((id, j) => { const px = UV.getX(id) * S, py = UV.getY(id) * S; j ? cx.lineTo(px, py) : cx.moveTo(px, py); }); cx.closePath(); cx.fill(); cx.stroke(); } }
    const t = new T.CanvasTexture(cv); t.flipY = false; t.colorSpace = T.SRGBColorSpace; t.userData.mimeType = 'image/jpeg';
    const nimg = await new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = '/__u/T_Superhero_Male_Normal.png'; }); const nc = document.createElement('canvas'); nc.width = nc.height = 512; nc.getContext('2d').drawImage(nimg, 0, 0, 512, 512);
    const nt = new T.CanvasTexture(nc); nt.flipY = false; nt.userData.mimeType = 'image/jpeg';
    body.material = new T.MeshStandardMaterial({ name: 'Skin', map: t, normalMap: nt, roughness: 0.85, metalness: 0 });
    o.traverse(m => { if (m.isMesh && m !== body) { const q = m.material; if (/Hair/.test(q.name)) m.material = new T.MeshStandardMaterial({ name: 'Hair', color: 0x8a6a3a, roughness: 0.9 }); else if (/Eye/.test(q.name)) m.material = new T.MeshStandardMaterial({ name: 'Eyes', color: 0x5a4030, roughness: 0.4 }); } });
    const hg = await load('/__u/Hair_Buzzed.gltf'); const B = {}; o.traverse(b => { if (b.isBone) B[b.name] = b; });
    const hm = []; hg.scene.traverse(m => { if (m.isSkinnedMesh) hm.push(m); }); for (const m of hm) { m.bind(new T.Skeleton(m.skeleton.bones.map(b => B[b.name] || b), m.skeleton.boneInverses), m.bindMatrix); m.material = new T.MeshStandardMaterial({ name: 'Hair', color: 0x8a6a3a, roughness: 0.9 }); body.parent.add(m); }
    const buf = await new Promise((res, rej) => new GLTFExporter().parse(o, res, rej, { binary: true, maxTextureSize: 1024 }));
    let s = ''; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); });
  fs.writeFileSync(path.join(__dirname, 'models/out/hero.raw.glb'), Buffer.from(b64, 'base64'));
  console.log('hero', fs.statSync(path.join(__dirname, 'models/out/hero.raw.glb')).size, 'errors:', logs.length, logs.slice(0, 3).join('\n')); await browser.close();
})();
