#!/usr/bin/env python3
"""Free, fully-local faceless-video renderer.

Turns a script JSON (scenes with narration + card design) into a 1080p MP4:
  - voiceover:  pico2wave (offline TTS), espeak-ng fallback
  - visuals:    Pillow-drawn 2400x1350 scene cards, animated with ffmpeg
                zoompan (Ken Burns), joined with xfade transitions
  - music bed:  soft synth pad generated with numpy
  - assembly:   ffmpeg, H.264 + AAC

Usage:  python3 render_video.py script.json output.mp4 [workdir]
"""

import json
import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CARD_W, CARD_H = 2400, 1350          # oversized for smooth Ken Burns
FADE = 0.5                           # xfade duration between scenes
VO_LEAD = 0.6                        # silence before narration in a scene
VO_TAIL = 1.2                        # silence after narration
SR = 44100

FONT_DIRS = [
    "/usr/share/fonts/opentype/inter",
    "/usr/share/fonts/truetype/dejavu",
]
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def find_font(names, fallback="DejaVuSans-Bold.ttf"):
    for d in FONT_DIRS:
        for n in names + [fallback]:
            p = Path(d) / n
            if p.exists():
                return str(p)
    raise FileNotFoundError(f"none of {names} found")


FONT_BLACK = find_font(["Inter-Black.otf", "Inter-ExtraBold.otf"])
FONT_BOLD = find_font(["Inter-Bold.otf", "Inter-SemiBold.otf"])


