// offline renderer: Kokoro-82M (q8 ONNX) -> 24 kHz mono WAVs. Usage: node render.mjs mm|fr [limit]
import ort from 'onnxruntime-node'; import fs from 'fs'; import { phonemize } from './phonemize.js'; import { phonemize as espeak } from 'phonemizer';
const FRPH = fs.existsSync('fr_ph.json') ? JSON.parse(fs.readFileSync('fr_ph.json')) : {};
const which = process.argv[2], limit = +process.argv[3] || 1e9;
const vocab = JSON.parse(fs.readFileSync('kokoro-config.json')).vocab;
const voice = (n) => new Float32Array(fs.readFileSync(n + '.bin').buffer.slice(0));
const mix = (a, b, k) => a.map((x, i) => x * k + b[i] * (1 - k));
const VOX = { mm: mix(voice('bm_lewis'), voice('bm_george'), 0.6), fr: voice('ff_siwis') };
const sess = await ort.InferenceSession.create('model_q8.onnx', { intraOpNumThreads: 4 });
// broad Australian on top of British English: FACE, PRICE, GOAT and MOUTH vowels shifted, FLEECE slightly diphthonged
const ocker = (p) => p.replace(/eɪ/g, 'æɪ').replace(/aɪ/g, 'ɒɪ').replace(/əʊ/g, 'ɐʊ').replace(/aʊ/g, 'æʊ').replace(/iː/g, 'ɪi');
const prep = (t) => t.replace(/[’‘]/g, "'").replace(/\bG'day\b/gi, 'Gidday').replace(/XXXX/g, 'four ex').replace(/'(em|ere)\b/g, '$1').replace(/\.\.\./g, ', ').replace(/(\w)in'(?=\W|$)/g, '$1ing');
async function phon(text, lang) {
  if (lang === 'fr') return FRPH[text];          // French phonemes come from espeak-ng's own French (fr_ph.py)
  return ocker(await phonemize(prep(text), 'b')).replace(/ɪŋ(?=[ ,.!?;:]|$)/g, 'ɪn');      // the dropped g: "takin'"
}
function wav(f32, sr) { const n = f32.length, b = Buffer.alloc(44 + n * 2); b.write('RIFF', 0); b.writeUInt32LE(36 + n * 2, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(sr, 24); b.writeUInt32LE(sr * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) b.writeInt16LE(Math.max(-32767, Math.min(32767, Math.round(f32[i] * 32767))), 44 + i * 2); return b; }
const clips = JSON.parse(fs.readFileSync('clips.json'))[which], keys = Object.keys(clips).slice(0, limit), dir = 'out_' + which; fs.mkdirSync(dir, { recursive: true });
const idx = {}; let i = 0, skipped = [];
for (const k of keys) { const text = clips[k], ph = await phon(text, which === 'fr' ? 'fr' : 'en');
  const ids = [...ph].map(c => vocab[c]).filter(x => x !== undefined); if (!ids.length) { skipped.push(k); continue; }
  const tok = [0, ...ids.slice(0, 500), 0], V = VOX[which], row = Math.min(ids.length, 509), style = V.slice(row * 256, row * 256 + 256);
  const out = await sess.run({ input_ids: new ort.Tensor('int64', BigInt64Array.from(tok.map(BigInt)), [1, tok.length]), style: new ort.Tensor('float32', style, [1, 256]), speed: new ort.Tensor('float32', new Float32Array([which === 'mm' ? 0.9 : 1.0]), [1]) });
  const f = 'c' + (i++) + '.wav'; fs.writeFileSync(dir + '/' + f, wav(out.waveform.data, 24000)); idx[k] = { f, text, ph };
  if (i % 40 === 0) console.log(i, '/', keys.length, text, '=>', ph); }
fs.writeFileSync(dir + '/index.json', JSON.stringify(idx, null, 0)); console.log('done', i, 'skipped', skipped);
