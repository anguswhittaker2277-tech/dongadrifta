# post-process the rendered clips with ffmpeg and pack them into one file: [u32 header length][JSON header][mp3 bytes...]
import json, subprocess, os, struct, sys, csv, glob, concurrent.futures as cf
from fx import TRIM, FX
def enc(src, fx, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', fx + ',loudnorm=I=-17:TP=-1.5:LRA=11', '-ar', '24000', '-ac', '1', '-c:a', 'libmp3lame', '-b:a', '32k', dst], check=True)
    d = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst]).decode().strip())
    return d
os.makedirs('mp3', exist_ok=True); jobs = []
# only the lines the game still says (out_* can hold clips for lines since dropped)
want = json.load(open('clips.json'))
mm, fr, dm = ({k: v for k, v in json.load(open('out_%s/index.json' % w)).items() if k in want[w]} for w in ('mm', 'fr', 'dm'))
for k, v in mm.items(): jobs.append(('mm', k, 'out_mm/' + v['f'], FX['mm'], 'mp3/mm_' + v['f'][:-4] + '.mp3', v['text']))
for k, v in fr.items():
    for who in 'MAC': jobs.append((who, k, 'out_fr/' + v['f'], FX[who], 'mp3/fr' + who + '_' + v['f'][:-4] + '.mp3', v['text']))
for k, v in dm.items(): jobs.append(('dm', k, 'out_dm/' + v['f'], FX['dm'], 'mp3/dm_' + v['f'][:-4] + '.mp3', v['text']))
# Matt: one file per row of matt-lines.csv (mt_001.wav or .mp3 ...) in rec_mt/, any he's missing just stay as bubbles
if os.path.isdir('rec_mt'):
    for row in csv.DictReader(open('matt-lines.csv', encoding='utf-8')):
        src = next(iter(sorted(glob.glob('rec_mt/' + row['file'] + '.*'))), None)
        if src: jobs.append(('mt', row['game_key'], src, FX['mt'], 'mp3/mt_' + row['file'] + '.mp3', row['line']))
with cf.ThreadPoolExecutor(8) as ex: durs = list(ex.map(lambda j: enc(j[2], j[3], j[4]), jobs))
head = {'mm': {}, 'fr': {'M': {}, 'A': {}, 'C': {}}, 'dm': {}, 'mt': {}}; blob = bytearray()
for j, d in zip(jobs, durs):
    b = open(j[4], 'rb').read(); ent = [len(blob), len(b), round(d, 3)]; blob += b
    if j[0] in ('mm', 'dm', 'mt'): head[j[0]][j[1]] = ent + [j[5][-1:] in ',.!?']
    else: head['fr'][j[0]][j[1]] = ent
h = json.dumps(head, ensure_ascii=False, separators=(',', ':')).encode()
open(sys.argv[1], 'wb').write(struct.pack('<I', len(h)) + h + bytes(blob))
print('clips', len(jobs), 'audio s', round(sum(durs)), 'MB', round((len(h) + len(blob)) / 1e6, 2))
