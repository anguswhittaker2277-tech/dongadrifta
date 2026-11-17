# every line Madman and the backpackers can say, one clip each
import json, re
d = json.load(open('lines.json'))
MM_L, MH_L, NPC_L = d['MM_L'], d['MH_L'], d['NPC_L']
def norm(t): t = t.replace('’', "'").replace('‘', "'").lower(); t = re.sub(r"[^a-z0-9' ]+", ' ', t); return re.sub(r'\s+', ' ', t).strip().replace("'", '')
mm = {}
for L in list(MM_L.values()) + list(MH_L.values()):
    for t in L:
        for v in ([t.replace('{n}', str(n)) for n in range(1, 7)] if '{n}' in t else [t]): mm.setdefault(norm(v), v)
fr = {pair[0]: pair[0] for L in NPC_L.values() for pair in L}; fr['À plus !'] = 'À plus !'
json.dump({'mm': mm, 'fr': fr}, open('clips.json', 'w'), ensure_ascii=False, indent=0)
print('madman clips', len(mm), 'french clips', len(fr))
