# png-splitter

Split one PNG with a transparent background into multiple standalone PNGs, one per disconnected visible object.

## Usage

```bash
python3 -m scripts /absolute/path/to/input.png
```

Outputs go to `<input-stem>_split/` (or `--output-dir`) alongside a `manifest.json` with bounding boxes.

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--output-dir` | `<input-stem>_split` | Where to write output PNGs |
| `--alpha-threshold` | `1` | Minimum alpha (0-255) counted as visible |
| `--min-pixels` | `64` | Drop components smaller than this (dust/fragments) |
| `--min-width` / `--min-height` | `1` | Drop components narrower/shorter than this |
| `--padding` | `0` | Extra pixels kept around each crop |
| `--background-mode` | `alpha` | `alpha` uses transparency; `auto` also strips near-background edge colors on opaque images |
| `--background-threshold` | `18` | Color distance used by `--background-mode auto` |

### Baked-in checkerboard background (no real transparency)

```bash
python3 scripts/removebg_ml.py /absolute/path/to/input.png /tmp/matted.png
python3 -m scripts /tmp/matted.png --alpha-threshold 8 --min-pixels 200 --padding 6
```

`removebg_ml.py` locates components via the classical checker matte, then runs per-component BiRefNet matting (rembg, ~1GB model) for photoroom-quality edges. Falls back to `scripts/removebg.py` alone if `numpy`/`pillow`/`scipy`/`rembg`/`onnxruntime` aren't available (rougher edges).

Don't run full-sheet ML background removal on a sprite sheet — salient-object models keep only the "main" subject and drop the rest.

## Requirements

- `magick` (ImageMagick CLI) on `PATH`.
- For ML matting: `numpy`, `pillow`, `scipy`, `rembg`, `onnxruntime`.

## Install

```bash
npx skills add redhajuanda/skills --skill png-splitter
```
