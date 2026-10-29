# Neon Drive - synthwave, Sonic Pi
# 100 bpm, 8 bars, about 19 seconds plus reverb tail.
# No live_loop, so it ends on its own.
# Variable names avoid Sonic Pi built-ins (no "chord" as a variable).

use_bpm 100

with_fx :reverb, mix: 0.2 do
  with_fx :echo, phase: 0.25, decay: 2 do
    8.times do |bar|
      neon_prog = [
        [:C3, :Eb3, :G3],
        [:Ab2, :C3, :Eb3],
        [:F3, :Ab3, :C4],
        [:G2, :Bb2, :D3]
      ]
      neon_now = neon_prog[bar % 4]

      use_synth :dsaw
      play neon_now[0] + 12, amp: 0.25, attack: 0.1, release: 1.5
      play neon_now[1] + 12, amp: 0.25, attack: 0.1, release: 1.5
      play neon_now[2] + 12, amp: 0.25, attack: 0.1, release: 1.5

      use_synth :tb303
      play neon_now[0] - 12, amp: 0.4, release: 0.5, cutoff: 90

      sample :bd_tek, amp: 0.8
      sleep 1
      sample :drum_cymbal_closed, amp: 0.25
      sleep 0.5
      sample :elec_hi_snare, amp: 0.5
      sleep 0.5
      sample :bd_tek, amp: 0.8
      sleep 1
      sample :drum_cymbal_closed, amp: 0.25

      use_synth :saw
      play neon_now[2] + 24, amp: 0.2, release: 0.5
      sleep 1
    end
  end
end
