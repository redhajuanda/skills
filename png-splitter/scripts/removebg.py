#!/usr/bin/env python3
"""Remove a light checkerboard (fake-transparency) background with soft,
color-decontaminated edges — then feed the result to the split CLI.

Usage: python3 scripts/removebg.py input.png output.png

Method (classical matting, no ML):
1. Detect background: near-white pixels connected to the border, plus
   enclosed near-white pockets showing the checker's two-tone signature
   (letter counters, gaps between branches). White highlights on objects
   are single-shade and survive.
2. Build a trimap: sure-bg / sure-fg (eroded) / unknown boundary band.
3. In the band, solve C = a*F + (1-a)*B against the nearest checker shade:
   alpha from color distance, then F = (C - (1-a)B) / a — this removes the
   white fringe instead of keeping or hard-cutting it.
"""

import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def build_bg_mask(arr: np.ndarray) -> tuple[np.ndarray, float, float]:
    mx, mn = arr.max(2), arr.min(2)
    gray = arr.mean(2)
    near_bg = (mn > 228) & ((mx - mn) < 10)

    lbl, n = ndimage.label(near_bg, structure=np.ones((3, 3)))
    border = np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))
    border = border[border != 0]
    bg = np.isin(lbl, border)

    # Enclosed checker pockets: bimodal (both shades well represented).
    if n:
        sizes = ndimage.sum(near_bg, lbl, range(1, n + 1))
        lo = ndimage.sum(near_bg & (gray < 248), lbl, range(1, n + 1))
        hi = ndimage.sum(near_bg & (gray >= 249), lbl, range(1, n + 1))
        fl, fh = lo / np.maximum(sizes, 1), hi / np.maximum(sizes, 1)
        # Uniform pockets the size of a checker cell are also background:
        # a single cell can be one shade, so bimodality alone misses it.
        means = ndimage.mean(gray, lbl, range(1, n + 1))
        stds = ndimage.standard_deviation(gray, lbl, range(1, n + 1))
        bimodal = (fl > 0.2) & (fh > 0.2)
        uniform_cell = (stds < 5) & (means > 240)
        ids = np.nonzero((sizes > 24) & (bimodal | uniform_cell))[0] + 1
        bg |= np.isin(lbl, ids)
        # Tiny checker slivers between petals/blades: the checker shades sit
        # at ~244/254, genuine white paint (heron feathers) below ~239.
        sliver_ids = np.nonzero((sizes <= 24) & (means >= 241))[0] + 1
        bg |= np.isin(lbl, sliver_ids)

    # The checker's two shades, measured from actual background pixels.
    bg_gray = gray[bg]
    shade_lo = float(np.median(bg_gray[bg_gray < 248]))
    shade_hi = float(np.median(bg_gray[bg_gray >= 248]))
    return bg, shade_lo, shade_hi


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert("RGB")
    arr = np.asarray(im).astype(np.float32)

    bg, shade_lo, shade_hi = build_bg_mask(arr)
    fg = ~bg
    fg = ndimage.binary_opening(fg, np.ones((3, 3)))
    # NOTE: no binary_closing — it seals thin checker gaps (between grass
    # blades, leaves) into the foreground and they survive as white slivers.
    # Fill pinholes only; large enclosed pockets were already handled.
    holes = ndimage.binary_fill_holes(fg) & ~fg
    hl, hn = ndimage.label(holes)
    if hn:
        sizes = ndimage.sum(holes, hl, range(1, hn + 1))
        hole_gray = ndimage.mean(arr.mean(2), hl, range(1, hn + 1))
        # Fill only dark pinholes; light ones are checker slivers.
        fg |= np.isin(hl, np.nonzero((sizes < 24) & (hole_gray < 241))[0] + 1)

    # Trimap: sure-fg core, unknown band. The source art carries a baked-in
    # pale glow around objects, so choke the matte: no outward dilation and
    # a deeper core erosion — the band's distance test then eats the glow.
    # Small components (text glyphs, hairline ornaments) can't afford the
    # full 2px choke — their strokes are 1-2px wide. Give them 1px.
    lbl_fg, n_fg = ndimage.label(fg, structure=np.ones((3, 3)))
    comp_sizes = ndimage.sum(fg, lbl_fg, range(1, n_fg + 1)) if n_fg else []
    small = np.isin(lbl_fg, np.nonzero(np.asarray(comp_sizes) < 2000)[0] + 1)
    core = ndimage.binary_erosion(fg, np.ones((3, 3)), iterations=2)
    core |= ndimage.binary_erosion(fg, np.ones((3, 3))) & small
    band = fg & ~core

    alpha = np.zeros(arr.shape[:2], dtype=np.float32)
    alpha[core] = 1.0

    # Matting in the band: distance to the nearer checker shade -> alpha.
    gray = arr.mean(2)
    d = np.minimum(np.abs(gray - shade_lo), np.abs(gray - shade_hi))
    chroma = arr.max(2) - arr.min(2)
    d = np.maximum(d, chroma)  # colored pixels are foreground even if light
    a_band = np.clip((d - 12.0) / (36.0 - 12.0), 0.0, 1.0)
    # Small comps (glyphs): stroke color can equal the checker shade, so a
    # color ramp shreds them. Trust the mask: full alpha, 1px box feather.
    a_small = ndimage.uniform_filter(fg.astype(np.float32), 3)
    a_band = np.where(small, a_small, a_band)
    alpha[band] = a_band[band]

    # The distance ramp itself anti-aliases (blend pixels get blended
    # alpha); no global blur — blurring either re-grows the glow or erodes
    # 1px twigs. Just clamp outside.
    alpha[~(fg | band)] = 0.0

    # Color decontamination: unmix the background from semi-transparent
    # pixels so no white fringe remains: F = (C - (1-a)B) / a.
    semi = (alpha > 0.02) & (alpha < 0.98)
    b_val = np.where(np.abs(gray - shade_lo) < np.abs(gray - shade_hi), shade_lo, shade_hi)
    a = alpha[semi][:, None]
    b = b_val[semi][:, None]
    f = (arr[semi] - (1.0 - a) * b) / np.maximum(a, 0.1)
    out_rgb = arr.copy()
    out_rgb[semi] = np.clip(f, 0, 255)

    rgba = np.dstack([out_rgb.astype(np.uint8), (alpha * 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(dst)
    print(f"bg shades: {shade_lo:.0f}/{shade_hi:.0f}, fg px: {int(fg.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
