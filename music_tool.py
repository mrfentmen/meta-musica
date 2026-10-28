#!/usr/bin/env python3
"""Music Tool command line.

Make music from math. No samples. No recordings.
Each instrument is built from sound waves in synth.py.
Each track is split into stems. Stems are separate files.
A mix is all stems added together.

Examples:
  python3 music_tool.py list
  python3 music_tool.py render rainy-window
  python3 music_tool.py render neon-drive --stems-only
  python3 music_tool.py render porch-light --mix-only
  python3 music_tool.py render-all
  python3 music_tool.py qc
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT_DEFAULT = os.path.join(HERE, "out")

import demos  # noqa: E402

ORIGINALS = {
    "loading-theme": "loading_theme",
    "battle-theme": "battle_theme",
    "ambient-exploration": "ambient",
    "menu-theme": "menu_theme",
    "victory-fanfare": "victory_fanfare",
    "defeat": "defeat",
}


def load_presets():
    with open(os.path.join(HERE, "presets.json")) as f:
        return json.load(f)


def list_tracks():
    data = load_presets()
    print("Tracks:")
    for t in data["tracks"]:
        tag = "NEW" if t.get("new") else "original"
        print(f"  {t['name']:22} {t['style']:20} {t['tempo_bpm']} BPM "
              f"{t['key']:10} {t['mood']} [{tag}]")
    print("\nNew instruments:")
    for line in data["new_instruments"]:
        print(f"  {line}")


def _convert_wavs(name, out_dir, stems_only, mix_only):
    """Convert WAV files made by compose.py to MP3, then remove WAVs."""
    made = []
    for wav in sorted(glob.glob(os.path.join(out_dir, f"{name}-*.wav"))):
        is_mix = wav.endswith("-mix.wav")
        if stems_only and is_mix:
            os.remove(wav)
            continue
        if mix_only and not is_mix:
            os.remove(wav)
            continue
        mp3 = wav[:-4] + ".mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav,
                        "-codec:a", "libmp3lame", "-b:a", "128k", mp3],
                       check=True)
        os.remove(wav)
        made.append(mp3)
    return made


def render(name, out_dir, stems_only=False, mix_only=False):
    os.makedirs(out_dir, exist_ok=True)
    if name in demos.DEMOS:
        fn, wet = demos.DEMOS[name]
        track_name, stems, gains = fn()
        made = demos.render(track_name, stems, gains, out_dir,
                            stems_only=stems_only, mix_only=mix_only,
                            reverb_wet=wet)
        for p in made:
            print(f"  -> {p}")
        return made
    if name in ORIGINALS:
        import compose
        fn = getattr(compose, ORIGINALS[name])
        track_name, stems, gains = fn()
        # compose.mix_track writes WAV stems + mix into out/
        compose.OUT = out_dir
        compose.mix_track(track_name, stems, gains, reverb_wet=0.20)
        made = _convert_wavs(track_name, out_dir, stems_only, mix_only)
        for p in made:
            print(f"  -> {p}")
        return made
    print(f"Unknown track: {name}", file=sys.stderr)
    print("Run: python3 music_tool.py list", file=sys.stderr)
    raise SystemExit(2)


def render_all(out_dir, stems_only=False, mix_only=False):
    all_made = []
    for name in demos.DEMOS:
        print(f"Rendering {name} ...")
        all_made += render(name, out_dir, stems_only, mix_only)
    return all_made


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="music_tool.py",
        description="Make music from math. No samples. Stems + mix as MP3.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List presets and tracks")
    r = sub.add_parser("render", help="Render one named track")
    r.add_argument("name", help="Track name, e.g. rainy-window")
    r.add_argument("--out", default=OUT_DEFAULT, help="Output folder")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--stems-only", action="store_true",
                   help="Render stems only, no mix")
    g.add_argument("--mix-only", action="store_true",
                   help="Render mix only, no stems")
    a = sub.add_parser("render-all", help="Render all 4 new demo tracks")
    a.add_argument("--out", default=OUT_DEFAULT, help="Output folder")
    a.add_argument("--stems-only", action="store_true")
    a.add_argument("--mix-only", action="store_true")
    sub.add_parser("qc", help="Run the QC check on rendered MP3s")
    args = p.parse_args(argv)
    if args.cmd == "list":
        list_tracks()
    elif args.cmd == "render":
        render(args.name, args.out, args.stems_only, args.mix_only)
    elif args.cmd == "render-all":
        render_all(args.out, args.stems_only, args.mix_only)
    elif args.cmd == "qc":
        import qc
        raise SystemExit(qc.main(args_out=None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
