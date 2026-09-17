#!/usr/bin/env python3
"""Ink-aware callout router (v3) run over every converted frame."""
import json, time, random, sys
import numpy as np
from PIL import Image, ImageFilter

BW, BH, PITCH = 46, 34, 37
CLRS = list(range(4, 122, 2))
INK_T, PAD = 190, 2

CTX = {}          # per-frame: IMG_X IMG_Y IW IH LBX LBR RBX


class Ink:
    def __init__(self, path):
        # "ink" = anything that carries information: local contrast (text, icons,
        # borders) or saturated colour (buttons, chips).  A flat region -- white
        # card, or the dark scrim behind a modal -- is NOT ink.
        im = Image.open(path).convert("RGB")
        a = np.asarray(im).astype(np.int16)
        g = np.asarray(im.convert("L")).astype(np.int16)
        med = np.asarray(im.convert("L").filter(ImageFilter.MedianFilter(9))).astype(np.int16)
        m = ((np.abs(g - med) > 22) | ((a.max(axis=2) - a.min(axis=2)) > 45)).astype(np.int32)
        self.H, self.W = m.shape
        self.ii = np.zeros((self.H + 1, self.W + 1), np.int32)
        self.ii[1:, 1:] = m.cumsum(0).cumsum(1)

    def _rect(self, x0, y0, x1, y1):
        x0, x1 = max(0, min(self.W, int(x0))), max(0, min(self.W, int(x1)))
        y0, y1 = max(0, min(self.H, int(y0))), max(0, min(self.H, int(y1)))
        if x1 <= x0 or y1 <= y0:
            return 0
        ii = self.ii
        return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])

    def h(self, y, x1, x2):
        ox, oy = CTX["IMG_X"], CTX["IMG_Y"]
        return self._rect(min(x1, x2) - ox, y - oy - PAD, max(x1, x2) - ox, y - oy + PAD + 1)

    def v(self, x, y1, y2):
        ox, oy = CTX["IMG_X"], CTX["IMG_Y"]
        return self._rect(x - ox - PAD, min(y1, y2) - oy, x - ox + PAD + 1, max(y1, y2) - oy)


def hit_h(y, x1, x2, rs, inf=2):
    return any(y >= r["y"] - inf and y <= r["y"] + r["h"] + inf and
               max(min(x1, x2), r["x"] - inf) <= min(max(x1, x2), r["x"] + r["w"] + inf) for r in rs)


def hit_v(x, y1, y2, rs, inf=2):
    return any(x >= r["x"] - inf and x <= r["x"] + r["w"] + inf and
               max(min(y1, y2), r["y"] - inf) <= min(max(y1, y2), r["y"] + r["h"] + inf) for r in rs)


def holds(o, a):
    return (o["x"] <= a["x"] + 1 and o["y"] <= a["y"] + 1 and
            o["x"] + o["w"] >= a["x"] + a["w"] - 1 and o["y"] + o["h"] >= a["y"] + a["h"] - 1)


def median(v):
    s = sorted(v); n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def pava(t):
    q = [v - i * PITCH for i, v in enumerate(t)]
    bl = []
    for v in q:
        bl.append([v])
        while len(bl) > 1 and median(bl[-2]) > median(bl[-1]):
            c = bl.pop(); a = bl.pop(); bl.append(a + c)
    out = []
    for b in bl:
        out += [median(b)] * len(b)
    return [v + i * PITCH for i, v in enumerate(out)]


def clear_rows(K, railX, portX, lo, hi, n=10, sep=8):
    ys = [(K.h(y, railX, portX), abs(y - (lo + hi) / 2), y) for y in range(int(lo), int(hi), 2)]
    ys.sort()
    out = []
    for ink, _, y in ys:
        if all(abs(y - o) >= sep for o in out):
            out.append(y)
        if len(out) >= n:
            break
    return out


