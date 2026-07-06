# Channel Launch Playbook — 3-Video Slate

Straight talk first: nobody can guarantee "viral." What actually drives reach
on YouTube is (1) click-through rate on the thumbnail+title, (2) how long
people watch, and (3) whether the channel gives the algorithm a reason to
keep recommending you (consistency + session time). Everything below pushes
one of those three levers. The packaging work — hooks, open loops, chapters,
tags, captions — is already done; this is the execution plan.

## 1. Upload (one command per video)

```bash
pip install google-api-python-client google-auth-oauthlib
# one-time: put client_secret.json next to pipeline/upload_youtube.py
#           (steps in that file's header, ~5 minutes)

python3 pipeline/upload_youtube.py package                      # nature
python3 pipeline/upload_youtube.py package/animal-encounters    # animals
python3 pipeline/upload_youtube.py package/home-warning-signs   # house
```

Each command uploads the video and sets: title, description with chapters,
tags, thumbnail, English captions, Education category, not-made-for-kids,
the AI-content disclosure, and adds it to a shared public playlist
("Warning Signs That Could Save Your Life") — created automatically on the
first run. Videos land as **private** so you can check them in YouTube
Studio, then publish/schedule (or pass `--publish-at`).

## 2. Release schedule (don't dump all 3 at once)

| Day | Action |
|---|---|
| Day 1 (Sat ~10 AM your audience's time) | Publish **nature** (broadest appeal) |
| Day 1, +1h | Post + pin the pinned comment; reply to every comment for the first 24h |
| Day 4 (Tue/Wed evening) | Publish **animals** |
| Day 8 (next Sat morning) | Publish **house** |
| Every upload | Community-tab post (if unlocked): thumbnail + one-line hook |

Three uploads in one week signals a living channel; spacing gives each video
its own impression budget instead of the three competing with each other.

## 3. Interlinking (session time is the multiplier)

- End screen on every video (last ~20s outro): subscribe button + "best for
  viewer" video card. Do this in Studio right after each upload.
- Info cards: nature@3:03 → house video · animals@3:34 → nature ·
  house@3:39 → animals. (Noted in each metadata.md.)
- All three sit in the shared playlist — link that playlist in every
  description once all are live, and make it the channel-page top shelf.

## 4. First-48-hours checklist per video (the algorithm's test window)

- [ ] Reply to every comment (comments in hour 1 weigh heaviest)
- [ ] Pin the prepared question comment (drives comment count)
- [ ] Share the link where it's natural: relevant subreddits
      (r/survival, r/homeowners — follow each sub's self-promo rules),
      WhatsApp/Telegram groups, Facebook groups in the niche
- [ ] Watch Studio analytics: **CTR** and **retention curve**
  - CTR < 3% after 48h → swap thumbnail (alternates are in the packages)
  - Retention cliff in the first 30s → the hook is the problem; note it for
    the next script (don't re-edit a live video)
  - CTR > 6% and retention > 50% → spend nothing, touch nothing, let it run

## 5. Shorts — the biggest free discovery lever still on the table

Each 5-min video contains 2-3 self-contained 30-60s segments (square waves,
the moose twist, the fish smell) that can be re-rendered vertical (9:16) as
Shorts, each ending with "full video on the channel." Shorts feed
subscribers to long-form and cost nothing with this pipeline. The renderer
needs a vertical card layout — ask Claude for it and post 2-3 Shorts per
week between long-form uploads.

## 6. Cadence — the only "viral" strategy that works long-term

One video/week minimum, same niche, same format. The pipeline makes each new
video ~1 hour of work: write `script_X.json`, run render, run make_thumb +
make_captions, fill upload.json, run the uploader. Topic backlog (all proven
in the niche): what disaster sirens mean, car warning signs (smells/sounds),
body warning signs before illness, warning labels decoded, airplane sounds
explained, weather signs sailors used, "if you see this on your car — drive
away."

## 7. What NOT to do

- Don't buy views/subs — it poisons your retention stats, which is the
  metric the algorithm actually ranks you on.
- Don't use "sub4sub" or spam links in other channels' comments.
- Don't re-upload the same video repeatedly chasing a better launch.
- Don't change niche for 10+ videos; the recommendation system needs a
  stable pattern of who watches you.
