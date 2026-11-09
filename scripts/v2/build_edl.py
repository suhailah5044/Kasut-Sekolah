"""Video 2 EDL: best take of each point, script order, pauses trimmed.
Run from repo root. Writes scripts/v2/edl.json."""
import json

# (src_start, src_end, label) — cut points checked against audio energy (20ms RMS dips)
SEGMENTS = [
    (18.50, 25.06, "HOOK: dekat mall takkan dapat bawah RM50, tak ada tali"),
    # 2.9-7.9 dropped: 1st take "ibu ayah... this one. Kena grab" (sangkut)
    (8.62, 11.84, "ibu ayah cari kasut sekolah, memang recommend"),
    (12.15, 17.90, "harga murah, design sporty, cantik"),
    # 25.3-32.9 dropped: "tapi dia, ok untuk anak kasut..." (tersangkut, ulang)
    (33.15, 41.75, "anak nak sangat, mudah, grab, kalis air"),
    (42.32, 44.88, "kotor? cuci je"),
    # 46.0-48.4 dropped: 1st take 'kena air takkan masuk' (ulang)
    (48.70, 51.33, "kena air tak tembus ke dalam"),
    (52.48, 54.70, "cara guna senang"),          # 'tak payah pakai tali' dropped (dah sebut di hook)
    (56.45, 60.00, "tarik dan ketatkan"),
    # 60.0-66.1 dropped: 'mudah... satu dua tiga' (diulang dalam ayat seterusnya)
    (66.15, 71.18, "sesuai sekolah rendah, senang pakai"),
    (73.03, 74.98, "tapak anti-slip"),            # 71.7-73.0 false start + 75-83 ulang anti-slip dropped
    (83.48, 90.25, "ringan, aktiviti dalam/luar sekolah"),
    (90.50, 94.84, "CTA: beg kuning"),
    # 95.1-98.7 dropped: 'beli sekarang... delay' (ulang 'beli sekarang')
    (98.76, 102.32, "beli sekarang, takut size habis"),
]

SILENCES = [(6.521, 6.995), (11.771, 12.133), (13.708, 14.140), (18.080, 18.547), (23.108, 23.607),
            (23.936, 24.225), (25.039, 25.410), (32.449, 32.918), (37.001, 37.374), (39.306, 39.666),
            (41.752, 42.245), (44.887, 45.259), (48.393, 48.797), (52.668, 53.153), (56.013, 56.409),
            (57.064, 57.774), (63.449, 63.933), (65.908, 66.168), (71.159, 71.541), (72.751, 73.051),
            (83.073, 83.509), (88.297, 88.660), (90.208, 90.547), (94.704, 95.098), (98.207, 98.820)]
KEEP_GAP = 0.12

ranges = []
for s, e, label in SEGMENTS:
    cur = s
    for a, b in SILENCES:
        if a > s and b < e:
            mid = (a + b) / 2
            ranges.append([cur, round(mid - KEEP_GAP / 2, 3), label])
            cur = round(mid + KEEP_GAP / 2, 3)
    ranges.append([cur, e, label])

t = 0.0
edl = []
for s, e, label in ranges:
    edl.append({"src_start": s, "src_end": e, "out_start": round(t, 3), "label": label})
    t += e - s
json.dump({"duration": round(t, 3), "edl": edl}, open("scripts/v2/edl.json", "w"), indent=1)
print(f"edited duration: {t:.2f}s, {len(edl)} cuts")
for r in edl:
    print(f'{r["out_start"]:6.2f}  src {r["src_start"]:6.2f}-{r["src_end"]:6.2f}  {r["label"]}')
