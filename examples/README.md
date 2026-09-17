# examples

`img/`의 스크린샷에 이 저장소의 스크립트를 그대로 돌려 `out/`을 만들었다.
스크린샷은 실제 제품이 아니라 이 저장소를 위해 합성한 가상 콘솔 화면이다.

재현:

```bash
export S=../skills/screenshot-annotator/scripts
python3 $S/verify.py spec.json     # 그리기 전 검증  -> 0 findings
python3 $S/route.py .              # 리더선 배선     -> cross=0 ovl=0 ink=0
python3 $S/build.py .              # 번호 부여 + halo 판정
python3 $S/render.py . --scale 2   # out/*.png
```

| 파일 | 수준 | 보여 주는 것 |
|---|---|---|
| `01-list.png` | L1 | 목록 화면. `nav` `card` `row` `ink` `solid` 모드가 한 화면에 |
| `02-dialog.png` | L1 | 딤 위의 창. `modal` `outline` 모드 |
| `03-dark.png` | L2 | 다크 UI. 어두운 구간에만 흰 halo가 자동으로 붙는다 |
| `04-placeholder.png` | L3 | 아직 화면에 없는 안내 문구를 점선 "표시 자리"로 |

## procedure/

문장이 지시한 것만 번호를 받는 경우와, 한 절차가 화면 여러 장에 걸치는 경우입니다.
번호를 문장 순서에 맞춰야 하므로 `build.py`에 `--keep-numbers`를 줍니다.

```bash
cd procedure
python3 $S/verify.py spec.json && python3 $S/route.py .
python3 $S/build.py . --keep-numbers && python3 $S/render.py . --scale 2
```

| 파일 | 보여 주는 것 |
|---|---|
| `05-command.png` | 문장이 가리킨 3개만 (전체 마크업이면 8개) |
| `06-step1.png` `07-step2.png` `08-step3.png` | 이미지 3장에 ①②③④가 이어짐 |

`img/`의 두 파일은 `../img/`를 가리키는 심링크입니다.

번호는 **왼쪽 열 위→아래, 그다음 오른쪽 열 위→아래**로 자동 부여된다
(`build.py`가 출력하는 `renumbered` 맵 참고).
