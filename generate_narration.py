#!/usr/bin/env python3
"""Generate the Blocky Dinos narration MP3s with OpenAI text-to-speech.

Usage:
    pip install openai
    export OPENAI_API_KEY=sk-...
    python generate_narration.py                 # writes ./narration/**.mp3
    python generate_narration.py --voice echo    # try another voice
    python generate_narration.py --only species/trex-name.mp3   # regenerate one clip
    python generate_narration.py --force         # regenerate everything

Commit the resulting narration/ folder next to dino-gallery.html (index.html) on GitHub Pages.
The app looks for narration/<file> and falls back to browser speech for anything missing.
Run this locally only: the key must never be embedded in the page.
"""
import argparse, json, os, sys, time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install openai")

ap = argparse.ArgumentParser()
ap.add_argument("--script", default="narration_script.json")
ap.add_argument("--out", default="narration")
ap.add_argument("--voice", help="alloy | ash | ballad | coral | echo | fable | nova | onyx | sage | shimmer")
ap.add_argument("--model", help="gpt-4o-mini-tts (supports style instructions) or tts-1-hd")
ap.add_argument("--only", help="regenerate only this clip path")
ap.add_argument("--force", action="store_true")
args = ap.parse_args()

if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("Set OPENAI_API_KEY in your environment first.")

script = json.loads(Path(args.script).read_text(encoding="utf-8"))
voice = args.voice or script.get("voice", "onyx")
model = args.model or script.get("model", "gpt-4o-mini-tts")
base_instructions = script.get("instructions", "")
client = OpenAI()
out = Path(args.out)

todo = [c for c in script["clips"] if not args.only or c["file"] == args.only]
made = skipped = failed = 0
for c in todo:
    path = out / c["file"]
    if path.exists() and not args.force:
        skipped += 1
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    instructions = base_instructions + (" Style: " + c["style"] + "." if c.get("style") else "")
    kwargs = dict(model=model, voice=voice, input=c["text"], response_format="mp3")
    if model.startswith("gpt-4o"):
        kwargs["instructions"] = instructions
    for attempt in range(3):
        try:
            with client.audio.speech.with_streaming_response.create(**kwargs) as r:
                r.stream_to_file(path)
            made += 1
            print(f"✓ {c['file']}")
            break
        except Exception as e:  # rate limits, transient errors
            if attempt == 2:
                failed += 1
                print(f"✗ {c['file']}: {e}")
            else:
                time.sleep(2 * (attempt + 1))

print(f"\n{made} generated, {skipped} already existed, {failed} failed → {out}/")
