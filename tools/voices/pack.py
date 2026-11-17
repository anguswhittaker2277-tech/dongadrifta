# post-process the rendered clips with ffmpeg and pack them into one file: [u32 header length][JSON header][mp3 bytes...]
import json, subprocess, os, struct, sys, concurrent.futures as cf
TRIM = "silenceremove=start_periods=1:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_threshold=-48dB,areverse"
FX = {
  # Madman: a big rough bloke: pitched down (formants too, so he sounds bigger), chest and low-mid weight, the nasal band
  # cut, some bite up top, driven hard into soft clipping with a fast flutter for gravel
  'mm': TRIM + ",asetrate=24000*0.86,aresample=24000,atempo=1.12,equalizer=f=140:t=q:w=0.9:g=5,equalizer=f=420:t=q:w=1:g=2,equalizer=f=1500:t=q:w=1.2:g=-4,equalizer=f=3200:t=q:w=1.4:g=2,tremolo=f=28:d=0.18,volume=4.5,asoftclip=type=tanh,lowpass=f=6200",
  # the backpackers off one French voice: Chloe as recorded, the two blokes pitched down (formants and all, so they sound bigger)
  # Dima: a huge Russian: pitched down a little, a big chest and a slow, heavy delivery, clean (no gravel; he's healthy)
  'dm': TRIM + ",asetrate=24000*0.9,aresample=24000,atempo=1.04,equalizer=f=110:t=q:w=0.9:g=6,equalizer=f=300:t=q:w=1:g=2,equalizer=f=2600:t=q:w=1.2:g=1.5,acompressor=threshold=0.12:ratio=3:attack=5:release=80,volume=2",
  'C': TRIM, 'M': TRIM + ",asetrate=24000*0.82,aresample=24000,atempo=1.2195", 'A': TRIM + ",asetrate=24000*0.77,aresample=24000,atempo=1.2987",
}
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
with cf.ThreadPoolExecutor(8) as ex: durs = list(ex.map(lambda j: enc(j[2], j[3], j[4]), jobs))
head = {'mm': {}, 'fr': {'M': {}, 'A': {}, 'C': {}}, 'dm': {}}; blob = bytearray()
for j, d in zip(jobs, durs):
    b = open(j[4], 'rb').read(); ent = [len(blob), len(b), round(d, 3)]; blob += b
    if j[0] in ('mm', 'dm'): head[j[0]][j[1]] = ent + [j[5][-1:] in ',.!?']
    else: head['fr'][j[0]][j[1]] = ent
h = json.dumps(head, ensure_ascii=False, separators=(',', ':')).encode()
open(sys.argv[1], 'wb').write(struct.pack('<I', len(h)) + h + bytes(blob))
print('clips', len(jobs), 'audio s', round(sum(durs)), 'MB', round((len(h) + len(blob)) / 1e6, 2))
