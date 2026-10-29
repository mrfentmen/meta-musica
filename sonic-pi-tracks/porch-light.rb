# Porch Light - gentle folk, Sonic Pi
# 90 bpm, 8 bars, about 21 seconds plus reverb tail.
# No live_loop, so it ends on its own.
# Variable names avoid Sonic Pi built-ins (no "chord" as a variable).

use_bpm 90

with_fx :reverb, mix: 0.35 do
  8.times do |bar|
    folk_prog = [
      [:G3, :B3, :D4],
      [:C4, :E4, :G4],
      [:D4, :Fs4, :A4],
      [:G3, :B3, :D4]
    ]
    folk_now = folk_prog[bar % 4]

    use_synth :tri
    play folk_now[0], amp: 0.3, attack: 0.2, release: 2
    play folk_now[1], amp: 0.3, attack: 0.2, release: 2
    play folk_now[2], amp: 0.3, attack: 0.2, release: 2

    use_synth :sine
    play folk_now[0] - 12, amp: 0.3, release: 1.5

    sample :drum_cymbal_soft, amp: 0.2
    sleep 1
    sample :elec_tick, amp: 0.2
    sleep 0.5
    sample :elec_tick, amp: 0.15
    sleep 0.5
    sample :drum_cymbal_soft, amp: 0.2
    sleep 1
    sample :elec_tick, amp: 0.2

    use_synth :tri
    play folk_now[2] + 12, amp: 0.3, release: 1
    sleep 1
  end
end
