"""Étape 1 : détourage des personnes (Mask2Former + SAM) et carte de profondeur (Depth Anything V2).

Sorties dans assets/layers/ :
  m2f_XX.png      masques d'instance bruts (Mask2Former, classe « person »)
  depth.png       profondeur relative 16 bits (grand = proche)
"""
import os
import sys

import cv2
import numpy as np
import torch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source", "selfie.png")
OUT = os.path.join(ROOT, "assets", "layers")

torch.set_num_threads(os.cpu_count())


def instances(img):
    from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation

    name = "facebook/mask2former-swin-large-coco-instance"
    proc = AutoImageProcessor.from_pretrained(name)
    model = Mask2FormerForUniversalSegmentation.from_pretrained(name).eval()
    with torch.no_grad():
        out = model(**proc(images=img, return_tensors="pt"))
    res = proc.post_process_instance_segmentation(
        out, target_sizes=[img.size[::-1]], threshold=0.5, return_binary_maps=True)[0]
    seg = res["segmentation"].numpy()
    kept = []
    for i, info in enumerate(res["segments_info"]):
        if model.config.id2label[info["label_id"]] != "person":
            continue
        m = seg[i] > 0
        kept.append((info["score"], m))
        print(f"person score={info['score']:.2f} area={m.sum()}")
    return kept


def depth(img):
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    name = "depth-anything/Depth-Anything-V2-Large-hf"
    proc = AutoImageProcessor.from_pretrained(name)
    model = AutoModelForDepthEstimation.from_pretrained(name).eval()
    with torch.no_grad():
        d = model(**proc(images=img, return_tensors="pt")).predicted_depth
    d = torch.nn.functional.interpolate(d[None], size=img.size[::-1], mode="bicubic")[0, 0].numpy()
    d = (d - d.min()) / (d.max() - d.min())
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    img = Image.open(SRC).convert("RGB")
    what = sys.argv[1:] or ["inst", "depth"]
    if "inst" in what:
        for i, (_, m) in enumerate(instances(img)):
            cv2.imwrite(os.path.join(OUT, f"m2f_{i:02d}.png"), m.astype(np.uint8) * 255)
    if "depth" in what:
        d = depth(img)
        cv2.imwrite(os.path.join(OUT, "depth.png"), (d * 65535).astype(np.uint16))


if __name__ == "__main__":
    main()
