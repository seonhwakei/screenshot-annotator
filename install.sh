#!/usr/bin/env bash
# 클론 후 전역 스킬 디렉터리에 심링크한다. 재실행해도 안전하다.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/screenshot-annotator"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
ln -sfn "$SRC" "$DEST/screenshot-annotator"
echo "linked: $DEST/screenshot-annotator -> $SRC"
python3 - <<'PY'
try:
    import PIL, numpy
    print("deps ok: pillow, numpy")
except ImportError as e:
    raise SystemExit(f"missing dependency: {e.name}\n  pip install pillow numpy")
PY
echo "새 세션에서 /screenshot-annotator 또는 '스크린샷에 번호 달아줘'로 사용하세요."
