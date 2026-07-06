#!/usr/bin/env python3
"""Config-driven YouTube thumbnail generator (1280x720 JPG).

Usage: python3 make_thumb.py config.json out.jpg

Config:
{
  "bg": ["#101A3C", "#2B1E66"], "diagonal": true,
  "emojis": [{"char": "🐻", "size": 300, "x": 940, "y": 180}],
  "ring":  [690, 290, 1210, 650],            // optional red ellipse outline
  "arrow": {"tail": [330, 330], "head": [560, 450]},   // optional
  "lines": [{"text": "IF A BEAR CHARGES", "size": 100,
             "color": "#FFFFFF", "x": 46, "y": 60}]
}
"""

import json
import sys

from make_thumbnails import (W, H, arrow, big_text, emoji, gradient,
                             hex_rgb, save, vignette)
from PIL import ImageDraw


def main():
    cfg = json.loads(open(sys.argv[1]).read())
    out = sys.argv[2]

    img = gradient(hex_rgb(cfg["bg"][0]), hex_rgb(cfg["bg"][1]),
                   diagonal=cfg.get("diagonal", False))
    for e in cfg.get("emojis", []):
        img.alpha_composite(emoji(e["char"], e["size"]), (e["x"], e["y"]))
    img = vignette(img)
    d = ImageDraw.Draw(img)
    if "ring" in cfg:
        d.ellipse(cfg["ring"], outline=(255, 40, 40), width=14)
    if "arrow" in cfg:
        arrow(d, tuple(cfg["arrow"]["tail"]), tuple(cfg["arrow"]["head"]))
    for ln in cfg["lines"]:
        big_text(d, (ln["x"], ln["y"]), ln["text"], ln["size"],
                 hex_rgb(ln["color"]))
    save(img, out)


if __name__ == "__main__":
    main()
