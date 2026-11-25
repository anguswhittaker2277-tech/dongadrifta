"""Turn the FS25 "John Deere Roller Pickers" mod (Jolly Farms Modding) into cp690.glb for the game.

Usage:  python3 -I build_cp690.py <extracted mod dir> <out.glb>
Then:   gltf-transform optimize <out.glb> cp690.glb --compress meshopt --texture-compress webp ... (see README.md)

What it does
- decrypts cp690.i3d.shapes / cottonBale238.i3d.shapes (i3dshapes.py, FS25 = shapes v10)
- walks the cp690.i3d scene and writes every node into glTF with its i3d name, so the game can find and
  animate the same nodes the mod's XML animates (pickerJoint, baleChamber, backDoorArm, baleDropper, ...)
- nodes hidden in the i3d (configuration variants) carry extras.hidden = true
- skinned meshes (hoses, chamber belt, chamber cover, seat) become glTF skins bound to their i3d bones
- materials: the mod mostly uses GIANTS' shared detail library (not in the zip), so each material becomes a
  plain PBR colour from its colorScale plus a tag in its name ("paint", "chrome", "glass", "decal", ...); the
  game builds the final materials from those tags. Meshes whose only texture is a missing alpha decal
  (screw heads, interior stickers, dashboard digits) are left out rather than drawn as solid quads.
- the decal atlas: the mod ships the 7760 sticker sheet, which is the CP690 sheet with "7760" painted in;
  a CP690 copy is made by painting "CP690" over it
- the round cotton module (cottonBale238) is written as its own root, "module"
"""
import sys, os, io, json, struct, math
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i3dshapes

MOD = sys.argv[1]
OUT = sys.argv[2]

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

SH = load_shapes(os.path.join(MOD, 'cp690.i3d.shapes'))
BSH = load_shapes(os.path.join(MOD, 'bales', 'cottonBale238.i3d.shapes'))

# ---------------------------------------------------------------- i3d scene
root = ET.parse(os.path.join(MOD, 'cp690.i3d')).getroot()
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

# ---------------------------------------------------------------- decal atlases
def load_png(rel):
    im = Image.open(os.path.join(MOD, rel)); im.load(); return im.convert('RGBA')

atlas7760 = load_png('textures/7760_decal.dds')
atlasCP = atlas7760.copy()
d = ImageDraw.Draw(atlasCP)
d.rectangle((278, 2, 632, 110), fill=(0, 0, 0, 0))
font = None
for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'):
    if os.path.exists(f): font = f; break
best = None
for size in range(140, 40, -2):
    F = ImageFont.truetype(font, size)
    bb = d.textbbox((0, 0), 'CP690', font=F, stroke_width=7)
    if bb[2] - bb[0] <= 340 and bb[3] - bb[1] <= 100: best = (F, bb); break
F, bb = best
w, h = bb[2] - bb[0], bb[3] - bb[1]
ox, oy = 284 + (340 - w) // 2 - bb[0], 6 + (100 - h) // 2 - bb[1]
d.text((ox, oy), 'CP690', font=F, fill=(255, 243, 0, 255), stroke_width=7, stroke_fill=(0, 0, 0, 255))

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

MISSING_ALPHA = {22, 23, 29, 31, 41, 57, 58, 66}   # alpha decals whose texture lives in the base game

