"""Étape 3 : la pièce vide (le décor sans personne), par inpainting Stable Diffusion.

Passe 1 : génération à demi-résolution (920×424) de plusieurs candidats.
Passe 2 : le candidat retenu est agrandi puis « redétaillé » à pleine résolution (débruitage partiel),
          et recollé sur l'original hors du masque, avec un fondu.

  python3 prep/plate.py gen  [seeds...]     -> assets/layers/plate_cand_<seed>.png
  python3 prep/plate.py draft <seed>        -> assets/layers/plate.png (version retenue pour le film : seed 11)
  python3 prep/plate.py final <seed>        -> assets/layers/plate.png (variante redétaillée, très lente sur CPU)
"""
import os
import sys

import cv2
import numpy as np
import torch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "source", "selfie.png")
LAY = os.path.join(ROOT, "assets", "layers")
MODEL = "stable-diffusion-v1-5/stable-diffusion-inpainting"

PROMPT = ("empty dim living room at night, nobody, a dark fabric sofa with rumpled cushions in the foreground, "
          "warm table lamp glowing on the left, potted plant, wooden ceiling beams, doorway and hallway in the "
          "background, sepia brown monochrome, soft warm light, cinematic film still, photorealistic 3D render, "
          "shallow depth of field")
NEG = ("person, people, man, woman, face, eyes, hands, body, silhouette, ghost, text, watermark, "
       "blurry, deformed, cartoon, bright colors")

GLOOM = 1.6     # la pièce vide : 1,6 fois la luminosité moyenne des personnes qu'elle remplace

torch.set_num_threads(os.cpu_count())


def people_mask(dilate=13):
    lab = cv2.imread(os.path.join(LAY, "labels.png"), 0)
    m = (lab > 0).astype(np.uint8) * 255
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate)))


def pipe(kind):
    from diffusers import StableDiffusionInpaintPipeline, DPMSolverMultistepScheduler

    p = StableDiffusionInpaintPipeline.from_pretrained(MODEL, torch_dtype=torch.float32, safety_checker=None)
    p.scheduler = DPMSolverMultistepScheduler.from_config(p.scheduler.config, use_karras_sigmas=True)
    p.set_progress_bar_config(disable=False)
    return p


def gen(seeds):
    img = Image.open(SRC).convert("RGB")
    W, H = 920, 424
    src = img.resize((W, H), Image.LANCZOS)
    m = Image.fromarray(people_mask(17)).resize((W, H), Image.BILINEAR)
    p = pipe("gen")
    for s in seeds:
        out = p(prompt=PROMPT, negative_prompt=NEG, image=src, mask_image=m, width=W, height=H,
                num_inference_steps=28, guidance_scale=7.0, generator=torch.Generator().manual_seed(s)).images[0]
        out.save(os.path.join(LAY, f"plate_cand_{s}.png"))
        print("ok", s)


