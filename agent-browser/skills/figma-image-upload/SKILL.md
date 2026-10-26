---
name: figma-image-upload
description: 로컬 PNG(렌더 캡처·비교 이미지)를 Figma 파일의 특정 페이지에 올리고 크기·위치·라벨까지 정리할 때 사용. "피그마에 올려줘", "기준 프레임 옆에 나란히", "비교 이미지 피그마 업로드", "이미지 교체" 요청에 쓴다. figma-remote MCP(create_session/upload_assets/use_figma/get_screenshot) 기준.
---

# Figma 이미지 업로드 · 배치

사전: `skill://figma/figma-use/SKILL.md`를 읽는다(use_figma 전 필수). 파일 키는 URL의 `/design/<fileKey>/`.

## 절차
1. `create_session(fileKey, 작업설명)` → sessionId. 이후 모든 Figma 호출에 전달.
2. `use_figma`로 기준 노드의 **페이지 id와 x/y/w/h**를 읽는다(`getNodeByIdAsync` → parent 타고 PAGE까지). 배치 기준점이 된다.
3. `upload_assets(fileKey, count=N, currentPageId=<페이지id>)` → 단회용 URL N개. (nodeIds를 주면 기존 사각형의 채움으로 들어감)
4. `scripts/upload_batch.py <pageId> a.png b.png … -- <uuid…>` 로 POST. uuid는 submitUrl의 `/upload/<uuid>/submit`.
5. **크기 보정 필수(잘림 방지)**: nodeIds 없이 올리면 400×300 프레임(비율 0.75)이 생기고 채움이 FILL이라 다른 비율 이미지는 **잘린다**. 프레임의 현재 width/height로 비율을 계산하면 안 된다(항상 4:3). 반드시 **원본 PNG의 픽셀 크기**(python `struct.unpack('>II', data[16:24])`)로 비율을 구해, `use_figma` 코드에 `{이름: 높이}` 맵을 넣고 `resize(W, round(W*h/w))` 한다. 위치·라벨(`loadFontAsync Inter Regular`)은 그 다음.
5a. **다량 배치(그리드)**: 도메인마다 SECTION 1개(첫 섹션이 비어 있으면 재사용), 4열 그리드, 셀 폭 480 고정·행 높이는 행 최대 높이, 라벨은 이미지 아래. 모든 이미지가 같은 크기면 셀 크기는 폭×(h/w). 업로드된 레이어 이름은 파일명(확장자 없음)이므로 이름 필터에 `.png`를 넣지 않는다. 섹션 안으로 옮길 때 `appendChild` 후 x/y를 다시 설정.
5b. 레인별 파일명이 겹치면 업로드 전에 `A_`, `C_` 같은 접두어를 붙인 스테이징 폴더로 복사한다. 업로드 URL은 `post.py`처럼 파이썬에서 URL 리스트와 정렬된 파일을 `zip`해서 8스레드로 POST한다.
6. `get_screenshot(섹션)`을 받아 PIL로 잘라 **잘림 여부를 눈으로 확인**한다(이미지 하단/우측이 원본과 같은지). 업로드 성공 응답만으로 "반영됨"이라 말하지 않는다.

## 함정
- URL은 1회용·10분 만료. 실패한 URL은 재사용 불가 → 새로 발급.
- 이미 이미지 채움이 있는 사각형에 재업로드하면 **조용히 무시**됨 → `use_figma`로 fills를 단색으로 리셋한 뒤 재업로드.
- zsh 배열은 1-base. 셸 루프로 uuid 인덱싱하지 말고 스크립트/파이썬 zip 사용(이번에 이것 때문에 URL 1개 낭비).
- `loadAllPagesAsync`, `setPluginData`, `createImageAsync` 사용 금지. 페이지 전환은 `figma.setCurrentPageAsync`.
- Inter 스타일명은 "Semi Bold"(공백 있음).
