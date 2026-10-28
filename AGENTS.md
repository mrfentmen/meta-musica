# Music Tool — instructions for agents

This tool is made for Muse agents and AI agents in general.
A human can use it too. The agent path is the main path.

## The one rule

Do not scrape human text output. Use `--json`.
Every command below prints only JSON on stdout when you pass `--json`.
If you did not pass `--json`, do not parse the output as data.

## Setup

    pip install -r requirements.txt

You also need ffmpeg for MP3 files.

## Step 1: list what exists

    python3 music_tool.py list --json

That gives tracks, styles, instruments, and commands.
It does not make any audio.

## Step 2a: render a preset track

    python3 music_tool.py render rainy-window --seed 42 --json

The JSON gives the track name, the seed, and a files list.
Each file has a path, a kind (`mix` or `stem`), and a stem name.

## Step 2b: make a NEW track from a description

This is the point of the tool. You are not limited to presets.

    python3 music_tool.py make my-track --style lofi --tempo 80 \
        --key "C minor" --bars 8 --seed 7 --json

Styles: `lofi`, `synthwave`, `folk`, `dark`, `epic`.
Tempo: 40 to 200 BPM. If you leave it out, the style default is used.
Key: e.g. `"C minor"`, `"G major"`. If you leave it out, the style
default is used. Mode defaults by style: minor for lofi, synthwave,
dark, and epic; major for folk.
Bars: 1 to 32. Default 8.
Name: lowercase letters, digits, and hyphens only, e.g. `my-track`.
Seed: default 42. Always pass a seed when you want the same audio again.

What you get back: aligned stems plus a mix, in the `out/` folder
unless you pass `--out`. Add `--stems-only` or `--mix-only` to get
only one of those.

## Step 3: check before you claim it

    python3 music_tool.py qc --out out/my-track --json

Or check the whole `out/` folder:

    python3 music_tool.py qc --json

Exit 0 means pass. Exit 1 means fail. Do not ship, link, or claim
a track that failed QC. Do not claim a track exists if you have not
rendered it and checked it.

QC checks: the file decodes, it is not silent, peak and loudness are
in range, there is no silence gap over 2 seconds, and stems for one
track are not copies of each other (correlation below 0.99).

## Seeds and reproducibility

Always pass `--seed` for work another agent must repeat.
The same seed, style, tempo, key, bars, and name give the same audio.
Without a seed, noise state carries across renders and mixes drift
slightly run to run. That drift is inside QC range, but it is not
the same bytes.

## How the music is made

No samples. No recordings. No soundfonts.
Every sound is built from sound waves in code, in `synth.py`.
Each instrument gets its own stem file. All stems line up in time.
A mix is all stems added together, with reverb and limiting.

## Limits, stated plainly

- The `make` command makes one structured track per call. It does
  not write lyrics, sing, or copy a real song.
- The `render` command renders the 4 new demos plus the 6 original
  game tracks from `compose.py`. The other copied source files
  (`compose5.py`, `compose6.py`, `compose_danger.py`,
  `compose_stingers.py`, `radio.py`, `sfx*.py`) are runnable source,
  but they are not wired into `music_tool.py render`.
- Without ffmpeg, renders leave WAV files instead of MP3s.
- Old game music lives in `old-game-music/`. Those are finished
  mixes, not stems. Their stems are about 1 GB and are not in this
  repo yet.
