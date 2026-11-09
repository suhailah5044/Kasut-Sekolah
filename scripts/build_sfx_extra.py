"""Extra original SFX so each overlay animation style has its own sound:
pop (pop-in), tick (typewriter), swish (blur/slide), rise (comfort bar fill).
Run from the working dir (writes hf/kasut/assets/)."""
import wave
import numpy as np

SR = 48000
OUT = "hf/kasut/assets"
rng = np.random.default_rng(11)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    x = np.stack([x, x], 1)
    with wave.open(path, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def norm(x, g):
    return x / np.abs(x).max() * g


def pop():
    # bubbly pop: fast downward pitch sweep + tiny click
    n = int(0.25 * SR); t = np.arange(n) / SR
    f = 380 + 900 * np.exp(-t / 0.018)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05)
    s[:60] += rng.standard_normal(60) * 0.3
    return norm(s * np.minimum(t / 0.001, 1), 0.6)


def tick():
    # soft typewriter-ish tick, repeated for the letters
    n = int(0.9 * SR); s = np.zeros(n)
    k = int(0.012 * SR); tt = np.arange(k) / SR
    click = (np.sin(2 * np.pi * 3200 * tt) + 0.5 * rng.standard_normal(k)) * np.exp(-tt / 0.003)
    for j in range(12):
        i = int(j * 0.045 * SR)
        s[i:i + k] += click * (0.9 if j % 2 else 0.7)
    return norm(s, 0.35)


def swish():
    # short airy swish (band-passed noise, fast swell)
    length = 0.45
    n = int(length * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    cut = 1200 + 6000 * np.sin(np.pi * t / length) ** 2
    a = np.exp(-2 * np.pi * cut / SR); y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc = (1 - a[i]) * x[i] + a[i] * acc; y[i] = acc
    y = np.diff(np.concatenate([[0], y]))  # high-pass for air
    y *= np.sin(np.pi * t / length) ** 3
    return norm(y, 0.4)


def rise():
    # gentle upward chime sweep for the comfort bar
    n = int(1.1 * SR); t = np.arange(n) / SR
    f = 700 * 2 ** (t / 0.6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(t / 0.05, 1) * np.exp(-t / 0.45)
    return norm(s, 0.35)


write_wav(f"{OUT}/sfx_pop.wav", pop())
write_wav(f"{OUT}/sfx_tick.wav", tick())
write_wav(f"{OUT}/sfx_swish.wav", swish())
write_wav(f"{OUT}/sfx_rise.wav", rise())
print("extra sfx ok")
