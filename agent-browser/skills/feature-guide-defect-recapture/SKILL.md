---
name: feature-guide-defect-recapture
description: Use when capture finds an app bug: ASR, fix, recapture.
category: screenshot-capture
---

# Feature-guide defect recapture

When capture exposes an app defect, log it, fix it, then retake the affected flow. Do not drop the flow as BLOCKED because the app misbehaved.

1. List each defect as an ASR document with the `asr-writer` skill.
2. Fix the defect, then recapture the flow it broke.
3. Capture all remaining flows in the same run. Do not leave them as gaps.
4. Keep captions for recaptured cuts consistent with the fixed behavior.

Defects that are observed but not fixed stay listed as observations in the lane report.
