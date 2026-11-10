"""Phone holder TikTok edit: EDL (pauses/stutters/repeats removed) -> A-roll + voice,
original music + UI-prompt SFX, and the HyperFrames composition.
Run from a dir containing src/headphone.mov; writes hf/phone-holder/.
No colour grade/filter on the footage (only full->limited range so browsers show it unchanged)."""
import json, os, subprocess, sys, html
import numpy as np, wave

SRC = "src/headphone.mov"
OUT = "hf/phone-holder"
A = f"{OUT}/assets"
os.makedirs(A, exist_ok=True)
SKIP_MEDIA = "--comp-only" in sys.argv

# ---------------- EDL (source seconds) -- script order, repeats & stutters dropped
SEGMENTS = [
    (8.10, 12.15),   # Okey, ramai betul yang tanya macam mana nak pasang phone holder ni.
    (12.55, 13.68),  # Nak pasang ni senang je.
    (14.15, 18.92),  # First kali korang tengok dekat bagian sini, ada tulis open.
    # 19.14-21.64 "Nampak tak? Dekat bagian sini ada tulis open." (repeat) dropped
    (22.06, 36.15),  # Lepas tu yang ini tulis tight. Open je... Manakala tight... kita nak.
    (36.45, 37.45),  # Macam ni.
    (37.88, 44.35),  # Make sure korang pusingkan dulu dekat bagian open ni...
    (44.93, 47.22),  # Lepas tu, tengoklah korang nak letak kat mana.
    # 49.16-50.64 "Tengok korang nak letak kat mana." (repeat) dropped
    (51.02, 54.62),  # Contohnya korang nak letak dekat sini. Tekapkan dulu.
    (55.16, 59.06),  # Lepas tu, korang pusingkan dekat.
    # 59.20-61.90 "Lepas tu korang yang... Lepas tu..." (stutter) dropped
    (63.10, 64.90),  # mounting action (no speech)
    (70.70, 72.60),  # Macam mana?
]
# silences (silencedetect -32dB) inside kept segments -> trimmed to a short breath
SILENCES = [(16.98, 17.63), (27.68, 28.22), (29.01, 29.33), (29.98, 30.75), (38.91, 39.29),
            (45.42, 45.77), (55.80, 56.30), (57.47, 58.40)]
KEEP_GAP = 0.12

ranges = []
for s, e in SEGMENTS:
    cur = s
    for a, b in SILENCES:
        if a > s and b < e:
            mid = (a + b) / 2
            ranges.append((cur, round(mid - KEEP_GAP / 2, 3)))
            cur = round(mid + KEEP_GAP / 2, 3)
    ranges.append((cur, e))
edl, t = [], 0.0
for s, e in ranges:
    edl.append({"src_start": s, "src_end": e, "out_start": round(t, 3)})
    t += e - s
DUR = round(t, 3)


def out(src):
    for r in edl:
        if r["src_start"] - 1e-6 <= src <= r["src_end"] + 1e-6:
            return round(r["out_start"] + src - r["src_start"], 3)
    return min(r["out_start"] for r in edl if r["src_start"] > src)


json.dump({"duration": DUR, "edl": edl}, open(f"{OUT}/edl.json", "w"), indent=1)
print(f"duration {DUR:.2f}s, {len(edl)} cuts")

# ---------------- media
SR = 48000
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-color_range", "tv", "-r", "30", "-movflags", "+faststart"]


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def env(n, a=0.005, d=0.3):
    tt = np.arange(n) / SR
    return np.minimum(tt / a, 1) * np.exp(-tt / d)


