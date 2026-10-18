#!/usr/bin/env python3
"""OPTIONAL, one-time tool: turn tools/portrait-source.png (transparent cut-out) into data/portrait.txt.

build.py only reads data/portrait.txt, so this is NOT needed for normal updates.
Needs:  pip install pillow numpy opencv-python-headless
Usage:  python tools/make_portrait.py [--cols 56] [--crop 0.36 0 1 0.43]
Tip: a close-up headshot (PNG with transparent background) gives a much more recognisable result.
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
RAMP = " .'`^:;-~+=*xoO#%@"

ap = argparse.ArgumentParser()
ap.add_argument("--cols", type=int, default=56)
ap.add_argument("--crop", type=float, nargs=4, default=[0.36, 0.0, 1.0, 0.43],
                help="x0 y0 x1 y1 as fractions of the subject's bounding box")
ap.add_argument("--src", default=str(ROOT / "tools" / "portrait-source.png"))
args = ap.parse_args()

CW, RH = 6.0, 9.6  # glyph cell used by build.py
im = Image.open(args.src).convert("RGBA")
im = im.crop(im.split()[3].point(lambda v: 255 if v > 128 else 0).getbbox())
x0, y0, x1, y1 = args.crop
im = im.crop((int(im.width * x0), int(im.height * y0), int(im.width * x1), int(im.height * y1)))
alpha = im.split()[3]
rows = round(args.cols * (im.height / im.width) * (CW / RH))
lum = Image.fromarray(cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(np.asarray(im.convert("L"))))
edges = lum.filter(ImageFilter.FIND_EDGES)
size = (args.cols, rows)
L = np.asarray(lum.resize(size, Image.LANCZOS), dtype=float) / 255
E = np.asarray(edges.resize(size, Image.LANCZOS), dtype=float) / 255
A = np.asarray(alpha.resize(size, Image.LANCZOS), dtype=float) / 255
out = []
for y in range(rows):
    line = ""
    for x in range(args.cols):
        if A[y, x] < 0.45:
            line += " "
            continue
        d = min(0.999, max(0.0, 0.12 + 0.70 * L[y, x] ** 1.6 + 1.8 * E[y, x]))
        line += RAMP[int(d * (len(RAMP) - 1)) + 1 if d > 0.02 else 1]
    out.append(line.rstrip())
(ROOT / "data" / "portrait.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote data/portrait.txt ({args.cols}x{rows})")
