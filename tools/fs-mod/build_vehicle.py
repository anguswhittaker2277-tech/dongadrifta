"""Generic FS25 vehicle -> GLB for the game (used for the John Deere 9RX).
Usage:  python3 -I build_vehicle.py <mod dir> <file.i3d> <out.glb> [show=a,b] [hide=c,d]
Same pipeline as build_cp690.py (names kept, hidden variants flagged, skins, quantised meshes), but materials are
classified generically: a texture the mod ships is used; a base-game texture that isn't in the zip falls back to a
flat colour by material type, and alpha decals whose sheet is missing are left out. show=/hide= override the i3d
visibility of named nodes (to pick a configuration).
"""
import sys, os, io, json, struct, math
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i3dshapes

MOD = sys.argv[1]
I3D = sys.argv[2]
OUT = sys.argv[3]
OPT = dict(a.split('=', 1) for a in sys.argv[4:])
SHOW = set(filter(None, OPT.get('show', '').split(','))); HIDE = set(filter(None, OPT.get('hide', '').split(',')))

# ---------------------------------------------------------------- shapes
def load_shapes(path):
    ver, ents = i3dshapes.load(path)
    out = {}
    for t, d in ents:
        if t == 1:
            s = i3dshapes.parse_shape(d, ver)
            assert s['leftover'] == 0, s['name']
            out[s['id']] = s
    return out

SH = load_shapes(os.path.join(MOD, I3D + '.shapes'))

# ---------------------------------------------------------------- i3d scene
root = ET.parse(os.path.join(MOD, I3D)).getroot()
FILES = {f.get('fileId'): f.get('filename') for f in root.find('Files')}
MATS = {}
for m in root.find('Materials'):
    d = dict(m.attrib)
    d['params'] = {c.get('name'): c.get('value') for c in m if c.tag == 'CustomParameter'}
    d['tex'] = {c.tag: FILES.get(c.get('fileId'), '') for c in m if c.tag in ('Texture', 'Normalmap', 'Glossmap')}
    d['custom'] = {c.get('name'): FILES.get(c.get('fileId'), '') for c in m if c.tag == 'Custommap'}
    MATS[int(d['materialId'])] = d

def fl(s, n=3, dflt=0.0):
    if s is None: return [dflt] * n
    v = [float(x) for x in s.split()]
    return v

def euler_zyx(rx, ry, rz):
    """i3d rotation (degrees): M = Rz * Ry * Rx"""
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2; w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    q = np.array([x, y, z, w]); return (q / np.linalg.norm(q)).tolist()

class Node:
    pass

NODES = []          # in glTF order
BY_ID = {}          # i3d nodeId -> Node
USED = {}

def uniq(name):
    name = (name or 'node').replace('.', '_').replace(' ', '_')
    if name not in USED:
        USED[name] = 1; return name
    USED[name] += 1
    return '%s~%d' % (name, USED[name])

def walk(el, parent, hidden):
    if el.tag not in ('Shape', 'TransformGroup', 'Light', 'Camera', 'ReferenceNode', 'Dynamic'):
        return
    n = Node(); n.el = el; n.tag = el.tag; n.parent = parent; n.children = []
    n.name = uniq(el.get('name'))
    t = fl(el.get('translation')); r = fl(el.get('rotation')); s = fl(el.get('scale'), dflt=1.0)
    if el.get('scale') is None: s = [1.0, 1.0, 1.0]
    n.t, n.r, n.s = t, r, s
    R = euler_zyx(*r)
    M = np.eye(4); M[:3, :3] = R @ np.diag(s); M[:3, 3] = t
    n.local = M
    n.world = (parent.world @ M) if parent else M
    n.hidden = el.get('visibility') == 'false'
    if el.get('name') in SHOW: n.hidden = False
    if el.get('name') in HIDE: n.hidden = True
    n.nonrender = el.get('nonRenderable') == 'true'
    n.shape = int(el.get('shapeId')) if el.tag == 'Shape' and el.get('shapeId') else None
    n.mats = [int(x) for x in el.get('materialIds', '').split(',') if x]
    n.skin = [int(x) for x in el.get('skinBindNodeIds', '').split()] if el.get('skinBindNodeIds') else None
    n.idx = len(NODES); NODES.append(n)
    if el.get('nodeId'): BY_ID[int(el.get('nodeId'))] = n
    if parent: parent.children.append(n)
    for c in el:
        walk(c, n, hidden or n.hidden)

scene = root.find('Scene')
ROOTS = []
for c in scene:
    before = len(NODES)
    walk(c, None, False)
    if len(NODES) > before: ROOTS.append(NODES[before])

