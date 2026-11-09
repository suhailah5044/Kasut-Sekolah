"""Generate the HyperFrames composition (hf/kasut/index.html) from the EDL + keyword list."""
import json, html

E = json.load(open("edl.json"))
edl, DUR = E["edl"], E["duration"]
BEAT = 0.6  # 100 BPM music grid


def out(src, t):
    """map (source take, source time) -> edited time"""
    for r in edl:
        if r["src"] == src and r["src_start"] - 1e-6 <= t <= r["src_end"] + 1e-6:
            return round(r["out_start"] + t - r["src_start"], 3)
    # inside a trimmed pause -> start of the next kept range of that take
    nxt = min((r for r in edl if r["src"] == src and r["src_start"] > t), key=lambda r: r["src_start"])
    return nxt["out_start"]


def snap(t):
    return round(round(t / BEAT) * BEAT, 3)


# keyword overlays: (take, src time of the spoken word, text)
KEYWORDS = [  # optional 4th field = zone: "tl" top-left wall (default), "r" right of face, "ml" mid-left
    ("k2", 10.84, "highly recommend"),
    ("k2", 14.60, "design sporty"),
    ("k2", 20.68, "bawah RM50", "r"),         # product zoom pushes the face into top-left
    ("k1", 30.54, "tapak anti-slip"),
    ("k1", 42.10, "tahan lasak"),
    ("k2", 84.74, "super ringan", "ml"),       # over the ringan b-roll: dress area, clear of shoe
    ("k2", 54.90, "tiada tali"),
    ("k2", 57.82, "tarik &|ketat", "r"),       # close-up: face sits top-left
    ("k2", 61.66, "senang untuk|darjah 1-3"),  # she steps back here: top-left wall is clear
    ("k1", 56.24, "anak suka"),
    ("k1", 58.22, "kotor? just lap"),
    ("k2", 92.70, "cek beg kuning"),
    ("k2", 98.86, "beli sekarang|size cepat habis"),
]
COMFORT = ("k1", 32.86)  # "memang selesa" -> comfort level + thin bar

# b-roll inserts (full screen product close-ups): (take, trigger src time, asset)
BROLLS = [("k2", 17.30, "broll_design"), ("k1", 35.00, "broll_tapak"), ("k2", 84.60, "broll_ringan")]
# product moments: smooth zoom toward the shoe in the live shot (stays lip-synced)
# (take, src start, src end, transform-origin of the shoe)
ZOOMS = [("k2", 19.00, 22.95, "55% 55%"), ("k1", 40.30, 44.60, "42% 55%"), ("k2", 90.60, 94.60, "48% 52%")]
BR_LEN = 2.4
TWIST = ("k2", 53.10, 63.50)   # twist-lock section: slow push-in
TWIST_SWEEP = ("k2", 57.82)    # "tarik" -> light sweep + shimmer

HOOK_END = 4.1  # hook text stays for the whole spoken hook
items = sorted((out(k[0], k[1]), k[2], (k[3] if len(k) > 3 else "tl")) for k in KEYWORDS)
comfort_t = out(*COMFORT)

ov = []
for i, (t, txt, zone) in enumerate(items):
    nxt = items[i + 1][0] if i + 1 < len(items) else DUR
    if t < comfort_t < nxt:
        nxt = comfort_t
    start = max(t - 0.05, HOOK_END + 0.1) if t < HOOK_END + 0.1 else t - 0.05
    dur = round(min(2.2, nxt - start - 0.15), 3)
    ov.append((round(start, 3), dur, txt, zone))

brolls = [(snap(out(k, s)), a) for k, s, a in BROLLS]
# twist-lock close-up: the A-roll itself (slow push-in + light sweep)
twist_start, twist_end = out(TWIST[0], TWIST[1]), out(TWIST[0], TWIST[2])

cuts = [r["out_start"] for r in edl[1:]]

el, js, sfx = [], [], []

# ---------- A-roll (muted: voice.wav carries the cleaned voice)
el.append(f'''<div id="aroll-wrap" class="stage">
      <video id="aroll" class="clip" src="assets/aroll.mp4" data-start="0" data-duration="{DUR}"
        data-media-start="0" data-track-index="0" muted playsinline></video>
    </div>''')
