# Kasut Sekolah — TikTok review edit (HyperFrames)

9:16 TikTok edit (~53s) combining **"kasut sekolah 1.mov" (k1)** and **"Kasut sekolah 2.mov" (k2)**, built as a HyperFrames composition. Preview stage only — no final render.

## Edit summary
- **Script from both takes:** the best delivery of each line is used once; repeats, false starts and the second take of the same point are dropped. Every kept sentence plays in full. Pauses trimmed to 0.1s.
  1. Hook (k1): "Kalau kena air pun jangan risau… takkan tembus ke dalam" + text "kasut sekolah ni worth ke tak?"
  2. (k2) Ibu ayah cari kasut sekolah → memang recommend
  3. (k2) Harga murah, design sporty, cantik → mall takkan dapat harga bawah RM50
  4. (k1) Tapak anti-slip, selesa, bersukan → anak lasak
  5. (k2) Sangat ringan → tak payah tali, tarik & ketat, darjah 1–3
  6. (k1) Anak suka, kotor just lap
  7. (k2) CTA beg kuning → beli sekarang, takut size tak ada
- **Overlays:** small white Cweyons text, slow fade + slide, a "ting" on each. Placed per shot in empty space (top-left wall by default; right of the face in the close-up twist shots; dress area over the "ringan" b-roll). Never over face or product.
- **B-roll:** 3 full-screen product close-ups from unused footage (twist knobs, sole/anti-slip, ringan), cross-dissolve on the 100 BPM grid, gentle zoom + light sweep, whoosh.
- **Product zooms:** smooth zoom toward the shoe at RM50, tahan lasak and CTA moments + light sweep; twist-lock push-in with shimmer.
- **Audio:** cleaned voice at -15 LUFS, original synthesized clean/upbeat music low underneath, SFX (ting, whoosh, shimmer).
- No colour grade or filters on the footage.

## Rebuild
Run from a working dir containing `src/k1.mov`, `src/k2.mov` and `hf -> hyperframes/`:
```
python3 scripts/build_edl.py && python3 scripts/build_media.py --preview && python3 scripts/gen_comp.py
cd hf/kasut && npx hyperframes@0.9.26 preview            # studio preview
npx hyperframes@0.9.26 render -q draft                   # draft preview
```
Drop `--preview` from `build_media.py` for full 1080×1920 media before a final render.
