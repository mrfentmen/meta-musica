#!/usr/bin/env python3
"""Music Tool command line. Built for agents first, humans second.

Make music from math. No samples. No recordings.
Each instrument is built from sound waves in synth.py.
Each track is split into stems. Stems are separate files.
A mix is all stems added together.

Agent rules that make this usable by another agent:
- Every command accepts --json and then prints ONLY JSON on stdout.
  Parse it, do not scrape the human text output.
- Every render accepts --seed. The same seed gives the same audio.
  Without a seed, noise state carries across renders and mixes drift.
- Exit codes: 0 = done, 2 = bad name / bad style / bad key / unknown
  track, 1 = QC failure or render failure.
- Always run qc after a render before you ship or claim a track.

Examples (human):
  python3 music_tool.py list
  python3 music_tool.py render rainy-window
  python3 music_tool.py render neon-drive --stems-only
  python3 music_tool.py render-all
  python3 music_tool.py qc

Examples (agent):
  python3 music_tool.py list --json
  python3 music_tool.py render rainy-window --seed 42 --json
  python3 music_tool.py make my-track --style lofi --tempo 80 \
      --key "C minor" --bars 8 --seed 7 --json
  python3 music_tool.py qc --json
  python3 music_tool.py qc --out out/my-track --json
"""
import argparse
import contextlib
import glob
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT_DEFAULT = os.path.join(HERE, "out")

import demos  # noqa: E402
import synth  # noqa: E402

ORIGINALS = {
    "loading-theme": "loading_theme",
    "battle-theme": "battle_theme",
    "ambient-exploration": "ambient",
    "menu-theme": "menu_theme",
    "victory-fanfare": "victory_fanfare",
    "defeat": "defeat",
}
STYLE_ALIASES = {
    "lo-fi": "lofi", "lofi": "lofi", "chill": "lofi",
    "synthwave": "synthwave", "synth": "synthwave",
    "folk": "folk", "acoustic": "folk",
    "dark": "dark", "dark-ambient": "dark", "horror": "dark",
    "epic": "epic", "game": "epic",
}


def load_presets():
    with open(os.path.join(HERE, "presets.json")) as f:
        return json.load(f)


def fail(message, as_json=False):
    if as_json:
        print(json.dumps({"error": message}, indent=2))
    else:
        print(message, file=sys.stderr)
    raise SystemExit(2)


def list_tracks(as_json=False):
    data = load_presets()
    if as_json:
        print(json.dumps({
            "tracks": data["tracks"],
            "new_instruments": data["new_instruments"],
            "make_styles": ["lofi", "synthwave", "folk", "dark", "epic"],
            "commands": ["list", "render", "render-all", "make", "qc"],
        }, indent=2))
        return
    print("Tracks:")
    for t in data["tracks"]:
        tag = "NEW" if t.get("new") else "original"
        print(f"  {t['name']:22} {t['style']:20} {t['tempo_bpm']} BPM "
              f"{t['key']:10} {t['mood']} [{tag}]")
    print("\nNew instruments:")
    for line in data["new_instruments"]:
        print(f"  {line}")
    print("\nMake a new track (agents):")
    print("  python3 music_tool.py make my-track --style lofi "
          "--tempo 80 --key \"C minor\" --bars 8 --seed 7 --json")


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


def _file_info(path):
    base = os.path.basename(path)
    if base.endswith("-mix.mp3"):
        return {"path": path, "kind": "mix", "stem": None}
    m = re.search(r"-stem-(.+)\.mp3$", base)
    return {"path": path, "kind": "stem",
            "stem": m.group(1) if m else None}


def render(name, out_dir, stems_only=False, mix_only=False, seed=None,
           as_json=False):
    os.makedirs(out_dir, exist_ok=True)
    if seed is not None:
        synth.set_seed(seed)
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
    fail(f"Unknown track: {name}. Run: python3 music_tool.py list",
         as_json=as_json)


def render_all(out_dir, stems_only=False, mix_only=False, seed=None):
    all_made = []
    for name in demos.DEMOS:
        print(f"Rendering {name} ...")
        all_made += render(name, out_dir, stems_only, mix_only, seed=seed)
    return all_made


