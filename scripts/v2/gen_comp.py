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
    (11.18, "memang recommend"),
    (14.60, "design sporty"),
    (33.72, "anak suka"),
    (40.08, "kalis air · water resistant"),
    (42.80, "kotor? cuci je"),
    (50.40, "tak tembus ke dalam"),
    (54.34, "senang guna"),
    (57.90, "tarik & ketat"),
    (67.30, "sesuai sekolah rendah"),
    (74.50, "tapak anti-slip"),
    (84.74, "super ringan"),
    (93.96, "cek beg kuning"),
    (99.70, "size cepat habis"),
]
COMFORT_SRC = 87.54          # "buat aktiviti dalam sekolah, luar sekolah"
BROLLS = [(14.60, "broll_design"), (40.08, "broll_kalis"), (57.82, "broll_tarik"),
          (74.50, "broll_tapak"), (84.74, "broll_ringan"), (91.38, "broll_cta")]
BR_LEN = 2.2
FADE = 0.4

comfort_t0 = out(COMFORT_SRC)
COMFORT_CD = 2.2
# b-roll comes in ~1.5s AFTER its keyword, so the pill is read on the face shot first,
# then the full-screen close-up takes over (on the beat)
kw_out = {s: out(s) for s, _ in KEYWORDS}
brolls = []
for s_, a in BROLLS:      # keep >=1.3s of face between two b-rolls
    bt = snap(out(s_) + 1.5)
    while brolls and bt < brolls[-1][0] + BR_LEN + 1.3:
        bt = round(bt + BEAT, 3)
    brolls.append((bt, a))


def in_broll(t, pad=0.0):
    for bt, _ in brolls:
        if bt - pad <= t < bt + BR_LEN - 0.2:
            return bt
    return None


# overlays never sit on a b-roll (full-screen shoe = no empty space): shift to when the face is back
events = sorted([(kw_out[s], "kw", txt) for s, txt in KEYWORDS] + [(comfort_t0, "comfort", "")])
placed = []
prev_end = HOOK_END + 0.15
for t, kind, txt in events:
    t = max(t - 0.08, prev_end + 0.1)
    bt = in_broll(t, pad=1.3)          # inside a b-roll, or too close before one to be read
    if bt is not None:
        t = max(t, bt + BR_LEN - 0.2)
    placed.append([round(t, 3), kind, txt])
    prev_end = t + 1.4
ov, comfort_t, SLOT = [], None, {"hook": HOOK_END - 0.1}
for i, (t, kind, txt) in enumerate(placed):
    lim = placed[i + 1][0] - 0.1 if i + 1 < len(placed) else DUR
    nb = min([bt for bt, _ in brolls if bt > t] + [DUR])      # gone by the time the next b-roll is in
    full = COMFORT_CD if kind == "comfort" else 1.8
    slot = round(min(lim - t, nb - 0.05 - t, DUR - 0.05 - t), 3)   # time it may use without hitting the next pill/b-roll
    d = round(min(full, slot), 3)
    SLOT["comfort" if kind == "comfort" else f"kw{len(ov)}"] = slot
    if kind == "comfort":
        comfort_t, COMFORT_CD = t, d
    else:
        ov.append((t, d, txt))

cuts = [r["out_start"] for r in edl[1:]]

# ---------- empty-space placement: every overlay sits only on wall/floor (see find_empty.py)
import os
CHAR_W, PILL_H, GAP = 23, 74, 10        # Inter 600 @40px pill, generous
BIG_W, BIG_H = 40, 66                   # Inter 800 @66px


def splits(txt, n):
    w = txt.split()
    if n == 1 or len(w) < n:
        return [txt] if n == 1 else None
    if n == 2:
        k = min(range(1, len(w)), key=lambda k: abs(len(" ".join(w[:k])) - len(" ".join(w[k:]))))
        return [" ".join(w[:k]), " ".join(w[k:])]
    best = None
    for i in range(1, len(w) - 1):
        for j in range(i + 1, len(w)):
            parts = [" ".join(w[:i]), " ".join(w[i:j]), " ".join(w[j:])]
            m = max(map(len, parts))
            if best is None or m < best[0]:
                best = (m, parts)
    return best[1]


def make(rows, sc):
    """rows: [(kind, text)] -> layout with pixel size at scale sc (bigger scale first = preferred)"""
    w = max((len(t) * (BIG_W if k == "big" else CHAR_W) + (0 if k == "big" else 64)) * sc for k, t in rows)
    h = sum((BIG_H if k == "big" else PILL_H) * sc for k, _ in rows) + GAP * (len(rows) - 1)
    return {"rows": rows, "s": sc, "w": int(w) + 4, "h": int(h) + 4}


def layouts(txt):
    L = []
    for sc in (1.0, 0.8):
        for n in (1, 2, 3):
            parts = splits(txt, n)
            if parts:
                L.append(make([("pill", x) for x in parts], sc))
    return L


HOOK_SUB = "berbaloi ke tak?"
hook_L = []
for sc in (1.0, 0.8):
    for big in (["bawah RM50?"], ["bawah", "RM50?"]):
        for sub in ([HOOK_SUB], splits(HOOK_SUB, 2)):
            hook_L.append(make([("big", x) for x in big] + [("pill", x) for x in sub], sc))
blocks = [("hook", 0.1, HOOK_END - 0.1, hook_L)]
blocks += [(f"kw{i}", t, d, layouts(txt)) for i, (t, d, txt) in enumerate(ov)]
blocks += [("comfort", comfort_t, COMFORT_CD, [make([("pill", "comfort level 9/10")], 1.0) | {"w": 420, "h": 132},
                                               make([("pill", "comfort level 9/10")], 0.8) | {"w": 340, "h": 108}])]


