"""Emit the HyperFrames composition for the DOC-EXAM walkthrough.

Why a generator instead of hand-written HTML: every clip's start and length is the *measured*
length of its narration file (scripts/make_narration.py reads the mp3 frame headers), so a
re-recorded beat retimes the picture, the caption and the following scene in one command. The
output is plain, static HTML committed under video/film/ — editable by hand afterwards, which
is what the skill asks for; only the numbers come from the audio.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "video" / "manifest.json"
FILM = REPO / "video" / "film"
SHOTS = REPO / "video" / "shots"

# Chapters: the film has four, and each one is a scene file. A beat belongs to a chapter by
# index; the ranges are the storyboard, not an afterthought.
CHAPTERS = [
    {"id": "foundations", "label": "The job", "beats": (0, 6),
     "shot": "task.png", "title": "Eight examinations a documentary-credit analyst would actually be given"},
    {"id": "grading", "label": "How it is marked", "beats": (6, 10),
     "shot": "integrity.png", "title": "The grader is the part that had to be proven"},
    {"id": "platform", "label": "The platform", "beats": (10, 16),
     "shot": "transcript.png", "title": "Files in, evidence out — no database, no dashboard that can disagree"},
    {"id": "evidence", "label": "What it showed", "beats": (16, 24),
     "shot": "results.png", "title": "168 scored trials, and the numbers were regenerated from the transcripts"},
]

# Per-beat on-screen line. Kept short: the voice carries the sentence, the picture carries the
# noun. Repeating the narration word for word on screen is the tell the skill calls out.
CARDS = {
    0: ("DOC · EXAM", "documentary credit examination"),
    1: ("an evaluation lab", "not a pile of prompts"),
    2: ("1 letter of credit", "5–6 documents · 1 rulebook"),
    3: ("23 rules", "26 finding codes · seeded, synthetic"),
    4: ("ground truth is computed", "the interpreter reads the same pages"),
    5: ("intent vs computed", "disagreement fails the build"),
    6: ("7 weighted dimensions", "the outcome, not the steps"),
    7: ("hard caps", "miss a critical → 0"),
    8: ("117 fixtures", "correct and deliberately wrong"),
    9: ("15 mutation levers", "the gate must be able to fail"),
    10: ("FastAPI + console", "served from artifact files"),
    11: ("grader integrity", "levers, fixtures, disclosed gaps"),
    12: ("raw output", "beside the scorecard that graded it"),
    13: ("9 models", "temperature 0 · 3 trials · free tiers"),
    14: ("panel 1 was my bug", "reasoning ate the completion"),
    15: ("0.00 → 70.52", "same transcripts, fixed harness"),
    16: ("168 trials", "61.9% passing · best 72.43"),
    17: ("rule 97.6 · severity 97.6", "recall 79.4 · uncertainty 60.7"),
    18: ("not a knowledge gap", "a noticing gap"),
    19: ("most-missed are minor", "CURRENCY 21 · ADDRESS 20 · MARKS 19"),
    20: ("read-only edge", "403 at the proxy, Zero Trust on the studio host"),
    21: ("no keys to reproduce", "validate · test · container"),
    22: ("README is generated", "a test fails if it drifts"),
    23: ("truth computed", "grader provable", ),
}

# Beats where the plate should push in on the part being named. Coordinates are percentages of
# the 1920×1080 plate, chosen from the screenshots themselves.
FOCUS = {
    2: (8, 12, 60, 46),
    6: (10, 20, 55, 30),
    9: (6, 40, 62, 34),
    12: (4, 22, 70, 52),
    16: (6, 14, 74, 40),
    17: (8, 20, 66, 30),
}

PALETTE = {
    "ground": "#080b10",
    "panel": "#0e141c",
    "ink": "#e8eef5",
    "muted": "#7f8fa3",
    "rule": "#1d2733",
    "amber": "#f5a524",
    "red": "#e5484d",
    "green": "#46a37a",
}

FONT_DISPLAY = "IBM Plex Mono"
FONT_BODY = "Inter"


def chapter_of(index: int) -> dict:
    for chapter in CHAPTERS:
        lo, hi = chapter["beats"]
        if lo <= index < hi:
            return chapter
    raise KeyError(index)


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def copy_assets(manifest: dict) -> None:
    audio = FILM / "assets" / "audio"
    shots = FILM / "assets" / "shots"
    audio.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    for beat in manifest["beats"]:
        shutil.copyfile(REPO / beat["file"], audio / Path(beat["file"]).name)
    for chapter in CHAPTERS:
        src = SHOTS / chapter["shot"]
        if src.is_file():
            shutil.copyfile(src, shots / src.name)


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def scene_file(chapter: dict, beats: list[dict], pad: float) -> str:
    lo, hi = chapter["beats"]
    start = beats[0]["start_s"]
    slot = round(beats[-1]["start_s"] + beats[-1]["duration_s"] + pad - start, 3)
    local = lambda b: round(b["start_s"] - start, 3)  # noqa: E731  scene clock starts at 0

    cards = []
    tweens = []
    for i, beat in enumerate(beats):
        index = beat["index"]
        card = CARDS.get(index, ("", ""))
        left, right = (card[0], card[1] if len(card) > 1 else "")
        # A card lives until the next beat's card arrives, plus the pad on the last one, so the
        # screen is never empty between sentences.
        duration = round((beats[i + 1]["start_s"] - beat["start_s"]) if i + 1 < len(beats)
                         else beat["duration_s"] + pad, 3)
        cid = f"c{index}"
        cards.append(
            f'      <div id="{cid}" class="clip card" data-start="{local(beat)}" '
            f'data-duration="{duration}" data-track-index="{2 + (i % 3)}">\n'
            f'        <p class="card-left">{esc(left)}</p>\n'
            f'        <p class="card-right">{esc(right)}</p>\n'
            f'        <span class="tick"></span>\n'
            f'      </div>'
        )
        tweens.append(
            f'    tl.fromTo("#{cid}", {{ opacity: 0, y: 26 }}, '
            f'{{ opacity: 1, y: 0, duration: 0.34, ease: "power3.out" }}, {local(beat)});'
        )
        # The detail line lands after the headline line, so a beat has two visible moments
        # instead of one and the screen is never frozen for the whole sentence.
        tweens.append(
            f'    tl.fromTo("#{cid} .card-right", {{ opacity: 0, y: 10 }}, '
            f'{{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }}, {round(local(beat) + 0.5, 3)});'
        )
        # A progress rule under the card runs for exactly as long as the sentence is spoken.
        # It is the only honest way to keep the frame alive between beats: the alternative is
        # decorative motion that means nothing.
        tweens.append(
            f'    tl.fromTo("#{cid} .tick", {{ scaleX: 0 }}, '
            f'{{ scaleX: 1, duration: {duration}, ease: "none" }}, {local(beat)});'
        )

    focus_markup = ""
    focus_tween = ""
    if any(b["index"] in FOCUS for b in beats):
        boxes = []
        for beat in beats:
            if beat["index"] not in FOCUS:
                continue
            x, y, w, h = FOCUS[beat["index"]]
            fid = f"f{beat['index']}"
            boxes.append(
                f'        <div id="{fid}" class="clip focus" data-start="{local(beat)}" '
                f'data-duration="{beat["duration_s"]}" data-layout-allow-overflow="true" '
                f'style="left:{x}%;top:{y}%;width:{w}%;height:{h}%"></div>'
            )
            focus_tween += (
                f'    tl.fromTo("#{fid}", {{ opacity: 0, scale: 1.04 }}, '
                f'{{ opacity: 1, scale: 1, duration: 0.3, ease: "power2.out" }}, {local(beat)});\n'
            )
        focus_markup = "\n".join(boxes)

    plate_dur = round(slot, 3)
    return f"""<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      background: {PALETTE['ground']};
      font-family: {FONT_BODY}, sans-serif;
      color: {PALETTE['ink']};
      overflow: hidden;
    }}
    .plate {{
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: left top;
    }}
    .scrim {{
      position: absolute;
      inset: 0;
      background: linear-gradient(105deg, rgba(8,11,16,0.94) 0%, rgba(8,11,16,0.80) 42%, rgba(8,11,16,0.30) 100%);
    }}
    .chapter {{
      position: absolute;
      left: 96px;
      top: 76px;
      font-family: {FONT_DISPLAY}, monospace;
      font-size: 28px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: {PALETTE['amber']};
    }}
    .scene-title {{
      position: absolute;
      left: 96px;
      top: 122px;
      width: 660px;
      font-size: 31px;
      line-height: 1.34;
      font-weight: 400;
      color: {PALETTE['muted']};
    }}
    .card {{
      position: absolute;
      left: 96px;
      top: 372px;
      width: 800px;
      border-left: 3px solid {PALETTE['amber']};
      padding: 22px 0 22px 26px;
      background: rgba(14,20,28,0.72);
    }}
    .card-left {{
      font-family: {FONT_DISPLAY}, monospace;
      font-size: 46px;
      line-height: 1.12;
      letter-spacing: -0.02em;
      color: {PALETTE['ink']};
    }}
    .card-right {{
      margin-top: 12px;
      font-size: 29px;
      line-height: 1.3;
      color: {PALETTE['muted']};
    }}
    .tick {{
      position: absolute;
      left: 26px;
      bottom: 10px;
      width: 210px;
      height: 2px;
      background: {PALETTE['amber']};
      transform-origin: left center;
      opacity: 0.55;
    }}
    .focus {{
      position: absolute;
      border: 2px solid {PALETTE['amber']};
      border-radius: 10px;
      box-shadow: 0 0 0 9999px rgba(8,11,16,0.42);
    }}
  </style>
  <div id="root" data-composition-id="{chapter['id']}" data-duration="{plate_dur}"
       data-width="1920" data-height="1080">
    <img id="{chapter['id']}-plate" class="clip plate" data-start="0" data-duration="{plate_dur}"
         data-track-index="0" src="assets/shots/{chapter['shot']}" alt="" />
    <div id="{chapter['id']}-scrim" class="clip scrim" data-start="0" data-duration="{plate_dur}" data-track-index="1"></div>
    <p id="{chapter['id']}-chapter" class="clip chapter" data-start="0" data-duration="{plate_dur}" data-track-index="1">{esc(chapter['label'])}</p>
    <p id="{chapter['id']}-title" class="clip scene-title" data-start="0.2" data-duration="{plate_dur}" data-track-index="1">{esc(chapter['title'])}</p>
{focus_markup}
{chr(10).join(cards)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#{chapter['id']}-plate", {{ opacity: 0, scale: 1.075 }},
      {{ opacity: 1, scale: 1.005, duration: {plate_dur}, ease: "none" }}, 0);
    tl.fromTo("#{chapter['id']}-chapter", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.15);
    tl.fromTo("#{chapter['id']}-title", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }}, 0.3);
{chr(10).join(tweens)}
{focus_tween}    window.__timelines["{chapter['id']}"] = tl;
  </script>