def make_track(name, style, bpm, key, bars, out_dir, seed,
               stems_only=False, mix_only=False, as_json=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", name or ""):
        fail("Bad track name. Use lowercase letters, digits, hyphens only, "
             "e.g. my-track.", as_json=as_json)
    style = STYLE_ALIASES.get(style)
    if style is None:
        fail("Unknown style. Use: lofi, synthwave, folk, dark, epic.",
             as_json=as_json)
    import agent_make
    import demos as demos_mod
    if seed is not None:
        synth.set_seed(seed)
    try:
        track_name, stems, gains, wet, ceiling = agent_make.make_track(
            name, style, bpm, key, bars, seed if seed is not None else 42)
    except ValueError as e:
        fail(str(e), as_json=as_json)
    made = demos_mod.render(track_name, stems, gains, out_dir,
                            stems_only=stems_only, mix_only=mix_only,
                            reverb_wet=wet, ceiling=ceiling)
    for p in made:
        print(f"  -> {p}")
    return made


def _render_json(track, made, extra=None):
    out = {"track": track, "files": [_file_info(p) for p in made]}
    if extra:
        out.update(extra)
    print(json.dumps(out, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="music_tool.py",
        description="Make music from math. No samples. Stems + mix as MP3.")
    sub = p.add_subparsers(dest="cmd", required=True)
    li = sub.add_parser("list", help="List presets and tracks")
    li.add_argument("--json", action="store_true")
    r = sub.add_parser("render", help="Render one named track")
    r.add_argument("name", help="Track name, e.g. rainy-window")
    r.add_argument("--out", default=OUT_DEFAULT, help="Output folder")
    r.add_argument("--seed", type=int, default=None,
                   help="Seed for reproducible audio, e.g. 42")
    r.add_argument("--json", action="store_true")
    g = r.add_mutually_exclusive_group()
    g.add_argument("--stems-only", action="store_true",
                   help="Render stems only, no mix")
    g.add_argument("--mix-only", action="store_true",
                   help="Render mix only, no stems")
    a = sub.add_parser("render-all", help="Render all 4 new demo tracks")
    a.add_argument("--out", default=OUT_DEFAULT, help="Output folder")
    a.add_argument("--seed", type=int, default=None)
    a.add_argument("--json", action="store_true")
    a.add_argument("--stems-only", action="store_true")
    a.add_argument("--mix-only", action="store_true")
    m = sub.add_parser("make", help="Make a NEW track from a description")
    m.add_argument("name", help="New track name, e.g. my-track")
    m.add_argument("--style", required=True,
                   help="lofi, synthwave, folk, dark, or epic")
    m.add_argument("--tempo", type=int, default=None,
                   help="BPM, 40-200. Defaults by style if omitted.")
    m.add_argument("--key", default=None,
                   help='e.g. "C minor", "G major". Defaults by style.')
    m.add_argument("--bars", type=int, default=8,
                   help="Bars, 1-32. Default 8 (32 beats).")
    m.add_argument("--seed", type=int, default=42,
                   help="Seed for reproducible audio. Default 42.")
    m.add_argument("--out", default=OUT_DEFAULT, help="Output folder")
    m.add_argument("--json", action="store_true")
    mg = m.add_mutually_exclusive_group()
    mg.add_argument("--stems-only", action="store_true")
    mg.add_argument("--mix-only", action="store_true")
    q = sub.add_parser("qc", help="Run the QC check on rendered MP3s")
    q.add_argument("--out", default=None, help="Folder to check")
    q.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "list":
        list_tracks(as_json=args.json)
    elif args.cmd == "render":
        if args.json:
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    made = render(args.name, args.out, args.stems_only,
                                  args.mix_only, seed=args.seed,
                                  as_json=True)
            except SystemExit:
                # Error JSON was printed into the buffer by fail();
                # flush it so an agent actually sees it.
                sys.stdout.write(buf.getvalue())
                raise
            _render_json(args.name, made, {"seed": args.seed})
        else:
            render(args.name, args.out, args.stems_only, args.mix_only,
                   seed=args.seed)
    elif args.cmd == "render-all":
        if args.json:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                made = render_all(args.out, args.stems_only, args.mix_only,
                                  seed=args.seed)
            _render_json("all-demos", made, {"seed": args.seed})
        else:
            render_all(args.out, args.stems_only, args.mix_only,
                       seed=args.seed)
    elif args.cmd == "make":
        style_key = STYLE_ALIASES.get(args.style, args.style)
        tempo = args.tempo
        if tempo is None:
            tempo = {"lofi": 72, "synthwave": 100, "folk": 90,
                     "dark": 60, "epic": 92}.get(style_key, 90)
        key = args.key
        if key is None:
            key = {"lofi": "A minor", "synthwave": "C minor",
                   "folk": "G major", "dark": "D minor",
                   "epic": "D minor"}.get(style_key, "C minor")
        if args.json:
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    made = make_track(args.name, style_key, tempo, key,
                                      args.bars, args.out, args.seed,
                                      args.stems_only, args.mix_only,
                                      as_json=True)
            except SystemExit:
                sys.stdout.write(buf.getvalue())
                raise
            _render_json(args.name, made, {
                "style": style_key, "tempo_bpm": tempo, "key": key,
                "bars": args.bars, "seed": args.seed})
        else:
            make_track(args.name, style_key, tempo, key, args.bars,
                       args.out, args.seed, args.stems_only, args.mix_only)
    elif args.cmd == "qc":
        import qc
        raise SystemExit(qc.main(out_dir=args.out, as_json=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
