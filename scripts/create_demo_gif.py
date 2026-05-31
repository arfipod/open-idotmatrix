#!/usr/bin/env python3
"""Create a tiny 32x32 demo GIF for upload/simulation tests."""

from pathlib import Path

from PIL import Image, ImageDraw

out = Path("out/demo_32.gif")
out.parent.mkdir(parents=True, exist_ok=True)
frames = []
for i in range(16):
    img = Image.new("RGB", (32, 32), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((i, i, 31 - i, 31 - i), outline=(255, 255 - i * 8, i * 8))
    draw.ellipse((i, 15, i + 4, 19), fill=(255, 0, 0))
    frames.append(img)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=80, loop=0)
print(out)