if not SKIP_MEDIA:
    fc, parts = [], []
    for i, r in enumerate(edl):
        s, e = r["src_start"], r["src_end"]
        fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,"
                  f"afade=t=out:st={e - s - 0.01:.3f}:d=0.01[a{i}]")
        parts += [f"[v{i}]", f"[a{i}]"]
    fc.append("".join(parts) + f"concat=n={len(edl)}:v=1:a=1[cv][ca]")
    fc.append("[cv]scale=1080:1920:in_range=pc:out_range=tv:flags=lanczos[vo]")
    fc.append("[ca]highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,"
              "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[ao]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", ";".join(fc),
                    "-map", "[vo]", *VENC, f"{A}/aroll.mp4",
                    "-map", "[ao]", "-c:a", "pcm_s16le", f"{A}/voice.wav"], check=True)
    print("aroll ok")

    # ---- original music: light lo-fi pop, 104 BPM, Dmaj9-Bm9-Gmaj7-A6
    BPM = 104; BEAT = 60 / BPM
    N = int((DUR + 2) * SR); mix = np.zeros((N, 2)); rng = np.random.default_rng(11)

    def add(sig, at, pan=0.0, g=1.0):
        i = int(at * SR); j = min(N, i + len(sig))
        if i >= N: return
        mix[i:j, 0] += sig[:j - i] * g * np.cos((pan + 1) * np.pi / 4)
        mix[i:j, 1] += sig[:j - i] * g * np.sin((pan + 1) * np.pi / 4)

    def mtof(m): return 440 * 2 ** ((m - 69) / 12)

    def tone(f, length, kind):
        n = int(length * SR); tt = np.arange(n) / SR
        if kind == "keys":  # soft electric piano
            s = (np.sin(2*np.pi*f*tt) + 0.3*np.sin(2*np.pi*2*f*tt)*np.exp(-tt/0.15)) * env(n, 0.006, 0.6)
        elif kind == "pad":
            s = sum(np.sin(2*np.pi*f*(1+d)*tt) for d in (-0.004, 0, 0.004)) / 3
            s *= np.minimum(tt/0.5, 1) * np.minimum((length - tt)/0.5, 1)
        elif kind == "bell":
            s = (np.sin(2*np.pi*f*tt) + 0.4*np.sin(2*np.pi*3.01*f*tt)*np.exp(-tt/0.1)) * env(n, 0.002, 0.4)
        else:  # bass
            s = np.tanh(1.5*np.sin(2*np.pi*f*tt)) * env(n, 0.01, 0.45)
        return s

    def kick():
        n = int(0.3*SR); tt = np.arange(n)/SR
        return np.sin(2*np.pi*np.cumsum(55 + 80*np.exp(-tt/0.035))/SR) * env(n, 0.002, 0.11)

    def snap():
        n = int(0.18*SR); s = rng.standard_normal(n)
        return np.diff(np.concatenate([[0], s])) * env(n, 0.001, 0.05) * 0.5

    def hat():
        n = int(0.05*SR); s = np.diff(np.concatenate([[0], rng.standard_normal(n)]))
        return s * env(n, 0.001, 0.012) * 0.45

    CH = [[62, 66, 69, 73, 76], [59, 62, 66, 69, 73], [55, 59, 62, 66, 69], [57, 61, 64, 66, 69]]
    BASS = [38, 35, 31, 33]
    for b in range(int((DUR + 2) / (4*BEAT)) + 1):
        t0 = b*4*BEAT; ch = CH[b % 4]
        for m in ch[:4]:
            add(tone(mtof(m), 4*BEAT, "pad"), t0, 0, 0.035)
        for k, at in enumerate([0, 1.5, 2.5]):
            add(tone(mtof(ch[(k+1) % 4]), BEAT, "keys"), t0 + at*BEAT, 0.3 if k % 2 else -0.3, 0.06)
        if b % 2 == 1:
            add(tone(mtof(ch[4] + 12), BEAT, "bell"), t0 + 3.5*BEAT, 0.5, 0.03)
        add(tone(mtof(BASS[b % 4]), 1.5*BEAT, "bass"), t0, 0, 0.22)
        add(tone(mtof(BASS[b % 4]), BEAT, "bass"), t0 + 2.5*BEAT, 0, 0.16)
        for k in range(4):
            add(kick(), t0 + k*BEAT, 0, 0.4 if k % 2 == 0 else 0.25)
            if k % 2: add(snap(), t0 + k*BEAT, 0, 0.18)
            for h in (0.5, 0.75):
                add(hat(), t0 + (k + h)*BEAT, 0.25, 0.3 if h == 0.5 else 0.15)
    tt = np.arange(N)/SR
    mix *= np.minimum(1, np.minimum(tt/0.8, (DUR + 2 - tt)/2.0))[:, None]
    write_wav(f"{A}/music.wav", mix / (np.abs(mix).max() * 1.12))
    print("music ok")

    # ---- SFX (new set, not the kasut 'ting'): UI pop, UI tick, bright double-ting, soft swish, sparkle
    def ui_pop():
        n = int(0.25*SR); tt = np.arange(n)/SR
        f = 520 + 900*np.exp(-tt/0.025)
        s = np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.001, 0.06)
        return s / np.abs(s).max() * 0.6

    def ui_tick():
        n = int(0.2*SR); tt = np.arange(n)/SR
        s = (np.sin(2*np.pi*1800*tt)*env(n, 0.0005, 0.02) + 0.6*np.sin(2*np.pi*2400*tt)*env(n, 0.0005, 0.035))
        s[int(0.045*SR):] += (np.sin(2*np.pi*2400*tt)*env(n, 0.0005, 0.04))[:n - int(0.045*SR)] * 0.7
        return s / np.abs(s).max() * 0.55

    def ting2():  # bright two-note "ting-ting"
        n = int(1.3*SR); s = np.zeros(n)
        for k, f in enumerate([2349.3, 3136.0]):
            o = int(k*0.11*SR); tt = np.arange(n - o)/SR
            s[o:] += (np.sin(2*np.pi*f*tt)*np.exp(-tt/0.32) + 0.35*np.sin(2*np.pi*f*2.76*tt)*np.exp(-tt/0.08)) * np.minimum(tt/0.002, 1)
        return s / np.abs(s).max() * 0.6

    def swish(length=0.45):
        n = int(length*SR); tt = np.arange(n)/SR; x = rng.standard_normal(n)
        cut = 600 + 7000*np.sin(np.pi*tt/length)**2; a = np.exp(-2*np.pi*cut/SR)
        y = np.zeros(n); acc = 0.0
        for i in range(n):
            acc = (1-a[i])*x[i] + a[i]*acc; y[i] = acc
        y *= np.sin(np.pi*tt/length)**2
        return y / np.abs(y).max() * 0.4

    def sparkle():
        n = int(1.4*SR); s = np.zeros(n)
        for k, f in enumerate([3520, 4186, 4699, 5274, 6272]):
            o = int(k*0.05*SR); tt = np.arange(n - o)/SR
            s[o:] += np.sin(2*np.pi*f*tt)*np.exp(-tt/0.3)
        return s / np.abs(s).max() * 0.35

    for name, fn in [("sfx_pop", ui_pop), ("sfx_tick", ui_tick), ("sfx_ting2", ting2),
                     ("sfx_swish", swish), ("sfx_sparkle", sparkle)]:
        write_wav(f"{A}/{name}.wav", fn())
    print("sfx ok")

