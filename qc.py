#!/usr/bin/env python3
"""QC check for Music Tool MP3s.

Checks each demo mix and stem in out/:
  - the file decodes with ffmpeg (ffprobe finds a stream)
  - it is not silent (RMS above 0.005)
  - peak is sane (0.05 to 1.0) and RMS is sane (0.01 to 0.60)
  - no silence gap longer than 2 seconds inside the file
  - stems for one track are distinct, not copies of each other

Prints one line per file plus a summary. Exit 0 = pass, 1 = fail.
Run: python3 qc.py  or  python3 music_tool.py qc
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SR = 44100


def decode_mp3(path):
    """Decode MP3 to mono float32 via ffmpeg. Raises on failure."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def longest_silence(x, thresh=0.005):
    """Longest run of near-silent 0.1 s windows, in seconds."""
    win = int(SR * 0.1)
    nwin = max(1, len(x) // win)
    rms = np.array([np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2) + 1e-12)
                    for i in range(nwin)])
    silent = rms < thresh
    best = cur = 0
    for s in silent:
        cur = cur + 1 if s else 0
        best = max(best, cur)
    return best * 0.1


def check_file(path, quiet=False):
    x = decode_mp3(path)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    dur = len(x) / SR
    gap = longest_silence(x)
    problems = []
    if rms < 0.005:
        problems.append("silent")
    if not (0.05 <= peak <= 1.0):
        problems.append(f"peak out of range ({peak:.3f})")
    if not (0.01 <= rms <= 0.60):
        problems.append(f"rms out of range ({rms:.3f})")
    if gap > 2.0:
        problems.append(f"silence gap {gap:.1f}s")
    status = "PASS" if not problems else "FAIL: " + "; ".join(problems)
    if not quiet:
        print(f"{os.path.basename(path):42} {dur:5.1f}s "
              f"peak={peak:.3f} rms={rms:.3f} gap={gap:.1f}s  {status}")
    return problems, x, {"file": os.path.basename(path), "path": path,
                         "duration_s": round(dur, 1), "peak": peak,
                         "rms": rms, "gap_s": gap, "problems": problems}


def main(out_dir=None, args_out=None, as_json=False):
    out_dir = out_dir or args_out or OUT
    files = sorted(glob.glob(os.path.join(out_dir, "*.mp3")))
    if not files:
        if as_json:
            print(json.dumps({"files": [], "failures": 1,
                              "error": f"No MP3 files found in {out_dir}"}))
        else:
            print(f"No MP3 files found in {out_dir}")
        return 1
    decoded = {}
    failures = 0
    results = []
    for path in files:
        try:
            problems, x, info = check_file(path, quiet=as_json)
        except subprocess.CalledProcessError:
            if as_json:
                results.append({"file": os.path.basename(path), "path": path,
                                "problems": ["not decodable"]})
            else:
                print(f"{os.path.basename(path)}  FAIL: not decodable")
            failures += 1
            continue
        decoded[path] = x
        results.append(info)
        if problems:
            failures += 1
    # stems distinct: pairwise correlation for stems of the same track
    stems_by_track = {}
    for path in files:
        base = os.path.basename(path)
        if "-stem-" in base:
            track = base.split("-stem-")[0]
            stems_by_track.setdefault(track, []).append(path)
    stem_results = {}
    if not as_json:
        print("\nStem distinct check (correlation must be below 0.99):")
    for track, paths in sorted(stems_by_track.items()):
        if len(paths) < 2:
            stem_results[track] = {"stems": len(paths), "worst_corr": None,
                                   "pass": True, "note": "skipped"}
            if not as_json:
                print(f"  {track}: only {len(paths)} stem(s), skipped")
            continue
        worst = 0.0
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                a, b = decoded[paths[i]], decoded[paths[j]]
                n = min(len(a), len(b))
                if n == 0:
                    continue
                corr = abs(float(np.corrcoef(a[:n], b[:n])[0, 1]))
                worst = max(worst, corr)
        ok = worst < 0.99
        if not ok:
            failures += 1
        stem_results[track] = {"stems": len(paths), "worst_corr": worst,
                               "pass": ok}
        if not as_json:
            print(f"  {track}: {len(paths)} stems, worst corr={worst:.3f} "
                  f"{'PASS' if ok else 'FAIL'}")
    if as_json:
        print(json.dumps({"files": results, "stems": stem_results,
                          "files_checked": len(files),
                          "failures": failures,
                          "pass": failures == 0}, indent=2))
    else:
        print(f"\n{len(files)} files checked, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
