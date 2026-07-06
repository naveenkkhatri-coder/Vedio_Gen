#!/usr/bin/env python3
"""Generate an SRT caption file from a script JSON and a render workdir.

Reads the actual per-scene voiceover WAVs (vo_NN.wav) to get exact timing,
splits each scene's narration into sentences, and distributes each scene's
spoken window across its sentences proportionally to word count.

Usage: python3 make_captions.py script.json workdir out.srt
"""

import json
import re
import subprocess
import sys
from pathlib import Path

FADE = 0.5
VO_LEAD = 0.6
VO_TAIL = 1.2


def dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    script, work, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    scenes = json.loads(script.read_text())["scenes"]

    entries, idx, t_scene = [], 1, 0.0
    for i, sc in enumerate(scenes):
        vo_len = dur(work / f"vo_{i:02d}.wav")
        scene_len = VO_LEAD + vo_len + VO_TAIL
        sentences = [s.strip() for s in
                     re.split(r"(?<=[.!?])\s+", sc["narration"]) if s.strip()]
        words = [len(s.split()) for s in sentences]
        total_words = sum(words)
        t = t_scene + VO_LEAD
        for s, w in zip(sentences, words):
            d = vo_len * w / total_words
            entries.append(f"{idx}\n{ts(t)} --> {ts(t + d - 0.05)}\n{s}\n")
            idx += 1
            t += d
        t_scene += scene_len - FADE
    out.write_text("\n".join(entries))
    print(f"{out}: {idx - 1} captions, ends {ts(t_scene + FADE)}")


if __name__ == "__main__":
    main()
