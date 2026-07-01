# 정합성 점검 2차 — 프런트엔드 구현 사실

> 수집일: 2026-07-02 / 기준: devpath-frontend origin/develop(62c161e), devpath-landing-page origin/develop(b725ef4)
> 수집: 읽기 전용 조사 에이전트 / 컨트롤러 표본 검증 2건 통과 — web `/mentor`(router.dart:87), mobile `/community/new`(router.dart:81-83) 직접 확인 일치

## devpath-frontend

기준 ref: `origin/develop` @ `62c161e2f4108f7169ffcd3060058d729bdbd040`

### 1. 앱 목록

`git ls-tree origin/develop:apps` 결과:

- `apps/admin`
- `apps/mobile`
- `apps/web`

### 2. 앱별 라우트

| 앱 | 라우트 경로 | 정의 파일 |
|---|---|---|
| admin | `/login` | `apps/admin/lib/src/app/router.dart:33` |
| admin | `/forbidden` | `apps/admin/lib/src/app/router.dart:34-38` |
| admin | `/dashboard` (ShellRoute 하위) | `apps/admin/lib/src/app/router.dart:41-44` |
| admin | `/users` (ShellRoute 하위) | `apps/admin/lib/src/app/router.dart:47` |
| admin | `/reports` (ShellRoute 하위) | `apps/admin/lib/src/app/router.dart:48` |
| mobile | `/login` | `apps/mobile/lib/src/app/router.dart:49` |
| mobile | `/onboarding` | `apps/mobile/lib/src/app/router.dart:50` |
| mobile | `/home` (StatefulShellBranch) | `apps/mobile/lib/src/app/router.dart:57` |
| mobile | `/learn` (StatefulShellBranch) | `apps/mobile/lib/src/app/router.dart:62-63` |
| mobile | `/learn/content/:slug` (하위 GoRoute) | `apps/mobile/lib/src/app/router.dart:66-67` |
| mobile | `/community` (StatefulShellBranch) | `apps/mobile/lib/src/app/router.dart:77-78` |
| mobile | `/community/new` (하위 GoRoute) | `apps/mobile/lib/src/app/router.dart:81-82` |
| mobile | `/community/posts/:id` (하위 GoRoute) | `apps/mobile/lib/src/app/router.dart:85-86` |
| mobile | `/notifications` (StatefulShellBranch) | `apps/mobile/lib/src/app/router.dart:96-97` |
| web | `/login` | `apps/web/lib/src/app/router.dart:67` |
| web | `/diagnostic` | `apps/web/lib/src/app/router.dart:68` |
| web | `/onboarding` | `apps/web/lib/src/app/router.dart:69` |
| web | `/auth/callback` | `apps/web/lib/src/app/router.dart:72-75` |
| web | `/dashboard` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:79` |
| web | `/path` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:80` |
| web | `/content/:id` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:81-85` |
| web | `/sandbox` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:86` |
| web | `/mentor` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:87` |
| web | `/community` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:88-92` |
| web | `/community/new` (ShellRoute 하위, `/community/:id`보다 먼저 선언) | `apps/web/lib/src/app/router.dart:94-97` |
| web | `/community/:id` (ShellRoute 하위) | `apps/web/lib/src/app/router.dart:98-101` |

집계: admin 5개, mobile 8개, web 11개 (총 24개 GoRoute 선언).

### 3. API 연동 방식 — 실 API 호출 vs 목(mock) 데이터 판정

대표 파일 3개(`apps/web/lib/src/providers/api_providers.dart`, `apps/admin/lib/src/providers/api_providers.dart`, `apps/mobile/lib/src/providers/api_providers.dart`) 전체 내용을 열람.

**판정: 코드 경로 자체는 실 HTTP(dio 기반 `ApiClient`)를 호출하도록 작성되어 있으나, 런타임 기본 설정이 목(mock) 어댑터를 장착하도록 되어 있어 기본 실행 시 API 응답은 전부 목 데이터다.**

근거 인용:

`apps/web/lib/src/providers/api_providers.dart`:
```dart
final apiClientProvider = Provider<ApiClient>((ref) {
  final config = ref.watch(appConfigProvider);
  final store = ref.watch(tokenStoreProvider);
  final client = ApiClient.create(
    ApiConfig(baseUrl: config.baseUrl, useMock: config.useMock),
  );
  ...
  if (config.useMock) {
    client.dio.httpClientAdapter = MockHttpAdapter(webMockFixtures);
  }
  return client;
});
```
(admin/mobile의 `api_providers.dart`도 동일 패턴: `config.useMock`이 true면 `MockHttpAdapter`를 각각 `adminMockFixtures`/`mobileMockFixtures`로 주입.)

