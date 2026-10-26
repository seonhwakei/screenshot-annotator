---
name: feature-guide-cut-assembly
description: Use when merging capture lane folders before Figma upload.
category: documentation
---

# Feature-guide cut assembly

Merge all lane outputs with one re-runnable script before any Figma upload. Never hand-pick files or copy PNGs ad hoc.

- Prefix each cut with its lane name (`G_`, `H1_`, `R2_`) so lanes never collide.
- Read `상태` from each lane's `captions.json`. Drop `BLOCKED` cuts and print the drop count per lane. Do not drop them silently.
- Check both directions per lane: every caption has a PNG, and every PNG has a caption. Report any PNG without a caption.
- Keep probe and contact-sheet files (`_probe-*.png`, `contact-sheet-*.png`) out of the upload set. Move them out of the lane folder.
- Record each cut's height/width ratio and its `대체대상` so replacements map to the old cut names.
- Build contact sheets (about 6 columns, about 42 cuts per sheet) and view them before upload. Discard cuts that show a loading, empty, or English-only screen.
- Upload replaced cuts over their old slots. Place new cuts in a new section.
