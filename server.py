#!/usr/bin/env python3
"""Music Tool web server. Local only. No build step. Python stdlib only.

Run:
    python3 server.py
    python3 server.py --port 8901
Then open http://localhost:8900 in a browser.

Serves:
  /                     -> ui/index.html
  /app.js, /styles.css  -> ui/ static files
  GET  /api/tracks?q=&style=&limit=&offset=
  GET  /api/track?name=
  POST /api/make   {name, style, tempo, key, bars, seed}
  POST /api/qc     {dir} or {track}
  GET  /audio/demos/<file>          (from out/)
  GET  /audio/old/<file>            (from old-game-music/mixes/)
  GET  /audio/ui/<track>/<file>     (from out/ui/<track>/)

Safety rules:
- Audio and QC paths never accept ".." or "/" inside a file name.
- QC only accepts folders under out/. Nothing outside out/ is checked.
- Bad make input returns a JSON error with a non-200 status.
  A stack trace is never sent as the main response.
"""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(HERE, "ui")
OUT_DIR = os.path.join(HERE, "out")
OLD_DIR = os.path.join(HERE, "old-game-music", "mixes")
MANIFEST = os.path.join(HERE, "old-game-music", "MANIFEST.csv")
PRESETS = os.path.join(HERE, "presets.json")
CLI = os.path.join(HERE, "music_tool.py")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
STYLES = ["lofi", "synthwave", "folk", "dark", "epic"]
STYLE_DEFAULTS = {
    "lofi": (72, "A minor"),
    "synthwave": (100, "C minor"),
    "folk": (90, "G major"),
    "dark": (60, "D minor"),
    "epic": (92, "D minor"),
}


def load_presets():
    with open(PRESETS) as f:
        return json.load(f)["tracks"]


def load_old_mixes():
    mixes = []
    with open(MANIFEST, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("kind") == "mix":
                name = row["filename"][:-4] if row["filename"].endswith(".mp3") else row["filename"]
                mixes.append({"name": name, "file": row["filename"],
                              "size_bytes": int(row["size_bytes"])})
    mixes.sort(key=lambda m: m["name"])
    return mixes


def preset_files(name):
    """Files on disk for a preset/demo track, as API file objects."""
    mix_path = os.path.join(OUT_DIR, f"{name}-mix.mp3")
    files = []
    if os.path.exists(mix_path):
        files.append({"path": mix_path, "kind": "mix", "stem": None,
                      "url": f"/audio/demos/{name}-mix.mp3"})
    for stem in sorted(os.path.basename(p) for p in
                       glob.glob(os.path.join(OUT_DIR, f"{name}-stem-*.mp3"))):
        stem_name = stem[len(name) + 6:-4]  # strip "<name>-stem-" and ".mp3"
        files.append({"path": os.path.join(OUT_DIR, stem), "kind": "stem",
                      "stem": stem_name, "url": f"/audio/demos/{stem}"})
    return files


def public_files(files):
    """API file objects: kind, stem, url only. Never leak local paths."""
    return [{"kind": f["kind"], "stem": f["stem"], "url": f["url"]}
            for f in files]


def ui_files(name):
    d = os.path.join(OUT_DIR, "ui", name)
    if not os.path.isdir(d):
        return []
    files = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".mp3"):
            continue
        if fn.endswith("-mix.mp3"):
            files.append({"path": os.path.join(d, fn), "kind": "mix",
                          "stem": None, "url": f"/audio/ui/{name}/{fn}"})
        elif "-stem-" in fn:
            files.append({"path": os.path.join(d, fn), "kind": "stem",
                          "stem": fn.split("-stem-")[1][:-4],
                          "url": f"/audio/ui/{name}/{fn}"})
    files.sort(key=lambda f: (f["kind"] != "mix", f["stem"] or ""))
    return files