def run(cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


# ---------------------------------------------------------------- voiceover

def tts(text, out_wav):
    """Offline TTS: pico2wave preferred, espeak-ng fallback."""
    if shutil.which("pico2wave"):
        run(["pico2wave", "-l", "en-US", "-w", str(out_wav), text])
    else:
        run(["espeak-ng", "-v", "en-us", "-s", "160", "-w", str(out_wav), text])


# ---------------------------------------------------------------- music bed

def make_music(duration, out_wav):
    """Soft ambient pad: slow chord progression, sines with gentle overtones."""
    import numpy as np

    chords = [  # frequencies (Hz): C, A minor, F, G — a warm loop
        [130.81, 164.81, 196.00, 261.63],
        [110.00, 130.81, 164.81, 220.00],
        [87.31, 130.81, 174.61, 220.00],
        [98.00, 123.47, 146.83, 196.00],
    ]
    bar = 4.0
    n = int(duration * SR)
    audio = np.zeros(n, dtype=np.float64)
    t_bar = np.arange(int(bar * SR)) / SR
    # attack/release envelope for each bar so chords swell instead of click
    env = np.minimum(1.0, np.minimum(t_bar / 0.8, (bar - t_bar) / 0.8)) ** 1.5
    for i in range(math.ceil(duration / bar)):
        chord = chords[i % len(chords)]
        seg = np.zeros_like(t_bar)
        for f in chord:
            seg += np.sin(2 * np.pi * f * t_bar)
            seg += 0.35 * np.sin(2 * np.pi * f * 2.003 * t_bar)  # soft octave
        seg *= env / (len(chord) * 1.35)
        start = int(i * bar * SR)
        end = min(n, start + len(seg))
        audio[start:end] += seg[: end - start]
    # global fade in/out
    fade_n = int(2.5 * SR)
    audio[:fade_n] *= np.linspace(0, 1, fade_n)
    audio[-fade_n:] *= np.linspace(1, 0, fade_n)
    pcm = (np.clip(audio, -1, 1) * 32767 * 0.14).astype("<i2")  # quiet bed
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- scene card

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_emoji(char, size):
    """Noto Color Emoji is a bitmap font with a single 109px strike."""
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((10, 10), char, font=f, embedded_color=True)
        box = img.getbbox()
        if not box:
            return None
        return img.crop(box).resize((size, size), Image.LANCZOS)
    except Exception:
        return None


def wrap_center(draw, lines, font, cy, fill, spacing=1.12, shadow=True):
    heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    line_h = max(heights) * spacing
    total = line_h * len(lines)
    y = cy - total / 2
    for ln in lines:
        w = draw.textbbox((0, 0), ln, font=font)[2]
        x = (CARD_W - w) / 2
        if shadow:
            draw.text((x + 5, y + 7), ln, font=font, fill=(0, 0, 0, 110))
        draw.text((x, y), ln, font=font, fill=fill)
        y += line_h


def make_card(scene, index, total, out_png):
    c1, c2 = hex_rgb(scene["colors"][0]), hex_rgb(scene["colors"][1])
    img = Image.new("RGB", (CARD_W, CARD_H))
    px = img.load()
    for y in range(CARD_H):  # vertical gradient
        t = y / CARD_H
        row = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        for x in range(0, CARD_W, 1):
            px[x, y] = row
    img = img.convert("RGBA")

    # decorative translucent circles
    deco = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    for (cx, cy, r, a) in [(180, 1180, 420, 26), (2260, 160, 360, 22),
                           (2150, 1250, 260, 30), (300, 120, 200, 18)]:
        dd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, a))
    img = Image.alpha_composite(img, deco.filter(ImageFilter.GaussianBlur(6)))

    # translucent shapes go on their own layer: ImageDraw writes RGBA values
    # verbatim (no blending), so drawing them straight onto the card would
    # come out opaque after the final RGB convert
    ov = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    meas = ImageDraw.Draw(img)

    # channel tag chip (top center)
    tag = scene.get("tag", "NATURE WARNING SIGNS")
    f_tag = ImageFont.truetype(FONT_BOLD, 44)
    tw = meas.textbbox((0, 0), tag, font=f_tag)[2]
    pad = 34
    x0 = (CARD_W - tw) / 2 - pad
    od.rounded_rectangle([x0, 92, x0 + tw + 2 * pad, 92 + 84], radius=42,
                         fill=(255, 255, 255, 46))

    # number badge circle
    badge = scene["badge"]
    br = 150
    bx, by = CARD_W / 2, 400
    od.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 255, 255, 240))

    # action strip pill
    action = scene.get("action")
    if action:
        f_act = ImageFont.truetype(FONT_BOLD, 58)
        aw = meas.textbbox((0, 0), action, font=f_act)[2]
        apad = 44
        ax0 = (CARD_W - aw) / 2 - apad
        od.rounded_rectangle([ax0, 990, ax0 + aw + 2 * apad, 990 + 116],
                             radius=58, fill=(0, 0, 0, 90))

    # progress dots (current one bigger and brighter)
    n = total
    dot_r, gap = 11, 44
    row_w = n * 2 * dot_r + (n - 1) * (gap - 2 * dot_r)
    sx = (CARD_W - row_w) / 2
    for i in range(n):
        cx = sx + i * gap + dot_r
        r = 15 if i == index else dot_r
        a = 255 if i == index else 90
        od.ellipse([cx - r, 1230 - r, cx + r, 1230 + r],
                   fill=(255, 255, 255, a))

    img = Image.alpha_composite(img, ov)

    # emoji flanking the badge
    em = draw_emoji(scene.get("emoji", ""), 300)
    if em is not None:
        img.alpha_composite(em, (int(bx) + 330, int(by) - 150))
        img.alpha_composite(em.transpose(Image.FLIP_LEFT_RIGHT),
                            (int(bx) - 330 - 300, int(by) - 150))

    # opaque text on top
    d = ImageDraw.Draw(img)
    d.text(((CARD_W - tw) / 2, 108), tag, font=f_tag, fill=(255, 255, 255))
    f_badge = ImageFont.truetype(FONT_BLACK, 170 if len(badge) == 1 else 120)
    bb = d.textbbox((0, 0), badge, font=f_badge)
    d.text((bx - (bb[2] - bb[0]) / 2 - bb[0], by - (bb[3] - bb[1]) / 2 - bb[1]),
           badge, font=f_badge, fill=hex_rgb(scene["colors"][0]))
    f_title = ImageFont.truetype(FONT_BLACK, 128)
    wrap_center(d, scene["title"].split("\n"), f_title, 760, (255, 255, 255, 255))
    if action:
        d.text(((CARD_W - aw) / 2, 1016), action, font=f_act,
               fill=(255, 255, 255, 245))

    img.convert("RGB").save(out_png, "PNG")


