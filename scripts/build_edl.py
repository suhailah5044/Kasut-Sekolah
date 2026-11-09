"""Build the edit decision list: script order, repeats removed, pauses trimmed.
Outputs edl.json with source ranges and a timeline map (src -> edited time)."""
import json

# (src_start, src_end, label) — script order after restructuring
SEGMENTS = [
    (60.00, 64.32, "HOOK: kena air pun jangan risau, takkan tembus"),
    (1.00, 5.22, "korang dah beli belum kasut sekolah"),
    (8.80, 17.85, "persiapan awal, stok, size ada"),  # 5.55-8.8 false start "better korang beli, better korang..." dropped
    (21.90, 28.22, "recommend, ringan, sekolah rendah"),
    (30.16, 35.88, "anti-slip, aktiviti, sukan"),  # "Bagi yang belakang ni pun," restart dropped
    # 36.26-40.12 filler dropped ("ada main... tak kisahlah. Memang sangat sesuai")
    (40.12, 44.78, "anak lasak, recommend"),
    (45.10, 52.58, "bukan bertali, twist lock"),
    (53.30, 55.03, "design mestilah cantik"),          # 2nd 'design memang cantik' dropped
    (55.74, 59.95, "anak suka, kotor just lap"),
    # 64.3-70.7 dropped: 3rd 'design cantik' + repeat 'ringan' + false start
    (70.72, 79.52, "CTA: selesa, cantik, beg kuning, harga murah"),
]

# pauses inside kept segments (from silencedetect -30dB), trimmed to a 0.10s breath
SILENCES = [(8.335, 8.879), (12.786, 13.228), (24.525, 24.983), (29.728, 30.223),
            (38.027, 38.404), (42.838, 43.314), (47.028, 48.227), (49.290, 49.687),
            (49.907, 50.318), (57.596, 58.018), (61.424, 61.794), (75.225, 75.756)]
KEEP_GAP = 0.10

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
print(f"edited duration: {t:.2f}s, {len(edl)} cuts")
json.dump({"duration": round(t, 3), "edl": edl}, open("edl.json", "w"), indent=1)


def src_to_out(x):
    for r in edl:
        if r["src_start"] <= x <= r["src_end"]:
            return round(r["out_start"] + x - r["src_start"], 3)
    return None


if __name__ == "__main__":
    for r in edl:
        print(f'{r["out_start"]:6.2f}  src {r["src_start"]:6.2f}-{r["src_end"]:6.2f}  {r["label"]}')
