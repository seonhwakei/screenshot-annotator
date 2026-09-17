# 마크업 스타일 사전

값은 전부 Figma 파일 `<FILE_KEY>`의 실제 노드에서 읽어낸 것이다.
새 값을 추가할 때는 눈대중이 아니라 노드 속성을 조회해서 적는다.

---

## 1. 기본 콜아웃 (L1)

| 요소 | 노드명 | 속성 |
|---|---|---|
| 프레임 | 화면 이름 | 1500 × 654, fill #FFF, `clipsContent = false` |
| 스크린샷 | `전체 화면` | RECTANGLE, (230, 60) 1040 × 524 |
| 영역선 | `area-<n>` | fill 없음, stroke #000 **1px OUTSIDE** |
| 리더선 | `leader` | RECTANGLE fill #000, 두께 2, 긴 축 양끝 **+1px씩 연장** |
| 점 | `Ellipse` | 6 × 6, fill #000, 중심 −3 |
| 배지 | `badge-<n>` | 46 × 34, r6, fill **#5283FF**, stroke #000 2px INSIDE |
| 배지 숫자 | `<n>` | TEXT, Inter Semi Bold 20, #FFF, H·V 중앙, 박스와 동일 좌표·크기 |

배지 열: 좌 `x = 135`, 우 `x = 1319`. 리더 레일: 좌 `x = 181`, 우 `x = 1319`.
배지 세로 간격(pitch) 37.

## 2. halo (L2)

```js
effects = [{
  type: 'DROP_SHADOW', color: {r:1,g:1,b:1,a:1},
  offset: {x:0,y:0}, radius: 0, spread: 1,
  visible: true, blendMode: 'NORMAL', showShadowBehindNode: true
}]
```

판정: 요소 아래 픽셀 중 **luma < 140인 비율 ≥ 20%**.
(과거의 "평균 휘도 < 125"는 밝은 표를 가로지르는 리더를 놓쳤다.)
배지는 이미지 밖에 있으므로 대상이 아니다. 영역선은 4변 밴드의 평균으로 판정한다.

## 3. 표시 자리 (L3) — 캡처에 없는 조건부 요소

| 요소 | 노드명 | 속성 |
|---|---|---|
| 영역선 | `area-<n>` | stroke #000 **2px OUTSIDE, dashPattern [6,4]** |
| 오류 문구 자리 | `오류 문구 표시 자리` | fill **#FEF2F2**, r4 |
| 스낵바(성공) | `snackbar (success)` | fill **#ECFDF3**, stroke **#BFFCD9** 1px INSIDE, r4 |
| 스낵바 아이콘 | `snackbar icon` | ELLIPSE 8 × 8, fill **#008A2E** |
| 스낵바 텍스트 줄 | `snackbar text line 1/2` | RECTANGLE 90×5 / 132×4, 회색 |

**실선 = 실재 / 점선 = 표시 자리**. 이 구분이 의미를 나른다. 섞지 말 것.

## 4. 확대 도해 (L4)

| 요소 | 노드명 | 속성 |
|---|---|---|
| 확대 패널 | `<대상> (확대)` | RECTANGLE, IMAGE fill `scaleMode: CROP` |
| 패널 테두리 | 위와 동일 노드 | stroke **#E5E7EB** 2px INSIDE, r8 |
| 연결선 | `연결선 (점선)` | LINE, stroke #000 2px, `dashPattern [6,6]` |
| 설명 라벨 | `설명 라벨` | Inter Semi Bold **20**, #000 |

크롭 변환 — **구간 변수 하나에서 전부 파생**시킨다:

```js
// RX,RY,RW,RH = 이미지 좌표 기준 확대할 구간
imageTransform = [[RW/1040, 0, RX/1040],
                  [0,       RH/524, RY/524]]
패널 크기        = ZW × round(ZW * RH/RW)        // 비율 유지
원본 표시 박스    = dash(IMG_X+RX, IMG_Y+RY, RW, RH)
연결선 y         = IMG_Y + RY + RH/2
확대 안 좌표     px(ix) = ZX + (ix-RX)/RW*ZW
                py(iy) = ZY + (iy-RY)/RH*ZH
```

표시 박스를 따로 손으로 놓으면 반드시 어긋난다(실제로 68px 어긋났다).

## 5. 상태 카탈로그 (L5)

| 요소 | 노드명 | 속성 |
|---|---|---|
| 상태 pill | `배지 <상태>` | RECTANGLE, `cornerRadius = 높이/2` (41 → 20.5) |
| pill 라벨 | `배지 라벨 <상태>` | Inter Semi Bold **22** |
| 진행 스피너 | `진행 표시` | ELLIPSE 19 × 19, fill 없음, stroke 3px |
| 제목 | `설명 라벨` | Inter Semi Bold 22 |

인스턴스 상태 팔레트 (배경 / 글자):

| 상태 | 배경 | 글자 | 스피너 |
|---|---|---|---|
| 준비 중 · 시작 중 · 재시작 중 | `#FEF9C3` | `#856F0E` | O |
| 실행 중 | `#DCFCE7` | `#166534` | |
| 중지 중 | `#6B7280` | `#FFFFFF` | |
| 중지됨 | `#E5E7EB` | `#374151` | |
| 오류 | `#FEE2E2` | `#B91C1C` | |
| 삭제 중 | `#374151` | `#FFFFFF` | O |
| 삭제됨 | `#F3F4F6` | `#9CA3AF` | |

배치: 3열 그리드, 열 간격 400, 행 간격 150. 배지는 pill 위 54px.

## 6. 조건 대조 (L6)

| 요소 | 노드명 | 속성 |
|---|---|---|
| 조건 라벨 | `조건 라벨 <n>` | Inter Semi Bold **20**, **#595959** |
| 카드 테두리 | `테두리 <n>` | fill 없음, stroke **#E5E7EB** 2px INSIDE, r8 |
| 변화 영역 | `변화 영역 <n>` | 기본 실선 영역선 |
| 연결선 | `연결선 (점선)` | LINE 2px, `dashPattern [6,4]` |

스크린샷을 축소해 넣으면 **좌표도 같은 배율로 변환**해야 한다:

```python
S = 실제폭 / 1040
frame_x = PANEL_X + image_x * S
frame_y = PANEL_Y + image_y * S
```

## 7. 프레임 크기 관례

| 용도 | 크기 |
|---|---|
| 단일 화면 | 1500 × 654 |
| 확대 도해 / 카탈로그 / 상태 패널 | 2200 ~ 2400 × 620 |
| 2-up 조건 대조 | 2420 × 720 |
| 카드만 확대 (스크린샷 없음) | 1700 × 440 |
| 세로로 긴 캡처 | 1500 × 956 (이미지 1040 × 836) |
