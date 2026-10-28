"""New demo tracks for the Music Tool.

Styles beyond the original epic game music:
  rainy-window  - lo-fi / chill
  neon-drive    - synthwave
  porch-light   - folk / acoustic
  hollow-house  - dark ambient / horror

All sounds come from synth.py. No samples. No recordings.
Each track returns aligned stems plus a mix, like the original tool.
"""
import os
import subprocess
import shutil
import numpy as np

from synth import Track, reverb_stereo, limiter, write_wav, SR

NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def n(name):
    """'D3' / 'F#4' / 'Bb2' -> midi number."""
    note = name[0].upper()
    i = 1
    acc = 0
    if i < len(name) and name[i] == "#":
        acc = 1
        i += 1
    elif i < len(name) and name[i] in ("b", "B"):
        acc = -1
        i += 1
    octave = int(name[i:])
    return 12 * (octave + 1) + NAMES[note] + acc


def _wav_to_mp3(wav_path):
    mp3_path = wav_path[:-4] + ".mp3"
    if not shutil.which("ffmpeg"):
        return wav_path
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", wav_path,
         "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path],
        check=True)
    os.remove(wav_path)
    return mp3_path


def render(name, stems, gains, out_dir, stems_only=False, mix_only=False,
           reverb_wet=0.20, ceiling=0.89):
    """Write stems and/or mix as MP3. Returns list of MP3 paths.

    Ceiling is the WAV peak before MP3 encoding. Presets use 0.89.
    Agent-made tracks use 0.80, so MP3 decode overshoot (which can
    push a 0.89 WAV mix just over 1.0, as a short synthwave test did)
    stays inside the QC peak range.
    """
    os.makedirs(out_dir, exist_ok=True)
    for s in stems.values():
        s.trim()
    bufs = {}
    for sname, trk in stems.items():
        bufs[sname] = trk.buf.astype(np.float64) * gains.get(sname, 1.0)
    made = []
    if not mix_only:
        for sname, b in bufs.items():
            wav = os.path.join(out_dir, f"{name}-stem-{sname}.wav")
            write_wav(wav, limiter(b, ceiling=ceiling))
            made.append(_wav_to_mp3(wav))
    if not stems_only:
        mix = sum(bufs.values())
        stereo = limiter(reverb_stereo(mix, wet=reverb_wet, decay=2.2),
                         ceiling=ceiling)
        wav = os.path.join(out_dir, f"{name}-mix.wav")
        write_wav(wav, stereo)
        made.append(_wav_to_mp3(wav))
        peak = float(np.max(np.abs(stereo)))
        rms = float(np.sqrt(np.mean(stereo ** 2)))
        dur = len(stereo) / SR
        print(f"{name}: {dur:.1f}s peak={peak:.3f} rms={rms:.3f}")
    return made


# ------------------------------------------------------------ LO-FI / CHILL
def rainy_window():
    """Lo-fi chill. A minor, 72 BPM, 48 beats = 40.0 s."""
    bpm, total = 72, 48
    piano = Track(bpm, total)
    bass = Track(bpm, total)
    drums = Track(bpm, total)
    texture = Track(bpm, total)
    Am = [n("A3"), n("C4"), n("E4")]
    F = [n("F3"), n("A3"), n("C4")]
    C = [n("C3"), n("E3"), n("G3")]
    G = [n("G3"), n("B3"), n("D4")]
    prog = [Am, F, C, G] * 3
    texture.wind(0, total, vel=0.35)
    for i, ch in enumerate(prog):
        b = i * 4
        # soft pad bed under the wind, so the texture never drops out
        # when the wind swell dips low
        texture.pad(b, ch, 4, vel=0.22, attack=1.5, cutoff=1500)
        # soft piano: chord tones, one per beat
        for k, note in enumerate(ch + [ch[1] + 12]):
            piano.piano(b + k, note, 1.5, vel=0.75)
        bass.synthbass(b, ch[0] - 12, 3.5, vel=0.7, cutoff=300)
        drums.kick(b, vel=0.7)
        drums.snare(b + 2, vel=0.55)
        for k in range(8):
            drums.hat(b + k * 0.5, vel=0.22)
    stems = {"piano": piano, "bass": bass, "drums": drums, "texture": texture}
    return "rainy-window", stems, {"piano": 1.0, "bass": 0.9,
                                   "drums": 0.8, "texture": 0.5}


