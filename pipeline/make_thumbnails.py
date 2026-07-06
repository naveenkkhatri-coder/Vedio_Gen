#!/usr/bin/env python3
"""Generate YouTube thumbnail variants (1280x720 JPG) with Pillow.

Usage: python3 make_thumbnails.py outdir
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(c1, c2, diagonal=False):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(0, W, 4):
            t = (x / W + y / H) / 2 if diagonal else y / H
            for dx in range(4):
                if x + dx < W:
                    px[x + dx, y] = tuple(
                        int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
    return img.convert("RGBA")


def emoji(char, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 10), char, font=f, embedded_color=True)
    box = img.getbbox()
    return img.crop(box).resize((size, size), Image.LANCZOS)


def big_text(d, xy, text, size, fill, stroke=10):
    f = ImageFont.truetype(FONT, size)
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke,
           stroke_fill=(0, 0, 0))


def arrow(d, tail, head, width=26, color=(255, 30, 30)):
    """Straight fat arrow with a triangular head."""
    import math
    dx, dy = head[0] - tail[0], head[1] - tail[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    px_, py_ = -uy, ux
    hl, hw = 70, 62  # head length/half-width
    bx, by = head[0] - ux * hl, head[1] - uy * hl
    d.line([tail, (bx, by)], fill=color, width=width)
    d.polygon([(head[0], head[1]),
               (bx + px_ * hw, by + py_ * hw),
               (bx - px_ * hw, by - py_ * hw)], fill=color)


def vignette(img):
    ov = Image.new("L", (W, H), 0)
    od = ImageDraw.Draw(ov)
    od.rectangle([0, 0, W, H], fill=70)
    od.ellipse([-W * 0.25, -H * 0.25, W * 1.25, H * 1.25], fill=0)
    ov = ov.filter(ImageFilter.GaussianBlur(80))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    return Image.composite(black, img, ov)


def save(img, path):
    img.convert("RGB").save(path, "JPEG", quality=90)
    print(path)


def variant_a(out):
    """Square waves: 'IF THE SEA LOOKS LIKE THIS' + arrow + GET OUT NOW"""
    img = gradient(hex_rgb("#0B7285"), hex_rgb("#083358"))
    d = ImageDraw.Draw(img)
    # checkerboard "square waves" field, lower right
    tile = 74
    for r in range(5):
        for c in range(9):
            x0 = 560 + c * tile - r * 8
            y0 = 330 + r * tile
            if (r + c) % 2 == 0:
                d.rectangle([x0, y0, x0 + tile - 6, y0 + tile - 6],
                            fill=(13, 60, 96, 255), outline=(160, 220, 240),
                            width=4)
            else:
                d.rectangle([x0, y0, x0 + tile - 6, y0 + tile - 6],
                            fill=(32, 130, 180, 255), outline=(160, 220, 240),
                            width=4)
    img.alpha_composite(emoji("🌊", 210), (1030, 120))
    img = vignette(img)
    d = ImageDraw.Draw(img)
    big_text(d, (46, 42), "IF THE SEA", 108, (255, 255, 255))
    big_text(d, (46, 168), "LOOKS LIKE THIS", 108, (255, 224, 27))
    arrow(d, (330, 330), (560, 450))
    big_text(d, (46, 520), "GET OUT NOW!", 128, (255, 59, 48))
    save(img, out / "thumb_A_square_waves.jpg")


def variant_b(out):
    """List promise: 7 WARNING SIGNS NATURE SENDS FIRST"""
    img = gradient(hex_rgb("#101A3C"), hex_rgb("#2B1E66"), diagonal=True)
    d = ImageDraw.Draw(img)
    # giant number 7 plate
    d.rounded_rectangle([880, 90, 1210, 630], radius=48,
                        fill=(255, 224, 27, 255))
    f7 = ImageFont.truetype(FONT, 430)
    bb = d.textbbox((0, 0), "7", font=f7)
    d.text((1045 - (bb[2] - bb[0]) / 2 - bb[0], 360 - (bb[3] - bb[1]) / 2 - bb[1]),
           "7", font=f7, fill=(16, 26, 60), stroke_width=0)
    img.alpha_composite(emoji("⚠️", 190), (60, 60))
    img = vignette(img)
    d = ImageDraw.Draw(img)
    big_text(d, (280, 90), "WARNING", 120, (255, 224, 27))
    big_text(d, (60, 280), "SIGNS NATURE", 100, (255, 255, 255))
    big_text(d, (60, 400), "SENDS BEFORE", 100, (255, 255, 255))
    big_text(d, (60, 520), "DISASTER", 120, (255, 59, 48))
    save(img, out / "thumb_B_seven_signs.jpg")


def variant_c(out):
    """Backyard sinkhole: DEAD GRASS CIRCLE? + house emoji"""
    img = gradient(hex_rgb("#38731C"), hex_rgb("#1E3D12"))
    d = ImageDraw.Draw(img)
    # lawn with a dead ring
    d.ellipse([700, 300, 1200, 640], fill=(158, 134, 62, 255))
    d.ellipse([790, 360, 1110, 580], fill=(72, 105, 38, 255))
    d.ellipse([900, 430, 1000, 500], fill=(40, 32, 20, 255))
    img.alpha_composite(emoji("🏠", 170), (740, 120))
    img = vignette(img)
    d = ImageDraw.Draw(img)
    # red alert ring on the dead patch
    d.ellipse([690, 290, 1210, 650], outline=(255, 40, 40), width=14)
    big_text(d, (46, 60), "THIS IN YOUR", 104, (255, 255, 255))
    big_text(d, (46, 184), "BACKYARD?", 116, (255, 224, 27))
    arrow(d, (500, 420), (690, 470))
    big_text(d, (46, 520), "ASK FOR HELP!", 118, (255, 59, 48))
    save(img, out / "thumb_C_backyard.jpg")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "thumbnails")
    out.mkdir(parents=True, exist_ok=True)
    variant_a(out)
    variant_b(out)
    variant_c(out)
