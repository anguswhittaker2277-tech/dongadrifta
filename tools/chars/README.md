# Character models (`assets/chars/`)

- `chars_m.glb`, `chars_w.glb`: Quaternius' **Ultimate Modular Men** and **Ultimate Modular Women** (CC0), every head, top,
  legs and feet on one skeleton, with 15 of their clips (Idle, Walk, Run, punches, kicks, hit reactions, Death, Wave ...).
- `hero.glb`: Dima, Quaternius' **Universal Base Characters** superhero male (CC0) with the buzzed hair, grey gym shorts
  painted over the briefs, light skin; textures cut to 1024 px (normal map 512).

How they were made (the scripts here run in the game page through Playwright, see the scratch harness they came from):

1. `build_packs.js` loads each pack's "All together" FBX, rebuilds one clean skeleton (the FBX importer nests a copy of the
   skeleton per part inside each other), bakes every face colour into vertex colours with three materials left per part
   (`Skin` and `Hair`, recoloured in game, and `Base`), keeps the useful clips and exports a GLB.
2. `build_hero.js` does the superhero body and hair from the Universal Base Characters glTF folder.
3. `npx @gltf-transform/cli optimize in.glb out.glb --compress meshopt --texture-compress false --simplify false --palette false`.

In game (`CH` in `index.html`) the old procedural rig still runs invisibly: its pivots' rotations are copied onto each
model's bones every frame, so every hand-made pose keeps working; plain walking, running, standing and NPC punches play the
pack's clips.
