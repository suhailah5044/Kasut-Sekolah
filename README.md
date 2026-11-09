# Kasut Sekolah — TikTok review edit (HyperFrames)

9:16 TikTok edit (~60s) of the "kasut sekolah 1.mov" review, built as a HyperFrames composition.

## Edit summary
- **Hook (0–3s):** "Kalau kena air pun jangan risau… takkan tembus ke dalam" moved to the front + text "kasut sekolah ni worth ke tak?"
- **Cuts:** pauses trimmed to 0.1s; repeats and false starts removed (2nd/3rd "design cantik", repeated "ringan", "yang mana nak dapatkan", "ada main… tak kisahlah"). Every kept sentence plays in full.
- **Overlays:** small white Cweyons text in the empty top-left area (below TikTok's top bar, clear of face/product), slow fade + 14px slide, a "ting" on each.
- **B-roll:** 4 full-screen product close-ups ( soft light sweep, 0.45s cross-dissolve on the 100 BPM grid).
- **Twist-lock close-up:** light sweep + shimmer.
- **Audio:** cleaned voice at -15 LUFS, original synthesized clean/upbeat music low underneath, SFX (ting, whoosh, shimmer).
- No colour grade or filters on the footage.

## Rebuild
```
# put the source at src/kasut.mov, then:
python3 scripts/build_edl.py && python3 scripts/build_media.py && python3 scripts/gen_comp.py
cd hyperframes/kasut && npx hyperframes@0.9.26 preview            # studio preview
npx hyperframes@0.9.26 render -q draft                             # draft preview
```
(Scripts expect to run from a working dir containing `src/` and `hf/kasut/`; adjust paths as needed.)
