"""Decrypt and parse GIANTS .i3d.shapes files (port of Donkie/I3DShapesTool, MIT).
Usage: python3 -I i3dshapes.py <file.i3d.shapes> <out.pkl>
"""
import sys, os, struct, pickle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KEYC = np.array([int(l, 16) for l in open(os.path.join(HERE, 'keyconst.txt'))], dtype=np.uint32)

def rol(v, b): return (v << np.uint32(b)) | (v >> np.uint32(32 - b))
def ror(v, b): return (v >> np.uint32(b)) | (v << np.uint32(32 - b))

def keystream(key, start_block, nblocks):
    """Return nblocks*16 uint32 keystream, vectorised over blocks."""
    K = np.tile(key.astype(np.uint32), (nblocks, 1))
    ctr = np.arange(start_block, start_block + nblocks, dtype=np.uint64)
    K[:, 8] = (ctr & np.uint64(0xFFFFFFFF)).astype(np.uint32)
    K[:, 9] = (ctr >> np.uint64(32)).astype(np.uint32)
    T = K.copy()
    t = [T[:, i].copy() for i in range(16)]
    def s1(a, b, c, d):
        t[c] ^= rol(t[b] + t[a], 7); t[d] ^= rol(t[c] + t[a], 9)
        t[b] ^= rol(t[c] + t[d], 13); t[a] ^= ror(t[b] + t[d], 14)
    def s2(a, b, c, d):
        t[c] ^= rol(t[b] + t[a], 7); t[d] ^= rol(t[b] + t[c], 9)
        t[a] ^= rol(t[c] + t[d], 13); t[b] ^= ror(t[d] + t[a], 14)
    with np.errstate(over='ignore'):
        for _ in range(10):
            s1(0x0, 0xC, 0x4, 0x8); s1(0x5, 0x1, 0x9, 0xD); s1(0xA, 0x6, 0xE, 0x2); s1(0xF, 0xB, 0x3, 0x7)
            s2(0x3, 0x0, 0x1, 0x2); s2(0x4, 0x5, 0x6, 0x7); s1(0xA, 0x9, 0xB, 0x8); s2(0xE, 0xF, 0xC, 0xD)
        out = np.stack(t, axis=1) + K
    return out.reshape(-1)

class Reader:
    def __init__(self, data):
        b1, b2, b3, b4 = data[:4]
        if b1 >= 4: self.version, seed = b1, b3
        else: self.version, seed = b4, b2
        self.key = KEYC[seed * 16: seed * 16 + 16].copy(); self.key[8] = 0; self.key[9] = 0
        self.data = data; self.pos = 4; self.block = 0
    def read(self, n):
        raw = self.data[self.pos:self.pos + n]; self.pos += n
        nb = (n + 63) // 64
        ks = keystream(self.key, self.block, nb).view(np.uint8)[:n]
        self.block += nb
        return (np.frombuffer(raw, dtype=np.uint8) ^ ks[:len(raw)]).tobytes()
    def i32(self): return struct.unpack('<i', self.read(4))[0]

class Buf:
    def __init__(self, b): self.b = b; self.p = 0
    def u32(self): v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v
    def i32(self): v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v
    def f32(self): v = struct.unpack_from('<f', self.b, self.p)[0]; self.p += 4; return v
    def bytes(self, n): v = self.b[self.p:self.p + n]; self.p += n; return v
    def align(self, n=4):
        if self.p % n: self.p += n - self.p % n
    def arr(self, dtype, count):
        a = np.frombuffer(self.b, dtype=dtype, count=count, offset=self.p).copy()
        self.p += a.nbytes; return a

def parse_shape(b, version):
    r = Buf(b)
    nl = r.i32(); name = r.bytes(nl).decode('latin1'); r.align(4); sid = r.u32()
    bv = [r.f32() for _ in range(4)]
    corners = r.u32(); nsub = r.u32(); nverts = r.u32(); opts = r.u32()
    subs = []
    extra = r.u32() if version >= 10 else None
    for _ in range(nsub):
        s = [r.u32() for _ in range(4)]
        if version >= 6:
            for k in range(4):
                if opts & (2 << k): r.f32()
        subs.append(s)
    mats = []
    if version >= 10:
        for _ in range(nsub):
            n = struct.unpack_from('<H', r.b, r.p)[0]; r.p += 2
            mats.append(r.bytes(n).decode('latin1')); r.align(2)      # (names are padded to an even length)
        r.align(4)
    big = nverts > 65536
    idx = r.arr('<u4' if big else '<u2', corners).astype(np.uint32)
    r.align(4)
    pos = r.arr('<f4', nverts * 3).reshape(-1, 3)
    nrm = r.arr('<f4', nverts * 3).reshape(-1, 3) if opts & 1 else None
    tan = None
    if opts & 0x80 and version >= 5: tan = r.arr('<f4', nverts * 4).reshape(-1, 4)
    uvs = []
    for k in range(4):
        if opts & (2 << k): uvs.append(r.arr('<f4', nverts * 2).reshape(-1, 2))
        else: uvs.append(None)
    col = r.arr('<f4', nverts * 4).reshape(-1, 4) if opts & 0x20 else None
    skin = None
    if opts & 0x40:
        single = bool(opts & 0x100)
        w = None if single else r.arr('<f4', nverts * 4).reshape(-1, 4)
        ix = r.arr('u1', nverts * (1 if single else 4)).reshape(nverts, -1)
        skin = (w, ix)
    gen = r.arr('<f4', nverts) if opts & 0x200 else None
    natt = r.u32() if r.p < len(b) else 0
    for _ in range(natt):
        fl = r.u32()
        if fl & 4: r.p += 12
        n = r.i32(); r.p += n
    return dict(name=name, id=sid, bv=bv, subsets=subs, mats=mats, extra=extra, idx=idx, pos=pos, nrm=nrm, uv=uvs, col=col,
                skin=skin, gen=gen, opts=opts, leftover=len(b) - r.p)

def load(path):
    rd = Reader(open(path, 'rb').read())
    n = rd.i32()
    if not (0 <= n < 1e6): raise RuntimeError('bad count %d (version %d)' % (n, rd.version))
    out = []
    for _ in range(n):
        t = rd.i32(); sz = rd.i32(); d = rd.read(sz)
        out.append((t, d))
    return rd.version, out

if __name__ == '__main__':
    ver, ents = load(sys.argv[1])
    print('version', ver, 'entities', len(ents))
    shapes = {}
    for t, d in ents:
        if t != 1:
            print(' non-shape entity type', t, len(d)); continue
        try:
            s = parse_shape(d, ver)
            shapes[s['id']] = s
        except Exception as e:
            nl = struct.unpack_from('<i', d)[0]
            print(' FAIL', d[4:4 + nl], e)
    bad = [s for s in shapes.values() if s['leftover']]
    print('parsed', len(shapes), 'leftover-mismatch', len(bad))
    for s in list(shapes.values())[:8]:
        print('  ', s['id'], s['name'], len(s['pos']), len(s['idx']) // 3, hex(s['opts']), s['leftover'])
    if len(sys.argv) > 2:
        pickle.dump(shapes, open(sys.argv[2], 'wb'))
