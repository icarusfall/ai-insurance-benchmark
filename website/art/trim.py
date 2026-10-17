"""Trim transparent margins from the rendered PNGs (run after make_art.py; needs Pillow)."""
import glob
import os

from PIL import Image

PAD = 12
for p in glob.glob(os.path.join(os.path.dirname(__file__), "..", "public", "img", "*.png")):
    im = Image.open(p).convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if box:
        l, t, r, b = box
        im = im.crop((max(0, l - PAD), max(0, t - PAD), min(im.width, r + PAD), min(im.height, b + PAD)))
    im.save(p, optimize=True)
    print(os.path.basename(p), im.size, f"{os.path.getsize(p) // 1024} KB")
