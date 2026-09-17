#!/usr/bin/env python3
"""Pull the callout contract out of a 매뉴얼 .docx.

The manual is the source of truth for callout NUMBERS and LABELS. This reads it
so the Figma markup can be checked against it instead of guessed.

Usage: python3 extract_docx.py <manual.docx> <outdir>

Writes:
  labels.json  {"<shotKey>": [[1, "검색", "이름 또는 ..."], ...]}
  uses.json    [{"shot", "head", "table": bool, "nums": [..]}, ...]
               `table` marks the 2.2 화면 구성 entry (full callout set);
               the rest are 2.3 절차 entries (subset)
  gaps.json    [{"head", "note"}, ...]  "※ ...스크린샷이 준비되지 않아..."
  media.json   shotKey -> word/media 파일명 (Word 재저장 시 바뀌므로 매번 갱신)

Two gotchas this encodes:

1. Word renames every media part on save (image_shot05.png -> image108.png), so
   nothing may depend on filenames. Parts are classified by PIXEL SIZE:
       callout number badge = small & reused many times (e.g. 184x136)
       screenshot           = width >= MIN_SHOT_W
   and a badge's NUMBER comes from its row order inside the 화면 구성 table.

2. A callout reference belongs to the most recently shown screenshot, but the
   tracking MUST reset at every Heading. Without the reset, references leak
   into the previous section (A-04-3-2's opening line refers to the previous
   screen's button and was being credited to A-04-3-1).
"""
import hashlib
import io
import json
import os
import sys
import zipfile
from collections import Counter

from lxml import etree
from PIL import Image

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

MIN_SHOT_W = 800      # anything this wide is a screenshot
MAX_BADGE = 300       # callout badges are small squares-ish
MIN_BADGE_USES = 2    # ...and they are reused across tables


