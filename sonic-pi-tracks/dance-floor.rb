# Dance Floor - upbeat dance, Sonic Pi
# 120 bpm, 8 bars, about 16 seconds plus reverb tail.
# No live_loop, so it ends on its own.
# Variable names avoid Sonic Pi built-ins (no "chord" as a variable).

use_bpm 120

with_fx :reverb, mix: 0.15 do
  8.times do |bar|
    dance_prog = [
      [:C4, :E4, :G4],
      [:A3, :C4, :E4],
      [:F3, :A3, :C4],
      [:G3, :B3, :D4]
    ]
    dance_now = dance_prog[bar % 4]

    use_synth :saw
    play dance_now[0], amp: 0.25, attack: 0.05, release: 0.8
    play dance_now[1], amp: 0.25, attack: 0.05, release: 0.8
    play dance_now[2], amp: 0.25, attack: 0.05, release: 0.8

    use_synth :tb303
    play dance_now[0] - 12, amp: 0.4, release: 0.4, cutoff: 110

    sample :bd_haus, amp: 0.9
    sleep 1
    sample :drum_cymbal_closed, amp: 0.3
    sleep 0.5
    sample :drum_snare_hard, amp: 0.5
    sleep 0.5
    sample :bd_haus, amp: 0.9
    sleep 1
    sample :drum_cymbal_closed, amp: 0.3

    use_synth :square
    play dance_now[2] + 12, amp: 0.2, release: 0.4
    sleep 1
  end
end
