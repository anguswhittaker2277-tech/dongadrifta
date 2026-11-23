const L = require('./lib2.js'); const fs = require('fs'), path = require('path');
const Q = path.join(__dirname, 'models/q');
(async () => {
  const { browser, page, logs } = await L.start({ w: 600, h: 400 });
  await page.route('**/__q/*', r => { const k = r.request().url().split('/__q/')[1]; r.fulfill({ body: fs.readFileSync(path.join(Q, k)), contentType: 'application/octet-stream' }); });
  await L.run(page, 1);
  for (const [src, dst] of [['M_all.fbx', 'chars_m.raw.glb'], ['W_all.fbx', 'chars_w.raw.glb']]) {
    const b64 = await page.evaluate(async (src) => { const G = __game, T = G.THREE; const { FBXLoader } = await import('three/addons/loaders/FBXLoader.js'); const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
      const o = await new Promise((res, rej) => new FBXLoader().load('/__q/' + src, res, undefined, rej));
      const arm = o.getObjectByName('CharacterArmature'); o.updateMatrixWorld(true);
      // one clean skeleton, rebuilt from the bones that actually drive a mesh (the importer nests 48 copies of every bone inside each other)
      const m0 = (() => { let r = null; o.traverse(m => { if (!r && m.isSkinnedMesh) r = m; }); return r; })();
      const W = {}, parentName = {}; for (const b of m0.skeleton.bones) { W[b.name] = b.matrixWorld.clone(); let p = b.parent; while (p && p.isBone && p.name === b.name) p = p.parent; parentName[b.name] = p && p.isBone ? p.name : null; }
      const nb = {}; for (const b of m0.skeleton.bones) { nb[b.name] = new T.Bone(); nb[b.name].name = b.name; }
      const old = arm.children.filter(c => c.isBone); old.forEach(c => arm.remove(c));
      const armInv = arm.matrixWorld.clone().invert();
      for (const b of m0.skeleton.bones) { const pn = parentName[b.name], par = pn && nb[pn] ? nb[pn] : arm; par.add(nb[b.name]);
        const local = (pn && W[pn] ? W[pn].clone().invert() : armInv.clone()).multiply(W[b.name]); local.decompose(nb[b.name].position, nb[b.name].quaternion, nb[b.name].scale); }
      const map = nb;
      const drop = ['Sword', 'Pistol']; const meshes = []; o.traverse(m => { if (m.isSkinnedMesh) meshes.push(m); });
      for (const m of meshes) { if (drop.includes(m.name)) { m.parent.remove(m); continue; }
        const bones = m.skeleton.bones.map(b => map[b.name]); if (bones.some(b => !b)) throw new Error('missing bone in ' + m.name);
        m.bind(new T.Skeleton(bones, m.skeleton.boneInverses), m.bindMatrix);
        // bake: every face's colour into the vertices, regrouped into three: skin (recolourable), hair (recolourable), the rest
        const mats = Array.isArray(m.material) ? m.material : [m.material], g0 = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry;
        const groups = g0.groups.length ? g0.groups : [{ start: 0, count: g0.attributes.position.count, materialIndex: 0 }];
        const kind = q => /^Skin/i.test(q.name) ? 0 : /^(Hair|Eyebrow|Moustache|Beard)/i.test(q.name) ? 1 : 2;
        const buckets = [[], [], []]; for (const gr of groups) { const q = mats[gr.materialIndex] || mats[0]; buckets[kind(q)].push([gr.start, gr.count, q]); }
        const names = Object.keys(g0.attributes).filter(k => ['position', 'normal', 'uv', 'skinIndex', 'skinWeight'].includes(k)), out = {}; names.forEach(k => out[k] = []); const col = []; const ng = new T.BufferGeometry(); let at = 0;
        buckets.forEach((B, bi) => { const st = at; for (const [s0, c, q] of B) { const cc = q.color ? q.color.clone().convertLinearToSRGB() : new T.Color(1, 1, 1); if (bi < 2) cc.set(1, 1, 1);
            for (let v = s0; v < s0 + c; v++) { for (const k of names) { const A = g0.attributes[k]; for (let j = 0; j < A.itemSize; j++) out[k].push(A.array[v * A.itemSize + j]); } col.push(cc.r, cc.g, cc.b); at++; } }
          if (at > st) ng.addGroup(st, at - st, bi); });
        for (const k of names) { const A = g0.attributes[k]; ng.setAttribute(k, new T.BufferAttribute(new A.array.constructor(out[k]), A.itemSize, A.normalized)); }
        ng.setAttribute('color', new T.Float32BufferAttribute(col, 3));
        const pick = (bi) => { const q = buckets[bi][0] && buckets[bi][0][2]; return q && q.color ? q.color.clone().convertLinearToSRGB() : new T.Color(1, 1, 1); };
        m.geometry = ng; m.material = [new T.MeshStandardMaterial({ name: 'Skin', color: pick(0), vertexColors: false, roughness: 1 }), new T.MeshStandardMaterial({ name: 'Hair', color: pick(1), roughness: 1 }), new T.MeshStandardMaterial({ name: 'Base', color: 0xffffff, vertexColors: true, roughness: 1 })]; }
      const keep = ['Idle', 'Idle_Neutral', 'Walk', 'Run', 'Punch_Left', 'Punch_Right', 'Kick_Left', 'Kick_Right', 'HitRecieve', 'HitRecieve_2', 'Death', 'Wave', 'Interact', 'Run_Back', 'Roll'];
      const clips = o.animations.filter(a => keep.includes(a.name.split('|').pop())).map(a => { const c = a.clone(); c.name = a.name.split('|').pop(); c.tracks = c.tracks.filter(t => map[t.name.split('.')[0]]); return c; });
      const buf = await new Promise((res, rej) => new GLTFExporter().parse(o, res, rej, { binary: true, animations: clips }));
      let s = ''; const u = new Uint8Array(buf); for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); }, src);
    fs.writeFileSync(path.join(__dirname, 'models/out', dst), Buffer.from(b64, 'base64')); console.log(dst, fs.statSync(path.join(__dirname, 'models/out', dst)).size);
  }
  console.log('errors:', logs.length, logs.slice(0, 3).join('\n')); await browser.close();
})();