</template>
"""


def root_file(manifest: dict) -> str:
    beats = manifest["beats"]
    pad = manifest["pad_s"]
    total = round(manifest["total_s"] + 1.2, 3)

    hosts = []
    for chapter in CHAPTERS:
        lo, hi = chapter["beats"]
        group = [b for b in beats if lo <= b["index"] < hi]
        start = group[0]["start_s"]
        end = round(group[-1]["start_s"] + group[-1]["duration_s"] + pad, 3)
        hosts.append(
            f'      <div id="{chapter["id"]}" data-composition-id="{chapter["id"]}" '
            f'data-composition-src="compositions/{chapter["id"]}.html" '
            f'data-start="{start}" data-duration="{round(end - start, 3)}" '
            f'data-track-kind="graphics" data-width="1920" data-height="1080"></div>'
        )

    audio = []
    for beat in beats:
        # 1.38 is not taste: `hyperframes normalize-audio` measured each clip at -20.9 LUFS and
        # raised it by +2.8 dB, which is as far as it can go before the true peak leaves -1 dBTP.
        # That lands the finished mix near -15 LUFS, inside the range a phone speaker can play.
        audio.append(
            f'      <audio id="{beat["id"]}" class="clip" src="assets/audio/{Path(beat["file"]).name}" '
            f'data-start="{beat["start_s"]}" data-duration="{beat["duration_s"]}" '
            f'data-volume="1.38" data-track-index="6"></audio>'
        )

    captions = []
    for beat in beats:
        # Captions follow the sentence boundaries edge-tts reported, not a fixed box, so the
        # line changes when the voice changes.
        duration = round(min(beat["duration_s"] + pad * 0.6, 6.0), 3)
        captions.append(
            f'        <p id="cap{beat["index"]:02d}" class="clip caption" data-start="{beat["start_s"]}" '
            f'data-duration="{duration}" data-track-index="0">{esc(beat["text"])}</p>'
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      :root {{
        --ground: {PALETTE['ground']};
        --ink: {PALETTE['ink']};
        --muted: {PALETTE['muted']};
        --amber: {PALETTE['amber']};
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: var(--ground);
      }}
      #root {{ position: absolute; inset: 0; }}
      .caption {{
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        bottom: 74px;
        width: 1560px;
        text-align: center;
        font-family: Inter, sans-serif;
        font-size: 30px;
        line-height: 1.36;
        color: var(--ink);
        text-shadow: 0 2px 18px rgba(0,0,0,0.85);
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}"
         data-width="1920" data-height="1080">
{chr(10).join(hosts)}

      <div id="captions" data-track-kind="captions" data-width="1920" data-height="1080"
           data-no-timeline="true">
{chr(10).join(captions)}
      </div>

{chr(10).join(audio)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def main() -> int:
    manifest = load()
    copy_assets(manifest)
    (FILM / "compositions").mkdir(parents=True, exist_ok=True)
    for chapter in CHAPTERS:
        lo, hi = chapter["beats"]
        group = [b for b in manifest["beats"] if lo <= b["index"] < hi]
        (FILM / "compositions" / f"{chapter['id']}.html").write_text(
            scene_file(chapter, group, manifest["pad_s"]), encoding="utf-8", newline="\n")
    (FILM / "index.html").write_text(root_file(manifest), encoding="utf-8", newline="\n")
    print(f"wrote index.html + {len(CHAPTERS)} scenes to {FILM.relative_to(REPO)} "
          f"(total {manifest['total_s']}s of narration)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