def text_of(el):
    return "".join(t.text or "" for t in el.iter(W + "t")).strip()


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    z = zipfile.ZipFile(src)
    doc = etree.fromstring(z.read("word/document.xml"))
    rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
    rmap = {r.get("Id"): r.get("Target").split("/")[-1]
            for r in rels if "media" in str(r.get("Target"))}
    body = doc.find(W + "body")

    uses_count = Counter(rmap.get(b.get(R + "embed")) for b in doc.iter(A + "blip"))
    size = {}
    for part in set(rmap.values()):
        try:
            size[part] = Image.open(io.BytesIO(z.read("word/media/" + part))).size
        except Exception:
            pass

    badges = {p for p, s in size.items()
              if max(s) <= MAX_BADGE and uses_count[p] >= MIN_BADGE_USES}
    shots = {p for p, s in size.items() if s[0] >= MIN_SHOT_W}

    # Word writes a separate media part every time the same screen is pasted, so
    # the 2.2 화면 구성 copy and the 2.3 절차 copy of one screen are different
    # parts. Merge only BYTE-IDENTICAL parts: fuzzy matching merged genuinely
    # different admin screens (they share the dark sidebar and layout) and that
    # silently corrupts the label mapping. Near-duplicates are reported instead.
    canon, by_digest = {}, {}
    for p in sorted(shots):
        try:
            digest = hashlib.sha1(z.read("word/media/" + p)).hexdigest()
        except Exception:
            digest = p
        canon[p] = by_digest.setdefault(digest, p)

    def imgs(el):
        return [rmap.get(b.get(R + "embed"), "") for b in el.iter(A + "blip")]

    def style(el):
        s = el.find(W + "pPr/" + W + "pStyle")
        return s.get(W + "val") if s is not None else ""

    badge_num = {}        # media part -> callout number, learned from table order
    conflicts = []
    labels, uses, gaps, media = {}, [], [], {}
    heads, cap, shot_seq = [None] * 5, None, {}

    for el in body:
        tag = etree.QName(el).localname

        if tag == "tbl":
            if cap is None:
                continue
            # only a real callout table counts: header must be 번호 / UI 요소 / 설명.
            # Without this gate any table holding a reused small image (bullets,
            # status icons) gets mistaken for callouts.
            first = el.find(W + "tr")
            head_txt = " ".join(text_of(tc) for tc in first.findall(W + "tc")) if first is not None else ""
            if "번호" not in head_txt or "UI" not in head_txt:
                continue
            rows, seen = [], []
            for tr in el.findall(W + "tr"):
                cells = [text_of(tc) for tc in tr.findall(W + "tc")]
                co = [i for i in imgs(tr) if i in badges]
                if not co:
                    continue
                seen.append(co[0])
                n = len(seen)                     # row order == callout number
                prev = badge_num.setdefault(co[0], n)
                if prev != n:
                    conflicts.append((co[0], prev, n, cap["shot"]))
                rows.append([n, cells[1] if len(cells) > 1 else "",
                             cells[2] if len(cells) > 2 else ""])
            if rows:
                cap["nums"] |= {r[0] for r in rows}
                cap["table"] = True
                labels.setdefault(cap["shot"], rows)
            continue

        if tag != "p":
            continue

        st, tx, im = style(el), text_of(el), imgs(el)

        if st.startswith("Heading"):
            lv = int(st[-1]) if st[-1].isdigit() else 1
            heads[lv - 1] = tx
            for k in range(lv, 5):
                heads[k] = None
            cap = None                            # <-- the reset that stops leakage
            continue

        if "스크린샷" in tx and ("싣지" in tx or "준비되지" in tx):
            gaps.append({"head": " > ".join(h for h in heads if h), "note": tx})

        found = [i for i in im if i in shots]
        if found:
            part = canon.get(found[0], found[0])   # same screen -> same key
            if part not in shot_seq:
                shot_seq[part] = "shot%02d" % len(shot_seq)
                media[shot_seq[part]] = part
            cap = {"shot": shot_seq[part], "head": " > ".join(h for h in heads if h),
                   "nums": set(), "table": False}
            uses.append(cap)
            continue

        if cap is not None:
            cos = [badge_num[i] for i in im if i in badge_num]
            if cos:
                cap["nums"] |= set(cos)

    for u in uses:
        u["nums"] = sorted(u["nums"])

    maxn = {k: max(n for n, _, _ in v) for k, v in labels.items()}
    over, orphan = [], []
    for u in uses:
        if not u["nums"]:
            continue
        if u["shot"] not in maxn:
            orphan.append((u["shot"], u["head"].split(" > ")[-1], u["nums"]))
        elif any(n > maxn[u["shot"]] for n in u["nums"]):
            over.append((u["shot"], u["head"].split(" > ")[-1],
                         [n for n in u["nums"] if n > maxn[u["shot"]]]))

    for name, obj in (("labels", labels), ("uses", uses),
                      ("gaps", gaps), ("media", media)):
        json.dump(obj, open(os.path.join(outdir, name + ".json"), "w"),
                  ensure_ascii=False, indent=1)

    print(f"미디어   : 스크린샷 {len(shots)} / 번호 배지 {len(badges)}")
    print(f"labels  : {len(labels)} shots")
    print(f"uses    : {len(uses)}  (화면 구성 {sum(1 for u in uses if u['table'])} / "
          f"절차 {sum(1 for u in uses if not u['table'])})")
    print(f"gaps    : {len(gaps)} '스크린샷 미비' 표기")
    if conflicts:
        print("\n!! 번호 배지가 표마다 다른 번호로 쓰임 (표 순서 가정 위반):")
        for part, a_, b_, shot in conflicts[:10]:
            print(f"   {part}  {a_} vs {b_}  @{shot}")
    if over:
        print("\n!! 표의 최대 번호를 넘는 참조 (문서 오류 가능):")
        for shot, sec, nums in over:
            print(f"   {shot}  {sec}  -> {nums}")
    if orphan:
        print(f"\n주의: 화면 구성 표가 없는 스크린샷 {len(orphan)}건.")
        print("      절차판이 2.2와 다른 캡처를 쓰고 있다는 뜻이므로,")
        print("      어느 화면 구성 표를 따를지 수동으로 연결해야 합니다.")
        for shot, sec, nums in orphan[:8]:
            print(f"   {shot}  {sec}  -> {nums}")
        if len(orphan) > 8:
            print(f"   ... 외 {len(orphan)-8}건")
    if not conflicts and not over and not orphan:
        print("정합성 이상 없음")


if __name__ == "__main__":
    main()