# -------------------------------------------------------------- SYNTHWAVE
def neon_drive():
    """Synthwave. C minor, 100 BPM, 64 beats = 38.4 s."""
    bpm, total = 100, 64
    bass = Track(bpm, total)
    pads = Track(bpm, total)
    lead = Track(bpm, total)
    drums = Track(bpm, total)
    Cm = [n("C3"), n("Eb3"), n("G3"), n("C4")]
    Ab = [n("Ab2"), n("C3"), n("Eb3"), n("Ab3")]
    Eb = [n("Eb3"), n("G3"), n("Bb3"), n("Eb4")]
    Bb = [n("Bb2"), n("D3"), n("F3"), n("Bb3")]
    prog = [Cm, Ab, Eb, Bb] * 2
    for i, ch in enumerate(prog):
        b = i * 8
        pads.pad(b, ch, 8, vel=0.6, attack=0.8, cutoff=2200)
        root = ch[0] - 12
        # driving 8th-note synth-bass arpeggio: root, fifth, octave, fifth
        arp = [root, root + 7, root + 12, root + 7]
        for k in range(16):
            bass.synthbass(b + k * 0.5, arp[k % 4], 0.45, vel=0.85,
                           cutoff=900)
        for beat in range(8):
            drums.kick(b + beat, vel=0.95)
            if beat % 2 == 1:
                drums.snare(b + beat, vel=0.85)
            drums.hat(b + beat, vel=0.4)
            drums.hat(b + beat + 0.5, vel=0.25)
    # intro motif, so the lead is present from the start, not only
    # in the second half
    intro = [(0, "C5", 2), (4, "Eb5", 2), (8, "G4", 2), (12, "Bb4", 2),
             (16, "C5", 2), (20, "Bb4", 2), (24, "G4", 2), (28, "Eb4", 2)]
    for b, note, d in intro:
        lead.lead(b, n(note), d, vel=0.7)
    melody = [(32, "G4", 2), (34, "Bb4", 2), (36, "C5", 2), (38, "Eb5", 2),
              (40, "C5", 2), (42, "Bb4", 2), (44, "G4", 4),
              (48, "Eb4", 2), (50, "F4", 2), (52, "G4", 2), (54, "Bb4", 2),
              (56, "C5", 4), (60, "Bb4", 4)]
    for b, note, d in melody:
        lead.lead(b, n(note), d, vel=0.9)
    stems = {"bass": bass, "pads": pads, "lead": lead, "drums": drums}
    return "neon-drive", stems, {"bass": 1.0, "pads": 0.8,
                                 "lead": 0.9, "drums": 0.95}


# ----------------------------------------------------------- FOLK / ACOUSTIC
def porch_light():
    """Folk acoustic. G major, 90 BPM, 48 beats = 32.0 s."""
    bpm, total = 90, 48
    pluck = Track(bpm, total)
    flute = Track(bpm, total)
    bass = Track(bpm, total)
    brush = Track(bpm, total)
    G = [n("G2"), n("B2"), n("D3")]
    C = [n("C3"), n("E3"), n("G3")]
    D = [n("D3"), n("F#3"), n("A3")]
    Em = [n("E2"), n("G2"), n("B2")]
    prog = [G, C, G, D, G, C, G, D, Em, C, G, D]
    for i, ch in enumerate(prog):
        b = i * 4
        # finger-picked pluck: root, third, fifth, octave, fifth, third
        seq = [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1]]
        for k, note in enumerate(seq):
            pluck.pluck(b + k * 0.5, note + 12, 2.0, vel=0.7)
        bass.bass(b, ch[0] - 12, 1.8, vel=0.65, cutoff=420)
        bass.bass(b + 2, ch[1] - 12, 1.8, vel=0.55, cutoff=420)
        for beat in range(4):
            brush.hat(b + beat, vel=0.20)
    melody = [(0, "G4", 3), (4, "D4", 2), (6, "E4", 2), (8, "G4", 3),
              (12, "E4", 2),
              (16, "D4", 2), (20, "B3", 3), (24, "D4", 2), (28, "G4", 2),
              (32, "A4", 3), (36, "G4", 2), (40, "E4", 2), (44, "D4", 4)]
    for b, note, d in melody:
        flute.flute(b, n(note), d, vel=0.85)
    stems = {"pluck": pluck, "flute": flute, "bass": bass, "brush": brush}
    return "porch-light", stems, {"pluck": 1.0, "flute": 0.95,
                                  "bass": 0.8, "brush": 0.6}


# ------------------------------------------------------- DARK AMBIENT / HORROR
def hollow_house():
    """Dark ambient horror. D minor, 60 BPM, 48 beats = 48.0 s."""
    bpm, total = 60, 48
    organ = Track(bpm, total)
    choir = Track(bpm, total)
    drums = Track(bpm, total)
    texture = Track(bpm, total)
    texture.wind(0, total, vel=0.6)
    texture.bass(0, n("D1"), total, vel=0.5, cutoff=200)
    Dm = [n("D3"), n("F3"), n("A3")]
    Bb = [n("Bb2"), n("D3"), n("F3")]
    # dissonant cluster: D + Eb a semitone apart, slow and low
    cluster = [n("D3"), n("Eb3"), n("A3")]
    for i, ch in enumerate([Dm, Bb, cluster, Dm]):
        b = i * 12
        for note in ch:
            organ.organ(b, note, 11, vel=0.6)
        # choir sings only root + fifth, an octave up, with its own
        # vibrato voice -- not the same notes or shape as the organ
        choir.choir(b, [ch[0] + 12, ch[2] + 12], 11, vel=0.5)
    for b in (0, 12, 24, 36):
        drums.taiko(b, vel=0.6)
        drums.taiko(b + 6, vel=0.35)
    # soft clock tick every beat, so the sparse drum stem never
    # sits silent for long stretches between taiko hits
    for b in range(total):
        drums.hat(b, vel=0.14)
    drums.taiko(44, vel=0.9)
    stems = {"organ": organ, "choir": choir, "drums": drums,
             "texture": texture}
    return "hollow-house", stems, {"organ": 0.9, "choir": 0.8,
                                   "drums": 0.7, "texture": 0.7}


DEMOS = {
    "rainy-window": (rainy_window, 0.28),
    "neon-drive": (neon_drive, 0.16),
    "porch-light": (porch_light, 0.20),
    "hollow-house": (hollow_house, 0.32),
}
