#!/usr/bin/env python3
"""Run the v3 ink-aware router over every frame listed in areas.txt.

areas.txt format (one line per frame):
    KEY|IMGNAME|n,label,x,y,w,h;n,label,x,y,w,h;...
    KEY|IMGNAME@IMGX,IMGY,IW,IH|...        (non-standard image placement)

  KEY      arbitrary identifier, used as the routes.json key
  IMGNAME  basename (no extension) of img/<IMGNAME>.png  -- MUST be the node's
           own export, not the raw source image (see SKILL.md §0-1)
  @...     where the image sits in the frame; default 230,60,1040,524. A
           narrower capture (the CSV shot is 619 wide, centred at x=440) is
           placed differently, and using the default origin for it puts every
           box outside the image.
  x,y,w,h  IMAGE-space pixels (origin = top-left of the screenshot)

Writes routes.json next to areas.txt.

Usage:  python3 route.py [workdir]      (default: cwd)
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_X, IMG_Y, IW, IH, FRAME_H = 230, 60, 1040, 524, 654


def load_router():
    """Import the router's helpers without running its own __main__ driver."""
    src = open(os.path.join(HERE, "router.py")).read()
    prefix = src.split("frames = json.load(")[0]
    ns = {}
    exec(compile(prefix, "router_prefix", "exec"), ns)
    return ns["Ink"], ns["CTX"], ns["solve"]


def parse(path):
    items = []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, img, rest = line.split("|", 2)
        geom = (IMG_X, IMG_Y, IW, IH)
        if "@" in img:
            img, g = img.split("@", 1)
            geom = tuple(int(v) for v in g.split(","))
        raw = []
        for part in rest.split(";"):
            if not part.strip():
                continue
            n, _label, x, y, w, h = part.split(",")
            raw.append((int(n), int(x) + geom[0], int(y) + geom[1], int(w), int(h)))
        items.append((key, img, raw, geom))
    return items


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    Ink, CTX, solve = load_router()
    items = parse(os.path.join(work, "areas.txt"))

    result, bad = {}, []
    t0 = time.time()
    for key, img, raw, geom in items:
        gx, gy, gw, gh = geom
        # 배지 레일은 이미지에 붙는다. 기본 1500x654 프레임이 아닐 때 상수를 쓰면
        # 배지가 이미지 위로 올라오거나 프레임 밖으로 나간다.
        CTX.update(IMG_X=gx, IMG_Y=gy, IW=gw, IH=gh,
                   LBX=gx - 95, LBR=gx - 49, RBX=gx + gw + 49)
        frame_h = gy + gh + 70
        ink = Ink(os.path.join(work, "img", img + ".png"))
        areas = [{"n": n, "x": x, "y": y, "w": w, "h": h} for n, x, y, w, h in raw]
        groups = [{"n": n, "ms": [a for a in areas if a["n"] == n]}
                  for n in sorted({a["n"] for a in areas})]
        b = solve(groups, areas, frame_h, ink)
        result[key] = {
            "segs": [[round(v, 1) for v in s] for s in b["segs"]],
            "dots": [[round(v, 1) for v in d] for d in b["dots"]],
            "badges": [{"n": g["n"],
                        "x": CTX["LBX"] if r["side"] == "L" else CTX["RBX"],
                        "y": r["by"]}
                       for r, g in zip(b["R"], groups)],
            "areas": [[n, x, y, w, h] for n, x, y, w, h in raw],
            "img": img,
            "geom": list(geom),
        }
        flag = "" if (b["cross"] == 0 and b["ovl"] == 0) else "   <-- CHECK"
        if flag:
            bad.append(key)
        print(f"{key:14s} n={len(groups):2d} cross={b['cross']} ovl={b['ovl']:3d} "
              f"ink={b['ink']:4d} len={round(b['len']):5d}{flag}", flush=True)

    json.dump(result, open(os.path.join(work, "routes.json"), "w"))
    print(f"\n=== {len(items)} frames  {time.time() - t0:.1f}s")
    if bad:
        print("PROBLEM frames:", bad)
        print("-> 영역을 줄이거나 나눠서 다시 라우팅하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