# ---------------- composition
HOOK = "Phone holder ni|memang worth it!"
HOOK_END = 3.0
# (src time of the spoken word, prompt text, icon)  -- ~half the lines, key words only
PROMPTS = [
    (12.94, "senang je pasang", "✓"),
    (18.12, "OPEN", "↺", "r"),
    (23.46, "TIGHT", "↻", "r"),
    (25.74, "open = longgarkan", "•"),
    (32.34, "tight = ketatkan", "•"),
    (40.24, "pusing dulu", "↺"),
    (46.32, "pilih kedudukan", "•"),
    (52.62, "tekap dulu", "✓"),
    (56.52, "pusing & lock", "↻"),
    (71.20, "siap! senang kan?", "✓"),
]
items = sorted((out(p[0]), p[1], p[2], p[3] if len(p) > 3 else "") for p in PROMPTS)
ov = []
for i, (t0, txt, ic, side) in enumerate(items):
    start = max(t0 - 0.08, HOOK_END + 0.15)
    nxt = items[i + 1][0] - 0.08 if i + 1 < len(items) else DUR
    d = round(min(1.9, nxt - start - 0.12, DUR - start), 3)
    ov.append((round(start, 3), d, txt, ic, side))

cuts = [r["out_start"] for r in edl[1:]]
el, js, sfx = [], [], []
el.append(f'''<div id="aroll-wrap" class="stage">
      <video id="aroll" class="clip" src="assets/aroll.mp4" data-start="0" data-duration="{DUR}"
        data-media-start="0" data-track-index="0" muted playsinline></video>
    </div>''')
# subtle punch-in alternation hides jump cuts (no filter, framing only)
scale = 1.0
for c in cuts:
    scale = 1.04 if scale == 1.0 else 1.0
    js.append(f'tl.set("#aroll-wrap", {{ scale: {scale} }}, {c});')
js.append(f'tl.fromTo("#aroll", {{ scale: 1.0 }}, {{ scale: 1.03, duration: {HOOK_END}, ease: "sine.out" }}, 0);')
js.append(f'tl.set("#aroll", {{ scale: 1.0 }}, {HOOK_END});')

# hook card
lines = "".join(f"<span>{html.escape(x)}</span>" for x in HOOK.split("|"))
el.append(f'<div id="hook" class="clip hook" data-start="0.1" data-duration="{HOOK_END - 0.1:.2f}" data-track-index="3">'
          f'<div class="tag">REVIEW</div><div class="lines">{lines}</div></div>')
