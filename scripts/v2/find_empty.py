"""Find empty space (wall/floor) for each text overlay.
Occupied = person (MediaPipe selfie multiclass: hair/body/face/clothes/accessories)
           incl. class 'others' = the shoes held in hand, dilated for breathing room.
For each overlay, sample frames across its whole on-screen time (A-roll or b-roll, whichever
is visible), union the masks, then pick the pill position with zero overlap and the
most clearance, inside TikTok's safe zone.
Usage: python3 scripts/v2/find_empty.py <model.tflite>   (writes scripts/v2/placements.json)"""
import json, subprocess, sys
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

MODEL = sys.argv[1]
ASSETS = "hyperframes/kasut2/assets"
W, H = 1080, 1920
SCALE = 4                      # work at 270x480
SAFE = dict(x0=50, x1=W - 150, y0=230, y1=H - 400)   # TikTok top bar / right rail / caption
RAIL_TOP = 860            # right-rail icons start about here; above it the right edge is free
X1_HIGH = W - 50
MASKS = {}
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=MODEL), output_category_mask=True))


def frame(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={W//SCALE}:{H//SCALE}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H // SCALE, W // SCALE, 3).copy()


def occupied(img):
    """-> (hard, soft): hard = face/hair+hijab/hands/shoes (never covered),
    soft = clothes (only if no empty wall/floor exists for the whole time on screen)."""
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=img))
    cat = res.category_mask.numpy_view().reshape(img.shape[:2])
    hard = np.isin(cat, (1, 2, 3, 5)).astype(np.uint8)    # hair, body-skin, face-skin, others(shoes)
    soft = (cat == 4).astype(np.uint8)                      # clothes
    # shoe parts the model misses: dark blobs touching the person
    dark = (cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) < 50).astype(np.uint8)
    n, lab = cv2.connectedComponents(dark)
    near = cv2.dilate(hard | soft, np.ones((5, 5), np.uint8)) > 0
    for k in np.unique(lab[near & (dark > 0)]):
        if k:
            hard[lab == k] = 1
    k = np.ones((11, 11), np.uint8)                          # ~20px margin (covers punch-in zoom)
    hard = cv2.dilate(cv2.morphologyEx(hard, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), k) > 0
    soft = cv2.dilate(soft, k) > 0
    return hard, soft & ~hard


def place(jobs):
    """jobs: list of {id, w, h, samples:[(path, t), ...]} -> {id: (x, y)} in 1080x1920 px."""
    outp, debug = {}, []
    for j in jobs:
        best = None
        for vi, V in enumerate(j["variants"]):
            hs = [MASKS.setdefault((p, round(t, 2)), occupied(frame(p, t))) for p, t in V["samples"]]
            hard = np.any([h for h, _ in hs], 0)
            occ = hard | np.any([s for _, s in hs], 0)
            free = (~occ).astype(np.uint8)
            dist = cv2.distanceTransform(free, cv2.DIST_L2, 5)
            integ = np.pad(occ.astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
            ih = np.pad(hard.astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
            box = lambda I, x, y, w, h: I[y + h, x + w] - I[y, x + w] - I[y + h, x] + I[y, x]
            for li, L in enumerate(j["layouts"]):
                w, h = int(np.ceil(L["w"] / SCALE)), int(np.ceil(L["h"] / SCALE))
                for y in range(SAFE["y0"] // SCALE, (SAFE["y1"] - L["h"]) // SCALE, 2):
                    x1 = X1_HIGH if y * SCALE + L["h"] < RAIL_TOP else SAFE["x1"]
                    for x in range(SAFE["x0"] // SCALE, (x1 - L["w"]) // SCALE + 1, 2):
                        hv = box(ih, x, y, w, h)
                        ov = box(integ, x, y, w, h)
                        clear = dist[y:y + h, x:x + w].min()
                        # never on face/hands/shoes; then fully empty; then on-time & full length; single line; clearance
                        score = (hv, ov, vi if ov == 0 else 0, li if ov == 0 and clear >= 6 else 0, -clear,
                                 abs(y * SCALE - 600) / 4000)
                        if best is None or score < best[0]:
                            best = (score, x * SCALE, y * SCALE, li, vi, occ)
        (hv, ov, _, _, negclear, _), x, y, li, vi, occ = best
        V = j["variants"][vi]
        L = j["layouts"][li]
        outp[j["id"]] = {"x": x, "y": y, "layout": li, "dt": V["dt"], "d": V["d"], "on_face_hands_shoe_px": int(hv) * SCALE * SCALE, "on_clothes_px": int(ov - hv) * SCALE * SCALE,
                         "clearance_px": int(-negclear * SCALE)}
        j = dict(j, w=L["w"], h=L["h"], samples=V["samples"])
        debug.append((j, occ, x, y))
        print(f'{j["id"]:8s} dt={V["dt"]} d={V["d"]} layout={li} x={x:4d} y={y:4d} face/hands/shoe={hv*SCALE*SCALE}px clothes={(ov-hv)*SCALE*SCALE}px clearance={-negclear*SCALE:.0f}px', flush=True)
    return outp, debug


if __name__ == "__main__":
    jobs = json.load(open("scripts/v2/overlay_jobs.json"))
    res, debug = place(jobs)
    json.dump(res, open("scripts/v2/placements.json", "w"), indent=1)
    # contact sheet: mask (red) + chosen box (green) on the middle sample
    tiles = []
    for j, occ, x, y in debug:
        p, t = j["samples"][len(j["samples"]) // 2]
        img = frame(p, t)
        img[occ] = (img[occ] * 0.5 + np.array([255, 0, 0]) * 0.5).astype(np.uint8)
        cv2.rectangle(img, (x // SCALE, y // SCALE), ((x + j["w"]) // SCALE, (y + j["h"]) // SCALE), (0, 255, 0), 2)
        cv2.putText(img, j["id"], (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        tiles.append(img)
    while len(tiles) % 6:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]
    cv2.imwrite(sys.argv[2] if len(sys.argv) > 2 else "/tmp/placements.png",
                cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))
