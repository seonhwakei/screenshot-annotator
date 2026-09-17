#!/usr/bin/env python3
"""draw.json -> PNG. Figma 없이 마크업 결과를 파일로 받는다.

Figma 플러그인 스니펫과 **같은 좌표·같은 스타일**로 그린다. 그래야 둘 중
무엇으로 렌더하든 결과가 같고, 한쪽에서 확인한 것이 다른 쪽에서도 성립한다.

Usage:
  python3 render.py [workdir] [--scale N] [--out DIR]

읽는 것 (모두 workdir 기준, 파이프라인이 이미 만들어 둔 것들):
  routes.json   프레임별 img 이름과 이미지 배치(geom)
  draw.json     그릴 도형 (areas / leaders / dots / badges / halo)
  spec.json     (선택) 프레임별 "dash": [n] — L3 표시 자리 번호
  extra.json    (선택) L3 모형 / L4 확대 도해 / 프레임 크기 override
  img/<IMG>.png 노드 export

쓰는 것:
  out/<KEY>.png

extra.json
  {"G5": {"mock": [{"t":"rect","x":560,"y":470,"w":380,"h":64,
                    "fill":"E6F4F1","stroke":"A7E0D5","r":8}, ...]},
   "G6": {"frame": [2400, 700],
          "zoom": {"rx":620,"ry":158,"rw":400,"rh":180,
                   "zx":1450,"zw":700,"label":"전환율 열 (확대)"}}}

  mock  L3 표시 자리의 모형 도형 (좌표는 프레임 기준)
  zoom  L4 확대 도해. 구간(rx,ry,rw,rh)은 **이미지 좌표**, 패널은 구간에서 파생한다
        — SKILL.md §0-2대로 손으로 따로 놓지 않는다.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BADGE = (0x52, 0x83, 0xFF)
BW, BH, BR = 46, 34, 6          # 배지 46x34 r6
SIDE_MARGIN = 230               # 이미지 좌우 여백 -> 프레임 폭
BOTTOM_MARGIN = 70

FONTS = [
    "Inter-SemiBold.ttf", "Inter_28pt-SemiBold.ttf",
    "/Library/Fonts/Inter-SemiBold.ttf",
    os.path.expanduser("~/Library/Fonts/Inter-SemiBold.ttf"),
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def badge_font(size):
    env = os.environ.get("CALLOUT_FONT")
    for p in ([env] if env else []) + FONTS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def rounded(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def dashed_rect(d, x, y, w, h, on=6, off=4, width=2, col=BLACK):
    """OUTSIDE 정렬 점선. Figma의 strokeAlign=OUTSIDE와 맞추려고 1px 바깥에서 시작."""
    x0, y0, x1, y1 = x - width, y - width, x + w + width - 1, y + h + width - 1

    def seg(ax, ay, bx, by):
        dist = math.hypot(bx - ax, by - ay)
        if dist == 0:
            return
        ux, uy = (bx - ax) / dist, (by - ay) / dist
        t = 0.0
        while t < dist:
            t2 = min(t + on, dist)
            d.line([ax + ux * t, ay + uy * t, ax + ux * t2, ay + uy * t2],
                   fill=col, width=width)
            t += on + off

    seg(x0, y0, x1, y0)
    seg(x1, y0, x1, y1)
    seg(x1, y1, x0, y1)
    seg(x0, y1, x0, y0)


def render(work, key, v, img_path, geom, dash, scale, font_cache):
    gx, gy, gw, gh = geom
    FW = gx + gw + SIDE_MARGIN
    FH = gy + gh + BOTTOM_MARGIN
    S = scale

    im = Image.new("RGB", (FW * S, FH * S), WHITE)
    shot = Image.open(img_path).convert("RGB")
    if shot.size != (gw * S, gh * S):
        shot = shot.resize((gw * S, gh * S), Image.LANCZOS)
    im.paste(shot, (gx * S, gy * S))
    d = ImageDraw.Draw(im)

    halo = {tuple(g) for g in v.get("H", [])}

    def with_halo(x, y, w, h, draw_fn):
        """Figma의 DROP_SHADOW spread 1 = 요소보다 1px 큰 흰 테두리."""
        if (x, y, w, h) in halo:
            draw_fn(x - 1, y - 1, w + 2, h + 2, WHITE)
        draw_fn(x, y, w, h, BLACK)

    def fill_rect(x, y, w, h, col):
        d.rectangle([x * S, y * S, (x + w) * S - 1, (y + h) * S - 1], fill=col)

    def dot(x, y, w, h, col):
        d.ellipse([x * S, y * S, (x + w) * S - 1, (y + h) * S - 1], fill=col)

    # 순서는 Figma 스니펫과 같아야 한다. 점을 먼저 그리면 뒤에 오는 영역선의
    # halo(흰 테두리)가 점을 덮어써 흰 고리만 남는다.
    # 영역선 — Figma strokeAlign=OUTSIDE 와 맞춘다
    for n, x, y, w, h in v.get("a", []):
        if n in dash:
            dashed_rect(d, x * S, y * S, w * S, h * S,
                        on=6 * S, off=4 * S, width=2 * S)
            continue
        if (x, y, w, h) in halo:
            d.rectangle([(x - 2) * S, (y - 2) * S, (x + w + 1) * S - 1,
                         (y + h + 1) * S - 1], outline=WHITE, width=1 * S)
        d.rectangle([(x - 1) * S, (y - 1) * S, (x + w) * S - 1, (y + h) * S - 1],
                    outline=BLACK, width=1 * S)

    # 리더선 (긴 축 ±1px 연장은 build.py가 이미 반영해 둠)
    for x, y, w, h in v.get("s", []):
        with_halo(x, y, w, h, fill_rect)

    # 점
    for x, y in v.get("d", []):
        with_halo(x, y, 6, 6, dot)

    # 배지
    fnt = font_cache.setdefault(20 * S, badge_font(20 * S))
    for n, x, y in v.get("b", []):
        box = [x * S, y * S, (x + BW) * S - 1, (y + BH) * S - 1]
        # PIL의 outline은 경계 안쪽으로 그려지므로 Figma의 strokeAlign=INSIDE와 같다.
        # 채우기와 테두리를 한 번에 그려야 이중선이 생기지 않는다.
        rounded(d, box, BR * S, fill=BADGE, outline=BLACK, width=2 * S)
        d.text(((x + BW / 2) * S, (y + BH / 2) * S), str(n), font=fnt,
               fill=WHITE, anchor="mm")

    out = os.path.join(work, "out")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"{key}.png")
    im.save(p)
    return p, im.size


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    work = args[0] if args else os.getcwd()
    scale = 1
    outdir = None
    for i, a in enumerate(sys.argv):
        if a == "--scale":
            scale = int(sys.argv[i + 1])
        if a == "--out":
            outdir = sys.argv[i + 1]

    draw = json.load(open(os.path.join(work, "draw.json")))
    routes = json.load(open(os.path.join(work, "routes.json")))
    spec_path = os.path.join(work, "spec.json")
    spec = json.load(open(spec_path)) if os.path.exists(spec_path) else {}

    font_cache = {}
    n = 0
    for key, v in draw.items():
        r = routes.get(key, {})
        geom = r.get("geom") or [230, 60, 1040, 524]
        img = os.path.join(work, "img", r.get("img", key) + ".png")
        dash = set(spec.get(key, {}).get("dash", []))
        p, size = render(work if not outdir else outdir, key, v, img, geom,
                         dash, scale, font_cache)
        print(f"{key:8s} {os.path.relpath(p)}  {size[0]}x{size[1]}"
              f"  a={len(v.get('a', []))} b={len(v.get('b', []))}"
              f" halo={len(v.get('H', []))}{'  dash=' + str(sorted(dash)) if dash else ''}")
        n += 1
    print(f"\n{n}개 렌더 완료 (scale={scale})")


if __name__ == "__main__":
    main()
