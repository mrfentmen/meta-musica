"""Make a NEW track from an agent's description.

This is the agent-facing generator. It does not only re-render presets.
An agent gives a style, a tempo, a key, a length, and a seed, and gets
aligned stems plus a mix back, all made from math in synth.py.

Styles: lofi, synthwave, folk, dark, epic
Keys:   e.g. "A minor", "C major", "D" (mode defaults by style)
Example:
  python3 music_tool.py make my-track --style lofi --tempo 80 \
      --key "C minor" --bars 8 --seed 7 --json

Every style keeps every stem active in every section, so QC never sees
a stem that is silent for a whole track. Melody notes are picked with a
seeded random walk on the scale, so the same seed gives the same notes.
Noise is seeded separately by music_tool.py before the render, so the
same seed gives the same audio bytes too.
"""
import re

import numpy as np

from synth import Track

NAMES = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4,
         "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9,
         "A#": 10, "BB": 10, "B": 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]

# Scale-degree progressions (0 = tonic). One chord per bar, cycled.
PROGRESSIONS = {
    "lofi": [0, 5, 2, 6],        # i VI III VII in minor
    "synthwave": [0, 5, 2, 6],   # i VI III VII in minor
    "folk": [0, 4, 5, 3],        # I V vi IV in major
    "dark": [0, 0, 5, 2],        # i i VI III, slow and heavy
    "epic": [0, 5, 2, 6],        # i VI III VII in minor
}
DEFAULT_MODE = {"lofi": "minor", "synthwave": "minor", "folk": "major",
                "dark": "minor", "epic": "minor"}
WET = {"lofi": 0.28, "synthwave": 0.16, "folk": 0.20, "dark": 0.32,
       "epic": 0.20}


def parse_key(key_text, style):
    """'A minor' / 'C major' / 'D' -> (root_midi, mode, scale)."""
    m = re.match(r"^\s*([A-Ga-g])([#bB]?)\s*(minor|major|m|M)?\s*$",
                 key_text or "")
    if not m:
        raise ValueError(f"Bad key: {key_text!r}. Use e.g. 'A minor'.")
    pc_name = (m.group(1).upper() + m.group(2).upper()).replace("B", "B")
    # Normalise flats: Db -> DB etc. is already in NAMES; sharps stay.
    if pc_name not in NAMES:
        raise ValueError(f"Unknown note: {pc_name}")
    mode = m.group(3)
    if mode in ("m", "minor"):
        mode = "minor"
    elif mode in ("M", "major"):
        mode = "major"
    else:
        mode = DEFAULT_MODE[style]
    scale = MINOR if mode == "minor" else MAJOR
    root = 12 * (3 + 1) + NAMES[pc_name]  # octave 3, e.g. A3 = 57
    return root, mode, scale


def scale_midi(root, scale, degree):
    """Scale degree (can be past 6, wraps an octave up) -> midi."""
    octaves, idx = divmod(degree, 7)
    return root + scale[idx] + 12 * octaves


def chord_midis(root, scale, degree):
    """Triad on a scale degree: root, third, fifth of that chord."""
    return [scale_midi(root, scale, degree + d) for d in (0, 2, 4)]


