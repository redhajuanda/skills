#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path


for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


@dataclass
class Component:
    index: int
    x: int
    y: int
    width: int
    height: int
    pixels: int
    members: list[int] = field(default_factory=list, repr=False)


@dataclass(frozen=True)
class RGB:
    r: int
    g: int
    b: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split one transparent PNG into multiple cropped PNGs."
    )
    parser.add_argument("input_png", help="Path to the source PNG")
    parser.add_argument(
        "--output-dir",
        help="Directory for extracted PNG files. Defaults to <input-stem>_split beside the source file.",
    )
    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=1,
        help="Minimum alpha value (0-255) considered visible. Default: 1",
    )
    parser.add_argument(
        "--min-pixels",
        type=int,
        default=64,
        help="Skip connected components with fewer visible pixels. Default: 64",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        default=1,
        help="Skip connected components narrower than this. Default: 1",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        default=1,
        help="Skip connected components shorter than this. Default: 1",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=0,
        help="Extra pixels to keep around each extracted component. Default: 0",
    )
    parser.add_argument(
        "--background-mode",
        choices=("alpha", "auto"),
        default="alpha",
        help="`alpha` uses transparency only. `auto` also removes edge-connected near-background colors for opaque images. Default: alpha",
    )
    parser.add_argument(
        "--background-threshold",
        type=int,
        default=18,
        help="Color distance threshold used by `--background-mode auto`. Default: 18",
    )
    return parser


def ensure_magick() -> None:
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick CLI not found. Install `magick` and try again.")


def read_image_size(input_png: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["magick", "identify", "-format", "%w %h", str(input_png)],
        check=True,
        capture_output=True,
        text=True,
    )
    width_str, height_str = result.stdout.strip().split()
    return int(width_str), int(height_str)


def read_alpha_channel(input_png: Path) -> tuple[int, int, bytes]:
    result = subprocess.run(
        ["magick", str(input_png), "-alpha", "extract", "pgm:-"],
        check=True,
        capture_output=True,
    )
    data = result.stdout
    if not data.startswith(b"P5"):
        raise RuntimeError("Unexpected alpha export format from ImageMagick.")

    tokens: list[bytes] = []
    cursor = 2
    while len(tokens) < 3:
        while cursor < len(data) and data[cursor] in b" \t\r\n":
            cursor += 1
        if cursor < len(data) and data[cursor] == ord("#"):
            while cursor < len(data) and data[cursor] != ord("\n"):
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and data[cursor] not in b" \t\r\n":
            cursor += 1
        tokens.append(data[start:cursor])
    while cursor < len(data) and data[cursor] in b" \t\r\n":
        cursor += 1

    width, height, max_value = (int(token) for token in tokens)
    if max_value > 255:
        raise RuntimeError("16-bit alpha channel is not supported by this script.")

    pixels = data[cursor:]
    expected = width * height
    if len(pixels) != expected:
        raise RuntimeError(
            f"Alpha channel size mismatch. Expected {expected} bytes, got {len(pixels)}."
        )
    return width, height, pixels


def read_rgb_pixels(input_png: Path) -> tuple[int, int, bytes]:
    result = subprocess.run(
        ["magick", str(input_png), "ppm:-"],
        check=True,
        capture_output=True,
    )
    data = result.stdout
    if not data.startswith(b"P6"):
        raise RuntimeError("Unexpected RGB export format from ImageMagick.")

    tokens: list[bytes] = []
    cursor = 2
    while len(tokens) < 3:
        while cursor < len(data) and data[cursor] in b" \t\r\n":
            cursor += 1
        if cursor < len(data) and data[cursor] == ord("#"):
            while cursor < len(data) and data[cursor] != ord("\n"):
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and data[cursor] not in b" \t\r\n":
            cursor += 1
        tokens.append(data[start:cursor])
    while cursor < len(data) and data[cursor] in b" \t\r\n":
        cursor += 1

    width, height, max_value = (int(token) for token in tokens)
    if max_value > 255:
        raise RuntimeError("16-bit RGB export is not supported by this script.")

    pixels = data[cursor:]
    expected = width * height * 3
    if len(pixels) != expected:
        raise RuntimeError(
            f"RGB size mismatch. Expected {expected} bytes, got {len(pixels)}."
        )
    return width, height, pixels