def qc_files(file_paths):
    """Run the same checks as qc.py on an explicit file list."""
    import numpy as np
    sys.path.insert(0, HERE)
    import qc
    results = []
    decoded = {}
    failures = 0
    for path in file_paths:
        try:
            problems, x, info = qc.check_file(path, quiet=True)
        except Exception:
            results.append({"file": os.path.basename(path), "path": path,
                            "problems": ["not decodable"]})
            failures += 1
            continue
        decoded[path] = x
        results.append(info)
        if problems:
            failures += 1
    stems = {}
    by_track = {}
    for path in file_paths:
        base = os.path.basename(path)
        if "-stem-" in base:
            by_track.setdefault(base.split("-stem-")[0], []).append(path)
    for track, paths in sorted(by_track.items()):
        if len(paths) < 2 or any(p not in decoded for p in paths):
            stems[track] = {"stems": len(paths), "worst_corr": None,
                            "pass": True, "note": "skipped"}
            continue
        worst = 0.0
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                a, b = decoded[paths[i]], decoded[paths[j]]
                n = min(len(a), len(b))
                if n:
                    worst = max(worst, abs(float(np.corrcoef(a[:n], b[:n])[0, 1])))
        ok = worst < 0.99
        if not ok:
            failures += 1
        stems[track] = {"stems": len(paths), "worst_corr": worst, "pass": ok}
    return {"files": results, "stems": stems,
            "files_checked": len(results), "failures": failures,
            "pass": failures == 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep logs short
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---------- helpers ----------
    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type):
        if not os.path.isfile(path):
            self.send_json({"error": "not found"}, status=404)
            return
        size = os.path.getsize(path)
        range_header = self.headers.get("Range")
        start, end = 0, size - 1
        status = 200
        if range_header and range_header.startswith("bytes="):
            try:
                parts = range_header[6:].split("-", 1)
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else size - 1
                end = min(end, size - 1)
                status = 206
            except ValueError:
                pass
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode()) if raw else {}
        except (ValueError, UnicodeDecodeError):
            return None

    # ---------- GET ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self.send_file(os.path.join(UI_DIR, "index.html"), "text/html")
        if path == "/app.js":
            return self.send_file(os.path.join(UI_DIR, "app.js"), "application/javascript")
        if path == "/styles.css":
            return self.send_file(os.path.join(UI_DIR, "styles.css"), "text/css")
        if path == "/api/tracks":
            return self.api_tracks(qs)
        if path == "/api/track":
            return self.api_track(qs)
        if path.startswith("/audio/demos/"):
            fn = unquote(path[len("/audio/demos/"):])
            if not FILE_RE.match(fn) or ".." in fn:
                return self.send_json({"error": "bad file name"}, status=400)
            return self.send_file(os.path.join(OUT_DIR, fn), "audio/mpeg")
        if path.startswith("/audio/old/"):
            fn = unquote(path[len("/audio/old/"):])
            if not FILE_RE.match(fn) or ".." in fn:
                return self.send_json({"error": "bad file name"}, status=400)
            return self.send_file(os.path.join(OLD_DIR, fn), "audio/mpeg")
        if path.startswith("/audio/ui/"):
            rest = unquote(path[len("/audio/ui/"):])
            parts = rest.split("/")
            if len(parts) != 2 or not NAME_RE.match(parts[0]) or not FILE_RE.match(parts[1]) or ".." in rest:
                return self.send_json({"error": "bad path"}, status=400)
            return self.send_file(os.path.join(OUT_DIR, "ui", parts[0], parts[1]), "audio/mpeg")
        return self.send_json({"error": "not found"}, status=404)

    def api_tracks(self, qs):
        q = (qs.get("q", [""])[0] or "").strip().lower()
        style = (qs.get("style", [""])[0] or "").strip().lower()
        try:
            limit = int(qs.get("limit", ["20"])[0])
            offset = int(qs.get("offset", ["0"])[0])
        except ValueError:
            return self.send_json({"error": "limit and offset must be numbers"}, status=400)
        limit = max(1, min(limit, 50))
        offset = max(0, offset)
        presets = load_presets()
        if q:
            presets = [t for t in presets if q in t["name"].lower() or q in t.get("mood", "").lower()]
        if style:
            presets = [t for t in presets if style in t["style"].lower()]
        old = load_old_mixes()
        if q:
            old = [m for m in old if q in m["name"].lower()]
        total_old = len(old)
        page = old[offset:offset + limit]
        for m in page:
            m["url"] = f"/audio/old/{m['file']}"
        return self.send_json({"presets": presets, "old": page,
                               "total_old": total_old, "limit": limit,
                               "offset": offset})

    def api_track(self, qs):
        name = (qs.get("name", [""])[0] or "").strip()
        if not name or "/" in name or ".." in name:
            return self.send_json({"error": "bad track name"}, status=400)
        base = name[:-4] if name.endswith(".mp3") else name
        ui = ui_files(base)
        if ui:
            pub = public_files(ui)
            mix = next((f for f in pub if f["kind"] == "mix"), None)
            return self.send_json({"name": base, "source": "ui", "mix": mix,
                                   "stems": [f for f in pub if f["kind"] == "stem"],
                                   "files": pub})
        old_path = os.path.join(OLD_DIR, f"{base}.mp3")
        if os.path.exists(old_path):
            mix = {"kind": "mix", "stem": None, "url": f"/audio/old/{base}.mp3"}
            return self.send_json({"name": base, "source": "old",
                                   "mix": mix, "stems": [], "files": [mix]})
        files = preset_files(base)
        if files:
            pub = public_files(files)
            mix = next((f for f in pub if f["kind"] == "mix"), None)
            return self.send_json({"name": base, "source": "preset",
                                   "mix": mix,
                                   "stems": [f for f in pub if f["kind"] == "stem"],
                                   "files": pub})
        return self.send_json({"error": f"unknown track: {base}"}, status=404)

    # ---------- POST ----------
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/make":
            return self.api_make()
        if parsed.path == "/api/qc":
            return self.api_qc()
        return self.send_json({"error": "not found"}, status=404)

    def api_make(self):
        data = self.read_json_body()
        if data is None:
            return self.send_json({"error": "body must be JSON"}, status=400)
        name = str(data.get("name", "")).strip()
        style = str(data.get("style", "")).strip().lower()
        if not NAME_RE.match(name):
            return self.send_json({"error": "bad name: use lowercase letters, digits, hyphens only, e.g. my-track"}, status=400)
        if style not in STYLES:
            return self.send_json({"error": "bad style: use lofi, synthwave, folk, dark, or epic"}, status=400)
        default_tempo, default_key = STYLE_DEFAULTS[style]
        try:
            tempo = int(data.get("tempo") or default_tempo)
            bars = int(data.get("bars") or 8)
            seed = int(data.get("seed") if data.get("seed") is not None else 42)
        except (TypeError, ValueError):
            return self.send_json({"error": "tempo, bars, and seed must be numbers"}, status=400)
        if not (40 <= tempo <= 200):
            return self.send_json({"error": "tempo must be 40 to 200"}, status=400)
        if not (1 <= bars <= 32):
            return self.send_json({"error": "bars must be 1 to 32"}, status=400)
        key = str(data.get("key") or default_key).strip()
        out_dir = os.path.join(OUT_DIR, "ui", name)
        os.makedirs(out_dir, exist_ok=True)
        cmd = [sys.executable, CLI, "make", name, "--style", style,
               "--tempo", str(tempo), "--key", key, "--bars", str(bars),
               "--seed", str(seed), "--out", out_dir, "--json"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return self.send_json({"error": "render timed out"}, status=500)
        if proc.returncode != 0:
            err = ""
            try:
                err = json.loads(proc.stdout).get("error", "")
            except (ValueError, AttributeError):
                err = (proc.stderr.strip().splitlines() or ["render failed"])[-1]
            print(f"make failed for {name}: {err}", file=sys.stderr)
            return self.send_json({"error": err or "render failed"}, status=400)
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            return self.send_json({"error": "render gave bad output"}, status=500)
        files = ui_files(name)
        pub = public_files(files)
        result["files"] = pub
        result["mix"] = next((f for f in pub if f["kind"] == "mix"), None)
        result["stems"] = [f for f in pub if f["kind"] == "stem"]
        return self.send_json(result)

    def api_qc(self):
        data = self.read_json_body()
        if data is None:
            return self.send_json({"error": "body must be JSON"}, status=400)
        files = None
        label = ""
        if data.get("track"):
            track = str(data["track"]).strip()
            if not NAME_RE.match(track):
                return self.send_json({"error": "bad track name"}, status=400)
            ui = ui_files(track)
            if ui:
                files, label = [f["path"] for f in ui], track
            else:
                preset = preset_files(track)
                if not preset:
                    return self.send_json({"error": f"unknown track: {track}"}, status=404)
                files, label = [f["path"] for f in preset], track
        elif data.get("dir"):
            d = str(data["dir"]).strip()
            if d.startswith("/") or ".." in d or "\\" in d:
                return self.send_json({"error": "dir must be under out/"}, status=400)
            import glob
            full = os.path.realpath(os.path.join(OUT_DIR, d))
            if not full.startswith(os.path.realpath(OUT_DIR) + os.sep) and full != os.path.realpath(OUT_DIR):
                return self.send_json({"error": "dir must be under out/"}, status=400)
            if not os.path.isdir(full):
                return self.send_json({"error": "no such folder"}, status=404)
            files = sorted(glob.glob(os.path.join(full, "*.mp3")))
            label = d
            if not files:
                return self.send_json({"error": "no MP3 files in that folder"}, status=404)
        else:
            return self.send_json({"error": "send {track} or {dir}"}, status=400)
        try:
            result = qc_files(files)
        except Exception as exc:  # never leak a stack trace to the client
            print(f"qc failed for {label}: {exc}", file=sys.stderr)
            return self.send_json({"error": "qc failed"}, status=500)
        result["track"] = label
        return self.send_json(result)


def main():
    ap = argparse.ArgumentParser(description="Music Tool web server (local only)")
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Music Tool UI: http://{args.host}:{args.port}  (Ctrl+C to stop)")
    print(f"Serving: {HERE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