`apps/web/lib/src/app/app_config.dart`:
```dart
/// 런타임 설정. `--dart-define`으로 주입(기본=목 프로토).
...
/// - `USE_MOCK`: `true`이면 [MockApiClient]를 사용, `false`이면 실 HTTP 호출.
///   기본값은 `true`(목 프로토 유지 — 변경 시 회귀 주의).
class AppConfig {
  factory AppConfig.fromEnvironment() => const AppConfig(
    baseUrl: String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'https://mock.devpath.ai',
    ),
    useMock: bool.fromEnvironment('USE_MOCK', defaultValue: true),
  );
  ...
}
```

`apps/web/lib/src/app/router.dart` 등에서 SSE(`mentor_sse_source.dart`, `path_sse_source.dart`)도 동일 목/실 분기 패턴(`useMock`이면 목 지연 emit, 아니면 `apiClient.sse(...)` 실 호출)임을 HANDOFF.md 서술에서 반복 확인(예: "목=토큰 지연emit/실서버=`apiClient.sse('/ai-mentor/sessions')`").

결론: 프로덕션 API 게이트웨이와의 실연동 코드는 존재(`ApiClient.create`, dio 인터셉터, `/auth/refresh` 등 실 엔드포인트 경로 하드코딩)하지만, **기본값(`USE_MOCK=true`, `baseUrl=https://mock.devpath.ai`)으로는 항상 목 데이터만 사용**하며, 실 API 연동은 `--dart-define=USE_MOCK=false`를 명시적으로 주입해야 활성화된다. 실서버 계약(SSE 이벤트명, admin refresh 엔드포인트 등)은 HANDOFF.md에 "백엔드 미합의"로 명시된 항목이 다수 존재.

### 4. README.md/CLAUDE.md 구현 상태 주장 인용

**README.md** (`origin/develop:README.md`):
> "런타임 설정(API 엔드포인트·`useMock` 등)은 **`--dart-define`**(또는 `--dart-define-from-file`)로 주입하고 `AppConfig.fromEnvironment`로 읽습니다. **기본값은 목 프로토라 별도 주입 없이도 실행됩니다.**"

> "과거 React `web`/`admin`은 Flutter로 전환 완료"

**CLAUDE.md** (`origin/develop:CLAUDE.md`, 83줄 전체):
- 구현 상태에 대한 직접적 주장은 없음(작업 규칙·브랜치 전략·빌드/테스트 명령 위주 문서). 유일한 관련 서술:
> "런타임 설정(API 엔드포인트·`useMock` 등)은 **`--dart-define`(또는 `--dart-define-from-file`)** 로 주입하고 `AppConfig.fromEnvironment`(`String.fromEnvironment`/`bool.fromEnvironment`)로 읽는다. **기본값은 목 프로토**. 비밀값(키·토큰)은 절대 커밋하지 않는다."

**HANDOFF.md** (`origin/develop:HANDOFF.md` — 구현 상태 주장이 집중된 문서, 최종 업데이트 2026-06-16 명시):

> "**상태: 설계·계획 + 디자인/Eng 리뷰 완료 + P1·P2·P3(main, PR#3) + P4a~P4f(web 골든패스 전체) + P5(admin 대표 3화면) 구현 완료.** 다음은 **P6(mobile)**."

> "**develop**: 통합 브랜치. Git 정책(PR#4)·P4a(PR#5)·P4b(PR#6)·P4c(PR#7)·P4d(PR#8)·P4e(PR#9)·P4f(PR#10) 머지됨. **P5(admin)는 `feat/p5-admin`에서 develop으로 PR(진행)**."

> "## P5 구현 완료 (2026-06-16, feat/p5-admin)
> `apps/admin`(devpath_admin) 관리자 셸 + 대표 3화면 TDD(Task 1~7). **검증됨**: `melos analyze`(전 멤버 No issues)·`melos test`(web 77·dp_design 19·dp_core 30·**admin 11**·mobile 1 PASS)·format 게이트 통과."

> "## P4f 구현 완료 (2026-06-15, ...) ... **web 골든패스 완성**."

> "프로토 = **목 API**(SSE·에러 정규화 포함), 범위 = 골든패스 + surface별 대표화면."

