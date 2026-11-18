// offline renderer: Kokoro-82M (q8 ONNX) -> 24 kHz mono WAVs. Usage: node render.mjs mm|fr|dm [limit]
import ort from 'onnxruntime-node'; import fs from 'fs'; import { phonemize } from './phonemize.js'; import { phonemize as espeak } from 'phonemizer';
const FRPH = fs.existsSync('fr_ph.json') ? JSON.parse(fs.readFileSync('fr_ph.json')) : {};
const which = process.argv[2], limit = +process.argv[3] || 1e9;
const vocab = JSON.parse(fs.readFileSync('kokoro-config.json')).vocab;
const voice = (n) => new Float32Array(fs.readFileSync(n + '.bin').buffer.slice(0));
const mix = (a, b, k) => a.map((x, i) => x * k + b[i] * (1 - k));
const VOX = { mm: mix(voice('bm_lewis'), voice('bm_george'), 0.6), fr: voice('ff_siwis'), dm: mix(voice('am_onyx'), voice('am_fenrir'), 0.7) };
const SPEED = { mm: 0.86, fr: 1.0, dm: 0.9 };
const sess = await ort.InferenceSession.create('model_q8.onnx', { intraOpNumThreads: 4 });
// broad Australian on top of British English (the vowels that give it away, a raised TRAP, flapped t, open final schwa)
const VW = 'aeiouyæɐɑɒɔəɛɜɪʊʌøœ';
const ocker = (p) => p
  .replace(/eɪ/g, 'aɪ@').replace(/aɪ(?!@)/g, 'ɔɪ').replace(/aɪ@/g, 'aɪ')          // FACE -> "mite", PRICE -> "roit"
  .replace(/əʊ/g, 'æʊ').replace(/aʊ/g, 'ɛʊ')                                     // GOAT -> "naow", MOUTH -> "neow"
  .replace(/iː/g, 'əɪ').replace(/uː/g, 'ɪu')                                     // FLEECE -> "sə-ee", GOOSE fronted
  .replace(/ɑː/g, 'aː').replace(/ɜː/g, 'øː')                                     // START "caah", NURSE rounded
  .replace(/a(?![ɪʊː])/g, 'ɛ')                                                   // TRAP raised: "ket"
  .replace(new RegExp(`([${VW}]ː?)t(?=[${VW}])`, 'g'), '$1ɾ')                    // flapped t between vowels: "budder"
  .replace(/ə(?=[ ,.!?;:]|$)/g, 'ɐ');                                            // final schwa opens: "mate-ah"
// Dima: a heavy Russian accent on top of American English: "ees" for is, rolled r, v for w, z for th, kh for h,
// "liftink", no flaps, and the voiced consonants at the ends of words devoiced ("gut day")
const RU_WORD = { 'do svidaniya': 'dəsvʲidˈanʲijə', 'da': 'dˈa', 'dima': 'dʲˈima', 'vodka': 'vˈotkə', 'pfft': 'pfː', 'leilx': 'lˈɛil' };
const russki = (p) => p
  .replace(/ɚ/g, 'ɛr').replace(/ɜː?ɹ?/g, 'ɛr').replace(/ɹ/g, 'r').replace(/ɾ/g, 't')
  .replace(/w/g, 'v').replace(/θ/g, 's').replace(/ð/g, 'z').replace(/h/g, 'x')
  .replace(/ɪ/g, 'i').replace(/ᵻ/g, 'i').replace(/æ/g, 'ɛ').replace(/ʌ/g, 'a').replace(/oʊ/g, 'o').replace(/ɑː/g, 'a')
  .replace(/ŋ(?=[ ,.!?;:]|$)/g, 'ŋk')
  .replace(/([dzvɡb])(?=[ ,.!?;:]|$)/g, (m, c) => ({ d: 't', z: 's', v: 'f', ɡ: 'k', b: 'p' })[c]);
const dmPhon = async (text) => { let t = text.replace(/[’‘]/g, "'").replace(/\.\.\./g, ', ').replace(/push-ups/gi, 'push ups');
  t = t.replace(/\bleil\b/gi, 'LEILX');                                                  // (the Estonian for sauna steam, said properly)
  const parts = []; for (const seg of t.split(/(\bDo svidaniya\b|\bDima\b|\bvodka\b|\bPfft\b|\bda\b|\bLEILX\b)/i)) { if (!seg) continue; const w = RU_WORD[seg.toLowerCase()];
    parts.push(w || russki(await phonemize(seg, 'a'))); }
  return parts.join(' ').replace(/ +/g, ' ').replace(/ ([,.!?])/g, '$1').trim(); };
const prep = (t) => t.replace(/[’‘]/g, "'").replace(/\bG'day\b/gi, 'Gidday').replace(/XXXX/g, 'four ex').replace(/'(em|ere)\b/g, '$1').replace(/\.\.\./g, ', ').replace(/(\w)in'(?=\W|$)/g, '$1ing');
async function phon(text, lang) {
  if (lang === 'fr') return FRPH[text];          // French phonemes come from espeak-ng's own French (fr_ph.py)
  if (lang === 'dm') return dmPhon(text);
  return ocker(await phonemize(prep(text), 'b')).replace(/ɪŋ(?=[ ,.!?;:]|$)/g, 'ɪn');      // the dropped g: "takin'"
}
function wav(f32, sr) { const n = f32.length, b = Buffer.alloc(44 + n * 2); b.write('RIFF', 0); b.writeUInt32LE(36 + n * 2, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(sr, 24); b.writeUInt32LE(sr * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) b.writeInt16LE(Math.max(-32767, Math.min(32767, Math.round(f32[i] * 32767))), 44 + i * 2); return b; }
const clips = JSON.parse(fs.readFileSync(process.env.CLIPS || 'clips.json'))[which], keys = Object.keys(clips).slice(0, limit), dir = process.env.OUT || ('out_' + which); fs.mkdirSync(dir, { recursive: true });
const idx = {}; let i = 0, skipped = [];
for (const k of keys) { const text = clips[k], ph = await phon(text, which === 'mm' ? 'en' : which);
  const ids = [...ph].map(c => vocab[c]).filter(x => x !== undefined); if (!ids.length) { skipped.push(k); continue; }
  const tok = [0, ...ids.slice(0, 500), 0], V = VOX[which], row = Math.min(ids.length, 509), style = V.slice(row * 256, row * 256 + 256);
  const out = await sess.run({ input_ids: new ort.Tensor('int64', BigInt64Array.from(tok.map(BigInt)), [1, tok.length]), style: new ort.Tensor('float32', style, [1, 256]), speed: new ort.Tensor('float32', new Float32Array([SPEED[which]]), [1]) });
  const f = 'c' + (i++) + '.wav'; fs.writeFileSync(dir + '/' + f, wav(out.waveform.data, 24000)); idx[k] = { f, text, ph };
  if (i % 40 === 0) console.log(i, '/', keys.length, text, '=>', ph); }
fs.writeFileSync(dir + '/index.json', JSON.stringify(idx, null, 0)); console.log('done', i, 'skipped', skipped);
