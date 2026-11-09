"""Video 2 composition (hyperframes/kasut2/index.html). Apple-clean style:
white frosted pills, Inter, pop-in; lower-third safe zone (face sits in the top third)."""
import json, html

E = json.load(open("scripts/v2/edl.json"))
edl, DUR = E["edl"], E["duration"]
BEAT = 60 / 112


def out(src):
    for r in edl:
        if r["src_start"] - 1e-6 <= src <= r["src_end"] + 1e-6:
            return round(r["out_start"] + src - r["src_start"], 3)
    nxt = min((r for r in edl if r["src_start"] > src), key=lambda r: r["src_start"])
    return nxt["out_start"]


def snap(t):
    return round(round(t / BEAT) * BEAT, 3)


HOOK_END = 3.0
# (src time of the spoken word, pill text) — each point appears once
KEYWORDS = [
    (24.38, "tiada tali"),
    (11.18, "mak ayah recommend"),
    (14.60, "design sporty"),
    (33.72, "anak suka"),
    (40.08, "kalis air · water resistant"),
    (42.80, "kotor? cuci je"),
    (50.40, "tak tembus ke dalam"),
    (54.34, "cara guna senang"),
    (57.90, "tarik & ketat"),
    (67.30, "sesuai sekolah rendah"),
    (74.50, "tapak anti-slip"),
    (84.74, "super ringan"),
    (93.96, "cek beg kuning"),
    (99.70, "size cepat habis"),
]
COMFORT_SRC = 87.54          # "buat aktiviti dalam sekolah, luar sekolah"
BROLLS = [(14.60, "broll_design"), (40.08, "broll_kalis"), (57.82, "broll_tarik"),
          (73.20, "broll_tapak"), (85.60, "broll_ringan"), (91.38, "broll_cta")]
BR_LEN = 2.6
FADE = 0.4

items = sorted((out(s), t) for s, t in KEYWORDS)
comfort_t = out(COMFORT_SRC)
ov = []
for i, (t, txt) in enumerate(items):
    start = max(t - 0.08, HOOK_END + 0.15)
    nxt = items[i + 1][0] - 0.08 if i + 1 < len(items) else DUR
    if start < comfort_t < nxt:
        nxt = comfort_t
    ov.append((round(start, 3), round(min(2.3, nxt - start - 0.12), 3), txt))

brolls = [(snap(out(s) - 0.15), a) for s, a in BROLLS]
cuts = [r["out_start"] for r in edl[1:]]
el, js, sfx = [], [], []

# ---------- A-roll (muted; voice.wav carries the cleaned voice)
el.append(f'''<div id="aroll-wrap" class="stage">
      <video id="aroll" class="clip" src="assets/aroll.mp4" data-start="0" data-duration="{DUR}"
        data-media-start="0" data-track-index="0" muted playsinline></video>
    </div>''')
# hook: slow push-in on the face for the first 3s
js.append('tl.fromTo("#aroll-wrap", { scale: 1.0 }, { scale: 1.05, duration: 3.0, ease: "sine.out" }, 0);')
# jump cuts: alternate punch-in so the cut reads as intentional
scale = 1.05
for c in cuts:
    if c < HOOK_END:
        continue
    scale = 1.0 if scale != 1.0 else 1.06
    js.append(f'tl.set("#aroll-wrap", {{ scale: {scale} }}, {c});')

# ---------- B-roll close-ups: full screen, soft fade, slow-mo (in clip), slow zoom, light sweep
for i, (t, a) in enumerate(brolls):
    bid = f"br{i}"
    el.append(f'<video id="{bid}" class="clip broll" src="assets/{a}.mp4" data-start="{t}" data-duration="{BR_LEN}" data-media-start="0" data-track-index="1" muted playsinline></video>')
    el.append(f'<div id="{bid}s" class="clip sweep-full" data-start="{t}" data-duration="{BR_LEN}" data-track-index="2"><div class="sweep"></div></div>')
    js.append(f'tl.fromTo("#{bid}", {{ opacity: 0 }}, {{ opacity: 1, duration: {FADE}, ease: "sine.inOut" }}, {t});')
    js.append(f'tl.to("#{bid}", {{ opacity: 0, duration: {FADE}, ease: "sine.inOut" }}, {t + BR_LEN - FADE:.3f});')
    js.append(f'tl.fromTo("#{bid}", {{ scale: 1.12 }}, {{ scale: 1.0, duration: {BR_LEN}, ease: "power1.out" }}, {t});')
    js.append(f'tl.fromTo("#{bid}s .sweep", {{ xPercent: -130, opacity: 0 }}, {{ xPercent: 130, opacity: 1, duration: 1.3, ease: "sine.inOut" }}, {t + 0.6:.3f});')
    sfx.append((round(t - 0.2, 3), "sfx_swish", 0.3, 0.6))
    sfx.append((round(t + 0.7, 3), "sfx_sparkle", 0.12, 1.4))

# ---------- Hook text
el.append(f'''<div id="hook" class="clip hook" data-start="0.1" data-duration="{HOOK_END - 0.1:.2f}" data-track-index="3">
      <div class="big">bawah RM50?</div>
      <div class="pill">kasut sekolah ni berbaloi ke?</div>
    </div>''')
js.append('tl.fromTo("#hook .big", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)" }, 0.1);')
js.append('tl.fromTo("#hook .pill", { opacity: 0, scale: 0.7, y: 10 }, { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "back.out(2)" }, 0.45);')
js.append(f'tl.to("#hook", {{ opacity: 0, scale: 0.96, duration: 0.3, ease: "sine.in" }}, {HOOK_END - 0.35:.2f});')
sfx += [(0.1, "sfx_pop", 0.5, 0.2), (0.45, "sfx_pop", 0.4, 0.2)]