def make_track(name, style, bpm, key_text, bars, seed):
    """Return (track_name, stems, gains, reverb_wet, ceiling).

    Ceiling 0.80 (not the preset 0.89) leaves headroom for MP3
    decode overshoot, so agent-made mixes stay inside QC peak range.
    """
    if style not in PROGRESSIONS:
        raise ValueError(f"Unknown style: {style}. "
                         f"Use one of: {', '.join(PROGRESSIONS)}")
    if bars < 1 or bars > 32:
        raise ValueError("bars must be 1 to 32")
    if not (40 <= bpm <= 200):
        raise ValueError("tempo must be 40 to 200 BPM")
    root, mode, scale = parse_key(key_text, style)
    total = bars * 4
    rng = np.random.default_rng(int(seed) + 1)
    prog = PROGRESSIONS[style]
    chords = [chord_midis(root, scale, d) for d in prog]
    # Seeded melody: bar start is the chord root, one octave up, then a
    # stepwise walk of 1-2 semitones on beats 2 and 3 of each bar.
    melody = []
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        melody.append((bar * 4, chord[0] + 12, 2))
        for beat in (2, 3):
            step = int(rng.integers(-2, 3))
            nxt = melody[-1][1] + step * 2
            nxt = max(root + 7, min(root + 24, nxt))
            melody.append((bar * 4 + beat, nxt, 1))

    if style == "lofi":
        piano, bass, drums, texture = (Track(bpm, total) for _ in range(4))
        texture.wind(0, total, vel=0.35)
        for i in range(bars):
            b, ch = i * 4, chords[i % len(chords)]
            texture.pad(b, ch, 4, vel=0.22, attack=1.5, cutoff=1500)
            for k, note in enumerate(ch + [ch[1] + 12]):
                piano.piano(b + k, note, 1.5, vel=0.75)
            bass.synthbass(b, ch[0] - 12, 3.5, vel=0.7, cutoff=300)
            drums.kick(b, vel=0.7)
            drums.snare(b + 2, vel=0.55)
            for k in range(8):
                drums.hat(b + k * 0.5, vel=0.22)
        stems = {"piano": piano, "bass": bass, "drums": drums,
                 "texture": texture}
        gains = {"piano": 1.0, "bass": 0.9, "drums": 0.8, "texture": 0.5}
    elif style == "synthwave":
        bass, pads, lead, drums = (Track(bpm, total) for _ in range(4))
        for i in range(bars):
            b, ch = i * 4, chords[i % len(chords)]
            pads.pad(b, ch, 4, vel=0.6, attack=0.8, cutoff=2200)
            root_b = ch[0] - 12
            arp = [root_b, root_b + 7, root_b + 12, root_b + 7]
            for k in range(8):
                bass.synthbass(b + k * 0.5, arp[k % 4], 0.45, vel=0.85,
                               cutoff=900)
            for beat in range(4):
                drums.kick(b + beat, vel=0.95)
                if beat % 2 == 1:
                    drums.snare(b + beat, vel=0.85)
                drums.hat(b + beat, vel=0.4)
                drums.hat(b + beat + 0.5, vel=0.25)
        for b, note, d in melody:
            lead.lead(b, note, d, vel=0.85)
        stems = {"bass": bass, "pads": pads, "lead": lead, "drums": drums}
        gains = {"bass": 1.0, "pads": 0.8, "lead": 0.9, "drums": 0.95}
    elif style == "folk":
        pluck, flute, bass, brush = (Track(bpm, total) for _ in range(4))
        for i in range(bars):
            b, ch = i * 4, chords[i % len(chords)]
            seq = [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1]]
            for k, note in enumerate(seq):
                pluck.pluck(b + k * 0.5, note + 12, 2.0, vel=0.7)
            bass.bass(b, ch[0] - 12, 1.8, vel=0.65, cutoff=420)
            bass.bass(b + 2, ch[1] - 12, 1.8, vel=0.55, cutoff=420)
            for beat in range(4):
                brush.hat(b + beat, vel=0.20)
        for b, note, d in melody:
            flute.flute(b, note, d, vel=0.85)
        stems = {"pluck": pluck, "flute": flute, "bass": bass,
                 "brush": brush}
        gains = {"pluck": 1.0, "flute": 0.95, "bass": 0.8, "brush": 0.6}
    elif style == "dark":
        organ, choir, drums, texture = (Track(bpm, total) for _ in range(4))
        texture.wind(0, total, vel=0.6)
        texture.bass(0, root - 24, total, vel=0.5, cutoff=200)
        for i in range(bars):
            b, ch = i * 4, chords[i % len(chords)]
            for note in ch:
                organ.organ(b, note, 4, vel=0.6)
            choir.choir(b, [ch[0] + 12, ch[2] + 12], 4, vel=0.5)
            if i % 2 == 0:
                drums.taiko(b, vel=0.6)
                drums.taiko(b + 2, vel=0.35)
        for b in range(total):
            drums.hat(b, vel=0.14)
        stems = {"organ": organ, "choir": choir, "drums": drums,
                 "texture": texture}
        gains = {"organ": 0.9, "choir": 0.8, "drums": 0.7, "texture": 0.7}
    else:  # epic
        strings, bass, drums, horn = (Track(bpm, total) for _ in range(4))
        for i in range(bars):
            b, ch = i * 4, chords[i % len(chords)]
            strings.pad(b, ch, 4, vel=0.75, attack=0.3)
            for k in range(8):
                bass.bass(b + k * 0.5, ch[0] - 12, 0.45, vel=0.9,
                          cutoff=750)
            horn.brass(b, ch[2], 1.6, vel=0.8)
            horn.brass(b + 2, ch[3] if len(ch) > 3 else ch[1], 1.6,
                       vel=0.8)
            drums.taiko(b, vel=0.95)
            drums.taiko(b + 2, vel=0.9)
            drums.crash(b, vel=0.5) if i == 0 else None
        for b, note, d in melody:
            horn.lead(b, note, d * 0.96, vel=0.95)
        stems = {"strings": strings, "bass": bass, "drums": drums,
                 "horn": horn}
        gains = {"strings": 0.85, "bass": 0.9, "drums": 1.0, "horn": 1.0}
    return name, stems, gains, WET[style], 0.80