js.append('tl.fromTo("#hook", { opacity: 0, y: 18, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "back.out(1.6)" }, 0.1);')
js.append('tl.fromTo("#hook .lines span", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out", stagger: 0.16 }, 0.3);')
js.append(f'tl.to("#hook", {{ opacity: 0, y: -10, duration: 0.3, ease: "sine.in" }}, {HOOK_END - 0.35:.2f});')
sfx += [(0.05, "sfx_swish", 0.35, 0.5), (0.3, "sfx_ting2", 0.45, 1.3)]

# UI-prompt overlays
for i, (t0, d, txt, ic, side) in enumerate(ov):
    oid = f"p{i}"
    el.append(f'<div id="{oid}" class="clip prompt{' right' if side else ''}" data-start="{t0}" data-duration="{d}" data-track-index="3">'
              f'<i>{ic}</i><b>{html.escape(txt)}</b></div>')
    js.append(f'tl.fromTo("#{oid}", {{ opacity: 0, y: 12, scale: 0.9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2)" }}, {t0});')
    js.append(f'tl.fromTo("#{oid} b", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.35, ease: "power2.out" }}, {t0 + 0.08:.3f});')
    js.append(f'tl.to("#{oid}", {{ opacity: 0, y: -6, duration: 0.25, ease: "sine.in" }}, {t0 + d - 0.25:.3f});')
    last = i == len(ov) - 1
    sfx.append((t0, "sfx_sparkle" if last else ("sfx_pop" if i % 2 == 0 else "sfx_tick"), 0.42 if last else 0.5, 1.3))

aud = [f'<audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{DUR}" data-media-start="0" data-volume="1" data-track-index="10"></audio>']  # no music (voice + SFX only)
for i, (t0, name, vol, d) in enumerate(sorted(sfx)):
    aud.append(f'<audio id="sfx{i}" src="assets/{name}.wav" data-start="{max(t0, 0)}" data-duration="{d}" data-media-start="0" data-volume="{vol}" data-track-index="{12 + i % 3}"></audio>')

HTML = f'''<!doctype html>
<html lang="ms" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Lexend Mega"; src: url("assets/LexendMega-Regular.ttf") format("truetype"); font-weight: 400; font-display: block; }}
      @font-face {{ font-family: "Lexend Mega"; src: url("assets/LexendMega-Medium.ttf") format("truetype"); font-weight: 500; font-display: block; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; }}
      #aroll-wrap {{ position: absolute; inset: 0; transform-origin: 50% 40%; }}
      #aroll-wrap video {{ width: 1080px; height: 1920px; object-fit: cover; transform-origin: 50% 40%; }}
      /* glass card behind white text: keeps text bright on any background */
      .hook, .prompt {{ inset: auto; color: #fff; font-family: "Lexend Mega", sans-serif;
        background: rgba(12,12,14,.42); backdrop-filter: blur(14px) saturate(1.1);
        border: 1px solid rgba(255,255,255,.22); box-shadow: 0 8px 30px rgba(0,0,0,.25); opacity: 0; }}
      /* empty area: top-left (car roof / window), below TikTok's top bar, clear of face & product */
      .hook {{ left: 64px; top: 270px; padding: 22px 30px 24px; border-radius: 26px; }}
      .hook .tag {{ font-size: 15px; letter-spacing: .3em; opacity: .75; margin-bottom: 12px; }}
      .hook .lines span {{ display: block; font-size: 34px; font-weight: 500; line-height: 1.35; letter-spacing: -.02em; }}
      .prompt {{ left: 64px; top: 290px; display: flex; align-items: center; gap: 14px;
        padding: 14px 26px 14px 16px; border-radius: 999px; }}
      .prompt.right {{ left: auto; right: 64px; }}  /* product arm sits top-left in these shots */
      .prompt i {{ font-style: normal; width: 34px; height: 34px; border-radius: 50%; background: #fff; color: #111;
        display: grid; place-items: center; font-size: 18px; font-family: system-ui, sans-serif; }}
      .prompt b {{ font-weight: 400; font-size: 24px; letter-spacing: -.01em; white-space: nowrap; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
{chr(10).join("      " + e for e in el)}
{chr(10).join("      " + a for a in aud)}
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
open(f"{OUT}/index.html", "w").write(HTML)
for t0, d, txt, ic, side in ov:
    print(f"  {t0:6.2f} +{d:.2f}  {txt}")
