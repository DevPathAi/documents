# 핸드오프 — 리드 수집 복구 완료, 다음은 `/notes` 콘텐츠 구현

- 작성일: 2026-08-10
- 이전 핸드오프: `handoff-2026-08-10-adsense-live-content-next.md` (PR #92)
- 다음 세션 착수점: **`devpath-home-page` PR #19 머지 → 계획 9태스크 실행**

## 한 줄 요약

애드센스 심사 대기 중 콘텐츠 보강을 하려다, **유입되는 베타 신청이 통째로 유실되고 있음**을 발견해 먼저 복구했다. 원인은 사용자 진단(환경변수 미주입)보다 한 겹 더 깊었고, 조사 과정에서 코드 결함 3건과 SEO 결함 2건을 함께 잡았다. 콘텐츠는 설계·계획까지 마쳤고 구현은 다음 세션이다.

## 심사 상태

애드센스 콘솔 **`Getting ready`** (2026-08-10 사용자 확인). 결과 미도착.

---

## 1. 리드 수집 복구 — 완료·라이브 검증됨

### 무엇이 깨져 있었나

```
POST https://leva.ai.kr/api/lead   → 503 {"ok":false,"error":"endpoint_not_configured"}
GET  https://leva.ai.kr/api/stats  → 503 (동일)
```

리드폼 위젯은 정상 마운트되고 검증·민감정보 가드까지 다 돌지만 **제출 순간 503**이었다. 홈페이지로 들어온 신청이 한 건도 접수되지 않는 상태.

### ★원인은 「환경변수만 넣으면 30분」이 아니었다★

직접 원인은 맞다 — `functions/api/lead.js:13`·`stats.js:12`가 `env.APPS_SCRIPT_URL` 부재 시 503을 낸다. **문제는 넣을 URL이 쓸 수 없는 상태였다는 것이다.**

랜딩에 하드코딩된 `/exec`에 직접 요청하니:

```
GET .../exec?action=stats → 200 text/html
<title>오류</title>  "다음 스크립트 함수(doGet)를 찾을 수 없습니다."
```

배포된 건 **옛 랜딩 백엔드**였다. 함수 목록 대조 결과 홈페이지판 `apps-script/Code.gs` = 랜딩판 + `doGet` + `computeStats_` + `nowIso_`. 그 URL을 그대로 주입했다면 `/api/stats`는 503 대신 **구글 HTML 오류 페이지를 200으로 통과시키는** 더 나쁜 상태가 됐다.

★**교훈: 「설정값이 비어 있다」는 진단이 맞아도, 채워 넣을 값이 유효한지는 별도로 실측해야 한다.**★

### 별첨6 §5-7 귀속에 대한 반증

「랜딩 경로에도 엔드포인트 미설정이라는 원인이 하나 더 있다」는 가설은 **증거가 반대로 나왔다.**

- 옛 랜딩은 `step1`/`step2`/`interview`를 보낸다(`devpath-landing-page/src/form-utils.js:80,102,150`)
- 이 셋은 배포본 `doPost`가 처리한다(없는 건 `doGet`뿐)
- 미설정으로 깨진 건 **`leva.ai.kr`(홈페이지) 경로**이고, 이 경로는 **2026-08-10 당일 처음 라이브**됐다

따라서 별첨6이 다루는 기간의 리드 0건을 이것으로 설명하기는 어렵다. 폼 설계 귀속을 뒤집을 근거가 되지 못한다.

### 교체가 랜딩을 깨뜨리지 않음을 먼저 증명했다

옛 스크립트는 랜딩과 공유 자산이라 교체 전에 대조했다:

- `HEADERS`·`SENSITIVE_PATTERNS` 해시 일치
- 헬퍼 12개 해시 일치
- 차이 2개는 **동작 무관** — `ensureHeaders_`는 `missing` 계산 위치, `parsePayload_`는 중괄호 스타일

### 사용자가 수행한 것과 실제로 일어난 일

「기존 배포 수정 → 새 버전」을 안내했으나 **새 배포가 생성됐다**(배포 ID `AKfycbwbnd…` → `AKfycbxZrY…`).

**결과적으로 무해했다.** 옛 배포가 옛 코드로 남아 랜딩이 깨지지 않았고, 새 배포에 `doGet`이 살아 있다.

```
신규 URL: 200 application/json {"ok":true,"signups":0,...}   ✅
기존 URL: 200 text/html "doGet을 찾을 수 없습니다"            (옛 코드 유지 → 랜딩 무사)
```

### Cloudflare 설정 (제가 API로 수행)

- `env_vars`가 production·preview **양쪽 다 비어 있었음**을 먼저 확인(덮어쓸 것 없음)
- `APPS_SCRIPT_URL`을 ★**`plain_text`가 아니라 `secret_text`**★로 주입. 이 URL은 설정값이 아니라 **리드 시트에 쓰기가 가능한 엔드포인트**다. 핸드오프 #92가 랜딩 프로젝트의 `plain_text` 저장을 이월 위험으로 지목한 것과 같은 계열
- `wrangler pages deploy dist`로 배포(직접 업로드 프로젝트라 `develop` 머지만으론 배포 안 됨)

### 라이브 검증 결과

```
GET  /api/stats  → 200 application/json  {"ok":true,"signups":…}
POST /api/lead   → 200 {"ok":false,"error":"Required consent is missing."}   (동의 누락 프로브)
POST /api/lead   → 200 {"ok":true,"lead_id":"PROBE-…","updated":false}       (동의 포함, signups 2→3)
/zzz-no-page     → 404 + <title>페이지를 찾을 수 없습니다 — Leva</title>
/sitemap.xml     → 200 application/xml
/ads.txt         → 200 text/plain (무변경)
```

동의 누락 프로브는 **시트를 오염시키지 않고** 경로 전체를 검증하는 방법이다 — `validatePayload_`가 시트 접근 **이전에** 예외를 던진다. 다음 세션도 이 방법을 쓸 것.

### ★배포 중 재현된 것 — 엣지가 옛/새를 섞어 응답★

| 라운드 | `/api/stats` | `/sitemap.xml` | `/zzz-no-page` |
|---|---|---|---|
| 1 | **503**(옛) | text/html(옛) | **404**(새) |
| 2 | 200(새) | text/html(옛) | 404(새) |
| 3 | 200(새) | **application/xml**(새) | **200**(옛으로 회귀) |
| 4~9 | 200 | application/xml | 404 (안정) |

**어느 한 라운드만 봤어도 오판이었다.** #92의 교훈이 그대로 값을 했다. 6라운드 반복 후 안정.

### 미해결 — 다음 세션이 확인할 것

1. ★**리드 스프레드시트 바인딩이 불확실하다.**★ 13:23 측정에서 `signups: 0`이었다. 기존 리드 이력이 있는 시트라면 0일 리 없다 → **새 시트일 가능성이 높다.** 옛 랜딩이 쌓은 데이터는 다른 스프레드시트에 있을 수 있다. `getLeadsSheet_`는 `leads` 시트가 없으면 **만들어 버리므로** 밖에서는 구별되지 않는다.
2. **13:23(0건) → 13:28(2건)** 사이에 제가 만들지 않은 신청 2건이 들어왔다. 사용자 테스트인지 실제 방문자인지 확인 필요.
3. **삭제할 프로브 행**: `lead_id = PROBE-20260810-delete-me` (`probe@example.test`)
4. **Cloudflare API 토큰 폐기** — 대화 기록에 남았고 배포는 끝났다.

---

## 2. 함께 잡은 결함 — PR #18 (머지 완료, `aff6f02`)

조사 중 발견한, **환경변수와 무관하게 남아 있던** 결함들.

### ★빈 응답을 성공으로 날조하던 함수★

`functions/api/lead.js`의 한 줄:

```js
return new Response(text || '{"ok":true}', { status: res.ok ? 200 : 502, … });
```

Apps Script는 실패도 **HTTP 200 + HTML**로 돌려준다. 그래서:

- HTML 본문에 `Content-Type: application/json`이 붙어 나가 클라이언트 `parseBody`가 파싱 실패
- **빈 본문이 `{"ok":true}`로 채워져, 시트에 기록되지 않은 리드가 사용자에게 성공 화면으로 보였다**

→ 본문 JSON 검증 후 `502 upstream_invalid`.

### soft-404

`/zzz-no-page` → **200 text/html**. Pages는 `404.html`이 없으면 매칭 안 되는 요청에 `index.html`을 준다. → `404.html` 신설(`noindex, follow`).

### robots.txt가 없는 sitemap을 선언 중

`/sitemap.xml`도 같은 이유로 200 + `index.html`. → `sitemap.xml` 신설(clean URL).

### 브랜드 잔재

`window.DEVPATH_CONFIG` → `window.LEVA_CONFIG`. 주입처가 없어 하위호환 별칭 없이 교체.

### ★사용자 보고 중 결함이 아니었던 것★

**CSS 중복 로드** — `index.html:40-41`은 `<noscript>` 안이다. **JS가 켜진 브라우저는 이 리소스를 가져오지 않는다**(명세상 scripting enabled면 noscript 자식은 원시 텍스트로만 파싱). 비동기 최적화는 무력화되지 않았다.

**StockPilot·LearnFlow 링크** — 연결 대상이 **존재하지 않는다.** `DevPathAi` 조직·개인 계정 모두에 레포가 없고, `documents/27_MVP_설계서.md:734`에 미완료 체크박스로 남아 있다. 지금 링크를 걸면 죽은 링크가 된다. 사용자 지시로 제외.

---

## 3. `/notes` 콘텐츠 — 설계·계획 완료, 구현 미착수 (PR #19)

### 왜 필요한가

`leva.ai.kr`의 배포 대상은 `index.html`(전부 제품 소개) + `privacy.html` 둘뿐. **콘텐츠 페이지 0개.**

### 결정된 것

- **마크다운 → HTML 빌드 파이프라인**(`marked` 18.0.9, 빌드타임 devDependency)
- `sitemap.xml`과 인덱스를 **원고 파일 집합에서 생성** → 「화이트리스트 등록 누락 시 조용한 배포 제외」 함정이 구조적으로 소멸
- 렌더 로직을 `scripts/notes.mjs`로 분리 — **테스트 가능성 때문**. 「원고 0개면 실패」를 실제 `content/`를 훼손하지 않고 픽스처로 검증
- URL은 `/notes/<slug>` (clean URL, `.html` 없음)
- 새 페이지 `<head>`에 애드센스 스크립트 포함. **광고 슬롯(`<ins>`)은 넣지 않음**(승인 후 결정)
- 창업자 개발기 **6편**, 편당 1,200~2,000자, 전부 측정값 있는 실화. 일반론 금지
- ★**AI 협업으로 개발했다는 사실을 숨기지 않는 톤**★ — 「사람이 혼자 겪은 일」로 포장하지 않는다
- 공개 금지(계정 ID·토큰·사업자 정보·`/exec` URL)를 **기계 검증 테스트로 강제**

### 계획 작성 중 실측이 스펙을 교정한 것

- ★**「slug 중복 시 빌드 실패」는 발생할 수 없는 조건**★ — slug는 한 디렉터리의 `.md` 파일명에서 온다. 대신 **본문 h1 금지**로 대체(템플릿이 이미 제목을 h1으로 낸다)
- ★**`.legal`에 코드블록 스타일이 없다**★ — `pre { overflow-x: auto }` 없이는 긴 줄이 모바일 레이아웃을 밀어낸다. `.note` 조판 규칙 추가
- **템플릿 치환에 `String.replace`의 문자열 인자를 쓰면 원고 본문의 `$&` 같은 패턴이 조용히 치환된다.** 함수 형태로 넘길 것 — 정규식을 다루는 글이라 실제로 밟는다

### 다음 세션이 할 일

1. **PR #19 머지**(설계+계획, 코드 변경 없음)
2. `docs/superpowers/plans/2026-08-10-founder-notes-content.md`의 **9태스크 63단계 실행**
3. ★**원고(Task 5·7·8)는 이 세션의 조사 맥락이 있어야 쓸 수 있다.**★ 서브에이전트에 맡기면 일반론이 되고, 그건 애드센스에서 정확히 피하려는 것이다. **코드 태스크만 위임하고 원고는 인라인으로 쓸 것**
4. 배포는 수동 — `npm run build` → `wrangler pages deploy dist`
5. Search Console에 sitemap 제출

원고 6편의 소재는 계획 문서 §Task 5·7·8에 slug·날짜·다룰 내용까지 확정돼 있다.

---

## 레포 상태 (2026-08-10 실측)

| 레포 | develop HEAD | 열린 PR |
|---|---|---|
| devpath-home-page | `aff6f02` (#18 머지) | **#19** (설계·계획) |
| documents | `83ba8e1` (#92) | 이 핸드오프 PR |

`devpath-home-page` 로컬 테스트: **9파일 85건 green**.

## 운영 정보 갱신

| 항목 | 값 |
|---|---|
| Pages 프로젝트 | `devpath-home-page` (**직접 업로드**, 프로덕션 브랜치 `develop`) |
| `APPS_SCRIPT_URL` | production에 **`secret_text`**로 주입 완료 (API로 되읽히지 않음) |
| Apps Script 배포 | **새 배포** `AKfycbxZrY…` 사용 중. 옛 배포 `AKfycbwbnd…`는 옛 코드로 살아 있고 랜딩이 사용 |

★**환경변수 변경은 재배포해야 적용된다.** 그리고 이 프로젝트는 직접 업로드라 대시보드의 "Retry deployment"는 **기존 업로드 산출물을 다시 배포**할 뿐 새 파일을 올리지 않는다.★

## 도구 함정 (이 환경)

- `python`은 스텁이다 → JSON 파싱은 `node -e`로. 게다가 `/tmp/...`는 Git Bash 경로라 **Windows 네이티브 node가 못 읽는다** → 파일 대신 **stdin 파이프**로 넘길 것
- `curl -w "…\n"`이 Git Bash에서 경로 변환으로 깨진다 → `\n` 빼고 `echo`로 개행
- `documents` 레포에 **다른 세션의 미커밋 변경**(`lcs-data-flow-diagrams.html`, `pitch-deck.html`)이 있다 → `git worktree`로 격리해 작업할 것
