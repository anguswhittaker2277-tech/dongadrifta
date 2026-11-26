# Put newly rendered Kokoro clips (render.mjs with CLIPS=<new clips json> OUT=<dir>) into an existing voice pack without
# touching any other clip. Usage, from tools/voices: python3 add_new.py ../../voices-v1.bin mm out_mm_new
# Same effects and encoding as pack.py; a line that already has a clip gets the new one.
import json, struct, sys, os, subprocess, tempfile
from fx import FX
def enc(src, fx, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', fx + ',loudnorm=I=-17:TP=-1.5:LRA=11', '-ar', '24000', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '32k', dst], check=True)
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst]).decode().strip())
path, who, src = sys.argv[1], sys.argv[2], sys.argv[3]
assert who in ('mm', 'dm', 'tk'), 'mm, dm or tk'
raw = open(path, 'rb').read(); n = struct.unpack('<I', raw[:4])[0]; head = json.loads(raw[4:4 + n]); base = 4 + n
idx = json.load(open(os.path.join(src, 'index.json'))); blob = bytearray()
def keep(ent): b = raw[base + ent[0]: base + ent[0] + ent[1]]; ent[0] = len(blob); blob.extend(b)
head.setdefault(who, {})
for w in ('mm', 'dm', 'mt', 'tk'):
    for k, e in list(head.get(w, {}).items()):
        if w == who and k in idx: del head[w][k]
        else: keep(e)
for v in head.get('fr', {}).values():
    for e in v.values(): keep(e)
tmp = tempfile.mkdtemp()
for k, v in idx.items():
    dst = os.path.join(tmp, v['f'][:-4] + '.mp3'); d = enc(os.path.join(src, v['f']), FX[who], dst); b = open(dst, 'rb').read()
    head[who][k] = [len(blob), len(b), round(d, 3), v['text'][-1:] in ',.!?']; blob.extend(b)
h = json.dumps(head, ensure_ascii=False, separators=(',', ':')).encode()
open(path, 'wb').write(struct.pack('<I', len(h)) + h + bytes(blob))
print(who, 'clips added', len(idx), '| total', len(head[who]), '| pack MB', round((len(h) + len(blob)) / 1e6, 2))