def grade(gen, orig, m):
    """Ramène la zone générée dans l'étalonnage de l'image. Le modèle redessine aussi le décor
    existant : la correspondance luminance générée -> luminance réelle, mesurée sur ce décor
    (hors masque), est appliquée à la zone inventée. La teinte (a, b) suit la luminance comme dans
    l'original (virage sépia)."""
    lab_o = cv2.cvtColor(orig.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_g = cv2.cvtColor(gen.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    bg = cv2.erode((m < 128).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    Lg, Lo = lab_g[..., 0][bg], lab_o[..., 0][bg]
    edges = np.linspace(0, 256, 65)
    mid = (edges[:-1] + edges[1:]) / 2
    curve = np.full(64, np.nan)
    for k in range(64):
        s = (Lg >= edges[k]) & (Lg < edges[k + 1])
        if s.sum() > 80:
            curve[k] = np.median(Lo[s])
    ok = ~np.isnan(curve)
    curve = np.interp(mid, mid[ok], curve[ok])
    # au-delà des valeurs observées : on prolonge avec la pente moyenne
    last = mid[ok][-1]
    slope = (curve[ok][-1] - curve[ok][0]) / max(last - mid[ok][0], 1)
    curve[mid > last] = curve[ok][-1] + slope * (mid[mid > last] - last)
    curve = np.maximum.accumulate(curve)
    L = np.interp(lab_g[..., 0], mid, curve)
    # teinte sépia : médiane de a, b par tranche de luminance dans l'original
    Lall = lab_o[..., 0].ravel()
    a_lut, b_lut = np.full(64, np.nan), np.full(64, np.nan)
    for k in range(64):
        s = (Lall >= edges[k]) & (Lall < edges[k + 1])
        if s.sum() > 50:
            a_lut[k] = np.median(lab_o[..., 1].ravel()[s])
            b_lut[k] = np.median(lab_o[..., 2].ravel()[s])
    ok = ~np.isnan(a_lut)
    A = np.interp(L, mid[ok], a_lut[ok])
    B = np.interp(L, mid[ok], b_lut[ok])
    out = np.dstack([L, A, B]).clip(0, 255).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_LAB2RGB).astype(np.float32)


def draft(seed):
    """Plaque finale à partir d'un candidat (sans redétaillage : le flou du fond se lit comme une
    profondeur de champ). Les mèches fines qui dépassent des masques sont effacées par un filtre
    médian dans une couronne autour des personnes ; la zone inventée est plongée dans la même
    pénombre que les personnes qu'elle remplace, en épargnant les abat-jour."""
    img = Image.open(SRC).convert("RGB")
    W, H = img.size
    orig = np.array(img, np.float32)
    cand = np.array(Image.open(os.path.join(LAY, f"plate_cand_{seed}.png")).resize((W, H), Image.LANCZOS), np.float32)
    m_in, m_out = people_mask(13), people_mask(41)
    g = grade(cand, orig, m_in)
    # pénombre, rang par rang
    lum = g.mean(axis=2)
    sel = m_in > 127
    olum = orig.mean(axis=2)
    rows_g = np.array([lum[y][sel[y]].mean() if sel[y].sum() > 20 else np.nan for y in range(H)])
    rows_o = np.array([olum[y][sel[y]].mean() if sel[y].sum() > 20 else np.nan for y in range(H)])
    ok = ~np.isnan(rows_g)
    yy = np.arange(H)
    rows_g = np.interp(yy, yy[ok], rows_g[ok])
    rows_o = np.interp(yy, yy[ok], rows_o[ok])
    k = np.ones(81) / 81
    rows_g = np.convolve(np.pad(rows_g, 40, mode="edge"), k, "valid")
    rows_o = np.convolve(np.pad(rows_o, 40, mode="edge"), k, "valid")
    gain = np.clip(GLOOM * rows_o / np.maximum(rows_g, 1), 0.12, 1.0)
    # en haut, le mur inventé touche le vrai mur : on garde l'accord trouvé par grade()
    w = np.clip((yy - 300) / 180.0, 0, 1)
    w = w * w * (3 - 2 * w)
    gain = (1 - w + w * gain)[:, None, None]
    lum_s = cv2.GaussianBlur(lum, (0, 0), 3)
    keep = np.clip((lum_s[..., None] - 200) / 40, 0, 1)
    g = g * (gain + (1 - gain) * keep)
    # abat-jour : lumière chaude, comme la lampe d'origine
    hot = np.clip((cv2.GaussianBlur(g.mean(axis=2), (0, 0), 3)[..., None] - 140) / 80, 0, 1)
    g = g * (1 - hot) + g * np.array([1.0, 0.84, 0.60], np.float32) * hot
    # volume des abat-jour : plus sombres en haut et sur les bords (cylindre éclairé de l'intérieur)
    blobs = ((cv2.GaussianBlur(g.mean(axis=2), (0, 0), 3) > 175) & (m_in > 127)).astype(np.uint8)
    k, cc, st, _ = cv2.connectedComponentsWithStats(blobs)
    for c in range(1, k):
        x, y, w, h, area = st[c]
        if area < 400:
            continue
        reg = cv2.dilate((cc == c).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        reg = cv2.GaussianBlur(reg, (0, 0), 2.0)[..., None]
        yy_, xx_ = np.mgrid[0:H, 0:W].astype(np.float32)
        v = np.clip((yy_ - y) / max(h, 1), 0, 1)
        u = np.clip((xx_ - x) / max(w, 1), 0, 1) * 2 - 1
        shape = (0.70 + 0.30 * v ** 0.7) * (1 - 0.22 * u ** 4)
        g = g * (1 - reg) + g * shape[..., None] * reg
    # couronne : décor d'origine sans les mèches
    ring = cv2.medianBlur(orig.astype(np.uint8), 15).astype(np.float32)
    a_out = cv2.GaussianBlur(m_out, (0, 0), 6).astype(np.float32)[..., None] / 255
    a_in = cv2.GaussianBlur(m_in, (0, 0), 4).astype(np.float32)[..., None] / 255
    base = orig * (1 - a_out) + ring * a_out
    plate = base * (1 - a_in) + g * a_in
    # léger piqué
    blur = cv2.GaussianBlur(plate, (0, 0), 1.5)
    plate = plate + 0.35 * (plate - blur) * a_in
    cv2.imwrite(os.path.join(LAY, "plate.png"), cv2.cvtColor(plate.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))


def final(seed):
    img = Image.open(SRC).convert("RGB")
    W, H = img.size
    cand = Image.open(os.path.join(LAY, f"plate_cand_{seed}.png")).resize((W, H), Image.LANCZOS)
    m = people_mask(13)
    # recolle l'original hors masque avant le redétaillage, pour que le modèle voie le vrai décor
    a = cv2.GaussianBlur(m, (0, 0), 4).astype(np.float32)[..., None] / 255
    base = np.array(img, np.float32) * (1 - a) + np.array(cand, np.float32) * a
    Wp, Hp = (W // 8) * 8, (H // 8) * 8
    base_im = Image.fromarray(base.clip(0, 255).astype(np.uint8)).resize((Wp, Hp), Image.LANCZOS)
    mask_im = Image.fromarray(m).resize((Wp, Hp), Image.BILINEAR)
    p = pipe("final")
    out = p(prompt=PROMPT, negative_prompt=NEG, image=base_im, mask_image=mask_im, width=Wp, height=Hp,
            strength=0.38, num_inference_steps=30, guidance_scale=6.0,
            generator=torch.Generator().manual_seed(seed)).images[0]
    out = np.array(out.resize((W, H), Image.LANCZOS), np.float32)
    orig = np.array(img, np.float32)
    out = grade(out, orig, m)
    plate = orig * (1 - a) + out * a
    cv2.imwrite(os.path.join(LAY, "plate.png"), cv2.cvtColor(plate.clip(0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    print("plate ok")


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen([int(s) for s in sys.argv[2:]] or [11, 23, 42, 77])
    elif sys.argv[1] == "draft":
        draft(int(sys.argv[2]))
    else:
        final(int(sys.argv[2]))
