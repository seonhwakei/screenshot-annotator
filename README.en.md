# screenshot-annotator

> **한국어**: [`README.md`](README.md)

A Claude skill that draws region outlines, leader lines and numbered callout badges
on screenshots — for the "click ①" style of screen documentation in manuals.

Coordinates are measured from the pixels instead of guessed off a scaled preview,
leader lines are routed so they never cross, and everything is checked before it is
drawn. **You get PNGs without Figma.**

<p align="center">
  <img src="examples/out/01-list.png" alt="A list screen with eight callouts applied" width="820">
</p>

---

## Install

```
/plugin marketplace add seonhwakei/screenshot-annotator
/plugin install screenshot-annotator@screenshot-annotator
```

Or clone it:

```bash
git clone https://github.com/seonhwakei/screenshot-annotator.git
cd screenshot-annotator && ./install.sh
```

You can also skip the skill and run the scripts directly. All you need is
**Python 3.9+, `pillow` and `numpy`**.

```bash
pip install pillow numpy
export S=/path/to/screenshot-annotator/skills/screenshot-annotator/scripts
```

Badge numbers are drawn in Inter Semi Bold. Without it a system sans-serif is used;
to match exactly, set `export CALLOUT_FONT=/path/to/Inter-SemiBold.ttf`.

---

## Coverage

### Elements it can fit

Give it a **rough box plus the element kind (MODE)** — it finds the exact rectangle.

| MODE | For |
|---|---|
| `ink` | Text, values, status badges, icons |
| `solid` | Solid-filled buttons, pills, avatars |
| `card` | Cards, whole tables, panels |
| `nav` | Left nav items (dark and light rails alike) |
| `row` `band` | A single row of a list |
| `panel` | Right-hand slide-over |
| `modal` | A dialog over a dimmed page |
| `outline` | Bordered items on white |

### Levels

| Level | When | PNG | Figma |
|---|---|---|---|
| **L1** Basic | Everything is visible on screen | O | O |
| **L2** Dark-aware | Dark UI (white halo added automatically) | O | O |
| **L3** Placeholder | A message that is not on screen yet | dashes O, mock via `extra.json` | O |
| **L4** Zoom inset | Small controls inside a table | `zoom` in `extra.json` | O |
| **L5** State catalog | One spot with several possible states | manual | O |
| **L6** Before/after | Empty state next to a populated one | manual | O |

### Usage

Put one `img/HOME.png` in a working directory and run five steps.

```bash
# 1. Measure — the seed box can be rough
python3 $S/fit.py img/HOME.png --batch "nav,8,92,128,22;solid,906,70,112,26;card,400,460,20,14"
#    nav   11  92 125  22
#    solid 905  69  55  28
#    card  176 155 551 351

# 2. Verify — catches empty / overlapping / oversized / out-of-bounds boxes
python3 $S/verify.py spec.json          # -> repeat until 0 findings

# 3. Route the leader lines
python3 $S/route.py .                   # -> must be cross=0 ovl=0 ink=0

# 4. Number them (left column top-down, then right)
python3 $S/build.py .                   # --keep-numbers to freeze the numbering

# 5. Render
python3 $S/render.py . --scale 2        # -> out/HOME.png
```

Working examples of `spec.json` and `areas.txt` live in [`examples/`](examples/).
Copy them as-is and they reproduce.

<table>
<tr>
<td width="50%"><img src="examples/out/02-dialog.png"><br><b>Dialog over dim</b> — <code>modal</code> <code>outline</code></td>
<td width="50%"><img src="examples/out/03-dark.png"><br><b>Dark UI</b> — halo only where the background is dark</td>
</tr>
<tr>
<td><img src="examples/out/04-placeholder.png"><br><b>Placeholder</b> — a not-yet-visible message, dashed</td>
<td><img src="examples/out/01-list.png"><br><b>List screen</b> — five modes in one frame</td>
</tr>
</table>

---

## Use cases

### Documenting a whole screen

You pick the elements; numbering follows position automatically. This is what you
want for a screen-anatomy table.

### Writing a procedure

Only the things the sentence points at get a number.

```
Click Campaigns (markup) to open the campaign screen.
Click New campaign (markup) to open the create dialog.
Check Progress (markup).
```

Three boxes on a screen that would have produced eight under full markup.
Because the numbering has to follow the sentences, use `--keep-numbers`.

### One procedure spanning several screens

Numbering continues across images.

```
1. Click New campaign (image1-①) to open the create dialog.
2. Enter a Campaign name (image2-②) and click Create (image2-③).
3. Check that the new campaign (image3-④) was added to the list.
```

```
STEP1|LIST |1,New campaign,905,69,55,28
STEP2|MODAL|2,Name,352,223,336,28;3,Create,613,342,76,30
STEP3|LIST |4,Added row,178,228,547,38
```

### Alongside Figma

Steps 1–4 are identical; only the drawing goes to Figma. The coordinates and styling
are the same, so the two outputs match — drawing the same frame both ways differed by
0.8% of pixels, all of it font antialiasing.

In Figma you can nudge shapes afterwards, and the markup survives a screenshot swap.
Measure on the **export Figma rendered**, never the source image — `scaleMode: FILL`
crops it and your coordinates drift. Snippets are in
[`references/figma-plugin.md`](skills/screenshot-annotator/references/figma-plugin.md).

### Keeping a Word manual in sync

```bash
python3 $S/extract_docx.py manual.docx out/                  # read numbers/labels from the doc
python3 $S/sync_docx.py manual.docx new.docx png/ map.json   # push renders into the doc
```

The document is the source of truth for numbering. Matching goes by **caption order**,
not filename, because Word renames every media part each time it saves.

---

## Limits

- Choosing *what* to point at is up to you or the agent. The tool only finds the exact rectangle.
- If the aspect ratio strays far from 1040:524, state the placement yourself (`@x,y,w,h`).
- A stale screenshot will contradict the text no matter how good the coordinates are. The tool cannot catch that.

---

The screenshots in `examples/` are synthetic screens made for this repository, not a real product.
