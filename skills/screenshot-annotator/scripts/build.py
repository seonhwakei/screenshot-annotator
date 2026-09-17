#!/usr/bin/env python3
"""routes.json -> draw payloads (renumbered, halo-detected, chunked).

Reads  : <work>/routes.json, <work>/img/*.png
Writes : <work>/draw.json          full payload, keyed by the areas.txt KEY
         <work>/p0.json p1.json .. 8 frames per chunk, ready to paste into
                                   the Figma plugin snippet
         <work>/renumber.json      original -> new number map (empty when kept)

Options:
  --keep-numbers   do not renumber; preserve the numbers from areas.txt
                   (use when the manual already references them)

Halo rule: an element gets a white halo when >=20% of the pixels under it are
darker than 140.  The older "mean luminance < 125" rule missed leaders that
cross a light table on their way over a dark panel.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

IMG_X, IMG_Y = 230, 60
DARK = 140          # pixel is "dark" below this luma
FRAC = 0.20         # ...and the element needs this share of dark pixels
CHUNK = 8


def seg_rect(x1, y1, x2, y2):
    """Router segment -> drawn rectangle, extended +-1px along the long axis."""
    x1, y1, x2, y2 = (int(round(v)) for v in (x1, y1, x2, y2))
    if abs(x2 - x1) >= abs(y2 - y1):
        return [min(x1, x2) - 1, y1 - 1, abs(x2 - x1) + 2, 2]
    return [x1 - 1, min(y1, y2) - 1, 2, abs(y2 - y1) + 2]


def dark_frac(g, x, y, w, h, ox=IMG_X, oy=IMG_Y):
    """ox/oy = where this frame's image starts. A narrower capture sits at a
    different x (the CSV shot is centred at 440), and using 230 for it reads
    the halo from the wrong pixels."""
    H, W = g.shape
    x0, x1 = max(0, min(W, x - ox)), max(0, min(W, x + w - ox))
    y0, y1 = max(0, min(H, y - oy)), max(0, min(H, y + h - oy))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float((g[y0:y1, x0:x1] < DARK).mean())


def main():
    work = os.getcwd()
    keep = "--keep-numbers" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        work = args[0]

    routes = json.load(open(os.path.join(work, "routes.json")))
    out, remap = {}, {}

    for key, d in routes.items():
        badges = d["badges"]
        if keep:
            m = {b["n"]: b["n"] for b in badges}
        else:
            left = sorted([b for b in badges if b["x"] < 700], key=lambda b: b["y"])
            right = sorted([b for b in badges if b["x"] >= 700], key=lambda b: b["y"])
            m = {b["n"]: i + 1 for i, b in enumerate(left + right)}
        if any(k != v for k, v in m.items()):
            remap[key] = {str(k): v for k, v in sorted(m.items())}

        v = {
            "a": [[m[n], int(x), int(y), int(w), int(h)] for n, x, y, w, h in d["areas"]],
            "s": [seg_rect(*s) for s in d["segs"]],
            "d": [[int(round(x)) - 3, int(round(y)) - 3] for x, y in d["dots"]],
            "b": [[m[b["n"]], int(round(b["x"])), int(round(b["y"]))] for b in badges],
        }

        g = np.asarray(Image.open(os.path.join(work, "img", d["img"] + ".png"))
                       .convert("L")).astype(int)
        ox, oy = (d.get("geom") or [IMG_X, IMG_Y])[:2]
        halo = []
        for x, y, w, h in v["s"]:
            if dark_frac(g, x - 1, y - 1, w + 2, h + 2, ox, oy) >= FRAC:
                halo.append([x, y, w, h])
        for x, y in v["d"]:
            if dark_frac(g, x - 2, y - 2, 10, 10, ox, oy) >= FRAC:
                halo.append([x, y, 6, 6])
        for n, x, y, w, h in v["a"]:
            bands = [dark_frac(g, x, y, w, 3, ox, oy),
                     dark_frac(g, x, y + h - 3, w, 3, ox, oy),
                     dark_frac(g, x, y, 3, h, ox, oy),
                     dark_frac(g, x + w - 3, y, 3, h, ox, oy)]
            if float(np.mean(bands)) >= FRAC:
                halo.append([x, y, w, h])
        v["H"] = halo
        out[key] = v

    json.dump(out, open(os.path.join(work, "draw.json"), "w"), separators=(",", ":"))
    json.dump(remap, open(os.path.join(work, "renumber.json"), "w"),
              ensure_ascii=False, indent=1)

    keys = list(out)
    for i in range(0, len(keys), CHUNK):
        part = {k: out[k] for k in keys[i:i + CHUNK]}
        path = os.path.join(work, "p%d.json" % (i // CHUNK))
        open(path, "w").write(json.dumps(part, separators=(",", ":")))
        print(f"{os.path.basename(path)}  {len(part)} frames  {os.path.getsize(path)} bytes")

    tot = sum(len(v["a"]) for v in out.values())
    print(f"\n{len(out)} frames  {tot} callouts  "
          f"{sum(len(v['H']) for v in out.values())} halo")
    if remap:
        print("renumbered:", json.dumps(remap, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
