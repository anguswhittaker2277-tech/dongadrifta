# FS mod → game model (the cotton picker)

`cp690.glb` in the repo root is the John Deere CP690 / 7760 round-module cotton picker from the Farming
Simulator 25 mod **"John Deere Roller Pickers 2008-2021"** by Jolly Farms Modding (version 1.2.1.0). These
scripts turn the mod's files into that GLB. The mod zip itself is not in the repo.

## Rebuild

```sh
unzip FS25_John_Deere_Pickers.zip -d mod/
python3 -I tools/fs-mod/build_cp690.py mod/ cp690.raw.glb      # needs numpy + Pillow (Pillow reads the BC7 .dds files)
node tools/fs-mod/pack.mjs cp690.raw.glb cp690.glb             # needs @gltf-transform/{core,extensions,functions}@4, meshoptimizer, sharp
```

## What the scripts do

- `i3dshapes.py` decrypts and parses GIANTS `.i3d.shapes` files. It's a Python port of
  [I3DShapesTool](https://github.com/Donkie/I3DShapesTool) (MIT, by Donkie), with the cipher key table in
  `keyconst.txt`, extended for the FS25 format (shapes version 10): an extra word before the subset table, and a
  material name per subset after it.
- `build_cp690.py` walks `cp690.i3d` and writes every node into glTF **with its i3d name**, so the game drives the
  same nodes the mod's XML animates (`pickerJoint`, `baleChamber`, `backDoorArm`, `baleDropper`, `baleNode`, the
  belt tensioner joints, ...). Hidden configuration variants keep `extras.hidden`. Skinned meshes (hoses, the
  chamber belt and cover, the seat) become glTF skins on their i3d bones. Positions, normals and UVs are quantised
  (`KHR_mesh_quantization`); each quantised mesh hangs off a `<name>_q` holder so the named node keeps its own
  transform.
- Materials: the mod uses GIANTS' shared detail library, which isn't in the zip, so each material becomes a flat
  PBR colour from its `colorScale` plus a tag in its name (`m26_paint`, `m42_steel`, `m79_glass1`, ...); the game
  builds the real materials from the tags (`cpMaterial` in `index.html`). Meshes whose only texture is a missing
  alpha decal (screw heads, interior stickers, dashboard digits) are dropped instead of being drawn as solid quads.
- Decals: the mod ships the 7760 sticker sheet, which lines up with every decal mesh on the machine; a CP690 copy
  is made by painting "CP690" over the "7760" lettering.
- The round module (`bales/cottonBale238`) is written as its own root, `module`; the five wrap textures and the
  CP690 sticker sheet ride on a hidden `texrack` mesh so every loader keeps them.
- `pack.mjs` converts the textures to WebP and meshopt-compresses the geometry without pruning, merging or
  re-parenting anything.

## Not in the mod (made in the game instead)

Tyres and rims (base-game wheel library: 520/85R42 duals and 460/85R34), the beacon, the StarFire 6000 receiver,
the reflectors, and the sounds (the mod's `sounds/cp690.xml` points at base-game sound templates).

The mod's animations and moving parts are copied into `index.html` as data (`CP_ANIM`, `CP_MP`) from `cp690.xml`.

## Other vehicles: `build_vehicle.py`

A generic version for the next mod (used for the 9RX): `python3 -I build_vehicle.py <mod dir> <file.i3d> <out.glb>
[show=node,node] [hide=node,node]`, then `pack.mjs`. Textures the mod ships are used; base-game ones fall back to flat
colours by material type; alpha decals with a missing sheet are dropped. `show=`/`hide=` pick a configuration. The
9RX was built with the US design parts shown, the EU ones hidden, and the broad-track `Fenders` hidden.