def load_png(rel):
    im = Image.open(os.path.join(MOD, rel)); im.load(); return im.convert('RGBA')

def local(path):           # a texture the mod ships (not $data/...)
    return path and not path.startswith('$') and os.path.exists(os.path.join(MOD, path))

# ---------------------------------------------------------------- glTF writer
BIN = bytearray()
J = {'asset': {'version': '2.0', 'generator': 'dongadrifta tools/fs-mod/build_cp690.py'},
     'scene': 0, 'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [], 'materials': [], 'accessors': [],
     'bufferViews': [], 'buffers': [], 'textures': [], 'images': [], 'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
     'skins': []}

def add_view(data, target=None):
    while len(BIN) % 4: BIN.append(0)
    off = len(BIN); BIN.extend(data)
    v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
    if target: v['target'] = target
    J['bufferViews'].append(v); return len(J['bufferViews']) - 1

def add_acc(arr, ctype, typ, target=None, minmax=False, normalized=False, pad_to=None):
    arr = np.ascontiguousarray(arr)
    data = arr
    if pad_to:                       # vertex attributes must start on 4-byte boundaries: pad each element out
        data = np.zeros((arr.shape[0], pad_to), arr.dtype); data[:, :arr.shape[1]] = arr
    bv = add_view(np.ascontiguousarray(data).tobytes(), target)
    if pad_to: J['bufferViews'][bv]['byteStride'] = data.itemsize * pad_to
    a = {'bufferView': bv, 'componentType': ctype, 'count': int(arr.shape[0]), 'type': typ}
    if normalized: a['normalized'] = True
    if minmax:
        a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    J['accessors'].append(a); return len(J['accessors']) - 1

def add_image(im, name):
    buf = io.BytesIO(); im.save(buf, 'PNG')
    bv = add_view(buf.getvalue())
    J['images'].append({'bufferView': bv, 'mimeType': 'image/png', 'name': name})
    J['textures'].append({'source': len(J['images']) - 1, 'sampler': 0, 'name': name})
    return len(J['textures']) - 1

TEX = {}
def tex(name, im):
    if name not in TEX: TEX[name] = add_image(im, name)
    return TEX[name]

def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def material(mid):
    """-> gltf material index, or None to drop the primitive"""
    key = ('m', mid)
    if key in TEX: return TEX[key]
    m = MATS[mid]; name = m['name']; P = m['params']; nl = name.lower()
    cs = [float(x) for x in P.get('colorScale', '1 1 1').split()[:3]]
    diff = m['tex'].get('Texture', '') or ''; det = (m['custom'].get('detailDiffuse', '') or '').split('/')[-1]
    ab = m.get('alphaBlending') == 'true'
    white = diff.endswith('white_diffuse.png') or not diff
    tag = 'plastic'; col = cs[:]; metal = 0.0; rough = 0.5; alpha = None; texi = None; a = 1.0
    if local(diff):
        im = load_png(diff); has_a = im.getextrema()[3][0] < 250
        texi = tex(os.path.basename(diff), im); col = [1, 1, 1] if 'colorScale' not in P or not has_a else cs
        tag = 'decal' if has_a else 'textured'
        if has_a: alpha = 'MASK'
        if 'colorScale' in P and not has_a: col = cs
    elif not white and (ab or 'decal' in nl or 'raster' in nl or nl in ('static', 'material', 'default') or 'interiordecal' in nl or diff.endswith('series9RXDecals_diffuse.dds')):
        if not ('glass' in nl or 'window' in nl): TEX[key] = None; return None
    if texi is None:
        if 'glass' in nl or 'window' in nl:
            tag = 'glass'; rough = 0.05; alpha = 'BLEND'
            if 'headlight' in nl or 'lightsglass' in nl or 'glassclear' in nl: tag = 'lens'; col, a = [max(0.25, c) for c in cs], 0.35
            else: col, a = [0.12, 0.14, 0.15], 0.25
        elif 'mirror' in nl: tag = 'mirror'; metal = 1.0; rough = 0.04; col = [0.85] * 3
        elif ('chrome' in nl or det.startswith('clear')) and 'staticLight' in m.get('customShaderVariation', '') : tag = 'lamp'; metal = 1.0; rough = 0.15; col = [0.9 * c for c in cs]
        elif 'chrome' in nl: tag = 'chrome'; metal = 1.0; rough = 0.12; col = [0.9] * 3
        elif 'silver' in nl or det.startswith(('silverScratched', 'scratched')) and 'colorScale' not in P: tag = 'steel'; metal = 1.0; rough = 0.42; col = [0.62, 0.62, 0.6]
        elif 'brass' in nl: tag = 'steel'; metal = 1.0; rough = 0.4
        elif 'rubber' in nl or det.startswith('rubber'): tag = 'rubber'; rough = 0.85; col = [min(c, 0.035) for c in cs] if 'colorScale' in P else [0.03] * 3
        elif det.startswith(('fabric', 'leather', 'perforated')): tag = 'interior'; rough = 0.9
        elif 'calibratedPaint' in det or 'paint' in nl: tag = 'paint'; rough = 0.3
        elif 'reflector' in nl: tag = 'reflector'; rough = 0.2
        elif 'colorScale' not in P: col = [0.06, 0.06, 0.065]
        if 'diode' in nl or 'led' in nl: tag = 'lamp'
    mm = {'name': 'm%d_%s' % (mid, tag), 'pbrMetallicRoughness': {
        'baseColorFactor': [min(1.0, float(col[0])), min(1.0, float(col[1])), min(1.0, float(col[2])), a], 'metallicFactor': metal, 'roughnessFactor': rough}}
    if texi is not None: mm['pbrMetallicRoughness']['baseColorTexture'] = {'index': texi}
    if alpha: mm['alphaMode'] = alpha
    if alpha == 'MASK': mm['alphaCutoff'] = 0.4
    if tag in ('glass', 'lens'): mm['doubleSided'] = True
    J['materials'].append(mm); TEX[key] = len(J['materials']) - 1
    return TEX[key]

