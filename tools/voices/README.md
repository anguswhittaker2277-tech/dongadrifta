# Voice pack (`voices-v1.bin`)

Madman's and the backpackers' voices are recorded offline with [Kokoro-82M](https://github.com/hexgrad/kokoro)
(Apache-2.0) and packed into `voices-v1.bin` in the repo root. The game loads that file the first time
someone speaks.

Rebuild it after changing any of their lines (`MM_L`, `MH_L`, `NPC_L` in `index.html`):

1. Dump the lines from the running game to `lines.json` (`JSON.stringify({ MM_L, MH_L, NPC_L })` from `window.__game`).
2. `python3 clips.py` lists every clip to record (`clips.json`).
3. `python3 fr_ph.py <espeakng_loader dir> fr_ph.json` gets the French phonemes from espeak-ng
   (the `espeakng-loader` wheel on PyPI).
4. Put the Kokoro model and voices next to the scripts: `model_q8.onnx` (the six parts of the
   `kokoro-q8-shards` npm package joined in order) and `bm_lewis.bin`, `bm_george.bin`, `ff_siwis.bin`
   (from the `kokoro-js` npm package). `npm install --ignore-scripts onnxruntime-node phonemizer`.
5. `node render.mjs mm` and `node render.mjs fr` render the WAVs.
6. `python3 pack.py voices-v1.bin` adds the effects with ffmpeg and packs the MP3s.

Madman is `bm_lewis` and `bm_george` blended 60/40 at 0.86 speed, with the vowels pushed toward broad Australian
(FACE "mite", PRICE "roit", GOAT "naow", MOUTH "neow", raised TRAP, flapped t, open final schwa), then pitched down
about 2.6 semitones (formants too), with a heavy chest, the nasal band cut, a fast flutter and hard soft clipping for growl.
The backpackers are `ff_siwis`; Mathieu and Alexandre are pitched down.

`phonemize.js` is adapted from kokoro-js (Apache-2.0); `kokoro-config.json` is from kokoro-onnx (MIT).