def visible(t):
    """which video file(s) are on screen at output time t -> [(path, media time)]"""
    for bt, a in brolls:
        if bt <= t <= bt + BR_LEN:
            v = [(f"hyperframes/kasut2/assets/{a}.mp4", t - bt)]
            if t < bt + FADE or t > bt + BR_LEN - FADE:     # cross-fade: both layers show
                v.append(("hyperframes/kasut2/assets/aroll.mp4", t))
            return v
    return [("hyperframes/kasut2/assets/aroll.mp4", t)]


jobs = []
for bid, t, d, lay in blocks:
    variants = []       # small timing freedom: start up to 0.5s later and/or show 1.4s, inside the original slot
    slot = SLOT[bid]
    for dt in ((0.0,) if bid == "hook" else (0.0, 0.25, 0.5, 0.75, 1.0)):
        for dd in sorted({round(min(d, slot - dt), 3), round(min(d, 1.4), 3)}, reverse=True):
            if dd < 1.2 or dt + dd > slot + 1e-6:
                continue
            samples = []
            for k in range(6):
                samples += visible(t + dt + dd * k / 5)
            variants.append({"dt": dt, "d": round(dd, 3), "samples": samples})
    jobs.append({"id": bid, "layouts": lay, "variants": variants})
json.dump(jobs, open("scripts/v2/overlay_jobs.json", "w"), indent=1)
PL = json.load(open("scripts/v2/placements.json")) if os.path.exists("scripts/v2/placements.json") else {}
LAY = {bid: lay for bid, _, _, lay in blocks}
def timing(bid, t, d):
    p = PL.get(bid)
    return (round(t + p["dt"], 3), p["d"]) if p else (t, d)
def lay(bid):
    return LAY[bid][PL.get(bid, {}).get("layout", 0)]


def rows_html(bid):
    L = lay(bid)
    return "".join(f'<div class="{k}">{html.escape(t)}</div>' for k, t in L["rows"])
def pos(bid):
    p = PL.get(bid, {"x": 80, "y": 1330})
    return f'style="left:{p['x']}px; top:{p['y']}px; --s:{lay(bid)["s"]}"'
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

# ---------- B-roll close-ups: full screen, soft fade, slow zoom, light sweep (normal speed)
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
el.append(f'''<div id="hook" class="clip hook" {pos("hook")} data-start="0.1" data-duration="{HOOK_END - 0.1:.2f}" data-track-index="3">
      {rows_html("hook")}
    </div>''')
js.append('tl.fromTo("#hook .big", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)", stagger: 0.1 }, 0.1);')
js.append('tl.fromTo("#hook .pill", { opacity: 0, scale: 0.7, y: 10 }, { opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "back.out(2)", stagger: 0.08 }, 0.45);')
js.append(f'tl.to("#hook", {{ opacity: 0, scale: 0.96, duration: 0.3, ease: "sine.in" }}, {HOOK_END - 0.35:.2f});')
sfx += [(0.1, "sfx_pop", 0.5, 0.2), (0.45, "sfx_pop", 0.4, 0.2)]

# ---------- point pills (pop-in)
for i, (t, d, txt) in enumerate(ov):
    oid = f"kw{i}"
    t, d = timing(oid, t, d)
    el.append(f'<div id="{oid}" class="clip ov" {pos(oid)} data-start="{t}" data-duration="{d}" data-track-index="3">{rows_html(oid)}</div>')
    js.append(f'tl.fromTo("#{oid} .pill", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2.2)", stagger: 0.08 }}, {t});')
    js.append(f'tl.to("#{oid} .pill", {{ opacity: 0, scale: 0.92, duration: 0.25, ease: "sine.in" }}, {t + d - 0.25:.3f});')
    sfx.append((t, "sfx_pop", 0.4, 0.2))

# ---------- comfort level card
comfort_t, cd = timing("comfort", comfort_t, COMFORT_CD)
el.append(f'''<div id="comfort" class="clip ov" {pos("comfort")} data-start="{comfort_t}" data-duration="{cd}" data-track-index="3">
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
      .ov, .hook {{ inset: auto; display: flex; flex-direction: column;
        align-items: flex-start; gap: 10px; }}
      .pill {{ background: var(--glass); color: var(--ink); font-weight: 600; font-size: calc(40px * var(--s, 1)); letter-spacing: -0.01em; line-height: 1;
        padding: calc(17px * var(--s, 1)) calc(32px * var(--s, 1)); border-radius: 999px; box-shadow: 0 10px 30px rgba(0,0,0,.18); transform-origin: 0% 50%;
        backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); white-space: nowrap; }}
      .big {{ font-weight: 800; font-size: calc(66px * var(--s, 1)); letter-spacing: -0.035em; color: #fff; line-height: 1;
        text-shadow: 0 6px 30px rgba(0,0,0,.35); transform-origin: 0% 100%; }}
      .card {{ background: var(--glass); color: var(--ink); border-radius: 34px; padding: calc(22px * var(--s, 1)) calc(28px * var(--s, 1)) calc(26px * var(--s, 1)); width: calc(420px * var(--s, 1));
        box-shadow: 0 10px 30px rgba(0,0,0,.18); transform-origin: 0% 50%; backdrop-filter: blur(18px); }}
      .row {{ display: flex; justify-content: space-between; font-weight: 600; font-size: calc(34px * var(--s, 1)); }}
      #cnum {{ color: var(--accent); }}
      .bar {{ height: 10px; border-radius: 6px; background: rgba(0,0,0,.1); margin-top: calc(18px * var(--s, 1)); overflow: hidden; }}
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
