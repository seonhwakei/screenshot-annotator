---
name: feature-guide-screenshot-lanes
description: Use when capturing per-feature user-guide screenshots, recapturing guide cuts in Korean UI, writing per-cut captions, or when a capture lane reports BLOCKED on a cut. Rules: all UI in Korean (/ko); every cut needs a Korean caption (captions.json); a BLOCKED cut is mocked or seeded locally, not handed back to a human. Lanes open the /ko route on their first navigation; English-UI cuts are discarded and retaken, never mixed into the Figma set. Background lanes report through task-notification; do not poll them with idle Monitor loops. Before launching lanes, probe the frontend sign-in route, the backend health route and any other services the cuts need, and confirm the next-server child is alive: a live `next dev` parent with no next-server child refuses connections, so restart the frontend before retaking. Discard cuts stuck on a loading preview instead of shipping them.
category: screenshot-docs
---

# Feature guide screenshots: one lane per feature area

**언어 규칙(필수)**: 사용자 가이드는 한국어다. 화면은 `/ko/...` 로케일로 촬영하고(`<app-url>/ko/...`), 시드 데이터·노트·보고·캡션은 전부 한국어로 쓴다. 영어 UI로 찍은 컷은 재촬영 대상이다. 촬영 전 계정 언어/로케일이 한국어인지 첫 컷에서 확인한다.
**컷 설명(필수)**: 레인은 컷마다 `captions.json`에 `{ "파일명": { "제목": "짧은 한국어 제목", "설명": "사용자가 이 화면에서 무엇을 보고 무엇을 해야 하는지 1~2문장", "단계": "기능 > 단계", "상태": "OK|MOCKED|BLOCKED" } }` 를 쓴다. 촬영자가 화면을 가장 잘 아므로 찍는 즉시 기록한다. Figma 라벨은 이 파일에서 만든다.

Run each feature area as its own lane with its own test account, seed data only for that account, and report every cut as OK or MOCKED. BLOCKED is allowed only after the unblock ladder in `feature-guide-local-seeding` was fully tried and documented.

- Lane = one feature area + one dedicated local test account + one agent-browser session. Log in with `agent-browser-session-login`.
- Order cuts prerequisites first (business info, settings, payment setup, then the feature). Each feature shows entry, filled form, and result.
- **Do not give up on data/state.** Missing site, posts, subscribers, sent campaigns, orders, mail tokens: create them (UI, API, DB insert, signed-token minting). "Needs a real email/payment" is not a reason to stop. See `feature-guide-local-seeding`.
- Mock data only through DB inserts or API calls for the lane's own user id. Never touch other users' rows. Never edit repo files or run git from a lane.
- Local mail does not deliver. Stop at review, draft, or confirm screens and never write "sent" for a real delivery; screens that depend on a sent campaign are produced from inserted rows, labeled MOCKED.
- Hygiene before each shot: click a blank area to clear focus rings and cursors, dismiss toasts, use realistic Korean sample data, and set the viewport to 1440x900. Repo-wide capture rules live in 별도의 레포 공통 촬영 규칙.
- Pass credentials to subagents as a file path, never inline in the prompt.
- Brief template for small-model lanes: state the locale rule (`/ko/...` UI, Korean seed data, notes, report, captions), require `captions.json` per cut (`제목`/`설명`/`단계`/`상태`), list the exact pages, the prerequisite chain, the repo files to read for data models, and the unblock ladder; require a final table `filename | feature | step | OK / MOCKED via <how> / BLOCKED <why + attempts>`, every DB insert, and cleanup SQL. A lane brief that omits the locale or caption rule produces English UI cuts with no descriptions, which must be re-shot.
- After capture, check each cut with a quick contact sheet: no empty/error/loading screens, no mid-transition modals. Re-shoot, do not just flag.
- Upload to Figma (한국어 제목+설명 라벨, captions.json 기반) with `figma-image-upload` (use the real PNG pixel size for frame ratio; never the 400x300 default).
- Native `window.prompt` / `confirm` freezes an agent-browser session. Register the dialog accept/dismiss handler before the click that opens it (`agent-browser skills get core --full`). If a session freezes anyway, continue in a new session name with `--state`.
- 세션 정리는 자기 레인만: `agent-browser --session <lane> close`. `agent-browser close --all`은 병렬 레인의 세션을 전부 닫으므로 어떤 레인에서도 쓰지 않는다.
- **프로세스 종료는 대상 검수 후에만**: `kill`·`pkill`을 금지하지는 않지만, 실행 전에 종료 대상이 의도한 것만인지 반드시 검수한다.
  1. **패턴은 고유해야 한다**: `cat`·`node`·`chrome`처럼 흔한 낱말은 쓰지 않는다. `pkill -f`는 실행 경로 전체를 검사해서 `/Applications/...`의 `Applications`에도 `cat`이 걸린다. 레인이 직접 만든 고유 문자열(자기 프로필 폴더 전체 경로, 자기 세션 이름, 자기 포트)만 패턴으로 쓴다.
  2. **먼저 목록을 본다(dry run)**: `pgrep -fl '<패턴>'`(또는 `ps -eo pid,etime,command | grep '<패턴>'`)을 실행해 매칭된 프로세스 전체를 출력한다. 건수와 각 명령행의 앞부분을 확인한다.
  3. **전부 레인 소유여야 한다**: 매칭된 모든 PID가 이 레인이 시작한 프로세스(시작할 때 기록한 PID 또는 자기 프로필·세션 경로 하위)임을 확인한다. 하나라도 사용자 앱(Chrome, Docker, Claude, 에디터, 개발 서버)이나 다른 레인의 것이면 중단하고, 레인 소유로 확인된 정확한 PID만 `kill <pid...>`로 종료한다.
  4. **종료 뒤 확인한다**: 같은 목록으로 대상이 사라졌는지, 그리고 사용자 앱(Chrome, Docker, Claude, 프런트·백엔드 dev 서버)이 살아 있는지 `pgrep`/`curl`로 확인하고, 하나라도 죽었으면 즉시 보고한다.
  5. 기록: 종료 명령, dry run 출력의 건수, 확인 결과를 레인 보고에 한 줄로 남긴다. (패턴 kill 한 번으로 사용자 앱이 함께 종료된 사고가 있었다.)