# jump cuts: rotate 3 different cut moves so no two neighbouring cuts look the same
CUT_MOVES = ["punch", "settle", "release"]
for n, c in enumerate(cuts):
    if twist_start - 0.01 <= c <= twist_end or c < 3.0:  # hook has its own push-in
        continue
    m = CUT_MOVES[n % 3]
    if m == "punch":      # hard punch-in
        js.append(f'tl.set("#aroll-wrap", {{ scale: 1.05 }}, {c});')
    elif m == "settle":   # quick zoom that eases back
        js.append(f'tl.fromTo("#aroll-wrap", {{ scale: 1.08 }}, {{ scale: 1.0, duration: 0.45, ease: "power3.out", immediateRender: false }}, {c});')
    else:                 # back to wide
        js.append(f'tl.set("#aroll-wrap", {{ scale: 1.0 }}, {c});')
js.append(f'tl.set("#aroll-wrap", {{ scale: 1 }}, {twist_start});')
js.append(f'tl.fromTo("#aroll", {{ scale: 1 }}, {{ scale: 1.1, duration: {twist_end - twist_start:.3f}, ease: "sine.inOut", immediateRender: false }}, {twist_start});')
js.append(f'tl.set("#aroll", {{ scale: 1 }}, {twist_end});')
# hook: gentle push-in on the face for the first 3s
js.append('tl.fromTo("#aroll-wrap", { scale: 1.0 }, { scale: 1.04, duration: 3.0, ease: "sine.out" }, 0);')

# ---------- B-roll: full screen, each one with its OWN in/out transition + light sweep direction
BR_IN = [
    # zoom-through with blur
    lambda b, t: [f'tl.fromTo("#{b}", {{ opacity: 0, scale: 1.3, filter: "blur(14px)" }}, {{ opacity: 1, scale: 1.04, filter: "blur(0px)", duration: 0.5, ease: "power3.out" }}, {t});',
                  f'tl.to("#{b}", {{ scale: 1.1, duration: {BR_LEN - 0.5:.2f}, ease: "none" }}, {t + 0.5:.3f});'],
    # circle reveal from the centre
    lambda b, t: [f'tl.fromTo("#{b}", {{ clipPath: "circle(0% at 50% 50%)" }}, {{ clipPath: "circle(75% at 50% 50%)", duration: 0.55, ease: "power2.inOut" }}, {t});',
                  f'tl.fromTo("#{b}", {{ scale: 1.12 }}, {{ scale: 1.0, duration: {BR_LEN - 0.45:.2f}, ease: "sine.out" }}, {t});'],
    # slide/push in from the right
    lambda b, t: [f'tl.fromTo("#{b}", {{ xPercent: 100 }}, {{ xPercent: 0, duration: 0.5, ease: "expo.out" }}, {t});',
                  f'tl.fromTo("#{b}", {{ yPercent: 0, scale: 1.06 }}, {{ yPercent: -3, scale: 1.06, duration: {BR_LEN - 0.4:.2f}, ease: "none" }}, {t});'],
]
BR_OUT = [
    lambda b, t: [f'tl.to("#{b}", {{ opacity: 0, duration: 0.4, ease: "sine.inOut" }}, {t - 0.4:.3f});'],
    lambda b, t: [f'tl.to("#{b}", {{ clipPath: "inset(0% 0% 0% 100%)", duration: 0.45, ease: "power2.in" }}, {t - 0.45:.3f});'],
    lambda b, t: [f'tl.to("#{b}", {{ opacity: 0, scale: 0.92, filter: "blur(10px)", duration: 0.4, ease: "power2.in" }}, {t - 0.4:.3f});'],
]
SWEEP_DIR = [(-120, 120), (120, -120), (-120, 120)]
BR_SFX = ["sfx_whoosh", "sfx_swish", "sfx_whoosh"]
for i, (t, a) in enumerate(brolls):
    bid = f"br{i}"
    el.append(f'<video id="{bid}" class="clip broll" src="assets/{a}.mp4" data-start="{t}" data-duration="{BR_LEN}" data-media-start="0" data-track-index="1" muted playsinline></video>')
    el.append(f'<div id="{bid}s" class="clip sweep-full" data-start="{t}" data-duration="{BR_LEN}" data-track-index="2"><div class="sweep{" rev" if i == 1 else ""}"></div></div>')
    js += BR_IN[i % 3](bid, t) + BR_OUT[i % 3](bid, t + BR_LEN)
    x0, x1 = SWEEP_DIR[i % 3]
    js.append(f'tl.fromTo("#{bid}s .sweep", {{ xPercent: {x0}, opacity: 0 }}, {{ xPercent: {x1}, opacity: 1, duration: 1.3, ease: "sine.inOut" }}, {t + 0.55:.3f});')
    sfx.append((round(t - 0.2, 3), BR_SFX[i % 3], 0.35, 0.8))