> "## 다음 세션 (RESUME HERE) ... 다음은 **P6(mobile)**: `docs/superpowers/plans/2026-06-14-p6-mobile.md`. **순서 의존** P6→P7."

> "## 미작성 플랜 — 없음 — **P1~P7 전부 작성·리뷰 완료**. 다음은 eng-review·구현."

즉 HANDOFF.md 기준(2026-06-16), mobile(P6)·landing(P7)은 플랜만 작성 완료 상태이고 구현은 아직 시작 전으로 서술되어 있다. 그러나 실제 `origin/develop` 트리에는 `apps/mobile/lib/src/app/router.dart` 등 mobile 구현 코드(GoRoute 8개, `test/features/...` 다수)가 이미 존재한다 — 즉 **HANDOFF.md의 "다음은 P6(mobile)" 서술은 이 ref 시점의 실제 트리 상태(이미 상당 부분 구현됨)보다 뒤처져 있다.**

---

## devpath-landing-page

기준 ref: `origin/develop` @ `b725ef49f61026d9523f2b91bea386b491b44fa4`

### 1. 페이지/라우트 목록

레포 구조(`git ls-tree -r --name-only origin/develop`)는 Flutter/Jaspr 기반이 아니라 **정적 단일 HTML + 바닐라 JS + Cloudflare Pages Functions** 구성이다. 별도 클라이언트 라우터(SPA 라우트)는 없고, `index.html` 한 페이지 내 앵커(`#id`) 섹션으로 구성됨.

`index.html` 내 섹션/앵커:

| 앵커/섹션 id | 용도 |
|---|---|
| `#hero` | 히어로(터미널 UI, 진단 소개) |
| (무 id, `.ba` 답변 비교 예시 섹션) | Before/After 답변 비교 예시 |
| `#how-it-works` | "3단계로 진행됩니다" 타임라인 |
| `#apply` | "AI 학습 진단 인터뷰" 신청 폼(`#interview-root`에 인터뷰 위젯 마운트, `#turnstile-widget` Cloudflare Turnstile) |
| (무 id, `.evidence` 검증 방식 섹션) | 검증 방식 설명 |
| `#faq` | FAQ |

백엔드 API 엔드포인트(Cloudflare Pages Functions, `functions/api/interview/`):
- `POST /api/interview/turn` — `functions/api/interview/turn.js`
- `POST /api/interview/compare` — `functions/api/interview/compare.js`

`src/interview-client.js`에서 실제 `fetch('/api/interview/turn', ...)`, `/api/interview/compare` SSE 스트림(`parseSSE`)으로 호출하며, 서버측(`turn.js`)은 Turnstile 검증(`verifyTurnstile`)·레이트리밋(`checkRateLimit`)·예산 체크(`overBudget`) 후 `callClaude`(`_lib/llm.js`)로 실제 LLM 호출을 수행한다 — 목 데이터가 아닌 실 서버리스 API + 실 LLM 연동.

폼 제출은 Google Apps Script Web App(`apps-script/Code.gs`)으로 별도 전송(`window.DEVPATH_FORM_ENDPOINT`).

### 2. README.md 상태 주장 인용

`origin/develop:README.md`:

> "# DevPath AI landing validation page
> 48-hour smoke-test landing page for DevPath AI pre-validation."

> "**This repo intentionally starts smaller than the long-term Jaspr landing plan.** It ships a static one-screen page plus a Google Apps Script + Google Sheets evidence pipeline so user interviews can start before the polished marketing site."

> "## Round 1 Pass Criteria
> Set these thresholds **before** launch and judge pass/fail against them ... **LCS value** ... the context-aware answer is preferred by **≥ 60%** of raters (n ≥ 15), and its mean rating beats the generic answer by **≥ +0.5**. **Demand** — **≥ 20** completed leads (finished interview + email). Both LCS conditions **and** the demand condition met → proceed to Round 2. Otherwise the signal is inconclusive: revise the hypothesis or the funnel rather than scaling."

> "## Run Locally
> Open `index.html` in a browser. If `DEVPATH_FORM_ENDPOINT` is empty, submissions stop with a retryable setup error instead of pretending success."

이 README는 devpath-frontend의 HANDOFF.md가 언급하는 "P7 landing(Jaspr SSG, standalone)" 플랜과는 **다른, 별개의 임시/검증용 정적 페이지 레포**임을 명시적으로 선언하고 있다(장기 Jaspr 랜딩 계획보다 의도적으로 축소된 스코프).
