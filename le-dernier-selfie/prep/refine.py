"""Étape 2 : masques nets par personne.

Mask2Former donne des masques justes mais « en escalier ». On les raffine avec SAM (ViT-H) :
boîte englobante + points positifs pris dans le masque + points négatifs sur les voisins.
Puis on partitionne l'avant-plan (SAM ∪ profondeur) entre les personnes par ligne de partage des eaux
sur le gradient de profondeur : les frontières suivent les vraies discontinuités 3D.

Sorties dans assets/layers/ :
  sam_XX.png      probabilité SAM par personne (8 bits)
  labels.png      partition finale (0 = décor, 1..N = personnes)
"""
import glob
import os

import cv2
import numpy as np
import torch
from PIL import Image
from skimage.segmentation import watershed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source", "selfie.png")
LAY = os.path.join(ROOT, "assets", "layers")

torch.set_num_threads(os.cpu_count())

# Corrections manuelles : (indice Mask2Former, polygone) — zones que le détecteur a ratées.
EXTRA = {
    # la main en V à côté de la fille de droite
    5: [np.array([[1283, 222], [1296, 218], [1330, 262], [1332, 205], [1345, 203], [1358, 265],
                  [1380, 300], [1378, 350], [1335, 352], [1305, 320], [1308, 285]])],
    # les genoux en maille de la fille au menton dans la main
    6: [np.array([[655, 853], [690, 700], [745, 650], [800, 628], [860, 625], [905, 650],
                  [940, 720], [975, 790], [1040, 800], [1045, 853]])],
}


def sample_points(m, n, rng):
    er = cv2.erode(m.astype(np.uint8), np.ones((25, 25), np.uint8))
    ys, xs = np.nonzero(er if er.sum() > 200 else m)
    idx = rng.choice(len(xs), size=min(n, len(xs)), replace=False)
    return [[float(xs[i]), float(ys[i])] for i in idx]


def main():
    from transformers import SamModel, SamProcessor

    img = Image.open(SRC).convert("RGB")
    H, W = img.size[1], img.size[0]
    masks = [cv2.imread(f, 0) > 127 for f in sorted(glob.glob(os.path.join(LAY, "m2f_*.png")))]
    for k, polys in EXTRA.items():
        mm = masks[k].astype(np.uint8)
        cv2.fillPoly(mm, polys, 1)
        masks[k] = mm > 0
    n = len(masks)
    cents = [np.array(np.nonzero(m)[::-1]).mean(1) for m in masks]

    name = "facebook/sam-vit-huge"
    proc = SamProcessor.from_pretrained(name)
    model = SamModel.from_pretrained(name).eval()
    inputs = proc(img, return_tensors="pt")
    with torch.no_grad():
        emb = model.get_image_embeddings(inputs["pixel_values"])

    rng = np.random.default_rng(7)
    probs = np.zeros((n, H, W), np.float32)
    for i, m in enumerate(masks):
        ys, xs = np.nonzero(m)
        box = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
        pos = sample_points(m, 6, rng)
        neg = [[float(c[0]), float(c[1])] for j, c in enumerate(cents)
               if j != i and box[0] - 80 < c[0] < box[2] + 80 and box[1] - 80 < c[1] < box[3] + 80
               and not m[int(c[1]), int(c[0])]]
        pts = pos + neg
        lab = [1] * len(pos) + [0] * len(neg)
        p = proc(img, input_points=[[pts]], input_labels=[[lab]], input_boxes=[[box]], return_tensors="pt")
        p.pop("pixel_values", None)
        p["input_points"] = p["input_points"][:, :, None] if p["input_points"].dim() == 3 else p["input_points"]
        with torch.no_grad():
            out = model(image_embeddings=emb, multimask_output=True, **{k: v for k, v in p.items()
                                                                      if k in ("input_points", "input_labels", "input_boxes")})
        low = out.pred_masks  # 1,1,3,256,256
        up = proc.post_process_masks(low, inputs["original_sizes"], inputs["reshaped_input_sizes"],
                                     binarize=False)[0][0]  # 3,H,W logits
        sig = torch.sigmoid(up).numpy()
        # garde la proposition la plus cohérente avec le masque Mask2Former
        ious = [((s > 0.5) & m).sum() / max(((s > 0.5) | m).sum(), 1) for s in sig]
        best = int(np.argmax(ious))
        probs[i] = sig[best]
        print(f"person {i}: iou={ious[best]:.3f} scores={out.iou_scores[0, 0].numpy().round(3)}")
        cv2.imwrite(os.path.join(LAY, f"sam_{i:02d}.png"), (sig[best] * 255).astype(np.uint8))

    # --- partition par ligne de partage des eaux sur la profondeur ---
    depth = cv2.imread(os.path.join(LAY, "depth.png"), -1).astype(np.float32) / 65535
    union_m2f = np.any(masks, axis=0)
    fg = (probs.max(0) > 0.5) | union_m2f
    seeds = np.zeros((H, W), np.int32)
    for i in range(n):
        core = (probs[i] > 0.85) & masks[i]
        core = cv2.erode(core.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        seeds[core] = i + 1
    bg_seed = ~cv2.dilate(fg.astype(np.uint8), np.ones((21, 21), np.uint8)).astype(bool)
    seeds[bg_seed] = n + 1
    gx = cv2.Sobel(depth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(depth, cv2.CV_32F, 0, 1, ksize=3)
    lum = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    cx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    cy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy) * 4.0 + np.hypot(cx, cy) * 0.6 + (1 - probs.max(0)) * 0.05
    lab = watershed(grad, seeds)
    lab[lab == n + 1] = 0
    cv2.imwrite(os.path.join(LAY, "labels.png"), lab.astype(np.uint8))
    print("pixels par personne", [(lab == i + 1).sum() for i in range(n)])


if __name__ == "__main__":
    main()
