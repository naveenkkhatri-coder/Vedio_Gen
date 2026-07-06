# Free Faceless-Video Pipeline

Renders a complete narrated YouTube video (1080p MP4) from a script JSON —
**no paid services, no API keys, no credits**. Everything runs locally:

| Stage | Tool | Cost |
|---|---|---|
| Voiceover | `pico2wave` (offline TTS; `espeak-ng` fallback) | free |
| Scene visuals | Pillow-drawn 2400×1350 cards (gradient, badge, emoji, title, action strip, progress dots) | free |
| Animation | ffmpeg `zoompan` Ken Burns (zoom in/out, pan left/right, alternating) | free |
| Transitions | ffmpeg `xfade` cross-dissolves | free |
| Music bed | numpy-synthesized ambient chord pad | free |
| Assembly | ffmpeg H.264 + AAC | free |

## Setup (Ubuntu/Debian)

```bash
apt-get install -y ffmpeg libttspico-utils espeak-ng fonts-inter fonts-noto-color-emoji
pip3 install pillow numpy
```

## Usage

```bash
python3 pipeline/render_video.py pipeline/script_5min.json output.mp4 workdir
```

Video length is driven by the narration: each scene lasts
`0.6s + voiceover + 1.0s`, scenes overlap by the 0.5s cross-fade.
~665 words of narration ≈ 5 minutes.

## Script format

`script_5min.json` — one object per scene:

```json
{
  "id": "square-waves",
  "badge": "7",                       // number shown in the circle badge
  "emoji": "🌊",                      // icon (Noto Color Emoji)
  "title": "Square Waves",            // \n for manual line breaks
  "action": "Swim parallel to shore", // black pill under the title
  "colors": ["#0B7285", "#22B8CF"],   // card gradient top → bottom
  "narration": "Number seven. ..."    // spoken by TTS, sets scene length
}
```

## Trade-offs vs. paid AI video

- Visuals are **motion-graphics cards** (title + icon + Ken Burns), not
  AI-animated scenes. Many faceless channels run exactly this style.
- The offline TTS voice is clear but noticeably synthetic. Two free upgrade
  paths when network access allows: `edge-tts` (Microsoft neural voices) or
  Piper (local neural TTS, needs a one-time voice-model download) — both are
  drop-in replacements for the `tts()` function in `render_video.py`.
