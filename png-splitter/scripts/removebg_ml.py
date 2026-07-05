#!/usr/bin/env python3
"""Photoroom-level background removal for sprite sheets on a fake
checkerboard background.

Usage: python3 scripts/removebg_ml.py input.png output.png

Two stages:
1. Classical checker matte (scripts/removebg.py logic) — locates every
   component reliably, including text glyphs and thin ornaments.
2. Per-component ML matting (rembg / isnet-general-use) — each component is
   cropped and matted alone, where it IS the salient subject. This removes
   painted glow/highlight smudge at edges that color heuristics cannot
   distinguish from art. Full-sheet ML fails here (keeps only the "main"
   subject); per-crop is the trick.

The ML alpha is clipped to the component's own (dilated) classical mask so
neighbors overlapping the crop don't bleed in. If the ML matte diverges
wildly from the classical one (glyphs, hairline ornaments — ML drops them),
the classical alpha is kept for that component.

Requires: numpy, pillow, scipy, rembg, onnxruntime.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

PAD = 12
MIN_ML_PIXELS = 2000  # small comps (glyphs, leaflets) keep the classical matte
ML_SCALE_MIN = 256   # upscale crops so the shorter side reaches this


def classical_matte(src: str) -> np.ndarray:
    """Run scripts/removebg.py and return its RGBA array."""
    out = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    script = Path(__file__).with_name("removebg.py")
    subprocess.run([sys.executable, str(script), src, out.name], check=True)
    return np.asarray(Image.open(out.name).convert("RGBA")).copy()


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]

    rgba = classical_matte(src)
    h, w = rgba.shape[:2]
    alpha = rgba[:, :, 3]

    import onnxruntime as ort
    from rembg import remove
    from rembg.session_factory import sessions_class

    # rembg's new_session doesn't expose SessionOptions; build the session
    # directly. Arena OFF: releases RAM between inferences AND measured ~20%
    # faster on macOS arm64 (the arena's growth causes page pressure).
    sess_opts = ort.SessionOptions()
    sess_opts.enable_cpu_mem_arena = False
    session = next(
        sc for sc in sessions_class if sc.name() == "birefnet-general"
    )("birefnet-general", sess_opts)
    original = Image.open(src).convert("RGB")

    fg = alpha > 8
    lbl, n = ndimage.label(fg, structure=np.ones((3, 3)))
    objects = ndimage.find_objects(lbl)

    replaced = kept = 0
    for i, sl in enumerate(objects):
        if sl is None:
            continue
        comp = lbl[sl] == (i + 1)
        if comp.sum() < MIN_ML_PIXELS:
            kept += 1
            continue

        y0 = max(0, sl[0].start - PAD)
        y1 = min(h, sl[0].stop + PAD)
        x0 = max(0, sl[1].start - PAD)
        x1 = min(w, sl[1].stop + PAD)

        comp_full = np.zeros((h, w), dtype=bool)
        comp_full[sl] = comp

        crop = original.crop((x0, y0, x1, y1))
        cw, ch = crop.size
        scale = max(1, int(np.ceil(ML_SCALE_MIN / min(cw, ch))))
        if scale > 1:
            crop = crop.resize((cw * scale, ch * scale), Image.LANCZOS)
        ml_img = remove(crop, session=session).split()[3]
        if scale > 1:
            ml_img = ml_img.resize((cw, ch), Image.LANCZOS)
        ml = np.asarray(ml_img, dtype=np.uint8)

        # BiRefNet is reliable enough to replace alpha wholesale within the
        # component's own (dilated) support — soft feathered edges, no white
        # remnants. Sanity check still guards odd failures: on divergence
        # keep the classical matte untouched.
        support = ndimage.binary_dilation(
            comp_full[y0:y1, x0:x1], np.ones((3, 3)), iterations=4
        )
        ml = np.where(support, ml, 0)
        classical_area = comp.sum()
        ml_area = (ml > 128).sum()
        if not 0.6 * classical_area <= ml_area <= 1.25 * classical_area:
            kept += 1
            continue
        region = rgba[y0:y1, x0:x1, 3]
        dominate = support & (ml.astype(np.int16) > region.astype(np.int16) + 8)
        rgba[y0:y1, x0:x1, :3][dominate] = np.asarray(original)[y0:y1, x0:x1][dominate]
        rgba[y0:y1, x0:x1, 3] = np.where(support, ml, region)
        replaced += 1

    # Cluster pass: small comps (glyphs, thin ornaments) whose strokes the
    # classical matte loses because they are checker-colored. Group nearby
    # small comps, ML the whole cluster (text reads as one subject), and
    # max-merge so classical pixels are never removed, only restored.
    small_fg = fg & ~np.isin(
        lbl, [i + 1 for i, sl in enumerate(objects) if sl is not None and (lbl[sl] == i + 1).sum() >= MIN_ML_PIXELS]
    )
    clusters, cn = ndimage.label(
        ndimage.binary_dilation(small_fg, np.ones((3, 3)), iterations=8),
        structure=np.ones((3, 3)),
    )
    restored = 0
    for ci, csl in enumerate(ndimage.find_objects(clusters)):
        if csl is None:
            continue
        cmask = (clusters[csl] == ci + 1) & small_fg[csl]
        if cmask.sum() < 20:
            continue
        y0 = max(0, csl[0].start - 2 * PAD)
        y1 = min(h, csl[0].stop + 2 * PAD)
        x0 = max(0, csl[1].start - 2 * PAD)
        x1 = min(w, csl[1].stop + 2 * PAD)
        crop = original.crop((x0, y0, x1, y1))
        cw, ch = crop.size
        scale = max(1, int(np.ceil(ML_SCALE_MIN / min(cw, ch))))
        if scale > 1:
            crop = crop.resize((cw * scale, ch * scale), Image.LANCZOS)
        ml_img = remove(crop, session=session).split()[3]
        if scale > 1:
            ml_img = ml_img.resize((cw, ch), Image.LANCZOS)
        ml = np.asarray(ml_img, dtype=np.uint8)
        support = ndimage.binary_dilation(
            clusters[y0:y1, x0:x1] == ci + 1, np.ones((3, 3)), iterations=6
        )
        ml = np.where(support, ml, 0)
        region = rgba[y0:y1, x0:x1, 3]
        dominate = support & (ml.astype(np.int16) > region.astype(np.int16) + 8)
        rgba[y0:y1, x0:x1, :3][dominate] = np.asarray(original)[y0:y1, x0:x1][dominate]
        rgba[y0:y1, x0:x1, 3] = np.maximum(region, ml)
        restored += 1
    print(f"cluster passes: {restored}")

    Image.fromarray(rgba, "RGBA").save(dst)
    print(f"components: {n}, ml-matted: {replaced}, classical kept: {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
