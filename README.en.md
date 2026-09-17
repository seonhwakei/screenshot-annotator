# screenshot-annotator

> **한국어**: [`README.md`](README.md)

A Claude skill that draws region outlines, leader lines and numbered callout badges
on screenshots — for the "click ①" style of screen documentation in manuals.

Coordinates are measured from the pixels instead of guessed off a scaled preview,
leader lines are routed so they never cross, and everything is checked before it is
drawn. **You get PNGs without Figma.**

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

## Use cases

### 1. Documenting a whole screen

You pick the elements; the numbering follows position — left column top-down, then
the right column. This is what you want for a screen-anatomy table.

<img src="examples/out/01-list.png" alt="Eight callouts on one screen">

### 2. Writing a procedure

Only the things the sentences point at get a number.

```
Click Campaigns (markup) to open the campaign screen.
Click New campaign (markup) to open the create dialog.
Check Progress (markup).
```

Same screen: full markup finds eight, this finds three.
Because the numbering has to follow the sentences, use `--keep-numbers`.

<img src="examples/procedure/out/05-command.png" alt="Only the three elements the sentences point at">

### 3. One procedure spanning several screens

Numbering continues across images.

```
1. Click New campaign (image1-①) to open the create dialog.
2. Enter a Campaign name (image2-②) and click Create (image2-③).
3. Check that the new campaign (image3-④) was added to the list.
```

<table>
<tr>
<td><img src="examples/procedure/out/06-step1.png"></td>
<td><img src="examples/procedure/out/07-step2.png"></td>
<td><img src="examples/procedure/out/08-step3.png"></td>
</tr>
<tr>
<td align="center">Image 1 — ①</td>
<td align="center">Image 2 — ② ③</td>
<td align="center">Image 3 — ④</td>
</tr>
</table>

```
STEP1|LIST |1,New campaign,905,69,55,28
STEP2|MODAL|2,Name,352,223,336,28;3,Create,613,342,76,30
STEP3|LIST |4,Added row,178,228,547,38
```

### 4. Documenting a dark UI

A white halo is added only to the lines and boxes that cross a dark area, and nowhere
else — so a screen that mixes light and dark regions needs no special handling.

<img src="examples/out/03-dark.png" alt="Markup with halo on a dark UI">

### 5. Documenting a dialog over a dimmed page

The dim makes the dialog edge hard to find; `modal` mode picks out the dialog alone.
Inputs inside it are `outline`, the filled button is `solid`.

<img src="examples/out/02-dialog.png" alt="Markup on a dialog over dim">

### 6. Pointing at something not on screen yet

A save-confirmation toast only appears under the right conditions, so it is not in the
screenshot. A dashed box says "it shows up here" — distinct from solid, so no confusion.

<img src="examples/out/04-placeholder.png" alt="Dashed placeholder">

### 7. Alongside Figma

Steps 1–4 are identical; only the drawing goes to Figma. The coordinates and styling
are the same, so the two outputs match — drawing the same frame both ways differed by
0.8% of pixels, all of it font antialiasing.

In Figma you can nudge shapes afterwards, and the markup survives a screenshot swap.
Measure on the **export Figma rendered**, never the source image — `scaleMode: FILL`
crops it and your coordinates drift. Snippets are in
[`references/figma-plugin.md`](skills/screenshot-annotator/references/figma-plugin.md).

### 8. Keeping a Word manual in sync

```bash
python3 $S/extract_docx.py manual.docx out/                  # read numbers/labels from the doc
python3 $S/sync_docx.py manual.docx new.docx png/ map.json   # push renders into the doc
```

The document is the source of truth for numbering. Matching goes by **caption order**,
not filename, because Word renames every media part each time it saves.

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

| Level | Where it shows up | PNG | Figma |
|---|---|---|---|
| **L1** Basic | Use cases 1, 2, 3, 5 | O | O |
| **L2** Dark-aware | Use case 4 | O | O |
| **L3** Placeholder | Use case 6 | dashes O, mock via `extra.json` | O |
| **L4** Zoom inset | Small controls inside a table | `zoom` in `extra.json` | O |
| **L5** State catalog | One spot with several possible states | manual | O |
| **L6** Before/after | Empty state next to a populated one | manual | O |

### Running it

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

If the image is not 1040×524, state the placement: `HOME|HOME@230,60,1040,585|...`

Every image above was produced by these commands in [`examples/`](examples/).
Copy the `spec.json` and `areas.txt` as-is and they reproduce.

---

## Limits

- Choosing *what* to point at is up to you or the agent. The tool only finds the exact rectangle.
- If the aspect ratio strays far from 1040:524, state the placement yourself (`@x,y,w,h`).
- A stale screenshot will contradict the text no matter how good the coordinates are. The tool cannot catch that.

---

The screenshots in `examples/` are synthetic screens made for this repository, not a real product.