def edge_seed_colors(width: int, height: int, rgb: bytes) -> list[RGB]:
    counts: dict[RGB, int] = {}

    def add_pixel(x: int, y: int) -> None:
        offset = (y * width + x) * 3
        color = RGB(rgb[offset], rgb[offset + 1], rgb[offset + 2])
        counts[color] = counts.get(color, 0) + 1

    for x in range(width):
        add_pixel(x, 0)
        add_pixel(x, height - 1)
    for y in range(1, height - 1):
        add_pixel(0, y)
        add_pixel(width - 1, y)

    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [color for color, _ in ordered[:8]]


def color_close(a: RGB, b: RGB, threshold: int) -> bool:
    return (
        abs(a.r - b.r) <= threshold
        and abs(a.g - b.g) <= threshold
        and abs(a.b - b.b) <= threshold
    )


def visible_from_auto_background(
    width: int,
    height: int,
    rgb: bytes,
    background_threshold: int,
) -> bytearray:
    seeds = edge_seed_colors(width, height, rgb)
    background = bytearray(width * height)
    queue: deque[int] = deque()

    for x in range(width):
        queue.append(x)
        queue.append((height - 1) * width + x)
    for y in range(1, height - 1):
        queue.append(y * width)
        queue.append(y * width + (width - 1))

    while queue:
        current = queue.popleft()
        if background[current]:
            continue
        offset = current * 3
        current_color = RGB(rgb[offset], rgb[offset + 1], rgb[offset + 2])
        if not any(color_close(current_color, seed, background_threshold) for seed in seeds):
            continue

        background[current] = 1
        x = current % width
        y = current // width
        for ny in range(max(0, y - 1), min(height - 1, y + 1) + 1):
            row_offset = ny * width
            for nx in range(max(0, x - 1), min(width - 1, x + 1) + 1):
                neighbor = row_offset + nx
                if not background[neighbor]:
                    queue.append(neighbor)

    return bytearray(0 if is_background else 1 for is_background in background)


def find_components(
    width: int,
    height: int,
    visible: bytearray,
    min_pixels: int,
    min_width: int,
    min_height: int,
) -> list[Component]:
    visited = bytearray(width * height)
    components: list[Component] = []
    index = 0

    for start in range(width * height):
        if not visible[start] or visited[start]:
            continue

        visited[start] = 1
        queue: deque[int] = deque([start])
        min_x = max_x = start % width
        min_y = max_y = start // width
        pixels = 0
        members: list[int] = []

        while queue:
            current = queue.popleft()
            x = current % width
            y = current // width
            pixels += 1
            members.append(current)

            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            for ny in range(max(0, y - 1), min(height - 1, y + 1) + 1):
                row_offset = ny * width
                for nx in range(max(0, x - 1), min(width - 1, x + 1) + 1):
                    neighbor = row_offset + nx
                    if visited[neighbor] or not visible[neighbor]:
                        continue
                    visited[neighbor] = 1
                    queue.append(neighbor)

        component_width = max_x - min_x + 1
        component_height = max_y - min_y + 1
        if pixels < min_pixels or component_width < min_width or component_height < min_height:
            continue

        index += 1
        components.append(
            Component(
                index=index,
                x=min_x,
                y=min_y,
                width=component_width,
                height=component_height,
                pixels=pixels,
                members=members,
            )
        )

    return components


def apply_padding(component: Component, image_width: int, image_height: int, padding: int) -> Component:
    left = max(0, component.x - padding)
    top = max(0, component.y - padding)
    right = min(image_width, component.x + component.width + padding)
    bottom = min(image_height, component.y + component.height + padding)
    return Component(
        index=component.index,
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
        pixels=component.pixels,
        members=component.members,
    )


