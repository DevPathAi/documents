# 핸드오프 2026-09-17 밤 — 홈 운영 배포 · 토큰 1.1.0 · 커뮤니티 독립 페이지화

> 2026-09-17 저녁~밤 세션의 재개 문서다. 같은 날 앞선 기록은 frontend
> `docs/community-information-architecture/handoff.md` 와 home
> `docs/plan/2026-09-17-govtech-submission-hotfix.md` 에 있다. 이 문서는 그 뒤에 일어난 일과
> **다음 세션으로 넘기는 큰 작업**을 고정한다. GovTech 제출일은 **2026-09-18**.

## 1. 지금 상태 (전부 실측)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 홈페이지 운영 | **배포 완료**, 라이브 검증됨 | CF Pages `devpath-home-page` Production 배포 id `005cf175-6e3e-4400-a201-1987ce9d8d84`, source `24c6e74`(2026-09-17 19:40 KST 경) |
| 홈 develop | 핫픽스 #85 + 토큰 미러 1.1.0 #86 + 배포 기록 #87 머지 | `1d3483f8` |
| 앱 시맨틱 토큰 계약 | 1.1.0 (`30.px` 투영 버그 수정 포함) | frontend #219 → develop `f25e2e9` |
| Claude Design | `Leva Design Tokens` 를 1.1.0 으로 재동기화, 원격 파일에서 `30px`·`"1.1.0"` 확인 | 프로젝트 id `19a7b5ca-6f2b-4d14-b291-ac9e47a31855` |
| 커뮤니티 독립 페이지화 | **develop 머지 완료**, CI 전부 통과(browser-ux 17/17) | frontend #220 → develop `0cdb2dbe` |
| 앱 운영(app.leva.ai.kr) | **변화 없음** — #217(스플래시·gzip·멘토 칩)·#219·#220 은 develop 에만 있다 | main `d10ee171` |

라이브 검증 값(`https://leva.ai.kr`): `assets/tokens.dc0cd99b.css` = manifest `1.1.0` · primary `#5653E7` ·
content-max `1360px`, 포스터 200, `/updates` 200, `/api/invite-rounds` 200,
`window.LEVA_CONFIG.appVersion` = `24c6e748…`.

## 2. 이번 세션이 한 일

### 2.1 홈: 토큰 미러 재동기화와 운영 배포

