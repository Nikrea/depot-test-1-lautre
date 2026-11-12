"""Prépare le modèle de détourage (IS-Net, DIS) pour le navigateur.

Sortie dans miniatures/model/ :
  isnet.json              plan de reconstruction
  isnet-structure.wasm    le graphe ONNX sans les poids (1,5 Mo)
  isnet-weights-N.wasm    les poids en int8 par canal (44 Mo, 4 morceaux < 15 Mo)
  (octets bruts, pas des modules WebAssembly : .wasm est juste un type binaire que les artefacts servent)
  ort-wasm-simd.wasm      le moteur ONNX Runtime Web 1.17.3

Le navigateur recolle tout en un modèle float32 (onnxruntime-web, WASM ou WebGL).
Étapes : une seule sortie, MaxPool sans ceil_mode (identique en 1024 px), formes figées
par ORT (constant folding), Resize en « scales » (requis par WebGL), poids int8 par canal.

    pip install onnx onnxruntime numpy
    python3 miniatures/tools/build_model.py
"""
import hashlib, json, os, sys, tempfile, urllib.request
import numpy as np
import onnx
import onnxruntime as ort
from onnx import numpy_helper, shape_inference

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'model')
MODEL_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx'
WASM_URL = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.17.3/dist/ort-wasm-simd.wasm'
CHUNK = 12 * 1024 * 1024
# Les artefacts claude.ai ne servent pas les .bin : les octets bruts sont publiés sous .wasm
# (type binaire accepté). Le navigateur les lit avec fetch().arrayBuffer(), jamais comme module.
EXT = '.wasm'


def fetch(url, path):
    if not os.path.exists(path):
        print('téléchargement', url)
        urllib.request.urlretrieve(url, path)
    return path


def trim(m):
    g = m.graph
    keep = [o for o in g.output if o.name == 'output_image']
    del g.output[:]; g.output.extend(keep)
    needed, alive = {'output_image'}, []
    for n in reversed(list(g.node)):
        if any(o in needed for o in n.output):
            alive.append(n); needed.update(i for i in n.input if i)
    del g.node[:]; g.node.extend(reversed(alive))
    inits = [i for i in g.initializer if i.name in needed]
    del g.initializer[:]; g.initializer.extend(inits)
    del g.value_info[:]
    for n in g.node:
        if n.op_type == 'MaxPool':
            for a in n.attribute:
                if a.name == 'ceil_mode':
                    a.i = 0
    return m


def fold(path_in, path_out):
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    so.optimized_model_filepath = path_out
    ort.InferenceSession(path_in, so, providers=['CPUExecutionProvider'])


def resize_to_scales(m):
    mi = shape_inference.infer_shapes(m)
    shapes = {vi.name: [d.dim_value for d in vi.type.tensor_type.shape.dim]
              for vi in list(mi.graph.value_info) + list(mi.graph.input) + list(mi.graph.output)}
    inits = {i.name: i for i in m.graph.initializer}
    for k, n in enumerate([n for n in m.graph.node if n.op_type == 'Resize']):
        x, _, _, sz = (list(n.input) + [''] * 4)[:4]
        scales = (numpy_helper.to_array(inits[sz]) / np.array(shapes[x])).astype(np.float32)
        name = f'resize_scales_{k}'
        m.graph.initializer.append(numpy_helper.from_array(scales, name))
        del n.input[:]; n.input.extend([x, '', name])
    needed = set(i for n in m.graph.node for i in n.input)
    keep = [i for i in m.graph.initializer if i.name in needed]
    del m.graph.initializer[:]; m.graph.initializer.extend(keep)
    ops = [o for o in m.opset_import if o.domain in ('', 'ai.onnx')]
    del m.opset_import[:]; m.opset_import.extend(ops)
    onnx.checker.check_model(m)
    return m


def pack(m):
    markers, weights = [], []
    for init in m.graph.initializer:
        w = numpy_helper.to_array(init)
        if w.dtype != np.float32 or w.size < 4:
            markers.append(None); weights.append(None); continue
        mk = hashlib.sha256(init.name.encode() + b'#mk').digest()[:16]
        if w.ndim >= 2 and w.size >= 64:
            flat = w.reshape(w.shape[0], -1)
            sc = (np.abs(flat).max(1) / 127.0).astype(np.float32); sc[sc == 0] = 1
            q = np.clip(np.round(flat / sc[:, None]), -127, 127).astype(np.int8)
            weights.append(('q', q.tobytes(), sc.tobytes(), w.shape[0], flat.shape[1]))
        else:
            weights.append(('f', w.tobytes()))
        init.ClearField('float_data'); init.raw_data = mk + bytes(w.size * 4 - 16)
        markers.append((mk, w.size * 4))
    buf = m.SerializeToString()
    parts, pos = [], 0
    for i, mkr in enumerate(markers):
        if mkr is None:
            continue
        off = buf.find(mkr[0], pos)
        assert off >= 0 and buf.find(mkr[0], off + 1) < 0
        parts.append((off, mkr[1], i)); pos = off + mkr[1]
    struct, layout, cur = bytearray(), [], 0
    for off, nb, i in parts:
        struct += buf[cur:off]; layout += [['s', off - cur], ['w', i]]; cur = off + nb
    struct += buf[cur:]; layout.append(['s', len(buf) - cur])
    blob, wmeta = bytearray(), []
    for w in weights:
        while len(blob) % 4:
            blob.append(0)
        if w is None:
            wmeta.append(None)
        elif w[0] == 'q':
            so = len(blob); blob += w[2]; qo = len(blob); blob += w[1]
            wmeta.append(['q', so, qo, w[3], w[4]])
        else:
            fo = len(blob); blob += w[1]; wmeta.append(['f', fo, len(w[1]) // 4])
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'isnet-structure' + EXT), 'wb').write(struct)
    chunks = []
    for k in range(0, len(blob), CHUNK):
        name = f'isnet-weights-{k // CHUNK}' + EXT
        open(os.path.join(OUT, name), 'wb').write(blob[k:k + CHUNK]); chunks.append(name)
    manifest = {'total': len(buf), 'structure': 'isnet-structure' + EXT, 'structureSize': len(struct),
                'chunks': chunks, 'weightsSize': len(blob), 'layout': layout, 'weights': wmeta,
                'input': m.graph.input[0].name, 'size': 1024}
    json.dump(manifest, open(os.path.join(OUT, 'isnet.json'), 'w'), separators=(',', ':'))
    print('modèle', len(buf), 'octets → structure', len(struct), '+ poids', len(blob), chunks)


def main():
    tmp = sys.argv[1] if len(sys.argv) > 1 else tempfile.gettempdir()
    src = fetch(MODEL_URL, os.path.join(tmp, 'isnet-general-use.onnx'))
    trimmed = os.path.join(tmp, 'isnet_trim.onnx'); folded = os.path.join(tmp, 'isnet_fold.onnx')
    onnx.save(trim(onnx.load(src)), trimmed)
    fold(trimmed, folded)
    pack(resize_to_scales(onnx.load(folded)))
    fetch(WASM_URL, os.path.join(OUT, 'ort-wasm-simd.wasm'))


if __name__ == '__main__':
    main()