def build_mask(component: Component, image_width: int, mask_source: bytes) -> bytes:
    # Mask value comes from mask_source (original alpha in alpha-mode, so soft edges
    # survive) for the component's own pixels, 0 for everything else in the crop
    # rectangle. CopyOpacity then drops neighboring objects that merely overlap this
    # component's bounding box.
    local = bytearray(component.width * component.height)
    for offset in component.members:
        gx = offset % image_width
        gy = offset // image_width
        lx = gx - component.x
        ly = gy - component.y
        if 0 <= lx < component.width and 0 <= ly < component.height:
            local[ly * component.width + lx] = mask_source[offset]
    header = f"P5\n{component.width} {component.height}\n255\n".encode("ascii")
    return header + bytes(local)


def write_component_pngs(
    input_png: Path,
    output_dir: Path,
    components: list[Component],
    image_width: int,
    mask_source: bytes,
) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for component in components:
        output_path = output_dir / f"{input_png.stem}_{component.index:03d}.png"
        crop = f"{component.width}x{component.height}+{component.x}+{component.y}"
        subprocess.run(
            [
                "magick",
                str(input_png),
                "-crop",
                crop,
                "+repage",
                "pgm:-",
                "-compose",
                "CopyOpacity",
                "-composite",
                str(output_path),
            ],
            input=build_mask(component, image_width, mask_source),
            check=True,
        )
        manifest.append(
            {
                "index": component.index,
                "file": output_path.name,
                "path": str(output_path),
                "bbox": {
                    "x": component.x,
                    "y": component.y,
                    "width": component.width,
                    "height": component.height,
                },
                "pixels": component.pixels,
            }
        )
    return manifest


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_png = Path(args.input_png).expanduser().resolve()
    if not input_png.exists():
        print(f"Input file not found: {input_png}", file=sys.stderr)
        return 1
    if input_png.suffix.lower() != ".png":
        print("Input must be a PNG file.", file=sys.stderr)
        return 1

    ensure_magick()

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_png.with_name(f"{input_png.stem}_split")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    width, height = read_image_size(input_png)
    alpha_width, alpha_height, alpha = read_alpha_channel(input_png)
    if (width, height) != (alpha_width, alpha_height):
        print("Image dimension mismatch while reading alpha channel.", file=sys.stderr)
        return 1

    if args.background_mode == "auto":
        rgb_width, rgb_height, rgb = read_rgb_pixels(input_png)
        if (width, height) != (rgb_width, rgb_height):
            print("Image dimension mismatch while reading RGB pixels.", file=sys.stderr)
            return 1
        visible = visible_from_auto_background(
            width=width,
            height=height,
            rgb=rgb,
            background_threshold=max(0, min(255, args.background_threshold)),
        )
    else:
        visible = bytearray(
            1 if value >= max(0, min(255, args.alpha_threshold)) else 0 for value in alpha
        )

    components = find_components(
        width=width,
        height=height,
        visible=visible,
        min_pixels=max(1, args.min_pixels),
        min_width=max(1, args.min_width),
        min_height=max(1, args.min_height),
    )
    if not components:
        print("No visible components found. Check transparency or lower the thresholds.", file=sys.stderr)
        return 2

    padded_components = [
        apply_padding(component, width, height, max(0, args.padding))
        for component in components
    ]
    # Members are guaranteed visible; in alpha-mode alpha carries soft edges, in
    # auto-mode the source may be fully opaque so force full opacity for members.
    mask_source = alpha if args.background_mode == "alpha" else b"\xff" * (width * height)
    manifest = write_component_pngs(input_png, output_dir, padded_components, width, mask_source)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Extracted {len(manifest)} component(s) to {output_dir}")
    print(f"Manifest: {manifest_path}")
    for item in manifest:
        bbox = item["bbox"]
        print(
            f"- {item['file']}: {bbox['width']}x{bbox['height']}+{bbox['x']}+{bbox['y']} "
            f"pixels={item['pixels']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
