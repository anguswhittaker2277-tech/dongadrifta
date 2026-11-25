// Pack the raw exporter GLB for the web: WebP textures and meshopt-compressed geometry. The exporter has already
// quantised positions/normals/UVs (KHR_mesh_quantization) without touching node transforms.
// Nothing is pruned, merged or re-parented: the game looks nodes, materials and textures up by name.
// node pack.mjs in.glb out.glb   (needs @gltf-transform/{core,extensions,functions}@4, meshoptimizer, sharp)
import { NodeIO, Logger } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { textureCompress } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import sharp from 'sharp';
const [,, inp, out] = process.argv;
await MeshoptEncoder.ready; await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(inp);
doc.setLogger(new Logger(Logger.Verbosity.WARN));
await doc.transform(
  textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 88 }),
);
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
await io.write(out, doc);
const r = doc.getRoot();
console.log('skins', r.listSkins().length, 'nodes', r.listNodes().length, 'textures', r.listTextures().map(t => t.getName()).join(','));
