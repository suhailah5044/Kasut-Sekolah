"""Cut the A-roll from the EDL, make slow-mo b-roll crops, synthesize music + SFX.
No colour filters: only a full->limited range conversion so colours look identical in browsers."""
import json, subprocess, os, sys
import numpy as np, wave

SRC = "src/kasut.mov"
OUT = "hf/kasut/assets"
os.makedirs(OUT, exist_ok=True)
edl = json.load(open("edl.json"))["edl"]
PREVIEW = "--preview" in sys.argv
W, H = (720, 1280) if PREVIEW else (1080, 1920)
RANGE = f"scale={W}:{H}:in_range=pc:out_range=tv:flags=lanczos"
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20" if PREVIEW else "16",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709", "-color_range", "tv", "-r", "30", "-movflags", "+faststart"]


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------- A-roll: concat all ranges, 8ms audio fades at every cut (no clicks)
parts_v, parts_a, fc = [], [], []
for i, r in enumerate(edl):
    s, e = r["src_start"], r["src_end"]
    d = e - s
    fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}]")
    fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,"
              f"afade=t=out:st={d-0.008:.3f}:d=0.008[a{i}]")
    parts_v.append(f"[v{i}]"); parts_a.append(f"[a{i}]")
n = len(edl)
fc.append("".join(p for pair in zip(parts_v, parts_a) for p in pair) + f"concat=n={n}:v=1:a=1[cv][ca]")
fc.append(f"[cv]{RANGE}[vo]")
# voice: gentle cleanup + loudness to TikTok-ish level (no colour/visual change)
fc.append("[ca]highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,"
          "loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000[ao]")
run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", ";".join(fc),
     "-map", "[vo]", *VENC, f"{OUT}/aroll.mp4", "-map", "[ao]", "-c:a", "pcm_s16le", f"{OUT}/voice.wav"])
# A-roll video stays muted in the composition; voice.wav is the voice track
print("aroll ok")

# ---------- B-roll: crop on the shoe, 0.6x slow motion, muted
BROLL = {  # name: (src_start, crop w, crop h, x, y)
    "broll_ringan": (3.20, 720, 1280, 40, 240),
    "broll_antislip": (33.00, 720, 1280, 150, 400),
    "broll_design": (75.30, 720, 1280, 120, 280),
    "broll_harga": (65.00, 720, 1280, 300, 180),
}
SPEED = 0.6
for name, (s, cw, ch, x, y) in BROLL.items():
    src_len = 2.6 * SPEED
    vf = (f"crop={cw}:{ch}:{x}:{y},setpts=PTS/{SPEED},"
          f"minterpolate=fps=30:mi_mode=blend,{RANGE}")
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", f"{src_len:.3f}", "-i", SRC,
         "-vf", vf, "-an", *VENC, f"{OUT}/{name}.mp4"])
    print(name, "ok")

# ---------- Music + SFX synthesis (original, royalty-free)
SR = 48000
BPM = 100
BEAT = 60 / BPM


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def env(n, a=0.005, d=0.3):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


dur = 62.0
N = int(dur * SR)
mix = np.zeros((N, 2))
rng = np.random.default_rng(7)


def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    j = min(N, i + len(sig))
    if i >= N:
        return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:j, 0] += sig[: j - i] * gain * l
    mix[i:j, 1] += sig[: j - i] * gain * r


def note(f, length, kind="pluck"):
    n = int(length * SR); t = np.arange(n) / SR
    if kind == "pluck":
        s = (np.sin(2*np.pi*f*t) + 0.35*np.sin(4*np.pi*f*t) + 0.12*np.sin(6*np.pi*f*t)) * env(n, 0.004, 0.35)
    elif kind == "pad":
        s = sum(np.sin(2*np.pi*f*(1+dt)*t) for dt in (-0.003, 0, 0.003)) / 3
        s *= np.minimum(t/0.4, 1) * np.minimum((length - t)/0.4, 1)
    else:  # bass
        s = np.sin(2*np.pi*f*t) * env(n, 0.01, 0.5)
    return s


