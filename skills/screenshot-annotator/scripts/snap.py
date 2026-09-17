#!/usr/bin/env python3
"""Snap rough callout boxes onto the real UI element edges.

Eyeballing coordinates off a scaled preview is the #1 source of misaligned
area outlines. This measures the element from the pixels instead.

Input : image path + rough boxes "n,x,y,w,h" in the image's own pixel space
Output: corrected boxes, tight to the element, padded by PAD
"""
import sys, json
import numpy as np
from PIL import Image

PAD = 2          # breathing room kept around the detected element
SEARCH = 14      # how far outside the seed box we look for the true edge
TOL = 8          # per-channel difference that counts as "not background"
MAX_GROW = 24    # refuse a result this much bigger than the seed (see snap())


def card_bounds(a, x, y, w, h, pad=PAD):
    """Fallback for low-contrast panels (white card on #F8F9FB page).

    snap() reports 'no-ink' for these because the card border barely differs
    from the page. Instead, walk out from the seed centre while the pixels stay
    pure white -- that run IS the card.
    """
    H, W, _ = a.shape
    cx, cy = min(W - 1, x + w // 2), min(H - 1, y + h // 2)
    if not np.all(a[cy, cx] >= 250):
        return None
    top = cy
    while top > 0 and np.all(a[top - 1, cx] >= 250):
        top -= 1
    bot = cy
    while bot < H - 1 and np.all(a[bot + 1, cx] >= 250):
        bot += 1
    # widen on a row that is inside the card but clear of text
    row = (top + bot) // 2
    left = cx
    while left > 0 and np.all(a[row, left - 1] >= 250):
        left -= 1
    right = cx
    while right < W - 1 and np.all(a[row, right + 1] >= 250):
        right += 1
    nx, ny = max(0, left - pad), max(0, top - pad)
    nw, nh = right - left + 1 + pad * 2, bot - top + 1 + pad * 2
    return int(nx), int(ny), int(min(W - nx, nw)), int(min(H - ny, nh))


def snap(a, x, y, w, h, pad=PAD, search=SEARCH, tol=TOL):
    H, W, _ = a.shape
    x0, y0 = max(0, x - search), max(0, y - search)
    x1, y1 = min(W, x + w + search), min(H, y + h + search)
    win = a[y0:y1, x0:x1]

    # background = the most common colour in a ring just outside the seed box
    ring = np.ones(win.shape[:2], bool)
    ix0, iy0 = x - x0, y - y0
    ring[iy0:iy0 + h, ix0:ix0 + w] = False
    if ring.sum() < 20:
        return x, y, w, h, 'seed-fills-window'
    cols, cnt = np.unique(win[ring].reshape(-1, 3), axis=0, return_counts=True)
    bg = cols[cnt.argmax()]

    m = np.abs(win - bg).max(axis=2) > tol
    if not m.any():
        alt = card_bounds(a, x, y, w, h, pad)
        if alt:
            return alt[0], alt[1], alt[2], alt[3], 'no-ink->card'
        return x, y, w, h, 'no-ink'

    # keep only the blob that the seed box actually sits on: grow from the seed
    seed = np.zeros_like(m)
    seed[iy0:iy0 + h, ix0:ix0 + w] = True
    keep = m & seed
    if not keep.any():
        return x, y, w, h, 'seed-empty'
    for _ in range(search * 2):
        grown = keep.copy()
        grown[1:, :] |= keep[:-1, :]
        grown[:-1, :] |= keep[1:, :]
        grown[:, 1:] |= keep[:, :-1]
        grown[:, :-1] |= keep[:, 1:]
        grown &= m
        if grown.sum() == keep.sum():
            break
        keep = grown

    ys, xs = np.where(keep)
    nx, ny = x0 + xs.min() - pad, y0 + ys.min() - pad
    nw, nh = xs.max() - xs.min() + 1 + pad * 2, ys.max() - ys.min() + 1 + pad * 2
    nx, ny = max(0, nx), max(0, ny)
    nw, nh = min(W - nx, nw), min(H - ny, nh)

    # A blob can bleed into equally-inky neighbours: a left-nav item runs into
    # the menu rows above and below it, a table row into the whole table. When
    # the result balloons past the seed, the seed was never wrong about SIZE --
    # only about position -- so refuse the growth and say which mode to use.
    if nw > w + MAX_GROW or nh > h + MAX_GROW:
        return x, y, w, h, f'overgrown({nw}x{nh}) -> fit.py 사용'

    d = max(abs(nx - x), abs(ny - y), abs(nw - w), abs(nh - h))
    return int(nx), int(ny), int(nw), int(nh), f'moved{d}'


def main():
    img, spec = sys.argv[1], sys.argv[2]
    a = np.asarray(Image.open(img).convert('RGB')).astype(int)
    out = []
    for part in spec.split(';'):
        if not part.strip():
            continue
        n, x, y, w, h = (int(v) for v in part.split(','))
        nx, ny, nw, nh, why = snap(a, x, y, w, h)
        out.append((n, nx, ny, nw, nh, why))
        print(f'{n:>3}  {x},{y},{w},{h}  ->  {nx},{ny},{nw},{nh}   {why}', file=sys.stderr)
    print(';'.join(f'{n},{x},{y},{w},{h}' for n, x, y, w, h, _ in out))


if __name__ == '__main__':
    main()