def candidates(g, obst, K):
    ms, num, out = g["ms"], g["n"], []
    LBR, RBX, IMG_Y, IH = CTX["LBR"], CTX["RBX"], CTX["IMG_Y"], CTX["IH"]
    for side in ("L", "R"):
        railX = LBR if side == "L" else RBX

        def push(c, side=side):
            c["side"] = side; c["n"] = num; out.append(c)

        if len(ms) == 1:
            a = ms[0]
            cy = a["y"] + a["h"] / 2
            portX = a["x"] if side == "L" else a["x"] + a["w"]
            lo = a["y"] + min(4, a["h"] / 2)
            hi = a["y"] + a["h"] - min(4, a["h"] / 2)
            portYs = sorted({cy} | ({lo + k * (hi - lo) / 6 for k in range(7)} if hi > lo else set()))
            rails = set(clear_rows(K, railX, portX,
                                   max(IMG_Y + 6, cy - 200), min(IMG_Y + IH - 6, cy + 200))) | set(portYs)
            for portY in portYs:
                pen = 0 if portY == cy else 1
                for railY in rails:
                    if railY == portY:
                        if hit_h(portY, railX, portX, obst):
                            continue
                        push({"mode": "single", "railY": portY, "branches": [], "jog": None,
                              "port": (portX, portY), "railEnd": portX,
                              "ink": K.h(portY, railX, portX) + pen})
                        continue
                    rng = range(int(railX) + 12, int(portX) - 5, 3) if side == "L" \
                        else range(int(portX) + 6, int(railX) - 11, 3)
                    bb, bsc = None, None
                    for bx in rng:
                        if hit_h(railY, railX, bx, obst) or hit_v(bx, railY, portY, obst) \
                           or hit_h(portY, bx, portX, obst):
                            continue
                        ink = K.h(railY, railX, bx) + K.v(bx, railY, portY) + K.h(portY, bx, portX)
                        sc = ink * 10 + abs(portX - bx) * 0.05
                        if bsc is None or sc < bsc:
                            bb, bsc = bx, sc
                    if bb is None:
                        continue
                    push({"mode": "single", "railY": railY, "branches": [], "jog": (bb, portY),
                          "port": (portX, portY), "railEnd": bb,
                          "ink": K.h(railY, railX, bb) + K.v(bb, railY, portY)
                                 + K.h(portY, bb, portX) + pen})
            vxs = sorted({a["x"] + a["w"] * k / 6 for k in range(1, 6)})
            for clr in CLRS:
                for ty, py in ((a["y"] - clr, a["y"]), (a["y"] + a["h"] + clr, a["y"] + a["h"])):
                    for vv in vxs:
                        if hit_v(vv, ty, py, obst) or hit_h(ty, railX, vv, obst):
                            continue
                        push({"mode": "single", "railY": ty, "branches": [(vv, ty, py)], "jog": None,
                              "port": (vv, py), "railEnd": vv,
                              "ink": K.h(ty, railX, vv) + K.v(vv, ty, py)})
        else:
            by0 = min(r["y"] for r in ms); by1 = max(r["y"] + r["h"] for r in ms)
            for clr in CLRS:
                for up in (True, False):
                    ry = by0 - clr if up else by1 + clr
                    far = max(r["x"] + r["w"] / 2 for r in ms) if side == "L" \
                        else min(r["x"] + r["w"] / 2 for r in ms)
                    if hit_h(ry, railX, far, obst):
                        continue
                    br, bad, ink = [], False, K.h(ry, railX, far)
                    for r in ms:
                        cx = r["x"] + r["w"] / 2
                        py = r["y"] if up else r["y"] + r["h"]
                        if hit_v(cx, ry, py, obst):
                            bad = True; break
                        br.append((cx, ry, py)); ink += K.v(cx, ry, py)
                    if not bad:
                        push({"mode": "row", "railY": ry, "branches": br, "jog": None,
                              "port": (far, ry), "railEnd": far, "ink": ink})
    for c in out:
        rx = LBR if c["side"] == "L" else RBX
        c["clen"] = abs(c["railEnd"] - rx) + abs(c["railY"] - c["port"][1]) \
            + (abs(c["port"][0] - c["jog"][0]) if c["jog"] else 0) \
            + sum(abs(b[2] - b[1]) for b in c["branches"])
    if not out:
        a = ms[0]; cy = a["y"] + a["h"] / 2
        out.append({"mode": "single", "side": "L", "n": num, "railY": cy, "branches": [],
                    "port": (a["x"], cy), "railEnd": a["x"], "jog": None, "clen": 0,
                    "ink": K.h(cy, LBR, a["x"])})
    return out