# ---------- point pills (pop-in)
for i, (t, d, txt) in enumerate(ov):
    oid = f"kw{i}"
    el.append(f'<div id="{oid}" class="clip ov" data-start="{t}" data-duration="{d}" data-track-index="3"><div class="pill">{html.escape(txt)}</div></div>')
    js.append(f'tl.fromTo("#{oid} .pill", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.2)" }}, {t});')
    js.append(f'tl.to("#{oid} .pill", {{ opacity: 0, scale: 0.92, duration: 0.25, ease: "sine.in" }}, {t + d - 0.25:.3f});')
    sfx.append((t, "sfx_pop", 0.4, 0.2))

# ---------- comfort level card
cd = 2.6
el.append(f'''<div id="comfort" class="clip ov" data-start="{comfort_t}" data-duration="{cd}" data-track-index="3">
      <div class="card"><div class="row"><span>comfort level</span><span id="cnum">9/10</span></div>
      <div class="bar"><div class="fill"></div></div></div>
    </div>''')
js.append(f'tl.fromTo("#comfort .card", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.2)" }}, {comfort_t});')
js.append(f'tl.fromTo("#comfort .fill", {{ scaleX: 0 }}, {{ scaleX: 0.9, duration: 1.0, ease: "power3.out" }}, {comfort_t + 0.3:.3f});')
js.append(f'tl.to("#comfort .card", {{ opacity: 0, scale: 0.92, duration: 0.25 }}, {comfort_t + cd - 0.25:.3f});')
sfx.append((comfort_t, "sfx_pop", 0.4, 0.2))

# ---------- audio
aud = [f'<audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{DUR}" data-media-start="0" data-volume="1" data-track-index="10"></audio>',
       f'<audio id="music" src="assets/music.wav" data-start="0" data-duration="{DUR}" data-media-start="0" data-volume="0.12" data-fade-in="0.6" data-fade-out="1.5" data-track-index="11"></audio>']
for i, (t, name, vol, d) in enumerate(sorted(sfx)):
    aud.append(f'<audio id="sfx{i}" src="assets/{name}.wav" data-start="{max(t, 0)}" data-duration="{d}" data-media-start="0" data-volume="{vol}" data-track-index="{12 + i % 4}"></audio>')

HTML = f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Inter"; font-weight: 600; src: url("assets/Inter-SemiBold.woff2") format("woff2"); font-display: block; }}
      @font-face {{ font-family: "Inter"; font-weight: 800; src: url("assets/Inter-Bold.woff2") format("woff2"); font-display: block; }}
      :root {{ --ink: #1d1d1f; --glass: rgba(255,255,255,.86); --accent: #0071e3; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; font-family: "Inter", -apple-system, sans-serif; }}
      .clip {{ position: absolute; inset: 0; }}
      #aroll-wrap {{ position: absolute; inset: 0; transform-origin: 50% 30%; }}
      #aroll-wrap video, video.broll {{ width: 1080px; height: 1920px; object-fit: cover; }}
      video.broll {{ transform-origin: 50% 50%; }}
      .sweep-full {{ pointer-events: none; overflow: hidden; }}
      .sweep {{ position: absolute; inset: -10% -40%; mix-blend-mode: soft-light;
        background: linear-gradient(105deg, rgba(255,255,255,0) 40%, rgba(255,255,255,.6) 50%, rgba(255,255,255,0) 60%); }}
      /* safe zone: lower third, clear of the face (top third), TikTok caption (bottom ~360px)
         and the right-hand action rail (~140px) */
      .ov, .hook {{ inset: auto; left: 80px; right: 160px; top: 1330px; display: flex; flex-direction: column;
        align-items: flex-start; gap: 18px; }}
      .hook {{ top: 1230px; }}
      .pill {{ background: var(--glass); color: var(--ink); font-weight: 600; font-size: 44px; letter-spacing: -0.01em;
        padding: 18px 34px; border-radius: 999px; box-shadow: 0 10px 30px rgba(0,0,0,.18); transform-origin: 0% 50%;
        backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); white-space: nowrap; }}
      .big {{ font-weight: 800; font-size: 104px; letter-spacing: -0.035em; color: #fff; line-height: 1;
        text-shadow: 0 6px 30px rgba(0,0,0,.35); transform-origin: 0% 100%; }}
      .card {{ background: var(--glass); color: var(--ink); border-radius: 34px; padding: 26px 34px 30px; width: 560px;
        box-shadow: 0 10px 30px rgba(0,0,0,.18); transform-origin: 0% 50%; backdrop-filter: blur(18px); }}
      .row {{ display: flex; justify-content: space-between; font-weight: 600; font-size: 40px; }}
      #cnum {{ color: var(--accent); }}
      .bar {{ height: 10px; border-radius: 6px; background: rgba(0,0,0,.1); margin-top: 18px; overflow: hidden; }}
      .fill {{ width: 100%; height: 100%; background: var(--accent); border-radius: 6px; transform-origin: 0 50%; }}
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
open("hyperframes/kasut2/index.html", "w").write(HTML)
print("duration", DUR)
print("brolls", brolls)
for t, d, txt in ov:
    print(f"  {t:6.2f} +{d:.2f}  {txt}")
print("  comfort", comfort_t)
