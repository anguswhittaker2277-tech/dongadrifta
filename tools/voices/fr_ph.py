import ctypes, json, sys, re
lib_dir, out = sys.argv[1], sys.argv[2]
L = ctypes.cdll.LoadLibrary(lib_dir + '/libespeak-ng.so')
assert L.espeak_Initialize(0x02, 0, (lib_dir + '/espeak-ng-data').encode(), 0) > 0
L.espeak_SetVoiceByName(ctypes.c_char_p(b'fr'))
L.espeak_TextToPhonemes.restype = ctypes.c_char_p
def ph(text):
    # phonemise each clause, keeping its punctuation (espeak drops it)
    res = []
    for part in re.split(r'([!?.,…]+)', text.replace('’', "'")):
        if not part.strip(): continue
        if re.fullmatch(r'[!?.,…]+', part.strip()): res.append(part.strip()); continue
        p = ctypes.c_char_p(part.strip().encode('utf-8')); acc = []
        while p.value:
            r = L.espeak_TextToPhonemes(ctypes.pointer(p), 1, 0x02)
            if r: acc.append(r.decode('utf-8'))
        res.append(' ' + ' '.join(acc))
    return ''.join(res).strip()
clips = json.load(open('clips.json'))['fr']
json.dump({k: ph(k) for k in clips}, open(out, 'w'), ensure_ascii=False, indent=0)
for k in list(clips)[:6]: print(k, '=>', ph(k))