# ---------- product zooms in the live shot: 3 different moves
ZOOM_MOVES = [
    lambda t0, d: [f'tl.to("#aroll", {{ scale: 1.15, duration: {d:.3f}, ease: "sine.inOut" }}, {t0});'],                       # smooth push
    lambda t0, d: [f'tl.fromTo("#aroll", {{ scale: 1.0, x: 0 }}, {{ scale: 1.14, x: -40, duration: {d:.3f}, ease: "power1.inOut" }}, {t0});'],  # push + pan
    lambda t0, d: [f'tl.to("#aroll", {{ scale: 1.12, duration: 0.35, ease: "back.out(2)" }}, {t0});',                         # snap zoom, then drift
                   f'tl.to("#aroll", {{ scale: 1.17, duration: {d - 0.35:.3f}, ease: "none" }}, {t0 + 0.35:.3f});'],
]
for i, (k, a, b, origin) in enumerate(ZOOMS):
    t0, t1 = out(k, a), out(k, b)
    js.append(f'tl.set("#aroll", {{ transformOrigin: "{origin}" }}, {t0});')
    js += ZOOM_MOVES[i % 3](t0, t1 - t0 - 0.5)
    js.append(f'tl.to("#aroll", {{ scale: 1.0, x: 0, duration: 0.5, ease: "sine.inOut" }}, {t1 - 0.5:.3f});')
    js.append(f'tl.set("#aroll", {{ transformOrigin: "50% 45%" }}, {t1:.3f});')
    el.append(f'<div id="pz{i}" class="clip sweep-full" data-start="{t0 + 0.4:.3f}" data-duration="1.6" data-track-index="2"><div class="sweep{" rev" if i % 2 else ""}"></div></div>')
    x0, x1 = (120, -120) if i % 2 else (-120, 120)
    js.append(f'tl.fromTo("#pz{i} .sweep", {{ xPercent: {x0}, opacity: 0 }}, {{ xPercent: {x1}, opacity: 1, duration: 1.5, ease: "sine.inOut" }}, {t0 + 0.4:.3f});')

# light sweep on the twist-lock close-up
tw = out(*TWIST_SWEEP)
el.append(f'<div id="tw-sweep" class="clip sweep-full" data-start="{tw - 0.2:.3f}" data-duration="1.8" data-track-index="2"><div class="sweep"></div></div>')
js.append(f'tl.fromTo("#tw-sweep .sweep", {{ xPercent: -120, opacity: 0 }}, {{ xPercent: 120, opacity: 1, duration: 1.5, ease: "sine.inOut" }}, {tw - 0.2:.3f});')
sfx.append((round(tw - 0.1, 3), "sfx_shimmer", 0.25, 1.5))


def chars(line):
    """split a line into per-letter spans (spaces kept) for letter animations"""
    return "".join(f'<i class="ch">{html.escape(c) if c != " " else "&nbsp;"}</i>' for c in line)


def lines_html(txt):
    return "".join(f'<span class="ln">{chars(x)}</span>' for x in txt.split("|"))


# ---------- Hook text: word-by-word rise
HOOK_TEXT = "hujan-hujan pun tak|perlu risau sangat,|kasut ni water|resistant tau"
HOOK_HTML = "".join('<span class="ln">' + "&nbsp;".join(f'<i class="w">{html.escape(w)}</i>' for w in ln.split()) + "</span>"
                    for ln in HOOK_TEXT.split("|"))
el.append(f'<div id="hook" class="clip ov hook" data-start="0.15" data-duration="{HOOK_END - 0.15:.2f}" data-track-index="3">{HOOK_HTML}</div>')
js.append('tl.fromTo("#hook .w", { opacity: 0, yPercent: 70 }, { opacity: 1, yPercent: 0, duration: 0.4, ease: "power3.out", stagger: 0.11 }, 0.15);')
js.append(f'tl.to("#hook", {{ opacity: 0, y: -10, filter: "blur(6px)", duration: 0.35, ease: "sine.in" }}, {HOOK_END - 0.4:.2f});')
sfx.append((0.15, "sfx_ting", 0.45, 1.2))