# ---------------------------------------------------------------- animation

KB_MODES = ["in", "out", "right", "left"]


def animate_card(png, seconds, mode, fps, w, h, out_mp4):
    frames = int(round(seconds * fps))
    if mode == "in":
        z = f"min(1+0.10*on/{frames},1.10)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "out":
        z = f"max(1.10-0.10*on/{frames},1.0)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z = "1.08"
        drift = f"(iw-iw/zoom)*on/{frames}"
        x = drift if mode == "right" else f"(iw-iw/zoom)-{drift}"
        y = "ih/2-(ih/zoom/2)"
    vf = (f"scale={CARD_W}:{CARD_H},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},"
          f"format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-vf", vf,
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "fast",
         "-crf", "18", str(out_mp4)])
    return frames / fps


# ---------------------------------------------------------------- main

def main():
    script_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    work = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("work")
    work.mkdir(parents=True, exist_ok=True)

    spec = json.loads(script_path.read_text())
    scenes = spec["scenes"]
    fps, w, h = spec.get("fps", 30), spec.get("width", 1920), spec.get("height", 1080)

    # 1) voiceover + cards + animated clips per scene
    durs, clips, vo_files = [], [], []
    for i, sc in enumerate(scenes):
        sc.setdefault("tag", spec.get("channel_tag", ""))
        vo = work / f"vo_{i:02d}.wav"
        tts(sc["narration"], vo)
        vo_len = ffprobe_duration(vo)
        scene_len = VO_LEAD + vo_len + VO_TAIL
        card = work / f"card_{i:02d}.png"
        make_card(sc, i, len(scenes), card)
        clip = work / f"clip_{i:02d}.mp4"
        d = animate_card(card, scene_len, KB_MODES[i % len(KB_MODES)],
                         fps, w, h, clip)
        durs.append(d)
        clips.append(clip)
        vo_files.append(vo)
        print(f"scene {i:02d} [{sc['id']}] vo={vo_len:.1f}s scene={d:.1f}s",
              flush=True)

    # 2) video: xfade chain
    total = sum(durs) - FADE * (len(durs) - 1)
    print(f"total video: {total:.1f}s", flush=True)
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    fc, prev, off = [], "0:v", 0.0
    for i in range(1, len(clips)):
        off += durs[i - 1] - FADE
        lab = f"v{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={FADE}:"
                  f"offset={off:.3f}[{lab}]")
        prev = lab
    # pin 4:2:0 — xfade can negotiate yuv444p, which most players can't decode
    fc.append(f"[{prev}]format=yuv420p[vout]")
    silent = work / "video_only.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
         "-map", "[vout]", "-c:v", "libx264", "-preset", "medium",
         "-crf", "19", "-profile:v", "high", str(silent)])

    # 3) audio: VO placed at each scene's start + music bed underneath
    music = work / "music.wav"
    make_music(total, music)
    a_in, a_fc, mix = [], [], []
    starts, t = [], 0.0
    for i, d in enumerate(durs):
        starts.append(t)
        t += d - FADE
    for i, vo in enumerate(vo_files):
        a_in += ["-i", str(vo)]
        ms = int((starts[i] + VO_LEAD) * 1000)
        a_fc.append(f"[{i}:a]aresample={SR},adelay={ms}|{ms}[a{i}]")
        mix.append(f"[a{i}]")
    a_fc.append(f"[{len(vo_files)}:a]aresample={SR}[bed]")
    mix.append("[bed]")
    a_fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0,"
                f"alimiter=limit=0.95[aout]")
    mixed = work / "audio.m4a"
    run(["ffmpeg", "-y", *a_in, "-i", str(music), "-filter_complex",
         ";".join(a_fc), "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{total:.3f}", str(mixed)])

    # 4) mux
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(mixed),
         "-c:v", "copy", "-c:a", "copy", "-shortest",
         "-movflags", "+faststart", str(out_path)])
    print(f"done: {out_path} ({ffprobe_duration(out_path):.1f}s)", flush=True)


if __name__ == "__main__":
    main()