- 홈 `assets/tokens.css`(앱 시맨틱 토큰의 랜딩 미러)가 9/13 개편 전 값(주황 `#B45309`, 1440/880/256/72)을
  고정하고 있었다. 앱 계약 1.1.0 투영으로 재생성하고 계약 테스트·DESIGN.md·visual baseline 4장을 함께 옮겼다(#86).
- develop `24c6e74` 에서 `npm test` 467 · `npm run build` · `npm run test:e2e` 64 통과 → 프리뷰
  `https://preview-govtech-20260917.devpath-home-page.pages.dev` 검증 → 운영 직접 업로드
  (`npx -y wrangler@4 pages deploy dist --project-name devpath-home-page --branch develop`, 레포 루트에서).
- **gitops 주의**: 이 직접 배포로 Production 의 직전 배포가 바뀌었다. 다음 landing-last 의 prior deployment
  기대값은 위 배포 id 다(기록: home `docs/plan/2026-09-17-govtech-submission-hotfix.md`「실행 기록」).

### 2.2 frontend: 커뮤니티 페이지 안 세그먼트 제거 (#220)

게시판이 `커뮤니티 > 게시판 > 자유/QA/피드백` 에서 `커뮤니티 > 자유/QA/피드백`(셸 직접 목적지)으로 올라온 뒤에도
페이지마다 자유/Q/A/피드백 `SegmentedButton` 이 남아 같은 이동 수단이 둘이었다.

- **세그먼트 제거.** compact(<600px) 하단 바에는 `커뮤니티` 하나뿐이라 세그먼트가 Q/A·피드백의 유일한 경로였다
  (실측). 사용자 결정에 따라 그 폭에서만 H1 이 세 게시판을 고르는 **제목 메뉴**가 된다
  (`DpPageHeader.titleMenu`, dp_design 신규 옵션). 검색 중 게시판을 바꾸면 같은 검색어를 새 게시판에서 다시 조회한다.
- 사용자가 고른 개선 4종: 작성 버튼 직행(3지선다 시트 제거) · 행 게시판 배지/색 제거(Q/A 강조색 = 해결 여부) ·
  게시판별 빈 상태/검색 힌트 · 최신순/추천순 정렬.
- **정렬은 클라이언트가 한다.** community-svc `QuestionService.list(board, tag, sort)` 는 `sort` 를 받기만 하고
  무시한다(origin/develop 실측). 목록이 페이지네이션 없는 전체 배열이라 클라이언트 정렬이 정확하다.
- mock 은 `GET /community/posts?board=X` 쿼리 키로 그 게시판 글만 돌려준다(배지가 없어 섞이면 구분 불가).
- 설계 기록: frontend `docs/community-information-architecture/history.md` **D07**, 도구 계약:
  `docs/design/browser-ux-contract.md`, fixture: `docs/design/et13-community-fixtures.md`.

### 2.3 Flutter 웹 시맨틱 함정 — 단위 테스트는 통과했고 browser-ux 게이트만 잡았다

1. `Semantics(header: true, button: true)` 한 노드 → 웹은 `<h2>도움말\n제목</h2>`: 제목 오염 + 버튼 역할 소실.
2. 헤더와 버튼을 형제로 분리해도 헤더 표식이 위로 합쳐져 버튼을 자식으로 거느리면 웹 엔진이 `<h2>` 를 내지 않는다
   → `Semantics(container: true, header: true)`. 재현 테스트 = `matchesSemantics(..., children: const [])`.
3. `IconButton` 위젯 크기는 48(패딩 포함)인데 웹 시맨틱 박스는 40 → `minimumSize: Size.square(44)`.
   테스트는 `tester.getSize` 가 아니라 `tester.getSemantics(...).rect` 로 잰다.
4. Flutter 웹은 `MenuItemButton` 을 role=menuitem 이 아니라 **button** 으로 낸다. 1024/1440 에서 셸 레일·크롬 액션은
   role 있는 시맨틱 노드로 나오지 않는다.
5. 웹 시맨틱스가 켜진 상태에서 `MenuAnchor` 를 Enter 로 열면 메뉴 안에 focus 받은 노드가 없어 DOM focus 가 `<body>` 로
   빠지고 Escape 가 닿지 않는다(VM 위젯 테스트에서는 재현 안 됨). `childFocusNode` 만으로는 해결되지 않았고(CI 실측),
   **열 때 첫 항목으로 focus 를 옮기는 것**(WAI-ARIA 메뉴 버튼)으로 해결했다.

교훈: dp_design 에 heading·메뉴·아이콘 버튼을 넣을 때는 단위 테스트가 통과해도 CI `browser-ux` 잡(푸시 후 약 6분)
으로 판정한다.

## 3. 다음 세션으로 넘기는 작업

### 3.1 큰 작업 (이번 세션에서 의도적으로 미착수)

| # | 작업 | 왜 큰가 / 선행 조건 |
|---|---|---|
| L1 | **frontend develop → main 릴리스 + 운영 승격 캠페인**(#217·#219·#220 반영) | gitops candidate → promotion → landing-last. **ET13 baseline 승인(사람)** 과 **Cloudflare durable token N01(사람)** 필요. #220 으로 ET13 커뮤니티 fixture 3종(`web-community-*`) visual baseline 이 바뀌므로 재렌더·재승인 포함. perf-gate 만 약 23분 |
| L2 | **게이트웨이 CORS dedupe(#44) 운영 반영** | gitops 승격 필요. 홈은 Pages Function 프록시로 이미 우회 중이라 급하지 않다 |
| L3 | **셸 `_AccountMenu` 의 같은 a11y 결함 확인·수정** | `apps/web/lib/src/features/shell/presentation/app_shell.dart` — 2.3-5 와 같은 `MenuAnchor` 패턴, 미측정. browser-ux 시나리오 추가 + 같은 수정. frontend PR 이라 perf-gate 23분 동반 |
| L4 | frontend `docs/community-information-architecture/{task,handoff}.md` 의 큐 표에 이번 세션(#219·#220) 반영 | docs 만 바꿔도 frontend CI 가 perf-gate 를 돌린다 → L3 PR 에 같이 태운다 |
| L5 | handoff.md §9.6 후속(폰트 서브셋 다음 지렛대: 운영 nginx 압축은 #217 로 develop 반영됨 → 승격 후 실측) | L1 뒤 |
| L6 | P2: 12주 미리보기 문구(learning-svc 생성 프롬프트/후처리), journeyId 간헐 누락 조사, pubspec rename(`devpath_web`→) | 각각 별도 브랜치 |

### 3.2 사람 단계 (도구로 도달 불가)

1. **YouTube 재업로드** — 게시본 `MTSrOoTlZss` 44–48s 에 자리표시자가 남아 있다. 로컬 v1.3 렌더는 정상이나
   홈 CLAUDE.md 가 "v1.3 TTS 검수 영상 공개 금지"(창업자 육성판 필요)라 결정이 필요하다. 새 videoId 를 받으면
   홈 `index.html data-video-id`·`evidence/video-release.v1.json` 갱신 → 재배포는 AI 가 이어받는다.
2. 멘토·경로 실캡처용 로그인 Chrome(`--remote-debugging-port=9222`) — 불가하면 mock 캡처 + 배지 명시로 대체.
3. AdSense 유지/제거 결정.
4. ET13 baseline 승인, Cloudflare durable token(N01; 명령은 frontend `docs/community-information-architecture/task.md` §5 N01).

## 4. 재개 절차

```bash
# 상태 실측부터 — 문서는 레포보다 뒤처질 수 있다
git -C D:/workspace/dpa/devpath-frontend fetch origin && git -C D:/workspace/dpa/devpath-frontend rev-list --left-right --count origin/main...origin/develop
git -C D:/workspace/dpa/devpath-home-page fetch origin && git -C D:/workspace/dpa/devpath-home-page log origin/develop --oneline -3
curl -4 -s https://leva.ai.kr/ | grep -oE 'appVersion":"[0-9a-f]{8}'
```

- frontend 주 checkout(`devpath-frontend`)은 더러우니 건드리지 말고 `origin/develop` 에서 새 worktree 를 만든다.
- 남아 있는 세션 worktree 는 `.worktrees/home-govtech-hotfix-20260917` 하나다(design-sync 검증기 `.ds-sync/`
  스테이징 보관용; 브랜치는 머지됨). 나머지(`frontend-community-flat-pages-…`, `frontend-token-contract-…`,
  `home-token-mirror-…`)는 제거했다.
- Claude Design 재동기화 절차: frontend `.design-sync/NOTES.md`「Rebuild」.

## 5. 작업 환경 메모

- 사용자는 작업을 맡겨 두고 같은 PC 에서 게임을 한다(여유 메모리 1.7 GB 까지 내려감). 콘솔 창은 게임 포커스를 뺏고,
  로컬 `flutter build web`·Docker Playwright 는 메모리 부족으로 죽는다. **무거운 검증은 CI 에 맡기고** 로컬은 단위
  테스트·analyze 까지만 한다. 도구 호출은 한 번에 묶는다(호출마다 훅이 node 프로세스를 여러 개 띄운다).
- 세션 마무리(문서·핸드오프·커밋·푸시)는 30분 안에 끝낸다. frontend 는 docs PR 에도 perf-gate 23분이 돌므로
  교차 레포 핸드오프는 CI 가 가벼운 이 레포(`documents`)에 쓴다.