# ---------- keyword overlays: 7 different entrance styles, rotated so neighbours never repeat,
# each with its own exit and its own sound
OV_ANIMS = [
    ("pop", "sfx_pop",
     lambda o, t: [f'tl.fromTo("#{o}", {{ opacity: 0, scale: 0.55 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.6)" }}, {t});'],
     lambda o, t: [f'tl.to("#{o}", {{ opacity: 0, scale: 0.85, duration: 0.25, ease: "power2.in" }}, {t - 0.25:.3f});']),
    ("type", "sfx_tick",
     lambda o, t: [f'tl.fromTo("#{o} .ch", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01, stagger: 0.045, ease: "none" }}, {t});'],
     lambda o, t: [f'tl.to("#{o}", {{ opacity: 0, duration: 0.25 }}, {t - 0.25:.3f});']),
    ("blur", "sfx_swish",
     lambda o, t: [f'tl.fromTo("#{o}", {{ opacity: 0, filter: "blur(12px)", scale: 1.08 }}, {{ opacity: 1, filter: "blur(0px)", scale: 1, duration: 0.55, ease: "power2.out" }}, {t});'],
     lambda o, t: [f'tl.to("#{o}", {{ opacity: 0, filter: "blur(8px)", duration: 0.3, ease: "sine.in" }}, {t - 0.3:.3f});']),
    ("wave", "sfx_ting_hi",
     lambda o, t: [f'tl.fromTo("#{o} .ch", {{ opacity: 0, y: 22, rotation: 8 }}, {{ opacity: 1, y: 0, rotation: 0, duration: 0.45, ease: "back.out(2)", stagger: 0.03 }}, {t});'],
     lambda o, t: [f'tl.to("#{o} .ch", {{ opacity: 0, y: -12, duration: 0.25, stagger: 0.012, ease: "power2.in" }}, {t - 0.35:.3f});']),
    ("slide", "sfx_swish",
     lambda o, t: [f'tl.fromTo("#{o}", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.5, ease: "expo.out" }}, {t});'],
     lambda o, t: [f'tl.to("#{o}", {{ opacity: 0, x: 30, duration: 0.3, ease: "power2.in" }}, {t - 0.3:.3f});']),
    ("mask", "sfx_ting",
     lambda o, t: [f'tl.fromTo("#{o} .ln", {{ clipPath: "inset(0% 100% 0% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power3.inOut", stagger: 0.15 }}, {t});'],
     lambda o, t: [f'tl.to("#{o} .ln", {{ clipPath: "inset(0% 0% 0% 100%)", duration: 0.35, ease: "power2.in" }}, {t - 0.35:.3f});']),
    ("spread", "sfx_ting_hi",
     lambda o, t: [f'tl.fromTo("#{o} .ch", {{ opacity: 0, x: (i, e, a) => (i - (a.length - 1) / 2) * 16 }}, {{ opacity: 1, x: 0, duration: 0.6, ease: "power3.out" }}, {t});'],
     lambda o, t: [f'tl.to("#{o}", {{ opacity: 0, y: -12, duration: 0.3, ease: "sine.in" }}, {t - 0.3:.3f});']),
]
for i, (t, d, txt, zone) in enumerate(ov):
    oid = f"kw{i}"
    name, snd, a_in, a_out = OV_ANIMS[i % len(OV_ANIMS)]
    el.append(f'<div id="{oid}" class="clip ov z-{zone} a-{name}" data-start="{t}" data-duration="{d}" data-track-index="3">{lines_html(txt)}</div>')
    js += a_in(oid, t) + a_out(oid, t + d)
    sfx.append((round(t, 3), snd, 0.32, 1.0))

# ---------- comfort level: pop-in + bar fill
cd = 2.0
el.append(f'''<div id="comfort" class="clip ov" data-start="{comfort_t}" data-duration="{cd}" data-track-index="3">
      <span>comfort level</span>
      <div class="bar"><div class="fill"></div></div>
    </div>''')
js.append(f'tl.fromTo("#comfort", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.4)" }}, {comfort_t});')
js.append(f'tl.fromTo("#comfort .fill", {{ scaleX: 0 }}, {{ scaleX: 0.9, duration: 1.1, ease: "power2.out" }}, {comfort_t + 0.25:.3f});')
js.append(f'tl.to("#comfort", {{ opacity: 0, duration: 0.3 }}, {comfort_t + cd - 0.3:.3f});')
sfx.append((round(comfort_t, 3), "sfx_pop", 0.32, 1.0))
sfx.append((round(comfort_t + 0.3, 3), "sfx_rise", 0.22, 1.2))

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
      .ov.z-r {{ left: auto; right: 72px; top: 500px; text-align: right; align-items: flex-end; }}
      .ov.z-ml {{ top: 1120px; }}
      .ov .ln {{ display: block; white-space: nowrap; }}
      .ov .ch {{ display: inline-block; font-style: normal; }}
      .ov {{ transform-origin: 0% 50%; }}
      .ov.z-r {{ transform-origin: 100% 50%; }}
      .ov.hook {{ font-size: 46px; max-width: none; }}
      .ov .w {{ display: inline-block; font-style: normal; }}
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
for t, d, txt, zone in ov:
    print(f"  {t:6.2f} +{d:.2f}  {zone:2} {txt}")
print("  comfort", comfort_t)
