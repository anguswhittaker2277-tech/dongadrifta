# Put recorded voices (Matt's, from rec_mt/) into an existing voice pack without touching the other voices' clips.
# Usage: python3 add_rec.py ../../voices-v1.bin   (run from tools/voices). Same encoding as pack.py: trimmed, levelled, 32 kbps MP3.
import json, struct, sys, csv, glob, os, subprocess, tempfile
TRIM = "silenceremove=start_periods=1:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_threshold=-48dB,areverse"
def enc(src, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', TRIM + ',loudnorm=I=-17:TP=-1.5:LRA=11', '-ar', '24000', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '32k', dst], check=True)
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst]).decode().strip())
path = sys.argv[1]; raw = open(path, 'rb').read(); n = struct.unpack('<I', raw[:4])[0]; head = json.loads(raw[4:4 + n]); base = 4 + n
blob = bytearray()
def keep(ent):           # copy one existing clip into the new blob
    b = raw[base + ent[0]: base + ent[0] + ent[1]]; ent[0] = len(blob); blob.extend(b)
for who in ('mm', 'dm'):
    for e in head.get(who, {}).values(): keep(e)
for v in head.get('fr', {}).values():
    for e in v.values(): keep(e)
head['mt'] = {}; tmp = tempfile.mkdtemp(); got = 0
for row in csv.DictReader(open('matt-lines.csv', encoding='utf-8')):
    src = next(iter(sorted(glob.glob('rec_mt/' + row['file'] + '.*'))), None)
    if not src: continue
    dst = os.path.join(tmp, row['file'] + '.mp3'); d = enc(src, dst); b = open(dst, 'rb').read()
    head['mt'][row['game_key']] = [len(blob), len(b), round(d, 3), row['line'][-1:] in ',.!?']; blob.extend(b); got += 1
h = json.dumps(head, ensure_ascii=False, separators=(',', ':')).encode()
open(path, 'wb').write(struct.pack('<I', len(h)) + h + bytes(blob))
print('matt clips', got, '| pack MB', round((len(h) + len(blob)) / 1e6, 2))
