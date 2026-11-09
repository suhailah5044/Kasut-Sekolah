"""Generate the HyperFrames composition (hf/kasut/index.html) from the EDL + keyword list."""
import json, html

E = json.load(open("edl.json"))
edl, DUR = E["edl"], E["duration"]
BEAT = 0.6  # 100 BPM music grid


def out(src):
    for r in edl:
        if r["src_start"] - 1e-6 <= src <= r["src_end"] + 1e-6:
            return round(r["out_start"] + src - r["src_start"], 3)
    # in a removed pause -> next kept range
    nxt = min((r for r in edl if r["src_start"] > src), key=lambda r: r["src_start"])
    return nxt["out_start"]


def snap(t):
    return round(round(t / BEAT) * BEAT, 3)


# keyword overlays: (src time of the spoken word, text)
KEYWORDS = [
    (63.18, "tak tembus air"),
    (3.18, "2 minggu lagi cuti sekolah"),
    (9.74, "persiapan awal-awal"),
    (15.68, "stok & size masih ada"),
    (24.92, "super ringan"),
    (26.04, "sesuai sekolah rendah"),
    (31.56, "tapak anti-slip"),
    (42.10, "tahan lasak"),
    (45.94, "tiada tali"),
    (48.16, "twist lock"),
    (50.28, "tarik & ketat"),
    (54.08, "design cantik"),
    (56.50, "anak suka"),
    (58.22, "kotor? just lap"),
    (73.44, "selesa · cantik"),
    (76.44, "cek beg kuning|lagi murah dari mall"),
]
COMFORT_SRC = 32.86  # "memang selesa" -> comfort level + thin bar

# b-roll inserts: (trigger src time, asset)
BROLLS = [(24.92, "broll_ringan"), (31.30, "broll_antislip"),
          (54.08, "broll_design"), (75.94, "broll_harga")]
BR_LEN = 2.4

HOOK_END = 2.9
items = sorted((out(s), t) for s, t in KEYWORDS)
comfort_t = out(COMFORT_SRC)

ov = []
for i, (t, txt) in enumerate(items):
    nxt = items[i + 1][0] if i + 1 < len(items) else DUR
    if t < comfort_t < nxt:
        nxt = comfort_t
    start = max(t - 0.05, HOOK_END + 0.1) if t < HOOK_END + 0.1 else t - 0.05
    dur = round(min(2.2, nxt - start - 0.15), 3)
    ov.append((round(start, 3), dur, txt))

brolls = [(snap(out(s)), a) for s, a in BROLLS]
# twist-lock close-up: the A-roll itself (slow push-in + light sweep)
twist_start, twist_end = out(45.10), out(52.58)

cuts = [r["out_start"] for r in edl[1:]]

el, js, sfx = [], [], []

# ---------- A-roll (muted: voice.wav carries the cleaned voice)
el.append(f'''<div id="aroll-wrap" class="stage">
      <video id="aroll" class="clip" src="assets/aroll.mp4" data-start="0" data-duration="{DUR}"
        data-media-start="0" data-track-index="0" muted playsinline></video>
    </div>''')
# punch-in alternation on jump cuts (hides cuts, 'zoom sikit')
scale = 1.0
for c in cuts:
    scale = 1.045 if scale == 1.0 else 1.0
    if twist_start - 0.01 <= c <= twist_end:
        continue
    js.append(f'tl.set("#aroll-wrap", {{ scale: {scale} }}, {c});')
js.append(f'tl.set("#aroll-wrap", {{ scale: 1 }}, {twist_start});')
js.append(f'tl.fromTo("#aroll", {{ scale: 1 }}, {{ scale: 1.1, duration: {twist_end - twist_start:.3f}, ease: "sine.inOut" }}, {twist_start});')
js.append(f'tl.set("#aroll", {{ scale: 1 }}, {twist_end});')
# hook: gentle push-in on the face for the first 3s
js.append('tl.fromTo("#aroll-wrap", { scale: 1.0 }, { scale: 1.04, duration: 3.0, ease: "sine.out" }, 0);')

# ---------- B-roll: full screen, cross-dissolve, slow-mo already in the clip, slow zoom + light sweep
for i, (t, a) in enumerate(brolls):
    bid = f"br{i}"
    el.append(f'<video id="{bid}" class="clip broll" src="assets/{a}.mp4" data-start="{t}" data-duration="{BR_LEN}" data-media-start="0" data-track-index="1" muted playsinline></video>')
    el.append(f'<div id="{bid}s" class="clip sweep-full" data-start="{t}" data-duration="{BR_LEN}" data-track-index="2"><div class="sweep"></div></div>')
    js.append(f'tl.fromTo("#{bid}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.45, ease: "sine.inOut" }}, {t});')
    js.append(f'tl.to("#{bid}", {{ opacity: 0, duration: 0.45, ease: "sine.inOut" }}, {t + BR_LEN - 0.45:.3f});')
    js.append(f'tl.fromTo("#{bid}", {{ scale: 1.0 }}, {{ scale: 1.08, duration: {BR_LEN}, ease: "none" }}, {t});')
    js.append(f'tl.fromTo("#{bid}s .sweep", {{ xPercent: -120, opacity: 0 }}, {{ xPercent: 120, opacity: 1, duration: 1.4, ease: "sine.inOut" }}, {t + 0.5:.3f});')
    sfx.append((round(t - 0.25, 3), "sfx_whoosh", 0.35, 0.8))

