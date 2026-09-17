#!/usr/bin/env python3
"""Figma 렌더를 매뉴얼 .docx 안으로 밀어 넣는다.

extract_docx.py 가 문서에서 '정답'을 읽어오는 쪽이라면, 이쪽은 그 반대 방향이다.

Usage:
  python3 sync_docx.py <manual.docx> <out.docx> <png_dir> <map.json>

map.json
  {
    "images": [ {"caption": "[관리자 대시보드 화면]", "png": "F00.png"}, ... ],
    "text":   [ {"section": "A-09-1", "find": "1. 입력", "set": ["1. 화면 열기"]},
                {"section": "A-09-1", "find": "참조",  "hard": "..."} ],
    "drop":   [ {"section": "A-05-1", "find": "사용 현황("} ],
    "move":   [ {"section": "A-09-1", "find": "관리자 메뉴 기본 상태(",
                 "after": "2. 변경"} ]
  }

캡션은 스크린샷 문단 **바로 다음** 문단이다. 순서가 곧 대응이므로 caption 은
같은 문자열이 여러 번 나와도 되고, 나온 순서대로 png 와 짝지어진다.

여기 담긴 함정 4가지는 전부 실제로 당한 것이다.

1. 한 미디어 파트를 여러 절차가 공유한다.
   A-06-1(1) · A-06-2(1) · A-06-3 이 같은 image99.png 를 쓰고 있었다. 그대로
   덮어쓰면 세 절차가 같은 그림이 된다. 두 번째부터는 **새 파트로 분리**한다.

2. 비율이 바뀌면 Word 가 늘려서 그린다.
   미디어만 바꾸고 drawing 의 extent(cx/cy) 를 그대로 두면 3836x1914 자리에
   3000x1308 이 들어가 세로로 눌린다. 폭을 유지하고 **cy 를 다시 계산**한다.

3. '1. 입력' 같은 단계 제목은 문서에 수십 번 나온다.
   범위를 안 주고 찾으면 엉뚱한 절이 고쳐지고, 문단 이동은 그 절로 날아간다.
   모든 텍스트 편집은 **절(section) 범위 안에서만** 한다.

4. 하이퍼링크/상호 참조 안의 글자는 문단의 직계 run 이 아니다.
   run 만 비우면 '일반 탭화면설명 11.1' 같은 찌꺼기가 남는다. 그림이 없는
   문단은 **통째로 교체**(hard)한다.
"""
import json
import os
import shutil
import sys
import zipfile

from lxml import etree
from PIL import Image

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
XS = "{http://www.w3.org/XML/1998/namespace}space"

MIN_SHOT_W = 800


