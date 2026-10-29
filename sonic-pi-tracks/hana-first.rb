# Hana's first Sonic Pi track
# Made from the docs in ~/workspace/sonic-pi
# play = a note, sleep = wait in beats, sample = a recorded sound
# This is a short, finite piece: 8 bars, about 24 seconds at 80 bpm.
# No live_loop, so it ends on its own and can be recorded cleanly.

use_bpm 80

with_fx :reverb, mix: 0.3 do
  8.times do |bar|
    # Chords: C minor, Ab major, Eb major, Bb major, then repeat
    # Note: "chord" is a built-in Sonic Pi name, so it cannot be a variable.
    # Using prog_notes instead.
    prog_notes = [
      [:C4, :Eb4, :G4],
      [:Ab3, :C4, :Eb4],
      [:Eb4, :G4, :Bb4],
      [:Bb3, :D4, :F4]
    ]
    now_notes = prog_notes[bar % 4]

    # Pad chord, soft
    use_synth :prophet
    play now_notes[0], amp: 0.3, attack: 0.5, release: 3
    play now_notes[1], amp: 0.3, attack: 0.5, release: 3
    play now_notes[2], amp: 0.3, attack: 0.5, release: 3

    # Bass note, low
    use_synth :tb303
    play now_notes[0] - 12, amp: 0.4, release: 0.8, cutoff: 80

    # Drums, one bar = 4 beats
    sample :bd_haus, amp: 0.8
    sleep 1
    sample :drum_cymbal_closed, amp: 0.3
    sleep 0.5
    sample :elec_snare, amp: 0.5
    sleep 0.5
    sample :bd_haus, amp: 0.8
    sleep 1
    sample :drum_cymbal_closed, amp: 0.3

    # Simple melody note on beat 4, from the chord
    use_synth :tri
    play now_notes[2] + 12, amp: 0.35, release: 0.8
    sleep 1
  end
end