# light sweep on the twist-lock close-up
tw = out(48.16)
el.append(f'<div id="tw-sweep" class="clip sweep-full" data-start="{tw - 0.2:.3f}" data-duration="1.8" data-track-index="2"><div class="sweep"></div></div>')
js.append(f'tl.fromTo("#tw-sweep .sweep", {{ xPercent: -120, opacity: 0 }}, {{ xPercent: 120, opacity: 1, duration: 1.5, ease: "sine.inOut" }}, {tw - 0.2:.3f});')
sfx.append((round(tw - 0.1, 3), "sfx_shimmer", 0.25, 1.5))

# ---------- Hook text (first 3s)
el.append(f'''<div id="hook" class="clip ov hook" data-start="0.15" data-duration="{HOOK_END - 0.15:.2f}" data-track-index="3">
      <span>kasut sekolah ni</span><span>worth ke tak?</span>
    </div>''')
js.append('tl.fromTo("#hook span", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out", stagger: 0.18 }, 0.15);')
js.append(f'tl.to("#hook", {{ opacity: 0, y: -8, duration: 0.35, ease: "sine.in" }}, {HOOK_END - 0.4:.2f});')
sfx.append((0.15, "sfx_ting", 0.45, 1.2))

# ---------- keyword overlays
for i, (t, d, txt) in enumerate(ov):
    oid = f"kw{i}"
    el.append(f'<div id="{oid}" class="clip ov" data-start="{t}" data-duration="{d}" data-track-index="3">{"".join(f"<span>{html.escape(x)}</span>" for x in txt.split("|"))}</div>')
    js.append(f'tl.fromTo("#{oid}", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }}, {t});')
    js.append(f'tl.to("#{oid}", {{ opacity: 0, duration: 0.3, ease: "sine.in" }}, {t + d - 0.3:.3f});')
    sfx.append((round(t, 3), "sfx_ting" if i % 2 == 0 else "sfx_ting_hi", 0.3, 1.2))

# ---------- comfort level (thin bar)
cd = 2.2
el.append(f'''<div id="comfort" class="clip ov" data-start="{comfort_t}" data-duration="{cd}" data-track-index="3">
      <span>comfort level</span>
      <div class="bar"><div class="fill"></div></div>
    </div>''')
js.append(f'tl.fromTo("#comfort", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }}, {comfort_t});')
js.append(f'tl.fromTo("#comfort .fill", {{ scaleX: 0 }}, {{ scaleX: 0.9, duration: 1.1, ease: "power2.out" }}, {comfort_t + 0.25:.3f});')
js.append(f'tl.to("#comfort", {{ opacity: 0, duration: 0.3 }}, {comfort_t + cd - 0.3:.3f});')
sfx.append((round(comfort_t, 3), "sfx_ting", 0.3, 1.2))

# ---------- audio
aud = [f'<audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{DUR}" data-media-start="0" data-volume="1" data-track-index="10"></audio>',
       f'<audio id="music" src="assets/music.wav" data-start="0" data-duration="{DUR}" data-media-start="0" data-volume="0.13" data-fade-in="0.8" data-fade-out="1.5" data-track-index="11"></audio>']
for i, (t, name, vol, d) in enumerate(sorted(sfx)):
    aud.append(f'<audio id="sfx{i}" src="assets/{name}.wav" data-start="{max(t, 0)}" data-duration="{d}" data-media-start="0" data-volume="{vol}" data-track-index="{12 + i % 4}"></audio>')

HTML = f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Cweyons"; src: url("assets/Cweyons-Regular.ttf") format("truetype"); font-display: block; }}
      :root {{ --ink: #ffffff; --font-display: "Cweyons", "Inter", "Helvetica Neue", sans-serif; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #fff; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; }}
      #aroll-wrap {{ position: absolute; inset: 0; }}
      #aroll-wrap video, video.broll {{ width: 1080px; height: 1920px; object-fit: cover; transform-origin: 50% 45%; }}
      .broll {{ overflow: hidden; }}
      .sweep-full {{ pointer-events: none; overflow: hidden; }}
      .sweep {{ position: absolute; inset: -10% -40%; mix-blend-mode: soft-light;
        background: linear-gradient(105deg, rgba(255,255,255,0) 42%, rgba(255,255,255,.55) 50%, rgba(255,255,255,0) 58%); }}
      /* overlays: small white text in the empty top-left wall area, below TikTok's top bar,
         clear of face/product and the right-hand action rail */
      .ov {{ inset: auto; left: 76px; top: 250px; max-width: 480px; color: var(--ink);
        font-family: var(--font-display); font-size: 42px; line-height: 1.15; letter-spacing: 0.01em;
        text-shadow: 0 2px 14px rgba(0,0,0,.28); display: flex; flex-direction: column; gap: 6px; }}
      .ov.hook {{ font-size: 54px; }}
      .ov.hook span {{ display: block; }}
      .bar {{ width: 300px; height: 3px; background: rgba(255,255,255,.35); border-radius: 2px; margin-top: 10px;
        box-shadow: 0 1px 8px rgba(0,0,0,.18); }}
      .fill {{ width: 100%; height: 100%; background: #fff; border-radius: 2px; transform-origin: 0 50%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
    {chr(10).join("    " + e for e in el)}
    {chr(10).join("    " + a for a in aud)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join("      " + j for j in js)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
open("hf/kasut/index.html", "w").write(HTML)
print("duration", DUR, "overlays", len(ov), "brolls", brolls, "twist", twist_start, twist_end)
for t, d, txt in ov:
    print(f"  {t:6.2f} +{d:.2f}  {txt}")
print("  comfort", comfort_t)