def build(sel, H, K, lane_ord):
    LBX, LBR, RBX = CTX["LBX"], CTX["LBR"], CTX["RBX"]
    R = [dict(c) for c in sel]
    minY, maxY = 8, max(60, H - 110)
    for side in "LR":
        g = sorted([r for r in R if r["side"] == side], key=lambda r: r["railY"])
        if not g:
            continue
        p = pava([r["railY"] - BH / 2 for r in g])
        if p[0] < minY:
            d = minY - p[0]; p = [v + d for v in p]
        if p[-1] > maxY:
            d = p[-1] - maxY; p = [max(minY, v - d) for v in p]
        for r, v in zip(g, p):
            r["by"] = round(v); r["bcy"] = round(v) + BH / 2
    for side in "LR":
        g = [r for r in R if r["side"] == side]
        for r in g:
            r["opo"] = abs(r["bcy"] - r["railY"]) > 4
        o = [r for r in g if r["opo"]]
        if o:
            lp = max(5, min(14, 45 / (len(o) + 1)))
            key = {0: lambda r: abs(r["bcy"] - r["railY"]), 1: lambda r: r["railY"],
                   2: lambda r: r["bcy"], 3: lambda r: -abs(r["bcy"] - r["railY"])}[lane_ord]
            for i, r in enumerate(sorted(o, key=key)):
                r["lane"] = LBR + lp * (i + 1) if side == "L" else RBX - lp * (i + 1)

    segs, dots, ink, length = [], [], 0, 0
    rlen = 0

    def add(x1, y1, x2, y2):
        nonlocal ink, length, rlen
        if x1 == x2 and y1 == y2:
            return
        segs.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        length += abs(x2 - x1) + abs(y2 - y1)
        rlen += abs(x2 - x1) + abs(y2 - y1)
        ink += K.h(y1, x1, x2) if y1 == y2 else K.v(x1, y1, y2)

    far = 0
    for r in R:
        rlen = 0
        be = LBX + BW if r["side"] == "L" else RBX
        if r["opo"]:
            add(be, r["bcy"], r["lane"], r["bcy"])
            add(r["lane"], r["bcy"], r["lane"], r["railY"])
            add(r["lane"], r["railY"], r["railEnd"], r["railY"])
        else:
            add(be, r["railY"], r["railEnd"], r["railY"])
        if r["jog"]:
            bx, py = r["jog"]
            add(bx, r["railY"], bx, py)
            add(bx, py, r["port"][0], py)
        for bx, y0, y1 in r["branches"]:
            add(bx, y0, bx, y1); dots.append((bx, y1))
        if not r["branches"]:
            dots.append(r["port"])
        far += max(0, rlen - 450)
    cross = overlap = 0
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i], segs[j]
            ah, bh = a[1] == a[3], b[1] == b[3]
            if ah != bh:
                Hs, V = (a, b) if ah else (b, a)
                if V[0] > Hs[0] + 1 and V[0] < Hs[2] - 1 and Hs[1] > V[1] + 1 and Hs[1] < V[3] - 1:
                    cross += 1
            elif ah:
                if abs(a[1] - b[1]) <= 5:
                    overlap += max(0, min(a[2], b[2]) - max(a[0], b[0]) - 2)
            else:
                if abs(a[0] - b[0]) <= 5:
                    overlap += max(0, min(a[3], b[3]) - max(a[1], b[1]) - 2)
    inv = 0
    for side in "LR":
        g = [r for r in R if r["side"] == side]
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                if (g[i]["n"] - g[j]["n"]) * (g[i]["by"] - g[j]["by"]) < 0:
                    inv += 1
    return {"R": R, "segs": segs, "dots": dots, "cross": cross, "far": far,
            "ink": ink, "len": length, "ovl": overlap, "inv": inv}


def cost(b):
    return (b["cross"] * 100000 + b["ovl"] * 60 + b["ink"] * 30
            + b["len"] * 0.4 + b["far"] * 1.5 + len(b["segs"]) * 6 + b["inv"] * 10)


