"""Synthesize the walkthrough narration, one clip per beat, and record the true timings.

The beat list is the script; the audio is the clock. Durations come out of edge-tts's own
word-boundary events rather than a words-per-minute estimate, because a scene that is 0.4 s
short of its narration cuts a sentence off mid-word, and that is the single most obvious tell
of a synthetic walkthrough.

edge-tts 7.x emits SentenceBoundary only on the voices available here — no WordBoundary — so a
"beat" is a sentence, which is what the storyboard is written as anyway. The per-beat caption
timings come from the same events, so the on-screen text is aligned to the audio it describes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BEATS = REPO / "video" / "beats.json"
AUDIO_DIR = REPO / "video" / "audio"
MANIFEST = REPO / "video" / "manifest.json"

# `ffprobe`-free duration: an mp3 frame scan is enough at these sample counts, and it keeps
# the build honest on a machine without ffmpeg installed.
BYTES_PER_MS = {128: 16.0, 96: 12.0, 64: 8.0}


async def synth(text: str, out_path: Path, voice: str, rate: str) -> list[dict]:
    import edge_tts

    submaker = edge_tts.SubMaker()
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    with out_path.open("wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
    # `get_srt()` returns a formatted string; `cues` is the structured list, and timings are
    # timedeltas measured from the start of this clip. Read the objects, then parse text.
    return [
        {
            "text": cue.content,
            "start_ms": int(cue.start.total_seconds() * 1000),
            "duration_ms": int((cue.end - cue.start).total_seconds() * 1000),
        }
        for cue in submaker.cues
    ]


def mp3_ms(path: Path) -> int:
    """Wall-clock length of the clip from its frame headers, not from the boundary events."""
    import struct

    data = path.read_bytes()
    i = 0
    total = 0.0
    while i < len(data) - 4:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            header = struct.unpack(">I", data[i:i + 4])[0]
            bitrate_index = (header >> 12) & 0x0F
            sample_index = (header >> 10) & 0x03
            padding = (header >> 9) & 0x01
            if bitrate_index in (0, 15) or sample_index == 3:
                i += 1
                continue
            bitrate = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320][bitrate_index]
            sample_rate = [44100, 48000, 32000][sample_index if sample_index < 3 else 0]
            frame_len = int(144000 * bitrate / sample_rate) + padding
            total += 1152 / sample_rate * 1000
            i += frame_len
        else:
            i += 1
    return int(total)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--voice", default="en-US-AndrewMultilingualNeural")
    ap.add_argument("--rate", default="+0%", help="edge-tts rate offset, e.g. +5%% or -10%%")
    ap.add_argument("--only", type=int, default=None, help="re-generate one beat index only")
    ap.add_argument("--pad", type=float, default=0.35,
                    help="seconds of silence to leave after each beat before the next starts")
    args = ap.parse_args(argv)

    beats = json.loads(BEATS.read_text(encoding="utf-8"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    previous = {}
    if MANIFEST.is_file():
        previous = {b["index"]: b.get("cues", []) for b in json.loads(MANIFEST.read_text(encoding="utf-8"))["beats"]}

    rows = []
    clock = 0.0
    for index, beat in enumerate(beats):
        name = f"beat-{index:02d}.mp3"
        out_path = AUDIO_DIR / name
        text = beat["text"]
        if args.only is not None and index != args.only:
            if not out_path.is_file():
                raise SystemExit(f"{name} missing; run without --only first")
            ms = mp3_ms(out_path)
            # Reuse the captions from the earlier run; re-timing them would need the audio
            # stream, and the clip on disk has not changed.
            cues = previous.get(index, [])
        else:
            cues = asyncio.run(synth(text, out_path, args.voice, args.rate))
            ms = mp3_ms(out_path)
            if not ms:
                print(f"beat {index}: frame scan found no frames", file=sys.stderr)
                return 1
        duration = round(ms / 1000.0, 3)
        if duration < 0.4:
            print(f"beat {index} produced {duration}s of audio — the file is empty", file=sys.stderr)
            return 1
        rows.append({
            "index": index,
            "id": beat.get("id", f"beat{index:02d}"),
            "scene": beat.get("scene"),
            "text": text,
            "file": f"video/audio/{name}",
            "duration_s": duration,
            "start_s": round(clock, 3),
            "cues": cues,
        })
        clock = round(clock + duration + args.pad, 3)

    MANIFEST.write_text(json.dumps({
        "voice": args.voice,
        "rate": args.rate,
        "pad_s": args.pad,
        "total_s": round(clock - args.pad, 3),
        "beats": rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} beat(s), total {clock - args.pad:.1f}s -> {MANIFEST.relative_to(REPO)}")
    for row in rows:
        print(f"  {row['index']:>2} {row['start_s']:>7.2f} +{row['duration_s']:<6.2f} {row['scene'] or '-':<10} {row['text'][:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