def kick():
    n = int(0.35*SR); t = np.arange(n)/SR
    f = 50 + 70*np.exp(-t/0.04)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.002, 0.12)


def hat():
    n = int(0.06*SR)
    s = rng.standard_normal(n); s = np.diff(np.concatenate([[0], s]))
    return s * env(n, 0.001, 0.015) * 0.5


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


# Cmaj7 - Am7 - Fmaj7 - G6, one chord per bar (4 beats)
CHORDS = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 64]]
BASS = [36, 33, 29, 31]
bars = int(dur / (4*BEAT)) + 1
for b in range(bars):
    t0 = b * 4 * BEAT
    ch = CHORDS[b % 4]
    for m in ch:
        add(note(mtof(m), 4*BEAT, "pad"), t0, 0, 0.05)
    add(note(mtof(BASS[b % 4]), 2*BEAT, "bass"), t0, 0, 0.30)
    add(note(mtof(BASS[b % 4]), 2*BEAT, "bass"), t0 + 2.5*BEAT, 0, 0.22)
    arp = [ch[0]+12, ch[2]+12, ch[1]+12, ch[3]+12, ch[2]+12, ch[1]+12, ch[3]+12, ch[2]+12]
    for k, m in enumerate(arp):
        add(note(mtof(m), BEAT, "pluck"), t0 + k*BEAT/2, (-0.4 if k % 2 else 0.4), 0.07)
    for k in range(4):
        add(kick(), t0 + k*BEAT, 0, 0.45)
        add(hat(), t0 + k*BEAT + BEAT/2, 0.3, 0.35)
fade = np.minimum(1, np.minimum(np.arange(N)/SR/1.0, (dur - np.arange(N)/SR)/2.0))
mix *= fade[:, None]
mix /= np.abs(mix).max() * 1.12
write_wav(f"{OUT}/music.wav", mix)
json.dump({"bpm": BPM, "beat": BEAT, "offset": 0.0}, open(f"{OUT}/beats.json", "w"))
print("music ok")


def ting(f0=2093.0):
    n = int(1.2*SR); t = np.arange(n)/SR
    s = (np.sin(2*np.pi*f0*t)*np.exp(-t/0.35) + 0.5*np.sin(2*np.pi*f0*1.5*t)*np.exp(-t/0.22)
         + 0.25*np.sin(2*np.pi*f0*2.76*t)*np.exp(-t/0.12))
    s *= np.minimum(t/0.002, 1)
    return s / np.abs(s).max() * 0.6


def whoosh(length=0.7):
    n = int(length*SR); t = np.arange(n)/SR
    x = rng.standard_normal(n)
    # sweeping one-pole low-pass
    cut = 300 + 5000*np.sin(np.pi*t/length)**2
    a = np.exp(-2*np.pi*cut/SR); y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc = (1-a[i])*x[i] + a[i]*acc; y[i] = acc
    y *= np.sin(np.pi*t/length)**2
    return y / np.abs(y).max() * 0.45


def shimmer():
    n = int(1.6*SR); s = np.zeros(n)
    for k, f in enumerate([2637, 3136, 3951, 5274]):
        tt = np.arange(n - int(k*0.07*SR))/SR
        s[int(k*0.07*SR):] += np.sin(2*np.pi*f*tt)*np.exp(-tt/0.4)*0.5
    return s / np.abs(s).max() * 0.4


write_wav(f"{OUT}/sfx_ting.wav", ting())
write_wav(f"{OUT}/sfx_ting_hi.wav", ting(2637.0))
write_wav(f"{OUT}/sfx_whoosh.wav", whoosh())
write_wav(f"{OUT}/sfx_shimmer.wav", shimmer())
print("sfx ok")
