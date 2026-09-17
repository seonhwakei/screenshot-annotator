#!/usr/bin/env python3
"""Correct a whole batch of callout boxes, column-aware.

snap.py fits a box to ONE UI element. That is wrong for boxes that indicate a
TABLE COLUMN: snap shrinks them to whichever cell text it finds, which was
losing up to 98px of the column. This script routes each box to the right
strategy:

  single  -> snap.py               (buttons, cards, inputs, menu rows, panels)
  column  -> keep x/w, fit y/h to the table band

A box is treated as a column when two or more boxes in the same frame share a
y/height band and sit side by side. That is exactly how column indicators are
drawn and nothing else in the set looks like it.

Input  : rows.txt lines of  frameId|name|imageHash|n,x,y,w,h;...
         images at <work>/hash/<imageHash>.png  (node exports, see SKILL.md 0-1)
Output : snapped.txt with the same shape, plus a report on stderr
"""
import os
import sys
import importlib.util

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('snap', os.path.join(HERE, 'snap.py'))
snapmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(snapmod)

BAND_TOL = 6        # boxes whose y and h match this closely are one band
MIN_COLS = 3        # fewer than this side by side is a card row, not a column set
PAD = 2


def column_groups(boxes):
    """Group indices into side-by-side bands; keep only real column sets.

    Each band is returned separately -- merging every band into one set made the
    admin dashboard's two card rows collapse into a single 195px-tall block.
    Two side-by-side boxes are a card row, not a table column set, so a band
    needs MIN_COLS members to qualify.
    """
    bands = []
    for i, (_, xi, yi, wi, hi) in enumerate(boxes):
        placed = False
        for b in bands:
            j = b[0]
            _, xj, yj, wj, hj = boxes[j]
            if abs(yi - yj) <= BAND_TOL and abs(hi - hj) <= BAND_TOL \
                    and min(wi, wj) >= 40:
                if all(boxes[k][1] + boxes[k][3] <= xi + BAND_TOL
                       or xi + wi <= boxes[k][1] + BAND_TOL for k in b):
                    b.append(i)
                    placed = True
                    break
        if not placed:
            bands.append([i])
    return [b for b in bands if len(b) >= MIN_COLS]


def table_band(a, boxes, idxs):
    """Vertical extent of the table the column boxes sit on."""
    x0 = min(boxes[i][1] for i in idxs)
    x1 = max(boxes[i][1] + boxes[i][3] for i in idxs)
    y0 = min(boxes[i][2] for i in idxs)
    y1 = max(boxes[i][2] + boxes[i][4] for i in idxs)
    nx, ny, nw, nh, _ = snapmod.snap(a, x0, y0, x1 - x0, y1 - y0)
    # never let the union snap collapse: keep at least the original height
    if nh < (y1 - y0) * 0.6:
        return y0, y1 - y0
    return ny, nh


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    cache, out, report = {}, [], []
    for line in open(os.path.join(work, 'rows.txt')):
        line = line.strip()
        if not line:
            continue
        fid, name, h, spec = line.split('|')[0], line.split('|')[1], line.split('|')[3], line.split('|')[-1]
        if h not in cache:
            cache[h] = np.asarray(Image.open(
                os.path.join(work, 'hash', h + '.png')).convert('RGB')).astype(int)
        a = cache[h]
        boxes = []
        for p in spec.split(';'):
            v = p.split(',')
            boxes.append((v[0], int(v[1]), int(v[2]), int(v[3]), int(v[4])))
        bands = column_groups(boxes)
        cols = {i: bi for bi, b in enumerate(bands) for i in b}
        band_of = [table_band(a, boxes, b) for b in bands]
        fixed, notes = [], []
        for i, (n, x, y, w, hh) in enumerate(boxes):
            if i in cols:
                ny, nh = band_of[cols[i]]
                fixed.append((n, x, ny, w, nh))
                notes.append(f'{n}:col')
            else:
                nx, ny, nw, nh, why = snapmod.snap(a, x, y, w, hh)
                d = max(abs(nx - x), abs(ny - y), abs(nw - w), abs(nh - hh))
                fixed.append((n, nx, ny, nw, nh))
                notes.append(f'{n}:{d}')
        out.append(f"{fid}|{name}|{h}|" + ';'.join(f'{n},{x},{y},{w},{hh}' for n, x, y, w, hh in fixed))
        report.append(f"{name[:44]:46s} {'COL ' if cols else '    '}" + ' '.join(notes))

    open(os.path.join(work, 'snapped.txt'), 'w').write('\n'.join(out) + '\n')
    for r in report:
        print(r, file=sys.stderr)
    print(f'{len(out)} frames -> snapped.txt', file=sys.stderr)


if __name__ == '__main__':
    main()
