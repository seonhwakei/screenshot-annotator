# Figma 플러그인 스니펫과 함정

`mcp__figma-remote__use_figma` 호출 시 `skillNames: "resource:figma-use"`를 반드시 넘긴다.

---

## 함정 (전부 실제로 당한 것)

### `node.x` / `node.y`는 부모 상대 좌표

섹션 안 프레임에 절대 좌표를 넣으면 프레임이 캔버스 저편으로 날아간다.
겉보기엔 성공하고 렌더만 비어 있어서 알아채기 어렵다.

```js
// 검증
`rel=${f.x},${f.y}  abs=${Math.round(f.absoluteBoundingBox.x)},${Math.round(f.absoluteBoundingBox.y)}`
```

**섹션을 `.x/.y`로 옮기면 자식은 자동으로 따라온다.** 자식 좌표는 섹션 상대값이므로
"같은 델타를 자식에도 더한다"고 하면 **두 번 밀린다**. (섹션을 `clone()` 후 옮기면서
자식에도 델타를 더했다가 51개 프레임이 전부 섹션 밖으로 나갔다.)

```js
sec.y = ny;                       // 이게 전부다. 자식 루프 금지.
// 검증: 자식 abs가 섹션 abs 안에 있는지
```

### `createSection()`은 현재 페이지에 생성된다

대상 페이지를 먼저 `await figma.setCurrentPageAsync(page)` 한다.
안 그러면 다른 페이지에 만들어져서 "안 보인다".

### LINE도 `resizeWithoutConstraints(w, h)` — height 인자 필수

빠뜨리면 예외가 나고 **그 호출의 모든 변경이 롤백**된다(원자적).
앞부분이 그려졌다고 착각하지 말 것.

### 한글 이름으로 노드를 찾지 말 것

`전체 화면` 같은 한글 이름 조회가 두 번 실패했다. 노드 id로 접근한다.

### 이미지 fill은 `scaleMode: FILL` — 비율이 다르면 잘린다

측정은 반드시 `download_assets(nodeId=<그 rect>)`로 받은 **렌더 결과** 위에서.

### 금지 API

`loadAllPagesAsync`, `setPluginData`, `createImageAsync`.
Inter 스타일명은 `Semi Bold`(`SemiBold` 아님).

---

## 그리기 스니펫

`build.py`가 만든 `p0.json` 내용을 `D`에 그대로 붙인다.
프레임 8개까지가 한 호출에 안전하다.

```js
const D = { /* p0.json */ };   // { "<rectId 또는 frameId>": {a,s,d,b,H}, ... }

await figma.loadFontAsync({family:'Inter', style:'Semi Bold'});
const BLACK={type:'SOLID',color:{r:0,g:0,b:0}};
const BLUE ={type:'SOLID',color:{r:0x52/255,g:0x83/255,b:0xff/255}};
const WHITE={type:'SOLID',color:{r:1,g:1,b:1}};
const EF=[{type:'DROP_SHADOW',color:{r:1,g:1,b:1,a:1},offset:{x:0,y:0},
           radius:0,spread:1,visible:true,blendMode:'NORMAL',showShadowBehindNode:true}];

const out=[];
for (const [rid,v] of Object.entries(D)) {
  const rect = await figma.getNodeByIdAsync(rid);
  const f = rect.parent;                       // rect id를 줬을 때
  for (const c of [...f.children]) if (c.name !== '전체 화면') c.remove();

  const H = new Set(v.H.map(g=>g.join(',')));
  const put = (node,x,y,w,h,nm) => {
    node.resizeWithoutConstraints(w,h);
    f.appendChild(node);                       // append 먼저, 좌표는 그 다음
    node.x=x; node.y=y; node.name=nm;
    if (H.has([x,y,w,h].join(','))) node.effects=EF;
  };

  for (const [n,x,y,w,h] of v.a) {
    const r=figma.createRectangle(); put(r,x,y,w,h,'area-'+n);
    r.fills=[]; r.strokes=[BLACK]; r.strokeWeight=1; r.strokeAlign='OUTSIDE';
  }
  for (const [x,y,w,h] of v.s) {
    const r=figma.createRectangle(); put(r,x,y,w,h,'leader');
    r.fills=[BLACK]; r.strokes=[];
  }
  for (const [x,y] of v.d) {
    const e=figma.createEllipse(); put(e,x,y,6,6,'Ellipse');
    e.fills=[BLACK]; e.strokes=[];
  }
  for (const [n,x,y] of v.b) {
    const r=figma.createRectangle(); r.resizeWithoutConstraints(46,34);
    f.appendChild(r); r.x=x; r.y=y; r.name='badge-'+n;
    r.cornerRadius=6; r.fills=[BLUE]; r.strokes=[BLACK];
    r.strokeWeight=2; r.strokeAlign='INSIDE';
    const t=figma.createText(); t.fontName={family:'Inter',style:'Semi Bold'};
    t.fontSize=20; t.characters=String(n); t.fills=[WHITE];
    t.textAlignHorizontal='CENTER'; t.textAlignVertical='CENTER';
    t.resizeWithoutConstraints(46,34); f.appendChild(t); t.x=x; t.y=y;
  }

  // 자가 검증 — 호출 결과로 바로 확인한다
  let b=0,a=0,d=0,l=0,hh=0,frac=0; const nums=new Set();
  for (const c of f.children) {
    if (c.name==='전체 화면') continue;
    if (c.effects && c.effects.length) hh++;
    if (c.x%1||c.y%1||c.width%1||c.height%1) frac++;
    if (c.name.startsWith('badge-')) { b++; nums.add(+c.name.slice(6)); }
    else if (c.name.startsWith('area-')) a++;
    else if (c.name==='leader') l++;
    else if (c.type==='ELLIPSE') d++;
  }
  const seq=[...Array(b).keys()].every(i=>nums.has(i+1));
  out.push(`${f.id} ${f.name} b=${b} a=${a} d=${d} l=${l} halo=${hh}/${v.H.length} frac=${frac} seq=${seq}`);
}
return out;
```

