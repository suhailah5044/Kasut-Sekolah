"""Video 2: cut A-roll from the EDL, b-roll close-ups, new music + SFX.
Run from repo root: python3 scripts/v2/build_media.py [--preview]
No colour grade: only full->limited range conversion so browser colours match the source."""
import json, subprocess, os, sys
import numpy as np, wave

SRC = "src/kasut2.mov"
OUT = "hyperframes/kasut2/assets"
os.makedirs(OUT, exist_ok=True)
edl = json.load(open("scripts/v2/edl.json"))["edl"]
PREVIEW = "--preview" in sys.argv
W, H = (720, 1280) if PREVIEW else (1080, 1920)
RANGE = f"scale={W}:{H}:in_range=pc:out_range=tv:flags=lanczos"
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "21" if PREVIEW else "16",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709", "-color_range", "tv", "-r", "30", "-movflags", "+faststart"]


def run(cmd):
    subprocess.run(cmd, check=True)


# ---------- A-roll + cleaned voice (8ms fades at every cut so no clicks)
fc, parts = [], []
for i, r in enumerate(edl):
    s, e = r["src_start"], r["src_end"]
    d = e - s
    fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}]")
    fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,"
              f"afade=t=out:st={d-0.008:.3f}:d=0.008[a{i}]")
    parts += [f"[v{i}]", f"[a{i}]"]
fc.append("".join(parts) + f"concat=n={len(edl)}:v=1:a=1[cv][ca]")
fc.append(f"[cv]{RANGE}[vo]")
fc.append("[ca]highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,"
          "loudnorm=I=-15:TP=-1.5:LRA=9,aresample=48000[ao]")
run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", ";".join(fc),
     "-map", "[vo]", *VENC, f"{OUT}/aroll.mp4", "-map", "[ao]", "-c:a", "pcm_s16le", f"{OUT}/voice.wav"])
print("aroll ok")

# ---------- B-roll close-ups: 9:16 crop on the shoe, normal speed, muted
BROLL = {  # name: (src_start, crop w, crop h, x, y)
    "broll_design": (15.0, 720, 1280, 180, 220),
    "broll_kalis": (39.6, 720, 1280, 0, 300),
    "broll_tarik": (57.2, 720, 1280, 0, 330),
    "broll_tapak": (72.9, 720, 1280, 60, 260),
    "broll_ringan": (30.0, 720, 1280, 260, 160),
    "broll_cta": (48.6, 720, 1280, 200, 220),
}
for name, (s, cw, ch, x, y) in BROLL.items():   # normal speed (no slow-mo)
    vf = f"crop={cw}:{ch}:{x}:{y},{RANGE}"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-t", "2.8", "-i", SRC,
         "-vf", vf, "-an", *VENC, f"{OUT}/{name}.mp4"])
    print(name, "ok")

# ---------- Music: original clean/upbeat bed, 112 BPM, Fmaj7-G6-Am7-Em7
SR, BPM = 48000, 112
BEAT = 60 / BPM
dur = 58.0
N = int(dur * SR)
mix = np.zeros((N, 2))
rng = np.random.default_rng(11)


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


def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if i >= N:
        return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:j, 0] += sig[: j - i] * gain * l
    mix[i:j, 1] += sig[: j - i] * gain * r


def tone(f, length, kind):
    n = int(length * SR); t = np.arange(n) / SR
    if kind == "keys":   # soft electric-piano-ish
        s = (np.sin(2*np.pi*f*t) + 0.25*np.sin(2*np.pi*2*f*t + 0.3*np.sin(2*np.pi*f*t))) * env(n, 0.003, 0.55)
    elif kind == "bell":
        s = (np.sin(2*np.pi*f*t) + 0.3*np.sin(2*np.pi*3.01*f*t)) * env(n, 0.002, 0.25)
    else:  # sub bass
        s = np.tanh(1.6*np.sin(2*np.pi*f*t)) * env(n, 0.008, 0.35)
    return s


def kick():
    n = int(0.3*SR); t = np.arange(n)/SR
    f = 48 + 90*np.exp(-t/0.03)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.002, 0.1)


def noise_hit(length, decay, hp=True):
    n = int(length*SR); s = rng.standard_normal(n)
    if hp:
        s = np.diff(np.concatenate([[0], s]))
    return s * env(n, 0.001, decay)


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


CHORDS = [[53, 57, 60, 64], [55, 59, 62, 64], [57, 60, 64, 67], [52, 55, 59, 62]]
BASS = [29, 31, 33, 28]
for b in range(int(dur / (4*BEAT)) + 1):
    t0 = b * 4 * BEAT
    ch = CHORDS[b % 4]
    for k in (0, 1.5, 2.5):  # syncopated chord stabs
        for m in ch:
            add(tone(mtof(m), 1.2*BEAT, "keys"), t0 + k*BEAT, 0, 0.045)
    for k, off in enumerate((0, 0.75, 2, 3.5)):
        add(tone(mtof(BASS[b % 4] + (12 if k == 3 else 0)), 0.9*BEAT, "bass"), t0 + off*BEAT, 0, 0.22)
    mel = [ch[3]+12, ch[2]+12, ch[3]+12, ch[1]+24]
    for k, m in enumerate(mel):
        add(tone(mtof(m), BEAT, "bell"), t0 + (k + 0.5)*BEAT, (-0.5 if k % 2 else 0.5), 0.035)
    for k in range(4):
        add(kick(), t0 + k*BEAT, 0, 0.5)
        add(noise_hit(0.05, 0.012), t0 + k*BEAT + BEAT/2, 0.35, 0.18)
        add(noise_hit(0.05, 0.008), t0 + k*BEAT + BEAT/4*3, -0.35, 0.08)
    for k in (1, 3):  # clap
        add(noise_hit(0.2, 0.05, hp=False) * 0.6, t0 + k*BEAT, 0, 0.22)
fade = np.minimum(1, np.minimum(np.arange(N)/SR/0.8, (dur - np.arange(N)/SR)/2.0))
mix *= fade[:, None]
mix /= np.abs(mix).max() * 1.12
write_wav(f"{OUT}/music.wav", mix)
json.dump({"bpm": BPM, "beat": BEAT, "offset": 0.0}, open(f"{OUT}/beats.json", "w"))
print("music ok")


# ---------- SFX: soft pop (text pop-in), swish (b-roll), sparkle (light sweep)
def pop():
    n = int(0.18*SR); t = np.arange(n)/SR
    f = 900*np.exp(-t/0.03) + 380
    s = np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.001, 0.035)
    return s / np.abs(s).max() * 0.55


def swish(length=0.55):
    n = int(length*SR); t = np.arange(n)/SR
    x = rng.standard_normal(n)
    cut = 800 + 7000*(t/length)**1.5
    a = np.exp(-2*np.pi*cut/SR); y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc = (1-a[i])*x[i] + a[i]*acc; y[i] = acc
    y *= np.sin(np.pi*t/length)**3
    return y / np.abs(y).max() * 0.4


def sparkle():
    n = int(1.4*SR); s = np.zeros(n)
    for k, f in enumerate([3520, 4186, 4699, 5588, 6272]):
        o = int(k*0.05*SR); tt = np.arange(n - o)/SR
        s[o:] += np.sin(2*np.pi*f*tt)*np.exp(-tt/0.3)*0.4
    return s / np.abs(s).max() * 0.35


write_wav(f"{OUT}/sfx_pop.wav", pop())
write_wav(f"{OUT}/sfx_swish.wav", swish())
write_wav(f"{OUT}/sfx_sparkle.wav", sparkle())
print("sfx ok")
