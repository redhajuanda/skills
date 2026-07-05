---
name: image-decomposer
description: Generate a copy-paste prompt for AI image generators (ChatGPT, Gemini, etc.) that decomposes a single illustration into animation-ready layers - one static background plate plus individual transparent-PNG cutouts of every movable element. Use this skill whenever the user wants to split, strip, un-layer, or decompose an image into separate objects/assets/sprites/layers, wants a sprite sheet or asset breakdown from an illustration, wants to prepare an image for parallax or motion graphics animation, or asks for "the decomposition prompt" / "the asset extraction prompt". Also use it when the user shows a decomposition result and asks to fix issues like duplicated elements, wrong background contents, or merged assets.
---

# Image Asset Decomposer

This skill produces a battle-tested prompt that instructs an AI image generator to break a single illustration into compositing-ready layers: **one background plate** + **individual cutout assets** on a transparent canvas. The typical use case is preparing a static illustration (e.g., a wedding invitation, poster, or scene) for animation, where side elements sway, characters move, and the background stays still.

## How to use this skill

1. Output the canonical prompt below inside a plain fenced code block (```) so the user can copy it in one tap. Do not wrap it in blockquotes or add markdown bold inside it unless the user asks.
2. If the user has shown you the specific image, you may append one short image-specific line at the end of the prompt (see "Per-image customization"), but keep the core prompt unchanged.
3. If the user reports a bad result, diagnose it using the "Known failure modes" section and patch the prompt accordingly rather than rewriting from scratch.

## The canonical prompt

```
Take this image and decompose it into separate assets, like a sprite sheet / asset breakdown, split into two categories: one background plate and individual foreground/side objects.

Strict rules:

1. Do not change any detail. Every asset must look exactly identical to how it appears in the input image — same art style, same colors, same line work, same textures, same proportions. Do not redraw, restyle, simplify, or "improve" anything.

2. The background is ONE single asset in the same aspect ratio as the input image. It must be a full edge-to-edge plate containing ONLY the static, structural, and environmental elements of the scene — for example: the sky or backdrop texture, distant scenery and architecture, the ground, floors, walls, water surfaces, stairs, fences, railings, and any other large fixed structures that objects stand on or in front of. Keep all of these in their exact original positions.

3. Everything else is an individual object. Extract each distinct movable or decorative element as its own separate asset, because they will be animated individually. This includes things like: characters/people, animals, individual trees and plants at the sides or edges, hanging branches or foliage in the corners, flowers, decorative ornaments, props, and any text or typography elements. Complete any occluded parts of each object plausibly, keeping visible parts pixel-faithful to the original.

4. CRITICAL — no duplication between categories. Every element exists in EXACTLY ONE place: either in the background plate or as an individual asset, never both. Any element extracted as an individual asset must be completely REMOVED from the background plate. Where a removed element was covering the background, fill that empty area with a plausible continuation of the surrounding scenery only (sky, water, ground, distant foliage) — never repaint, redraw, or leave any trace of the removed element itself in the background.

5. The deciding rule: if an element is part of the environment or structure (something things stand on, lean against, or that frames the scene as fixed scenery), it belongs in the background plate. If an element sits on top of the scene and could plausibly move, sway, or be repositioned independently (living things, plants, decorations, text), it becomes an individual asset and must be absent from the background.

6. Sensible grouping is allowed within a single visual unit. For example: a person together with their outfit and accessories, a flower with its own leaves, a pot with the plant growing in it, or an ornamental frame with its flourishes. But do not merge separate elements together — each tree, each plant cluster, each prop must remain its own asset so it can move independently.

7. Include everything. Every element visible in the input must exist somewhere in the output — either inside the background plate or as an individual object. Do not skip anything, and do not include anything twice.

8. Output format: One single large PNG with a plain pure white background (#FFFFFF) — a flat solid white canvas, not a checkerboard pattern and not transparency. The background plate is placed as one asset, and every individual object is a clean cutout laid out separately with clear spacing — no asset may touch or overlap another asset. No added shadows, outlines, halos, or any new elements.

Think of it as preparing layers for an animated composition, laid out on a clean white canvas: when all the individual cutouts are placed back on top of the background plate in their original positions, the result recomposes the original image exactly — with no doubled elements.
```

## Per-image customization

The prompt is intentionally general (rule 5 is the decision principle). When the user wants specific elements sorted differently, append ONE line at the end instead of editing the rules:

- Force into background: `For this image, also include the [pond, stairs, railing] in the background plate.`
- Force into individual assets: `For this image, extract the [waterfall / clouds] as individual assets even though they are environmental.`
- Fixed output ratio: if the user needs a specific ratio (e.g., 9:16 for reels/stories), change "in the same aspect ratio as the input image" in rule 2 to "in 9:16 ratio" and mention the ratio again in the closing line.

## Known failure modes and fixes

- **Elements appear in BOTH the background and as cutouts.** The most common failure. Cause: the model satisfies "background looks like the input" and "objects are extracted" independently. Fix: rule 4 (mutual exclusivity) plus the recomposition framing in the closing line already guard against this. If it still happens, reply to the generator with: "Elements X, Y appear both in the background plate and as individual assets. Remove them from the background plate and fill the gaps with surrounding scenery only."
- **Checkerboard instead of white.** Some generators render a fake checkerboard "transparency" pattern instead of the requested flat white canvas. Fix: reply with "The canvas must be flat solid white (#FFFFFF), not a checkerboard pattern — regenerate with a plain white background." Note the white canvas is intentional: it is easy to strip locally afterward for real transparency (`rembg`, or ImageMagick `convert in.png -fuzz 5% -transparent white out.png`) — but this only works cleanly for assets that contain no white/near-white areas themselves; use `rembg` for those.
- **Over-grouping.** Small items (individual flowers, lily pads) get merged into one cluster. Follow up with: "Some objects were grouped together — separate them further: each [flower/tree/ornament] as its own isolated asset."
- **Missing elements.** Dense illustrations lose small background-level items. Follow up with a checklist of what you can see so the model can verify coverage.
- **Restyled assets.** The cutouts come back in a slightly different art style. Re-emphasize rule 1 and ask for a redo of the specific assets, attaching the original image again.

## Iterating instead of re-running

When the user already has a mostly-good result, prefer a targeted follow-up message to the image generator over re-running the full prompt — this preserves the assets that already came out right. Describe only the delta, e.g.: "Redo the background plate: merge the pond water, stone steps, and railing into it at their original positions, and remove them from the individual assets."