---

## 프레임 생성 (원본 복제)

```js
const pg = await figma.getNodeByIdAsync('<PAGE_ID>');
await figma.setCurrentPageAsync(pg);                  // 필수

const FW=1500, FH=654, GX=120, GY=120, COLS=5, PADX=100, PADY=180;
const ROWS = Math.ceil(N/COLS);
const W = PADX*2 + COLS*FW + (COLS-1)*GX;
const H = PADY + ROWS*FH + (ROWS-1)*GY + PADX;

// 빈 자리 찾기 — 겹치면 나중에 통째로 옮겨야 한다
let spot=null;
for (const [x,y] of CANDIDATES)
  if (!pg.children.some(n=> n.x<x+W && x<n.x+n.width && n.y<y+H && y<n.y+n.height))
    { spot=[x,y]; break; }

const sec = figma.createSection();
sec.name='[마크업 대상] ...';
sec.x=spot[0]; sec.y=spot[1];
sec.resizeWithoutConstraints(W,H);

for (let i=0;i<N;i++){
  const f = figma.createFrame();
  f.resizeWithoutConstraints(FW,FH);
  f.fills=[{type:'SOLID',color:{r:1,g:1,b:1}}];
  f.clipsContent=false;
  sec.appendChild(f);
  f.x = PADX + (i%COLS)*(FW+GX);                      // 섹션 상대 좌표
  f.y = PADY + Math.floor(i/COLS)*(FH+GY);
  const c = SRC[i].clone();                           // 원본은 수정 금지
  c.name='전체 화면';
  f.appendChild(c); c.x=230; c.y=60;
  c.resizeWithoutConstraints(1040,524);
}
```

## 구버전 캡처 교체 (SKILL.md §6-5)

프레임을 다시 만들지 말고 **fill의 `imageHash`만** 바꾼다. 마크업은 그대로 남으므로
교체 후 export를 다시 받아 좌표를 재정합한다.

```js
const src = await figma.getNodeByIdAsync('2304:8');      // 최신 캡처 rect
const NEW = src.fills[0].imageHash;
for (const f of sec.children)
  for (const c of f.children)
    if (c.name === '전체 화면' && c.fills[0].imageHash.slice(0,10) === OLD10)
      c.fills = [{type:'IMAGE', scaleMode:'FILL', imageHash: NEW}];
```

`imageHash` 앞 10자로 어느 프레임이 같은 캡처를 쓰는지 한 번에 찾을 수 있다.

## 점선 영역 + 모형 (L3 표시 자리)

```js
r.fills=[]; r.strokes=[BLACK]; r.strokeAlign='OUTSIDE';
r.strokeWeight=2; r.dashPattern=[6,4];
```

## 섹션 이동

```js
sec.x = nx; sec.y = ny;        // 자식은 섹션 상대좌표라 따라온다 — 손대지 말 것
```

## 모자이크 (민감 정보)

Figma에서 지우지 말고, **픽셀화한 새 이미지를 올려 fill로 교체**한다.

```python
B=16
reg = im.crop(box)
im.paste(reg.resize((w//B, h//B), Image.BOX).resize((w,h), Image.NEAREST), box)
```

```
upload_assets(fileKey, count=1, nodeIds=["<rect>"], scaleMode="FILL")
curl -X POST -F "file=@masked.png;type=image/png" "<submitUrl>"
```