def material(mid):
    """-> (gltf material index | None to drop the primitive)"""
    if mid in MISSING_ALPHA: return None
    key = ('m', mid)
    if key in TEX: return TEX[key]
    m = MATS[mid]; name = m['name']; P = m['params']
    cs = [float(x) for x in P.get('colorScale', '1 1 1').split()[:3]]
    diff = m['tex'].get('Texture', '')
    det = (m['custom'].get('detailDiffuse', '') or '').split('/')[-1]
    tag = 'plastic'; col = cs[:]; metal = 0.0; rough = 0.5; alpha = None; texi = None; a = 1.0
    if 'glass' in name or 'window' in name or mid == 5:
        tag = 'glass'; rough = 0.05
        if mid == 79: col, a = [0.07, 0.07, 0.07], 0.55; tag = 'glass1'
        elif mid == 80: col, a = [0.02, 0.02, 0.025], 0.7; tag = 'glass2'
        elif mid in (63, 64, 65): tag = 'lens'; col, a = [max(0.25, c) for c in cs], 0.35
        elif mid == 5: col, a = [0.1, 0.12, 0.15], 0.45
        else: col, a = [0.12, 0.14, 0.15], 0.22
        alpha = 'BLEND'
    elif 'Light_chrome' in name:
        tag = 'lamp'; metal = 1.0; rough = 0.15; col = [0.9 * c for c in cs]
    elif 'mirror' in name:
        tag = 'mirror'; metal = 1.0; rough = 0.04; col = [0.85, 0.85, 0.85]
    elif mid in (43, 44, 45, 46):
        tag = 'decal'; alpha = 'MASK'; col = [1, 1, 1]
        texi = tex('decal7760', atlas7760)
    elif mid == 74:
        tag = 'sfdecal'; alpha = 'MASK'; col = [1, 1, 1]; texi = tex('starfire', load_png('textures/StarFire3000_Decal_diffuse.dds'))
    elif mid in (67, 68):
        tag = 'numbers'; alpha = 'MASK'; col = [1, 1, 1]; texi = tex('numbers', load_png('textures/numbers_diffuse.dds'))
    elif mid == 81:
        tag = 'wrap'; col = cs; rough = 0.35
    elif 'chrome' in name and 'Interior' not in name:
        tag = 'chrome'; metal = 1.0; rough = 0.12; col = [0.9, 0.9, 0.9]
    elif 'silverScratched' in name or det.startswith('silverScratched'):
        tag = 'steel'; metal = 1.0; rough = 0.42; col = [0.62, 0.62, 0.6]
    elif 'rubber' in name and 'plasticPainted' not in det:
        tag = 'rubber'; rough = 0.85; col = [min(c, 0.035) for c in cs] if 'colorScale' in P else [0.03, 0.03, 0.03]
    elif 'Interior' in name:
        tag = 'interior'
        if 'fabric' in name: col, rough = [0.1, 0.1, 0.1], 0.95
        elif 'chrome' in name: col, metal, rough = [0.7, 0.7, 0.7], 1.0, 0.25
        elif 'colorScale' in P: rough = 0.4
        else: col, rough = [0.06, 0.06, 0.065], 0.6
    elif 'calibratedPaint' in det or 'JOHNDEERE' in name:
        tag = 'paint'; rough = 0.3
        if det.startswith('silverScratched'): tag, metal, rough, col = 'steel', 1.0, 0.42, [0.62, 0.62, 0.6]
    elif 'reflector' in name:
        tag = 'reflector'; rough = 0.2
    elif 'metalPainted' in det:
        tag = 'metal'; rough = 0.5
    elif 'plasticGranite' in det:
        tag = 'plastic'; rough = 0.7
    if mid in (6, 8): tag = 'grille'                  # cp690Alpha_* : perforated sheet in the game (alpha map missing)
    if mid == 7: tag, metal, rough, col = 'steel', 1.0, 0.4, [0.62, 0.62, 0.6]
    mm = {'name': 'm%d_%s' % (mid, tag), 'pbrMetallicRoughness': {
        'baseColorFactor': [min(1.0, float(col[0])), min(1.0, float(col[1])), min(1.0, float(col[2])), a], 'metallicFactor': metal, 'roughnessFactor': rough}}
    if texi is not None: mm['pbrMetallicRoughness']['baseColorTexture'] = {'index': texi}
    if alpha: mm['alphaMode'] = alpha
    if alpha == 'MASK': mm['alphaCutoff'] = 0.4
    if tag in ('glass', 'glass1', 'glass2', 'lens', 'decal', 'numbers', 'sfdecal'): mm['doubleSided'] = tag != 'decal'
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

# ---------------------------------------------------------------- the cotton module
bs = [s for s in BSH.values() if s['name'] == 'roundbale_visShape'][0]
cot = load_png('bales/cottonModule_diffuse.dds')
mt = {'name': 'module_cotton', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0, 'roughnessFactor': 0.9,
      'baseColorTexture': {'index': tex('cotton', cot.convert('RGB').resize((1024, 1024), Image.LANCZOS))}}}
J['materials'].append(mt); bmat = len(J['materials']) - 1
for c in ('yellow', 'pink', 'green', 'orange', 'lightBlue'):
    tex('wrap_' + c, load_png('bales/%sWrap_diffuse.dds' % c))
tex('decalCP690', atlasCP)
pos = bs['pos'].astype(np.float32)
attrs = {'POSITION': add_acc(pos, 5126, 'VEC3', 34962, minmax=True),
         'NORMAL': add_acc((bs['nrm'] / np.linalg.norm(bs['nrm'], axis=1, keepdims=True)).astype(np.float32), 5126, 'VEC3', 34962)}
for k in range(2):
    u = bs['uv'][k].copy().astype(np.float32); u[:, 1] = 1 - u[:, 1]
    attrs['TEXCOORD_%d' % k] = add_acc(u, 5126, 'VEC2', 34962)
J['meshes'].append({'name': 'module', 'primitives': [{'attributes': attrs, 'indices': add_acc(bs['idx'].astype(np.uint16), 5123, 'SCALAR', 34963), 'material': bmat}]})
J['nodes'].append({'name': 'module', 'mesh': len(J['meshes']) - 1, 'extras': {'hidden': True}})
J['scenes'][0]['nodes'].append(len(J['nodes']) - 1)
# the textures the game swaps in at run time (module wraps, the CP690 sticker sheet) ride on a hidden one-triangle
# mesh, one material each ("tex_<name>"), so every loader keeps and decodes them
tri = add_acc(np.array([[0, 0, 0], [0.01, 0, 0], [0, 0.01, 0]], np.float32), 5126, 'VEC3', 34962, minmax=True)
tuv = add_acc(np.array([[0, 0], [1, 0], [0, 1]], np.float32), 5126, 'VEC2', 34962)
prims = []
for k in ['wrap_' + c for c in ('yellow', 'pink', 'green', 'orange', 'lightBlue')] + ['decalCP690']:
    J['materials'].append({'name': 'tex_' + k, 'pbrMetallicRoughness': {'baseColorTexture': {'index': TEX[k]}}})
    prims.append({'attributes': {'POSITION': tri, 'TEXCOORD_0': tuv}, 'material': len(J['materials']) - 1})
J['meshes'].append({'name': 'texrack', 'primitives': prims})
J['nodes'].append({'name': 'texrack', 'mesh': len(J['meshes']) - 1, 'extras': {'hidden': True}})
J['scenes'][0]['nodes'].append(len(J['nodes']) - 1)

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
atlasCP.save(os.path.join(os.path.dirname(OUT) or '.', 'decalCP690_preview.png'))
