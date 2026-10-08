"""Planche des temps forts -> output/storyboard.jpg"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from render import FPS, OUT, Renderer

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, "..", "pub-chine", "assets", "fonts", "Inter-SemiBold.otf")

BEATS = [
    (1.6, "Vingt yeux dans le noir"),
    (3.4, "La lampe s'allume : le selfie"),
    (6.2, "Le premier se lève"),
    (12.6, "Leurs regards restent"),
    (17.0, "Le père s'en va"),
    (22.2, "Plus que deux"),
    (25.0, "Le dernier part, le cadre tressaille"),
    (28.6, "Le canapé vide"),
    (33.2, "Au fond du couloir..."),
]


def main():
    R = Renderer()
    tw, th = 640, 296
    font = ImageFont.truetype(FONT, 22)
    tiles = []
    for t, label in BEATS:
        f = R.frame(int(round(t * FPS)))[96:984]
        if t > 32:  # dans le noir : on éclaircit la vignette pour qu'on voie les yeux
            f = np.clip(f.astype(np.float32) * 3.0, 0, 255).astype(np.uint8)
        im = Image.fromarray(cv2.cvtColor(cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(im)
        d.rectangle([0, th - 40, tw, th], fill=(0, 0, 0))
        d.text((14, th - 33), f"{t:4.1f} s   {label}", font=font, fill=(236, 214, 178))
        tiles.append(np.array(im))
    gap = 8
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            row.append(tiles[r * 3 + c])
            if c < 2:
                row.append(np.zeros((th, gap, 3), np.uint8))
        rows.append(np.hstack(row))
        if r < 2:
            rows.append(np.zeros((gap, rows[-1].shape[1], 3), np.uint8))
    sheet = np.vstack(rows)
    sheet = np.pad(sheet, ((gap, gap), (gap, gap), (0, 0)))
    cv2.imwrite(os.path.join(OUT, "storyboard.jpg"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("ok storyboard")


if __name__ == "__main__":
    main()
