# Voice pack (`voices-v1.bin`)

Madman's, the backpackers' and Dima's voices are recorded offline with [Kokoro-82M](https://github.com/hexgrad/kokoro)
(Apache-2.0) and packed into `voices-v1.bin` in the repo root. The game loads that file the first time
someone speaks.

Rebuild it after changing any of their lines (`MM_L`, `MH_L`, Madman's crude `MM_C` and `MH_C`, `NPC_L`, `DIMA_L` in `index.html`):

1. Dump the lines from the running game to `lines.json` (`JSON.stringify({ MM_L, MH_L, MM_C, MH_C, NPC_L, DIMA_L })` from `window.__game`).
2. `python3 clips.py` lists every clip to record (`clips.json`).
3. `python3 fr_ph.py <espeakng_loader dir> fr_ph.json` gets the French phonemes from espeak-ng
   (the `espeakng-loader` wheel on PyPI).
4. Put the Kokoro model and voices next to the scripts: `model_q8.onnx` (the six parts of the
   `kokoro-q8-shards` npm package joined in order) and `bm_lewis.bin`, `bm_george.bin`, `ff_siwis.bin`, `am_onyx.bin`, `am_fenrir.bin`
   (from the `kokoro-js` npm package). `npm install --ignore-scripts onnxruntime-node phonemizer`.
5. `node render.mjs mm`, `node render.mjs fr` and `node render.mjs dm` render the WAVs.
6. `python3 pack.py voices-v1.bin` adds the effects with ffmpeg and packs the MP3s.

To add only new lines without re-recording the rest: put just the new clips in a JSON shaped like `clips.json`, then
`CLIPS=new.json OUT=out_mm_new node render.mjs mm` and `python3 add_new.py ../../voices-v1.bin mm out_mm_new` (every other
clip in the pack is copied across untouched). Then change the `?v=` on `VOX.url` in `index.html` so browsers fetch the new pack.

Madman is `bm_lewis` and `bm_george` blended 60/40 at 0.86 speed, with the vowels pushed toward broad Australian
(FACE "mite", PRICE "roit", GOAT "naow", MOUTH "neow", raised TRAP, flapped t, open final schwa), then pitched down
about 2.6 semitones (formants too), with a heavy chest, the nasal band cut, a fast flutter and hard soft clipping for growl.
The backpackers are `ff_siwis`; Mathieu and Alexandre are pitched down.
Dima is `am_onyx` and `am_fenrir` blended 70/30 at 0.9 speed with a Russian accent put on the American phonemes
("ees", rolled r, v for w, z for th, kh for h, "liftink", word-final consonants devoiced), pitched down a little with a big chest.

`phonemize.js` is adapted from kokoro-js (Apache-2.0); `kokoro-config.json` is from kokoro-onnx (MIT).

## Recording Madman yourself

`madman-lines.csv` lists every Madman recording (`mm_001` ... `mm_213`) with the situation, the mood and the
line. Record each one to a file of that name (WAV or MP3) and they can replace the Kokoro clips: the
`game_key` column is the line exactly as the game looks it up.

## Matt

Matt's lines (`MATT_L` in `index.html`) are listed in `matt-lines.csv` (`mt_001` ... `mt_111`) with the situation, the mood
and the line. They're recorded in Voicebox off Matt's voice profile: save each as a file of that name (WAV or MP3) in
`rec_mt/`, then `python3 add_rec.py ../../voices-v1.bin` (from this folder) puts them in the pack without touching anyone
else's clips (a full `python3 pack.py voices-v1.bin` rebuild takes them too). The `game_key` column is the line exactly as the
game looks it up; until a line has a recording, Matt just says it in his speech bubble.
`matt-lines-to-record.csv` lists just the lines that don't have a recording yet (none right now), in the same columns.
