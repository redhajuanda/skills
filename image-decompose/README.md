# image-asset-decomposer

Generates a copy-paste prompt for AI image generators (ChatGPT, Gemini, etc.) that decomposes one illustration into animation-ready layers: a single static background plate plus individual transparent-PNG cutouts of every movable element.

## Usage

Ask for it directly — no CLI, no scripts. The skill returns the canonical prompt in a fenced code block, ready to paste into an image generator.

Trigger it when you want to:
- Split, strip, un-layer, or decompose an image into separate objects/assets/sprites/layers
- Get a sprite sheet or asset breakdown from an illustration
- Prepare a static image for parallax or motion graphics animation
- Fix a bad decomposition result (duplicated elements, wrong background contents, merged assets)

## What it does

- Outputs one background plate (static/structural scene elements) and one cutout per movable/decorative element, laid out on a flat white canvas.
- Guards against the most common failure: elements appearing in both the background and as cutouts.
- Supports per-image tweaks (force an element into the background or into its own asset, or fix the output aspect ratio) by appending one line instead of rewriting the prompt.
- Diagnoses and patches known failure modes: checkerboard canvas instead of white, over-grouped elements, missing elements, restyled cutouts.

## Install

```bash
npx skills add redhajuanda/skills --skill image-decompose
```
