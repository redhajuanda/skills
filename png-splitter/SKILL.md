---
name: png-splitter
description: Split one PNG with a transparent background into multiple standalone PNG files by detecting disconnected visible regions. Use when a source image contains several separate objects or stickers on transparency and each object should become its own cropped PNG.
---

# PNG Splitter

Use this skill when the user has one PNG with multiple disconnected objects on a transparent background and wants each object exported as its own PNG.

## Workflow

1. Confirm the source file path.
2. Check whether the image already has real transparency: `magick identify -format "%A" input.png` (prints `True`/`Blend` if an alpha channel is present). If it does, skip the matting/background-removal step entirely — go straight to step 3 on the original file.
3. From this skill directory, run the CLI:

```bash
python3 -m scripts /absolute/path/to/input.png
```

3. If the user needs tuning, rerun with flags such as:

```bash
python3 -m scripts /absolute/path/to/input.png --padding 24 --min-pixels 400 --alpha-threshold 8
```

## Behavior

- Requires `magick` (ImageMagick CLI) on `PATH`.
- Detects connected components from the PNG alpha channel.
- Exports each kept component as a tightly cropped PNG with optional padding.
- Writes files to a sibling directory named `<input-stem>_split/` unless `--output-dir` is provided.
- Emits `manifest.json` with bounding boxes and output paths.

## Tuning Notes

- Raise `--min-pixels` to drop dust or tiny fragments.
- Raise `--alpha-threshold` when soft shadows or nearly invisible pixels should be ignored.
- Raise `--padding` when the crops feel too tight.
- Only run background removal/matting when the image has no real alpha transparency (an opaque PNG, or one with a fake baked-in checkerboard pattern). If the alpha channel already carries real transparency, matting is unnecessary — split it directly.
- If the image has no transparency but a fake checkerboard background (baked-in checker pixels), run the bundled matting tool first, then split its output:

```bash
python3 scripts/removebg_ml.py /absolute/path/to/input.png /tmp/matted.png
python3 -m scripts /tmp/matted.png --alpha-threshold 8 --min-pixels 200 --padding 6
```

  `removebg_ml.py` = classical checker matte (`removebg.py`) to locate components, then per-component BiRefNet matting (rembg `birefnet-general`, ~1GB model, auto-downloaded) for large objects, plus a cluster pass that groups small comps (text glyphs, thin ornaments) and mattes each cluster as one subject. Photoroom-level output. Requires `numpy`, `pillow`, `scipy`, `rembg`, `onnxruntime`. Use plain `scripts/removebg.py` if the ML deps are unavailable — noticeably rougher edges and pale leftovers.
- Never run full-sheet ML background removal on a sprite sheet: salient-object models keep only the "main" subject and drop the rest.
- If the image has a photographic background, use an ML background-removal workflow per object instead.
