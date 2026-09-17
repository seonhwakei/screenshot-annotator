#!/usr/bin/env python3
"""Fit a callout box to a real UI element, by element KIND.

snap.py grows a blob from a seed until the ink stops. That is right for an
isolated control and WRONG for anything embedded in a run of equally inky
neighbours: a left-nav item swallows the rows above and below it, a table row
swallows the whole table. Every "영역 제대로 못잡음" case so far was this.

So the caller states what kind of thing the box is, and we fit accordingly.

Usage:
  python3 fit.py IMG MODE x y w h
  python3 fit.py IMG --batch "MODE,x,y,w,h;MODE,x,y,w,h;..."

MODE
  ink    tight bbox of ink inside the seed window; NEVER grows past the seed.
         Use for text runs, values, pills, icons — anything you can bracket.
  card   the white card / panel that contains the seed centre, bounded by the
         page background. Use for 카드, 패널, 모달, 표 전체.
  nav    the accent-filled nav item under the seed centre. Bounded to the
         sidebar column, so it cannot leak into the neighbouring menu row.
  row    the table row band containing the seed centre, x/w kept from the seed.
         Use for 목록의 한 행.
  band   like row but also fits x/w to the table's own left/right edge.
  panel  right-hand slide-over: from its left border to the image edge,
         full image height. Shadows outside the border are excluded.

Output per box: MODE x y w h  why
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image

PAD = 2
PAGE_BG_TOL = 6


def _a(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(int)


def _clip(x, y, w, h, a):
    H, W = a.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def _page_bg(a):
    """Modal colour of the page body.

    사분면 전체를 쓰면 흰 카드가 많은 화면에서 카드 색이 '페이지 배경'으로 뽑혀
    card 모드가 즉시 무너진다(카드=배경이 되어 버린다). 여백일 확률이 가장 높은
    **아래쪽 띠 + 오른쪽 띠**(레일 제외)에서 뽑는다."""
    H, W = a.shape[:2]
    rail = rail_width(a, default=0)
    strips = []
    if H > 24:
        strips.append(a[H - 10:H - 2, rail + 4:W - 2].reshape(-1, 3))
    if W > 24:
        strips.append(a[int(H * 0.35):H - 12, W - 10:W - 2].reshape(-1, 3))
    s = np.concatenate(strips) if strips else a[H // 2:, W // 2:].reshape(-1, 3)
    if not len(s):
        s = a[H // 2:, W // 2:].reshape(-1, 3)
    cols, cnt = np.unique(s, axis=0, return_counts=True)
    return cols[cnt.argmax()]


def fit_ink(a, x, y, w, h, tol=12):
    x, y, w, h = _clip(x, y, w, h, a)
    win = a[y:y + h, x:x + w]
    cols, cnt = np.unique(win.reshape(-1, 3), axis=0, return_counts=True)
    bg = cols[cnt.argmax()]
    m = np.abs(win - bg).max(axis=2) > tol
    if not m.any():
        return x, y, w, h, "no-ink"
    ys, xs = np.where(m)
    nx, ny = x + xs.min() - PAD, y + ys.min() - PAD
    nw, nh = xs.max() - xs.min() + 1 + 2 * PAD, ys.max() - ys.min() + 1 + 2 * PAD
    return (*_clip(nx, ny, nw, nh, a), "ink")


def fit_card(a, x, y, w, h):
    """Walk out from the seed centre while pixels are card-coloured."""
    H, W = a.shape[:2]
    cx, cy = x + w // 2, y + h // 2
    bg = _page_bg(a)

    def is_page(px):
        return np.abs(px - bg).max() <= PAGE_BG_TOL

    # A row divider inside a card can be within tolerance of the page colour,
    # so only a RUN of page-coloured pixels ends the card. Without the run the
    # card collapses onto one table row (observed on 워크스페이스 목록).
    RUN = 3

    def out_at(seq):
        for i in range(len(seq) - RUN + 1):
            if all(is_page(p) for p in seq[i:i + RUN]):
                return i
        return None

    up = out_at(a[cy::-1, cx])
    top = cy - (up if up is not None else cy)
    dn = out_at(a[cy:, cx])
    bot = cy + (dn - 1 if dn else H - 1 - cy)
    probe = min(H - 1, max(0, top + 3))
    lf = out_at(a[probe, cx::-1])
    left = cx - (lf if lf is not None else cx)
    rt = out_at(a[probe, cx:])
    right = cx + (rt - 1 if rt else W - 1 - cx)
    if bot - top < 8 or right - left < 8:
        return x, y, w, h, "card-fail"
    return left, top, right - left + 1, bot - top + 1, "card"


def rail_width(a, default=140):
    """Where the left nav ends.

    "어두운 열의 연속" 기준은 다크 사이드바에만 맞는다. 밝은 회색 레일
    (#F1F4F3 on #F7F8F7)에서는 0이 나와 기본값으로 떨어지고, 그러면 nav 박스가
    본문까지 먹는다. 그래서 색이 아니라 **세로 경계선**을 찾는다: 화면 아래쪽
    밴드에서 좌측 1/3 안의 첫 강한 수직 에지가 레일의 오른쪽 끝이다."""
    H, W = a.shape[:2]
    band = a[int(H * 0.5):int(H * 0.95), :max(8, W // 3)].astype(int)
    if band.shape[1] < 4:
        return default
    # 평균이 아니라 '세로로 끊기지 않는 비율'로 고른다. 평균을 쓰면 메뉴 아이콘의
    # 짧은 에지(몇 줄짜리)가 레일 경계선보다 세게 잡혀 20px에서 잘린다.
    dif = np.abs(np.diff(band, axis=1)).max(axis=2)
    frac = (dif > 3).mean(axis=0)
    cand = np.where(frac > 0.9)[0]
    cand = cand[cand > 15]
    if not len(cand):
        return default
    x = int(cand[0]) + 1
    return x if 20 <= x <= W // 3 else default


def fit_nav(a, x, y, w, h, sidebar=None):
    """The highlighted menu item under the seed centre, clipped to the rail.

    허용 오차를 고정할 수 없다. 넓으면 옅은 강조(#E6F4F1 on #F1F4F3, 차이 11)가
    레일 배경과 한 덩어리가 되어 레일 전체를 삼키고, 좁으면 그라데이션 강조
    (그라데이션 pill)가 몇 줄로 쪼그라든다. 그래서 오차를 넓혀 가며
    **한도 안에 드는 마지막 결과**를 쓴다."""
    cap = max(h * 2.5, 44)
    best = None
    for tol in (10, 22, 40):
        r = _fit_nav_at(a, x, y, w, h, sidebar, tol)
        if r[4] != "nav" or r[3] > cap:
            continue
        best = r
    return best or (x, y, w, h, "nav-fail")


def _fit_nav_at(a, x, y, w, h, sidebar, tol):
    H, W = a.shape[:2]
    if sidebar is None:
        sidebar = rail_width(a)
    cx, cy = min(x + w // 2, sidebar - 2), y + h // 2
    seed = a[cy, cx]
    m = np.abs(a - seed).max(axis=2) <= tol
    m[:, sidebar:] = False
    # keep only the run of rows connected to cy at column cx
    colrun = m[:, cx]
    if not colrun[cy]:
        return x, y, w, h, "nav-fail"
    top = cy
    while top > 0 and colrun[top - 1]:
        top -= 1
    bot = cy
    while bot < H - 1 and colrun[bot + 1]:
        bot += 1
    band = m[top:bot + 1]
    xs = np.where(band.any(axis=0))[0]
    return int(xs.min()), top, int(xs.max() - xs.min() + 1), bot - top + 1, "nav"


def _row_edges(a, cx, cy):
    """Rows of a table are separated by a 1px divider or a colour change."""
    H = a.shape[0]
    base = a[cy, cx]

    def same(yy):
        return np.abs(a[yy, cx] - base).max() <= 10

    top = cy
    while top > 0 and same(top - 1):
        top -= 1
    bot = cy
    while bot < H - 1 and same(bot + 1):
        bot += 1
    return top, bot


def fit_row(a, x, y, w, h):
    cx, cy = x + w // 2, y + h // 2
    # probe in a gutter column: pick the x inside the seed with the least ink
    win = a[y:y + h, x:x + w]
    ink = (np.abs(win - win.reshape(-1, 3)[0]).max(axis=2) > 12).sum(axis=0)
    cx = x + int(np.argmin(ink))
    top, bot = _row_edges(a, cx, cy)
    if bot - top < 6:
        return x, y, w, h, "row-fail"
    return x, top, w, bot - top + 1, "row"


def fit_band(a, x, y, w, h):
    nx, ny, nw, nh, why = fit_row(a, x, y, w, h)
    if why == "row-fail":
        return nx, ny, nw, nh, why
    cx0, cy0, cw, ch, w2 = fit_card(a, x, y, w, h)
    if w2 == "card":
        nx, nw = cx0, cw
    return nx, ny, nw, nh, "band"


def fit_panel(a, x, y, w, h):
    """Right slide-over: find its left border, then take it to the image edge."""
    H, W = a.shape[:2]
    # The page behind a slide-over is dimmed, so the panel is the trailing run
    # of BRIGHT columns. Measuring per column (not per pixel) ignores the
    # panel's own dividers and text, and excludes the drop shadow, which is
    # what pushed the box 16px left of the real border.
    luma = a.mean(axis=2).mean(axis=0)
    left = W
    while left > 0 and luma[left - 1] > 200:
        left -= 1
    if W - left < 60:
        return x, y, w, h, "panel-fail"
    return left, 0, W - left, H, "panel"


def fit_modal(a, x, y, w, h, thr=250):
    """A dialog over a dimmed page. `card` cannot find it: both the dialog and
    the dimmed card behind it are "not page background", so the walk runs past
    the dialog edge. The dialog is the only PURE-white region left, so grow the
    >=thr component that contains the seed centre."""
    H, W = a.shape[:2]
    cx, cy = x + w // 2, y + h // 2
    pure = a.min(axis=2) >= thr
    if not pure[cy, cx]:
        ys, xs = np.where(pure[max(0, y):y + h, max(0, x):x + w])
        if not len(ys):
            return x, y, w, h, "modal-fail"
        cy, cx = y + int(ys[len(ys) // 2]), x + int(xs[len(xs) // 2])
    top = cy
    while top > 0 and pure[top - 1, cx]:
        top -= 1
    bot = cy
    while bot < H - 1 and pure[bot + 1, cx]:
        bot += 1
    # the dialog's own dividers break the column run, so widen using the row
    # with the longest pure run inside [top, bot]
    band = pure[top:bot + 1]
    best, bx0, bx1 = 0, cx, cx
    for r in range(band.shape[0]):
        xs = np.where(band[r])[0]
        if not len(xs):
            continue
        lo = hi = cx
        if not band[r, cx]:
            continue
        while lo > 0 and band[r, lo - 1]:
            lo -= 1
        while hi < W - 1 and band[r, hi + 1]:
            hi += 1
        if hi - lo > best:
            best, bx0, bx1 = hi - lo, lo, hi
    # Vertical extent by ROW COVERAGE, not by a single column: a divider or a
    # text line breaks any one column, which clipped the dialog to one band.
    cov = pure[:, bx0:bx1 + 1].mean(axis=1) > 0.05
    # 창 안의 가로 구분선은 폭 전체를 가로질러 coverage를 0으로 만든다. 한 줄에서
    # 멈추면 창이 띠 하나로 잘린다(실제로 두 번 당함) -> 최대 GAP줄까지 건너뛴다.
    GAP = 3

    def walk(start, step):
        i, last = start, start
        while 0 <= i + step < H:
            if cov[i + step]:
                i += step
                last = i
                continue
            j, ok = i, False
            for _ in range(GAP):
                j += step
                if not (0 <= j < H):
                    break
                if cov[j]:
                    ok = True
                    break
            if not ok:
                break
            i = j
            last = i
        return last

    top, bot = walk(cy, -1), walk(cy, +1)
    if bx1 - bx0 < 40 or bot - top < 30:
        return x, y, w, h, "modal-fail"
    return bx0, top, bx1 - bx0 + 1, bot - top + 1, "modal"


def fit_outline(a, x, y, w, h, search=60, line=0.6, tol=8):
    """A bordered item sitting on white (a list item inside a dialog, a
    bordered sub-card). `ink` returns only the text inside it and `card` needs
    a page background to stop at, so neither finds the border."""
    H, W = a.shape[:2]
    cx, cy = x + w // 2, y + h // 2
    off = np.abs(a - 255).max(axis=2) > tol
    x0, x1 = max(0, cx - search), min(W, cx + search)
    y0, y1 = max(0, cy - search), min(H, cy + search)

    def nearest(vals, start, step, limit):
        i = start
        while 0 <= i + step < limit:
            i += step
            if vals[i]:
                return i
        return None

    colline = off[max(0, y - 4):y + h + 4, :].mean(axis=0) > line
    left = nearest(colline, cx, -1, W) or x
    right = nearest(colline, cx, +1, W) or x + w
    # Measure the horizontal borders across the FULL width just found and
    # demand near-total coverage: a line of text spans a narrow seed window
    # well enough to look like a border, which clipped the 지시사항 card to
    # its first text row.
    rowline = off[:, left:right + 1].mean(axis=1) > 0.9
    top = nearest(rowline, cy, -1, H) or y
    bot = nearest(rowline, cy, +1, H) or y + h
    if bot - top < 8 or right - left < 8:
        return x, y, w, h, "outline-fail"
    return left, top, right - left + 1, bot - top + 1, "outline"


def fit_solid(a, x, y, w, h, tol=16):
    """A solid-filled control: primary button, pill, badge, avatar.

    `ink`은 '균일한 배경 위의 잉크'를 전제한다. 창 안에 꽉 찬 채움 버튼이 들어오면
    버튼 색이 그 창의 최빈색이 되어 **버튼이 배경으로 뒤집힌다**(seed 그대로 반환).
    여기서는 반대로 seed 색과 같은 덩어리를 키운다."""
    H, W = a.shape[:2]
    sx, sy, sw, sh = _clip(x, y, w, h, a)
    win = a[sy:sy + sh, sx:sx + sw].reshape(-1, 3)
    cols, cnt = np.unique(win, axis=0, return_counts=True)
    target = cols[cnt.argmax()]           # seed 창의 최빈색 = 버튼 채움
    m = np.abs(a - target).max(axis=2) <= tol
    # 중심 픽셀이 라벨 글자일 수 있으므로, 채움색 픽셀 중 중심에 가장 가까운 점에서 시작
    ys, xs = np.where(m[sy:sy + sh, sx:sx + sw])
    if not len(ys):
        return x, y, w, h, "solid-fail"
    cy0, cx0 = sh / 2, sw / 2
    i = int(np.argmin((ys - cy0) ** 2 + (xs - cx0) ** 2))
    cy, cx = sy + int(ys[i]), sx + int(xs[i])
    keep = np.zeros_like(m)
    keep[cy, cx] = True
    for _ in range(max(w, h) + 8):
        g = keep.copy()
        g[1:, :] |= keep[:-1, :]
        g[:-1, :] |= keep[1:, :]
        g[:, 1:] |= keep[:, :-1]
        g[:, :-1] |= keep[:, 1:]
        g &= m
        if g.sum() == keep.sum():
            break
        keep = g
    ys, xs = np.where(keep)
    nx, ny = int(xs.min()) - 1, int(ys.min()) - 1
    nw, nh = int(xs.max() - xs.min()) + 3, int(ys.max() - ys.min()) + 3
    return (*_clip(nx, ny, nw, nh, a), "solid")


MODES = {"ink": fit_ink, "card": fit_card, "nav": fit_nav, "row": fit_row,
         "band": fit_band, "panel": fit_panel, "modal": fit_modal,
         "outline": fit_outline, "solid": fit_solid}


def fit(a, mode, x, y, w, h):
    return MODES[mode](a, x, y, w, h)


def main():
    img = sys.argv[1]
    a = _a(img)
    if sys.argv[2] == "--batch":
        specs = [s for s in sys.argv[3].split(";") if s.strip()]
    else:
        specs = [",".join(sys.argv[2:7])]
    for s in specs:
        p = s.split(",")
        mode = p[0]
        x, y, w, h = map(int, p[1:5])
        if "@" in mode:                      # nav@150 -> 레일 폭을 직접 지정
            mode, arg = mode.split("@", 1)
            nx, ny, nw, nh, why = MODES[mode](a, x, y, w, h, int(arg))
        else:
            nx, ny, nw, nh, why = fit(a, mode, x, y, w, h)
        print(f"{mode} {nx} {ny} {nw} {nh}  {why}")


if __name__ == "__main__":
    main()