MESH_CACHE = {}
def vertex_attrs(pos, nrm, uvs, skin, qt):
    attrs = {}
    if qt is not None:
        c, h = qt
        q = np.round((pos - np.array(c)) / h * 32767).clip(-32767, 32767).astype(np.int16)
        attrs['POSITION'] = add_acc(q, 5122, 'VEC3', 34962, minmax=True, normalized=True, pad_to=4)
    else:
        attrs['POSITION'] = add_acc(pos, 5126, 'VEC3', 34962, minmax=True)
    if nrm is not None:
        nn = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
        n8 = np.round(nn * 127).clip(-127, 127).astype(np.int8)
        attrs['NORMAL'] = add_acc(n8, 5120, 'VEC3', 34962, normalized=True, pad_to=4)
    for k, uv in enumerate(uvs):
        if uv is None: continue
        u = uv.copy().astype(np.float32); u[:, 1] = 1.0 - u[:, 1]
        if u.min() >= 0 and u.max() <= 1:
            attrs['TEXCOORD_%d' % k] = add_acc(np.round(u * 65535).astype(np.uint16), 5123, 'VEC2', 34962, normalized=True)
        else:
            attrs['TEXCOORD_%d' % k] = add_acc(u, 5126, 'VEC2', 34962)
    if skin is not None:
        J4, W4 = skin
        attrs['JOINTS_0'] = add_acc(J4, 5121, 'VEC4', 34962)
        attrs['WEIGHTS_0'] = add_acc(W4, 5126, 'VEC4', 34962)
    return attrs

def mesh_for(shape, mats, skin_bones=None, bake=None):
    """one glTF primitive per i3d subset, each with only its own vertex range (subsets are contiguous)"""
    key = (shape['id'], tuple(mats), bool(skin_bones))
    if key in MESH_CACHE and bake is None: return MESH_CACHE[key]
    pos = shape['pos'].astype(np.float32); nrm = shape['nrm']
    if bake is not None:
        pos = (pos @ bake[:3, :3].T + bake[:3, 3]).astype(np.float32)
        if nrm is not None:
            N = np.linalg.inv(bake[:3, :3]).T; nrm = nrm @ N.T
    qt = None
    if skin_bones is None:      # KHR_mesh_quantization: int16 positions, dequantised by a holder node
        lo, hi = pos.min(0), pos.max(0); c = (lo + hi) / 2; h = float(max((hi - lo).max() / 2, 1e-6))
        qt = (c.tolist(), h)
    skin = None
    if skin_bones is not None and shape['skin'] is not None:
        w, ix = shape['skin']; nv = len(pos)
        J4 = np.zeros((nv, 4), np.uint8); W4 = np.zeros((nv, 4), np.float32)
        if w is None: J4[:, 0] = ix[:, 0]; W4[:, 0] = 1
        else:
            J4[:] = ix; W4[:] = np.maximum(w, 0)
            W4 /= np.maximum(W4.sum(1, keepdims=True), 1e-8)
            J4[W4 == 0] = 0
        skin = (J4, W4)
    prims = []
    for si, (fv, nv, fi, ni) in enumerate(shape['subsets']):
        mid = mats[si] if si < len(mats) else mats[-1]
        mi = material(mid)
        if mi is None or ni == 0: continue
        sl = slice(fv, fv + nv)
        attrs = vertex_attrs(pos[sl], None if nrm is None else nrm[sl], [None if u is None else u[sl] for u in shape['uv'][:2]],
                             None if skin is None else (skin[0][sl], skin[1][sl]), qt)
        idx = shape['idx'][fi:fi + ni].astype(np.int64) - fv
        assert idx.min() >= 0 and idx.max() < nv
        big = nv > 65535
        prims.append({'attributes': attrs, 'indices': add_acc(idx.astype(np.uint32 if big else np.uint16), 5125 if big else 5123, 'SCALAR', 34963), 'material': mi})
    if not prims: return None
    J['meshes'].append({'name': shape['name'].replace('.', '_'), 'primitives': prims})
    mi = (len(J['meshes']) - 1, qt)
    if bake is None: MESH_CACHE[key] = mi
    return mi

