Music Tool
==========

What it is
----------
A small tool that makes music from math.
It does not use samples. It does not use recordings.
Each sound is built from sound waves in code.

How stems work
--------------
Each instrument gets its own file. That file is a stem.
All stems line up in time.
A mix is all the stems added together.
You can use one stem on its own. You can also use the mix.

How to run it
--------------
First, install the parts it needs:

    pip install -r requirements.txt

You also need ffmpeg for MP3 files. Most systems have it.

List the tracks:

    python3 music_tool.py list

Make one track:

    python3 music_tool.py render rainy-window

Make all 4 new demos:

    python3 music_tool.py render-all

Make stems only, no mix:

    python3 music_tool.py render neon-drive --stems-only

Make a mix only, no stems:

    python3 music_tool.py render porch-light --mix-only

Files go in the `out/` folder.

What the new demos show
------------------------
The first version made epic game music.
This version adds 4 new styles:

- rainy-window: lo-fi and chill. Soft piano, mellow bass, soft drums.
- neon-drive: synthwave. Driving bass, pads, lead, steady drums.
- porch-light: folk and acoustic. Plucked guitar, flute, soft bass.
- hollow-house: dark ambient and horror. Organ drone, choir pad, sparse drums.

It also adds 4 new instruments:
piano, flute, organ, and synth bass.
They use the same math engine as the old instruments.

How to check the files
-----------------------
Run the QC check:

    python3 qc.py

It checks each MP3. It checks the file decodes.
It checks it is not silent. It checks peak and loudness.
It checks there is no long silence gap.
It checks stems for one track are not copies of each other.

Old files
---------
The files `synth.py`, `compose.py`, `compose5.py`, `compose6.py`,
`compose_danger.py`, `compose_stingers.py`, `radio.py`, `sfx.py`,
`sfx2.py`, and `sfx3.py` come from the first game music work.
They are kept with the same names so you can see where they came from.
`synth.py` has new instruments added at the end.
`demos.py` holds the 4 new tracks.
`presets.json` holds tempo, key, mood, and sections for each track.