- **파괴적 버튼은 이름으로 누르지 않는다**: 같은 이름의 버튼이 목록마다 있으면(병합·삭제·발행) `find role button --name`으로 누르지 말고, 대상 행의 고유 id를 확인한 뒤 그 id에 붙은 단일 버튼만 누른다. 이름 기반 클릭으로 실제 콘텐츠가 병합된 적이 있다.
- **외부에 쓰는 실행은 레인이 하지 않는다**: 가져오기 실행, 실제 발행, 외부 저장소(CDN·S3) 업로드를 레인이 실행하지 않는다. 미리보기·확인 화면까지만 찍고 실행 여부는 메인 세션이 사용자에게 확인한다. 실제 실행으로 올라간 이미지는 되돌릴 수 없었다.
- 레인이 "사람이 ~해야 한다"며 멈추면 미완료다. 같은 컷을 더 강한 모델로 재배정하고 해소 사다리를 단계별로 명시한다. 실제로 작은 모델 레인이 설정이 많은 컷에서 멈춘 적이 있었다.
- Figma 업로드는 산출물의 일부다. 사용자가 준 Figma URL(fileKey·페이지)에 촬영 완료 후 같은 런 안에서 올린다. 올리지 않고 보고를 끝내지 않는다.
- **사이트 주소 브리프**: 레인 브리프에는 검증된 공개 사이트 주소를 적는다. 게시 사이트는 `https://<site-key>.<host>/` 형태다. 주소를 추측한 레인들이 전부 연결 실패로 막혀 재배정이 필요한 적이 있다. 레인이 주소를 추측하지 않도록 브리프의 "새 사실" 항목에 올바른 주소와 probe 결과를 넣는다.
- Each lane ends with the table above plus every DB insert it made.
- **첫 컷 게이트**: 배치 촬영 전에 첫 컷의 URL이 `/ko/`인지와 화면 문구가 한국어인지 먼저 확인한다. 영어 화면이 나오면 나머지를 찍지 말고 로케일을 고친 뒤 처음부터 다시 찍는다. (실제로 영어 UI로 44컷을 찍은 뒤 전부 재촬영한 적이 있다.)
- **동선 수정 루프**: 촬영 중 앱 결함이 보이면 그 자리에서 고치지 않는다. 결함을 ASR로 기록하고(asr-writer), 수정이 끝나면 같은 동선을 처음부터 다시 찍는다. 새 컷의 `captions.json`에는 교체할 기존 컷을 `대체대상`으로 적어 Figma 섹션에서 교체할 수 있게 한다.
- **프런트 중단 대응**: 프런트 포트가 응답하지 않으면 레인이 임의로 재기동하지 않는다. `lsof -iTCP:<frontend-port> -sTCP:LISTEN`으로 리스닝 프로세스를 확인하고, 부모 `next dev`만 살아 있고 자식이 없으면 상태를 기록한 뒤 메인 세션에 보고한다. 재기동은 프로젝트의 표준 dev 서버 기동 명령으로 하고 `kill-port` 류는 쓰지 않는다. 복구되면 멈춘 레인은 같은 에이전트에 `SendMessage`로 이어서 찍게 하고, 새 레인으로 다시 띄우지 않는다.
