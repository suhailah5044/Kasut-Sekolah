"""Build the edit decision list from TWO takes (k1 = 'kasut sekolah 1.mov', k2 = 'Kasut sekolah 2.mov').
Best delivery of each line is picked, repeats dropped, every kept sentence plays in full,
pauses trimmed to a short breath. Outputs edl.json (source, src range, out time)."""
import json

# (source, src_start, src_end, label) — final script order
SEGMENTS = [
    ("k1", 60.00, 64.32, "HOOK: kena air pun jangan risau, takkan tembus ke dalam"),
    ("k2", 8.62, 11.80, "ibu ayah cari kasut sekolah, memang recommend"),
    ("k2", 12.14, 18.20, "harga murah, design sporty, cantik"),
    ("k2", 18.50, 23.10, "mall takkan dapat harga bawah RM50, anak-anak suka"),
    ("k1", 30.16, 35.88, "tapak anti-slip, selesa, aktiviti, bersukan"),
    ("k1", 40.12, 44.78, "anak lasak, recommend"),
    ("k2", 83.48, 85.94, "kasut sekolah ni sangat ringan"),
    ("k2", 53.10, 63.50, "senang guna, tiada tali, tarik & ketat, darjah 1-3"),
    ("k1", 55.74, 59.95, "anak suka, kotor just lap"),
    ("k2", 90.50, 94.75, "CTA: murah, cantik, beg kuning"),
    ("k2", 98.80, 102.30, "beli sekarang, takut size tak ada"),
]
# dropped: k1 intro/persiapan (k2 intro is stronger), k1 'twist-tash' take (k2 clearer),
# k2 water-resistant + 2nd water line (hook covers it), k2 2nd 'sekolah rendah', k2 2nd anti-slip,
# k1/k2 repeated 'design cantik', k2 1st 'beli sekarang ... delay'.

# pauses (silencedetect -30dB, >=0.3s) per source, trimmed to KEEP_GAP
SILENCES = {
    "k1": [(29.728, 30.223), (35.886, 36.261), (38.027, 38.404), (42.838, 43.314), (57.596, 58.018),
           (61.424, 61.794)],
    "k2": [(11.768, 12.140), (13.707, 14.140), (18.079, 18.548), (52.668, 53.153), (56.009, 56.410),
           (57.039, 57.778), (90.205, 90.553), (98.184, 98.821)],
}
KEEP_GAP = 0.10

ranges = []
for src, s, e, label in SEGMENTS:
    cur = s
    for a, b in SILENCES[src]:
        if a > s and b < e:
            mid = (a + b) / 2
            ranges.append([src, cur, round(mid - KEEP_GAP / 2, 3), label])
            cur = round(mid + KEEP_GAP / 2, 3)
    ranges.append([src, cur, e, label])

FPS = 30  # snap cut points to whole frames so per-segment video/audio stay in sync
ranges = [[src, round(round(s * FPS) / FPS, 4), round(round(e * FPS) / FPS, 4), label] for src, s, e, label in ranges]

t = 0.0
edl = []
for src, s, e, label in ranges:
    edl.append({"src": src, "src_start": s, "src_end": e, "out_start": round(t, 3), "label": label})
    t += e - s
json.dump({"duration": round(t, 3), "edl": edl}, open("edl.json", "w"), indent=1)

if __name__ == "__main__":
    print(f"edited duration: {t:.2f}s, {len(edl)} cuts")
    for r in edl:
        print(f'{r["out_start"]:6.2f}  {r["src"]} {r["src_start"]:6.2f}-{r["src_end"]:6.2f}  {r["label"]}')
