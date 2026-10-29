# Hollow Night - dark ambient, Sonic Pi
# 60 bpm, 6 bars, about 24 seconds plus reverb tail.
# Slow, sparse, and low. No live_loop, so it ends on its own.
# Variable names avoid Sonic Pi built-ins (no "chord" as a variable).

use_bpm 60

with_fx :reverb, mix: 0.6 do
  6.times do |bar|
    dark_prog = [
      [:D3, :F3, :A3],
      [:D3, :F3, :A3],
      [:Bb2, :D3, :F3],
      [:C3, :Eb3, :G3]
    ]
    dark_now = dark_prog[bar % 4]

    use_synth :hollow
    play dark_now[0], amp: 0.3, attack: 2, release: 4
    play dark_now[1], amp: 0.3, attack: 2, release: 4
    play dark_now[2], amp: 0.3, attack: 2, release: 4

    use_synth :sine
    play dark_now[0] - 12, amp: 0.35, attack: 1, release: 3

    sample :bd_boom, amp: 0.5
    sleep 2
    sample :drum_cymbal_soft, amp: 0.15
    sleep 1

    use_synth :hollow
    play dark_now[2] + 12, amp: 0.2, attack: 1, release: 2
    sleep 1
  end
end
