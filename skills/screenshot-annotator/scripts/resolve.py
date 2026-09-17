#!/usr/bin/env python3
"""Pull partially-overlapping callout boxes apart.

Two boxes that CONTAIN one another read fine (카드 안의 값, 표 안의 열): the
reader sees a region and a detail inside it. Two boxes that merely CLIP each
other read as a drawing mistake — that is the "박스 겹침" defect.

So: leave containment alone, and resolve every partial overlap by retreating
the edge of the box that loses the least area, never the smaller box.

Usage:
  python3 resolve.py "n,x,y,w,h;n,x,y,w,h;..."      -> corrected spec on stdout
  python3 resolve.py --check "..."                  -> report only, exit 1 if any
"""
import sys

GAP = 2          # keep this many px of clear space between two boxes
CONTAIN = 0.92   # inner box this much inside the outer -> treat as containment


def parse(spec):
    out = []
    for s in spec.split(";"):
        s = s.strip()
        if not s:
            continue
        p = s.split(",")
        out.append([int(p[0])] + [int(v) for v in p[1:5]])
    return out


def inter(a, b):
    x = max(a[1], b[1])
    y = max(a[2], b[2])
    r = min(a[1] + a[3], b[1] + b[3])
    t = min(a[2] + a[4], b[2] + b[4])
    return max(0, r - x), max(0, t - y)


def contains(outer, inner):
    iw, ih = inter(outer, inner)
    return iw * ih >= CONTAIN * inner[3] * inner[4]


def resolve(boxes):
    notes = []
    for _ in range(8):
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                iw, ih = inter(a, b)
                if iw <= 0 or ih <= 0:
                    continue
                if contains(a, b) or contains(b, a):
                    notes.append(f"contain {a[0]}~{b[0]} (허용)")
                    continue
                big, sml = (a, b) if a[3] * a[4] >= b[3] * b[4] else (b, a)
                if iw <= ih:                      # retreat horizontally
                    if big[1] < sml[1]:
                        big[3] = sml[1] - big[1] - GAP
                    else:
                        nx = sml[1] + sml[3] + GAP
                        big[3] = big[1] + big[3] - nx
                        big[1] = nx
                else:                             # retreat vertically
                    if big[2] < sml[2]:
                        big[4] = sml[2] - big[2] - GAP
                    else:
                        ny = sml[2] + sml[4] + GAP
                        big[4] = big[2] + big[4] - ny
                        big[2] = ny
                notes.append(f"overlap {a[0]}~{b[0]} {iw}x{ih} -> {big[0]} 축소")
                changed = True
        if not changed:
            break
    return boxes, notes


def main():
    check = sys.argv[1] == "--check"
    spec = sys.argv[2] if check else sys.argv[1]
    boxes = parse(spec)
    before = [list(b) for b in boxes]
    boxes, notes = resolve(boxes)
    bad = [n for n in notes if n.startswith("overlap")]
    for n in notes:
        print("#", n, file=sys.stderr)
    if check:
        sys.exit(1 if bad else 0)
    print(";".join(",".join(str(v) for v in b) for b in boxes))
    if bad:
        print("# 변경 전:", ";".join(",".join(str(v) for v in b) for b in before),
              file=sys.stderr)


if __name__ == "__main__":
    main()
