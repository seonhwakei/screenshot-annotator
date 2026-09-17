#!/usr/bin/env python3
"""Audit a whole markup section BEFORE drawing it.

Counting badges is not enough — every defect the reviewer has caught so far
passed the count check and failed the eye. This catches those classes:

  empty     the box covers no ink -> it points at blank space
  overlap   two boxes clip each other (containment is fine, see resolve.py)
  coarse    the box covers > COARSE of the image -> "영역 제대로 못잡음"
  outside   the box leaves the image
  tiny      degenerate box

Usage:
  python3 verify.py spec.json
  spec.json = {"F08": {"img": "img/F08.png",
                       "boxes": [[1,x,y,w,h], ...],
                       "dash":  [3]}, ...}

`dash`는 L3 **표시 자리**(캡처에 없는 조건부 요소)의 번호다. 이 박스는 빈 공간을
가리키는 게 정상이므로 empty 검사에서 뺀다. 다만 "비어 있어도 되는 박스"는
의도를 적었을 때만 허용한다 — 적지 않으면 그냥 잘못 짚은 박스다.

Exit 1 if anything failed.
"""
import json
import sys

import numpy as np
from PIL import Image

COARSE = 0.55     # fraction of image area
MIN_SIDE = 6
INK_MIN = 0.012   # fraction of pixels under the box that must differ from bg


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(int)


def ink_frac(a, x, y, w, h):
    H, W = a.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    win = a[y0:y1, x0:x1]
    cols, cnt = np.unique(win.reshape(-1, 3), axis=0, return_counts=True)
    bg = cols[cnt.argmax()]
    return float((np.abs(win - bg).max(axis=2) > 12).mean())


def inter(a, b):
    x = max(a[1], b[1]); y = max(a[2], b[2])
    r = min(a[1] + a[3], b[1] + b[3]); t = min(a[2] + a[4], b[2] + b[4])
    return max(0, r - x), max(0, t - y)


def main():
    spec = json.load(open(sys.argv[1]))
    bad = 0
    for key, v in sorted(spec.items()):
        a = load(v["img"])
        H, W = a.shape[:2]
        dash = set(v.get("dash", []))
        msgs = []
        for b in v["boxes"]:
            n, x, y, w, h = b
            if w < MIN_SIDE or h < MIN_SIDE:
                msgs.append(f"tiny {n} {w}x{h}")
            if x < 0 or y < 0 or x + w > W or y + h > H:
                msgs.append(f"outside {n} {x},{y},{w},{h} (img {W}x{H})")
            if w * h > COARSE * W * H:
                msgs.append(f"coarse {n} {100*w*h/(W*H):.0f}% of image")
            f = ink_frac(a, x, y, w, h)
            if f < INK_MIN and n not in dash:
                msgs.append(f"empty {n} ink={f:.3f}")
            if f >= INK_MIN and n in dash:
                msgs.append(f"dash {n} 표시 자리인데 캡처에 이미 내용이 있음")
        for i in range(len(v["boxes"])):
            for j in range(i + 1, len(v["boxes"])):
                p, q = v["boxes"][i], v["boxes"][j]
                iw, ih = inter(p, q)
                if iw <= 0 or ih <= 0:
                    continue
                ap, aq = p[3] * p[4], q[3] * q[4]
                if iw * ih >= 0.92 * min(ap, aq):
                    continue                      # containment: allowed
                msgs.append(f"overlap {p[0]}~{q[0]} {iw}x{ih}")
        if msgs:
            bad += 1
            print(f"{key}: " + "; ".join(msgs))
    print(f"-- {len(spec)} frames, {bad} with findings")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