def solve(groups, areas, H, K):
    n = len(groups)
    keep = 14 if n <= 8 else 8
    rounds = 6 if n <= 8 else 3
    nstart = 12 if n <= 6 else (6 if n <= 9 else 3)
    CS = []
    for g in groups:
        obst = [a for a in areas if a["n"] != g["n"] and not any(holds(a, m) for m in g["ms"])]
        cs = candidates(g, obst, K)
        uniq = []
        for sd in ("L", "R"):
            seen, cnt = set(), 0
            for c in sorted([c for c in cs if c["side"] == sd], key=lambda c: (c["ink"], c["clen"])):
                k = (round(c["railY"]), round(c["port"][1]))
                if k in seen:
                    continue
                seen.add(k); uniq.append(c); cnt += 1
                if cnt >= keep:
                    break
        uniq.sort(key=lambda c: (c["ink"], c["clen"]))
        CS.append(uniq)

    def near_side(g):
        bx0 = min(r["x"] for r in g["ms"]); bx1 = max(r["x"] + r["w"] for r in g["ms"])
        return "L" if (bx0 - CTX["LBR"]) <= (CTX["RBX"] - bx1) else "R"

    rnd = random.Random(7)
    starts = [[c[0] for c in CS],
              [next((c for c in cs if c["side"] == near_side(g)), cs[0]) for cs, g in zip(CS, groups)]]
    for _ in range(nstart):
        starts.append([cs[rnd.randrange(min(6, len(cs)))] for cs in CS])
    overall = None
    for sel in starts:
        sel = list(sel)
        best = min((build(sel, H, K, lo) for lo in range(4)), key=cost)
        for _ in range(rounds):
            improved = False
            for i in range(len(sel)):
                for c in CS[i]:
                    if c is sel[i]:
                        continue
                    trial = list(sel); trial[i] = c
                    b = min((build(trial, H, K, lo) for lo in range(4)), key=cost)
                    if cost(b) < cost(best) - 1e-9:
                        sel, best, improved = trial, b, True
            if not improved:
                break
        if overall is None or cost(best) < cost(overall):
            overall = best
    return overall


frames = json.load(open("/tmp/callout/frames_a.json")) + json.load(open("/tmp/callout/frames_b.json"))
inks, result, stats = {}, {}, []
t0 = time.time()
for fid, H, ix, iy, iw, ih, hsh, raw in frames:
    CTX.update(IMG_X=ix, IMG_Y=iy, IW=iw, IH=ih, LBX=ix - 95, LBR=ix - 49, RBX=ix + iw + 49)
    if hsh not in inks:
        inks[hsh] = Ink(f"/tmp/callout/img/{hsh}.png")
    K = inks[hsh]
    areas = [{"n": n, "x": x, "y": y, "w": w, "h": h} for n, x, y, w, h in raw]
    groups = [{"n": n, "ms": [a for a in areas if a["n"] == n]}
              for n in sorted({a["n"] for a in areas})]
    b = solve(groups, areas, H, K)
    result[fid] = {
        "segs": [[round(v, 1) for v in s] for s in b["segs"]],
        "dots": [[round(v, 1) for v in d] for d in b["dots"]],
        "badges": [{"n": g["n"], "x": CTX["LBX"] if r["side"] == "L" else CTX["RBX"], "y": r["by"]}
                   for r, g in zip(b["R"], groups)],
    }
    border = 5 * len(b["segs"])
    stats.append((fid, len(groups), b["cross"], b["ovl"], b["inv"], b["ink"], round(b["len"])))
    print(f"{fid:12s} n={len(groups):2d} cross={b['cross']} ovl={b['ovl']:3d} inv={b['inv']} "
          f"ink={b['ink']:4d} len={round(b['len']):5d}  [{time.time()-t0:5.1f}s]", flush=True)

json.dump(result, open("/tmp/callout/routes_all.json", "w"))
bad = [s for s in stats if s[2] or s[3]]
print("\n=== %d frames, %.1fs" % (len(stats), time.time() - t0))
print("crossings total:", sum(s[2] for s in stats), " overlap total:", sum(s[3] for s in stats))
print("frames with cross/overlap:", len(bad))
for s in bad:
    print("   ", s)
