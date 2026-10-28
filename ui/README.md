# Music Tool UI

A web page for the Music Tool. Plain HTML, CSS, and JavaScript.
No build step. No npm. No outside files, fonts, or CDNs.
The server uses only the Python standard library.

## Run it

From the `music-tool` folder:

    python3 server.py

Then open this address in a browser:

    http://localhost:8900

To use a different port:

    python3 server.py --port 8901

Then open `http://localhost:8901`.

## Stop it

Press Ctrl+C in the terminal where the server runs.

## What the page has

1. Make music. A form for name, style, tempo, key, bars, and seed.
   Press Make. You get a mix player, a player for each stem, and a
   QC pass or fail badge.
2. Ready-made tracks. The 10 preset tracks, with a style filter.
   Each track has a mix player and parts you can open.
3. Old game music. Search the 255 old mixes, 20 per page.
   Each song has its own player.
4. How it works. Short plain sentences, plus the commands agents use.

## What each API does

- `GET /api/tracks?q=&style=&limit=&offset=`
  Preset tracks plus old mixes. `q` searches names.
  `style` filters presets. Old mixes come back 20 per page.
  Use `limit` and `offset` to page through the old mixes.
- `GET /api/track?name=`
  Mix and stem links for one track. For an old mix, mix only.
  For a track made in the UI, its own mix and stems.
- `POST /api/make` with JSON like:
  `{"name": "my-track", "style": "lofi", "tempo": 80, "key": "C minor", "bars": 8, "seed": 7}`
  Makes a new track in `out/ui/<name>/` and returns its JSON
  plus file links. A bad name or style returns a JSON error
  with a non-200 status, not a stack trace.
- `POST /api/qc` with JSON `{"track": "my-track"}` or `{"dir": "ui/my-track"}`
  Runs QC and returns its JSON. Folders must be under `out/`.
- `GET /audio/demos/<file>` — a preset demo MP3 from `out/`.
- `GET /audio/old/<file>` — an old mix MP3 from `old-game-music/mixes/`.
- `GET /audio/ui/<track>/<file>` — a UI-made MP3 from `out/ui/<track>/`.

Audio links reject any name with `..` or `/` in it.

## Limits, stated plainly

- The server is local only. It is not a public host.
  It listens on your own machine by default (`127.0.0.1`).
  Do not expose it to the internet without adding real security first.
- Preset tracks that have not been rendered on this machine show
  a note instead of a player. Render one with, for example:
  `python3 music_tool.py render loading-theme`
- The old game music here is mixes only. Its stems are not in
  this repo yet.
- The server needs ffmpeg and the Python packages in
  `requirements.txt` to make and check music, just like the CLI.