def main():
    src, dst, pngdir, mapfile = sys.argv[1:5]
    spec = json.load(open(mapfile))
    work = "/tmp/sync_docx_work"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with zipfile.ZipFile(src) as z:
        z.extractall(work)

    dpath = os.path.join(work, "word/document.xml")
    rpath = os.path.join(work, "word/_rels/document.xml.rels")
    doc, rels = etree.parse(dpath), etree.parse(rpath)
    body = doc.getroot().find(W + "body")
    rroot = rels.getroot()
    rmap = {r.get("Id"): r.get("Target").split("/")[-1]
            for r in rroot if "media" in str(r.get("Target"))}

    def tx(el):
        return "".join(t.text or "" for t in el.iter(W + "t")).strip()

    size = {}
    for part in set(rmap.values()):
        try:
            size[part] = Image.open(os.path.join(work, "word/media", part)).size
        except Exception:
            pass

    # ---- 캡션 -> blip ---------------------------------------------------
    shots, pend = [], None
    for el in body:
        if etree.QName(el).localname != "p":
            continue
        bs = [b for b in el.iter(A + "blip")
              if size.get(rmap.get(b.get(R + "embed")), (0, 0))[0] >= MIN_SHOT_W]
        t = tx(el)
        if bs:
            pend = bs[0]
            continue
        if pend is not None and t.startswith("["):
            shots.append((t, pend))
            pend = None

    def next_rid():
        used = {r.get("Id") for r in rroot}
        n = 1
        while f"rIdsync{n}" in used:
            n += 1
        return f"rIdsync{n}"

    def add_media(name, data):
        open(os.path.join(work, "word/media", name), "wb").write(data)
        rid = next_rid()
        e = etree.SubElement(rroot, PR + "Relationship")
        e.set("Id", rid)
        e.set("Type", "http://schemas.openxmlformats.org/officeDocument/"
                      "2006/relationships/image")
        e.set("Target", "media/" + name)
        return rid

    def fix_extent(blip, w, h):
        d = blip
        while d is not None and etree.QName(d).localname != "drawing":
            d = d.getparent()
        if d is None:
            return
        for ext in list(d.iter(WP + "extent")) + list(d.iter(A + "ext")):
            if ext.get("cx") and ext.get("cy"):
                ext.set("cy", str(int(round(int(ext.get("cx")) * h / w))))

    log, written, cursor = [], {}, 0
    for item in spec.get("images", []):
        cap, png = item["caption"], item["png"]
        hit = None
        for i in range(cursor, len(shots)):
            if shots[i][0] == cap:
                hit, cursor = i, i + 1
                break
        if hit is None:
            log.append(f"!! 캡션 못 찾음: {cap}")
            continue
        blip = shots[hit][1]
        path = os.path.join(pngdir, png)
        data = open(path, "rb").read()
        w, h = Image.open(path).size
        part = rmap[blip.get(R + "embed")]
        if part in written:
            blip.set(R + "embed", add_media(f"image_sync_{png}", data))
            log.append(f"{png} <- 신규 파트 (공유 {part} 분리)")
        else:
            open(os.path.join(work, "word/media", part), "wb").write(data)
            written[part] = png
            log.append(f"{png} -> {part}")
        ow, oh = size.get(part, (w, h))
        if abs(ow / oh - w / h) > 0.01:
            fix_extent(blip, w, h)
            log[-1] += f"  (비율 보정 {ow}x{oh} -> {w}x{h})"

    # ---- 텍스트 ---------------------------------------------------------
    def set_runs(p, pieces):
        runs = [r for r in p.findall(W + "r") if r.find(W + "t") is not None]
        for i, r in enumerate(runs):
            ts = r.findall(W + "t")
            ts[0].text = pieces[i] if i < len(pieces) else ""
            ts[0].set(XS, "preserve")
            for extra in ts[1:]:
                extra.text = ""

    def hard_set(p, text):
        style = next((r.find(W + "rPr") for r in p.findall(W + "r")
                      if r.find(W + "rPr") is not None), None)
        for ch in list(p):
            if etree.QName(ch).localname != "pPr":
                p.remove(ch)
        r = etree.SubElement(p, W + "r")
        if style is not None:
            r.append(style)
        t = etree.SubElement(r, W + "t")
        t.text = text
        t.set(XS, "preserve")

    def section(title):
        start, lvl = None, None
        for i, el in enumerate(body):
            if etree.QName(el).localname != "p":
                continue
            s = el.find(W + "pPr/" + W + "pStyle")
            st = s.get(W + "val") if s is not None else ""
            if not st.startswith("Heading"):
                continue
            if start is None and tx(el).startswith(title):
                start, lvl = i, st
            elif start is not None and st <= lvl:
                return start, i
        return start, len(body)

    def find(sec, needle, kind="p"):
        s, e = section(sec)
        if s is None:
            return None
        for i in range(s, e):
            el = body[i]
            if kind == "p" and etree.QName(el).localname == "p" \
                    and tx(el).startswith(needle):
                return i
            if kind == "any":
                for p in el.iter(W + "p"):
                    if tx(p).startswith(needle):
                        return p
        return None

    for it in spec.get("text", []):
        if "hard" in it:
            node = find(it["section"], it["find"], "any")
            if node is None:
                log.append(f"!! 못 찾음 {it['section']} / {it['find']}")
                continue
            hard_set(node, it["hard"])
        else:
            i = find(it["section"], it["find"])
            if i is None:
                log.append(f"!! 못 찾음 {it['section']} / {it['find']}")
                continue
            set_runs(body[i], it["set"])
        log.append(f"{it['section']}: '{it['find'][:20]}' 수정")

    for it in spec.get("drop", []):
        i = find(it["section"], it["find"])
        if i is None:
            log.append(f"!! 못 찾음(drop) {it['section']} / {it['find']}")
            continue
        body.remove(body[i])
        log.append(f"{it['section']}: '{it['find'][:20]}' 문단 삭제")

    for it in spec.get("move", []):
        i = find(it["section"], it["find"])
        if i is None:
            log.append(f"!! 못 찾음(move) {it['section']} / {it['find']}")
            continue
        node = body[i]
        body.remove(node)
        j = find(it["section"], it["after"])
        body.insert(j + 1, node)
        log.append(f"{it['section']}: '{it['find'][:20]}' -> "
                   f"'{it['after'][:20]}' 뒤로 이동")

    doc.write(dpath, xml_declaration=True, encoding="UTF-8", standalone=True)
    rels.write(rpath, xml_declaration=True, encoding="UTF-8", standalone=True)

    if os.path.exists(dst):
        os.remove(dst)
    zf = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    zf.write(os.path.join(work, "[Content_Types].xml"), "[Content_Types].xml")
    for base, _, files in os.walk(work):
        for f in files:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, work)
            if rel != "[Content_Types].xml":
                zf.write(full, rel)
    zf.close()

    print("\n".join(log))
    print(f"\n-> {dst}  {os.path.getsize(dst)/1e6:.1f} MB")
    print("반드시 원본과 텍스트 diff 를 떠서 의도한 줄만 바뀌었는지 확인할 것")


if __name__ == "__main__":
    main()
