import json, re
d = json.load(open('lines.json'))
MG, MM_L, MH_L, NPC_L = d['MG'], d['MM_L'], d['MH_L'], d['NPC_L']
def norm(t): t = t.replace('’', "'").replace('‘', "'").lower(); t = re.sub(r"[^a-z0-9' ]+", ' ', t); return re.sub(r'\s+', ' ', t).strip().replace("'", '')
mm = {}
def add(text, say=None):
    k = norm(text)
    if k and k not in mm: mm[k] = say or text
cap = lambda s: s[:1].upper() + s[1:]
for L in MM_L.values():
    for t in L: add(t)
for L in MH_L.values():
    for t in L:
        if '{n}' in t:
            for n in range(0, 7): add(t.replace('{n}', str(n)))
        else: add(t)
for t in MG['openF'] + MG['openA'] + MG['closeF'] + MG['closeA']: add(t)
for t in MG['termF']: add(t, t + '.')
for t in MG['insult']: add(t, t + '!')
for L in MG['topic'].values():
    for t in L: add(t, cap(t) + '.')
for L in MG['angry'].values():
    for t in L: add(t, cap(t) + '!')
for L in MG['hunt'].values():
    for t in L:
        for dog in ['Tank', 'Dusty']: add(t.replace('{dog}', dog), cap(t.replace('{dog}', dog)) + '!')
for t in ['G’day', 'How ya goin’', 'Oi oi', 'Here he is', 'Ow ya goin’', 'Catch ya', 'Hooroo', 'See ya', 'Righto, see ya', 'Go hard',
          'Don’t touch the ute.', 'Mind the pigs.', 'Don’t do anything I wouldn’t.', 'Dogs say hooroo.', 'Righto,', 'Strewth,', 'Fuck me dead,', 'Go on,', 'Yeah!', 'Oi,', 'Fair dinkum,']: add(t)
fr = {}
for L in NPC_L.values():
    for pair in L: fr[pair[0]] = pair[0]
fr['À plus !'] = 'À plus !'
json.dump({'mm': mm, 'fr': fr}, open('clips.json', 'w'), ensure_ascii=False, indent=0)
print('madman clips', len(mm), 'french clips', len(fr), 'madman chars', sum(len(v) for v in mm.values()))
print(list(mm.items())[:5]); print(list(fr)[:6])