# Skinned shapes: vertices are in the shape's own space at the rest pose. They're baked to model space, the mesh
# node goes at the scene root (glTF ignores a skinned node's transform anyway) and each bone gets
# inverseBindMatrix = inverse(bone world at rest).
SKINNED = []
for n in NODES:
    n.gl = {'name': n.name}
    if n.parent is None or True:
        if n.parent is not None or True:
            q = mat_to_quat(euler_zyx(*n.r))
            if any(abs(x) > 1e-9 for x in n.t): n.gl['translation'] = [float(x) for x in n.t]
            if abs(q[3] - 1) > 1e-9: n.gl['rotation'] = q
            if any(abs(x - 1) > 1e-9 for x in n.s): n.gl['scale'] = [float(x) for x in n.s]
    ex = {}
    if n.hidden: ex['hidden'] = True
    if n.tag in ('Light', 'Camera', 'ReferenceNode'): ex['kind'] = n.tag
    if ex: n.gl['extras'] = ex
    if n.shape is not None and not n.nonrender and n.shape in SH:
        shp = SH[n.shape]
        if n.skin and len(n.skin) > 1 or (n.skin and BY_ID.get(n.skin[0]) is not n):
            SKINNED.append(n)
        else:
            mi = mesh_for(shp, n.mats)
            if mi is not None: n.qmesh = mi

for n in NODES: J['nodes'].append(n.gl)
HOLD = {}
for n in NODES:                       # the quantised mesh hangs off a holder child, so the i3d node keeps its own transform
    if getattr(n, 'qmesh', None):
        (mi, (c, h)) = n.qmesh
        J['nodes'].append({'name': n.name + '_q', 'mesh': mi, 'translation': c, 'scale': [h, h, h]})
        HOLD[n.idx] = len(J['nodes']) - 1
for c in n.children if False else []: pass
for n in NODES:
    ch = [c.idx for c in n.children] + ([HOLD[n.idx]] if n.idx in HOLD else [])
    if ch: n.gl['children'] = ch

for n in SKINNED:
    shp = SH[n.shape]
    bones = [BY_ID[b] for b in n.skin]
    ibm = np.stack([np.linalg.inv(b.world).T.astype(np.float32) for b in bones])   # column-major
    acc = add_acc(ibm.reshape(len(bones), 16), 5126, 'MAT4')
    J['skins'].append({'joints': [b.idx for b in bones], 'inverseBindMatrices': acc, 'name': n.name + '_skin'})
    mi = mesh_for(shp, n.mats, skin_bones=bones, bake=n.world)[0]
    sk = {'name': n.name + '_skinned', 'mesh': mi, 'skin': len(J['skins']) - 1}
    if n.hidden: sk['extras'] = {'hidden': True}
    J['nodes'].append(sk)
    J['scenes'][0]['nodes'].append(len(J['nodes']) - 1)

J['scenes'][0]['nodes'] = [r.idx for r in ROOTS] + J['scenes'][0]['nodes']
J['extensionsUsed'] = ['KHR_mesh_quantization']; J['extensionsRequired'] = ['KHR_mesh_quantization']

# rest-pose world positions of the nodes the game's moving-part solver needs (handy for checks)
if not J['skins']: del J['skins']
while len(BIN) % 4: BIN.append(0)
J['buffers'].append({'byteLength': len(BIN)})
js = json.dumps(J, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
with open(OUT, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(BIN)))
    f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
    f.write(struct.pack('<II', len(BIN), 0x004E4942)); f.write(BIN)
print('wrote', OUT, len(BIN) // 1024, 'KB bin;', len(J['nodes']), 'nodes', len(J['meshes']), 'meshes', len(J['materials']), 'materials', len(J.get('skins', [])), 'skins')
