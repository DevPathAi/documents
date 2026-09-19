# 웹 문법 재구성 + 모바일 레포 분리 — 설계

> 작성일: 2026-09-19 · 대상: `app.leva.ai.kr`(devpath-frontend `apps/web` + `packages/dp_design`), 신규 레포 `devpath-mobile`
>
> 상태: 설계 승인됨(사용자, 2026-09-19). 구현 계획은 하위 프로젝트별로 따로 쓴다.

## 1. 배경과 목표

`app.leva.ai.kr` 은 2026-09-13 mobile-first 개편(frontend PR #198, `af1995c`)의 시각 언어를 쓴다: 플로팅 하단 내비,
64px 브랜드 바, 280px 다크 레일, 큰 반경(칩 999·버튼 12·카드 18), 44px 터치 타깃, 카드 위주 구성. 데스크톱
브라우저에서는 "휴대폰 앱을 넓힌 화면"으로 읽힌다.

목표는 **모바일 앱 문법을 걷어내고 데스크톱 웹페이지 문법으로 재구성**하는 것이다. 동시에 네이티브 모바일 앱
(`apps/mobile`)은 **별도 레포·작업 디렉터리로 분리**해 두 제품의 디자인이 서로를 제약하지 않게 한다.

## 2. 사용자 결정 (2026-09-19)

| # | 결정 | 고른 것 | 버린 것 |
|---|---|---|---|
| D1 | 재구성의 층 | **Flutter 유지, 디자인만 웹화** | DOM 재작성 · 읽기 화면만 DOM 혼합 |
| D2 | 폰 폭(<600px) | **반응형 웹 문법으로 축소**(햄버거 메뉴·1열) | 데스크톱 전용 · 현 compact 유지 |
| D3 | 모바일 앱 | **별도 레포·작업 디렉터리로 분리** | 모노레포 유지 |
| D4 | 공용 패키지 | **`dp_design` 포크 + `dp_core` git 참조(커밋 핀)** | 둘 다 포크 · 제3 패키지 레포 |
| D5 | 전역 내비 | **상단 헤더 + 중앙 본문 + 푸터** | 헤더+좌측 보조 메뉴 · 사이드바 유지 |
| D6 | 시각 검증 | **약 20화면 시안을 브라우저로 확인한 뒤 구현**(필요 시 Claude Design) | 시안 없이 구현 |

D1 은 2026-09-15 결정("React 로 재작성하지 않는다", frontend
`docs/superpowers/plans/2026-09-15-flutter-web-react-grade-design.md`)과 일치한다. 따라서 CanvasKit 한계(네이티브 텍스트
선택·페이지 내 찾기·초기 전송 약 17 MB)는 **이번 범위 밖으로 남는다.**

## 3. 범위

**안**: `apps/web` 전 화면(라우트 23개), `packages/dp_design`(셸·레이아웃·데이터 위젯·토큰), 시맨틱 토큰 계약,
홈 `assets/tokens.css` 미러와 Claude Design `Leva Design Tokens` 재동기화, ET13·browser-ux·perf 기준선 재기록,
`apps/mobile` 의 레포 분리와 그에 딸린 CI·도구 이관.

**밖**: `apps/admin`(이미 데스크톱 콘솔), 백엔드·API, 렌더러 교체, 랜딩(`leva.ai.kr`) 디자인, 모바일 앱의 기능 변경.

## 4. 하위 프로젝트와 순서

| # | 하위 프로젝트 | 산출물 | 완료 게이트 |
|---|---|---|---|
| S1 | 웹 시안 약 20화면 | HTML 시안 갤러리 + 확정된 웹 시각 문법(§5 수치 확정) | 사용자 시각 승인 |
| S2 | 모바일 레포 분리 | `DevPathAi/devpath-mobile`(로컬 `D:\workspace\dpa\devpath-mobile`), frontend 에서 `apps/mobile` 제거 | 두 레포 CI 녹색 |
| S3 | 웹 재구성 구현 | 토큰 2.0.0 · 새 셸 · 공용 위젯 웹화 · 화면군별 개편 | ET13·browser-ux·perf 재기준선, develop 머지 |

순서의 근거:

- **S1 이 먼저** — 시안 승인 전에 Flutter 코드를 바꾸면 ET13 visual baseline(현재 visual 120 · a11y 30)을 여러 번
  다시 찍는다. 시안은 값싸게 바꿀 수 있는 유일한 단계다.
- **S2 가 S3 앞** — 모바일은 *현재의* mobile-first `dp_design` 을 포크해 가져간다. 분리가 끝나야 frontend 의
  `dp_design` 을 모바일 회귀 걱정 없이 바꿀 수 있고, ET13 카탈로그에서 모바일 fixture 가 빠져 S3 의 재기준선 범위가 준다.
- 각 하위 프로젝트는 자기 구현 계획(`writing-plans`)을 따로 갖는다. 이 문서는 셋을 묶는 설계다.

## 5. S1 — 시안

### 5.1 대상 화면(20)

로그인 · 동의 · 베타 대기 · 진단 시작 · 진단 문항 · 진단 결과 · 오늘 · 학습 경로 · 경로 today · 콘텐츠 읽기 ·
실습(샌드박스) · AI 멘토 · 커뮤니티 자유 · Q/A · 피드백 · 글 상세 · 질문 상세 · 글/질문 작성 · 마이페이지 · 설정.
공통 요소(헤더·푸터·빈/오류 상태)는 각 화면 안에서 함께 보인다.

### 5.2 방법

- 실제 토큰 값(시맨틱 토큰 계약 1.1.0의 색·타이포)을 CSS 변수로 쓰는 **정적 HTML 시안**. Flutter 가 아니라
  HTML 인 이유는 반복 비용이다 — 시안은 문법을 정하는 도구이고 산출 코드가 아니다.
- 한 페이지 갤러리로 게시(Artifact): 화면 선택, 라이트/다크, 1440/390 폭 전환.
- **2회차 진행**: 1회차 5화면(셸 포함 오늘 · Q/A 목록 · 글 상세 · 로그인 · 학습 경로)으로 문법을 확정 →
  승인 후 2회차 15화면으로 확장. 반복 수정·코멘트가 길어지면 Claude Design 프로젝트로 옮긴다.
- 시안에 쓰는 문구·데이터는 mock 프로필의 실제 화면 내용을 따른다(가짜 기능을 그리지 않는다).

### 5.3 웹 시각 문법(시안에서 확정할 초안)

| 축 | 현재(mobile-first) | 웹 문법 초안 |
|---|---|---|
| 전역 내비 | 280px 다크 레일 / compact 플로팅 하단 내비 | 상단 헤더: 로고 · 오늘 · 학습경로 · AI멘토 · 커뮤니티▾ · 검색 · 계정▾ |
| 폰 폭 | 하단 내비 + 브랜드 바 + 제목 메뉴 | 헤더가 햄버거 메뉴로 접힘, 본문 1열. 하단 고정 요소 없음 |
| 본문 | 레일 옆 전폭, large 에서만 최대폭 | 항상 중앙 정렬 최대폭, 읽기 화면은 `readableMaxWidth` |
| 푸터 | 없음 | 이용약관 · 개인정보 · 문의 · 사업자 표기 |
| 반경 | 칩 999 · 버튼 12 · 카드 18 · 다이얼로그 20 | 칩 4 · 버튼 6 · 카드 8 · 다이얼로그 12 수준 |
| 목록 | 카드 나열 | 구분선 목록·표. 카드는 "카드가 곧 인터랙션"일 때만(DESIGN.md §0 유지) |
| 밀도 | 터치 기준 44px·표준 밀도 | 포인터 기준으로 행 높이 축소. 최소 타깃은 §5.4 |
| 링크 | 버튼·카드 탭 | 밑줄·hover 가 있는 링크 문법, 브레드크럼은 본문 상단 |
| 작성 버튼 | FAB(`community_home_page.dart`) | 페이지 헤더의 일반 버튼 |

색(인디고·슬레이트), 폰트(Pretendard·D2Coding), 접근성 계약(DESIGN.md §6)은 유지한다. 다크 레일 전용 토큰 6종
(`rail*`)은 어두운 헤더의 `header*` 토큰으로 승계한다(§5.4-2).

### 5.4 시안 1회차에서 닫은 결정 (사용자, 2026-09-19)

시안 1회차(5화면, https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd)의 비교 토글로 확인한 뒤 정했다.

| # | 결정 | 고른 것 | 구현에 주는 영향 |
|---|---|---|---|
| 1 | 포인터 타깃·밀도 | **촘촘(컨트롤 높이 30px, 표 행 여백 8px)** | 최소 타깃 기준을 44px 에서 WCAG 2.2 AA 2.5.8(24px)로 옮긴다. DESIGN.md §6 의 "터치 타깃 ≥44" 와 browser-ux 기대값을 S3-P1·P5 에서 다시 쓴다. 390 폭에서도 같은 기준을 쓰되 인접 타깃 간격으로 2.5.8 의 예외 조건을 만족시킨다 |
| 2 | 헤더 톤 | **어두운 면**(현 `railBg` 계열) | `rail*` 토큰 6종은 삭제가 아니라 `header*` 로 이름을 바꿔 승계한다(값 유지, 계약 2.0.0 의 이름 변경) |
| 3 | 커뮤니티 게시판 이동 | **헤더 드롭다운만** | 게시판 페이지 본문에는 이동 수단을 두지 않는다 — PR #220 의 정리 방향과 같다. 390 폭에서는 햄버거 메뉴 안에 세 게시판을 펼쳐 둔다(`DpPageHeader.titleMenu` 제거의 대체 경로) |

## 6. S2 — 모바일 레포 분리

### 6.1 실측한 결합(2026-09-19, frontend `origin/develop` `0cdb2db`)

- `apps/mobile`: 207 파일. `dp_core` import 37곳, `dp_design` import 17곳, `resolution: workspace` 경로 의존.
- 워크플로: `mobile.yml`, `mission-spine-signed-mobile-build.yml`, 그리고 `et13-evidence.yml` ·
  `mission-spine-manual-at-evidence.yml` 이 모바일을 언급.
- 도구: `tools/mobile_source_guard.dart`, `tools/et13_evidence.dart`·`tools/et13/capture.mjs`(모바일 fixture 포함),
  `tools/mission_spine_release_evidence.mjs`·`tools/mission_spine_protected_approval.mjs`(릴리스 증거).

### 6.2 설계

1. **이력 보존 추출**: `git filter-repo` 로 `apps/mobile` 과 포크할 `packages/dp_design` 의 이력을 새 레포로 옮긴다.
   새 레포 구조는 `app/`(구 `apps/mobile`) + `packages/dp_design/`(포크). 브랜치 전략은 조직 공통(main 보호 · develop 통합 · 2단계 PR).
2. **`dp_design`**: 분리 시점의 복사본을 모바일 레포가 소유한다. 이후 두 `dp_design` 은 독립적으로 진화한다.
   시맨틱 토큰 계약의 **색·타이포 값**만 공통 브랜드로 남고, 반경·밀도·레이아웃 토큰은 갈라진다.
3. **`dp_core`**: frontend 레포를 git 의존성으로 참조한다(`git: {url, ref: <commit>, path: packages/dp_core}`).
   핀 갱신은 모바일 레포의 PR 이다. `dp_core` 의 하위 호환을 깨는 변경은 frontend PR 본문에 모바일 영향 여부를 적는다.
4. **CI 이관**: `mobile.yml`·서명 빌드 워크플로·`mobile_source_guard` 를 모바일 레포로 옮긴다. 서명 비밀은 레포
   단위라 새 레포에 다시 넣어야 한다(값은 사람이 가진다 — 사람 단계로 명시).
5. **frontend 정리**: `apps/mobile` 삭제, 루트 `pubspec.yaml` workspace 목록·melos 스크립트에서 제거, ET13 카탈로그에서
   모바일 fixture 제거(카탈로그·스키마 `prefixItems`·도구 카운트·`capture.mjs`·계약 테스트를 함께 — 2026-09-17
   N06 의 교훈: 리터럴 grep 을 합계 검사까지 넓힌다).

### 6.3 gitops 릴리스 계약 — 실측과 결정 (2026-09-19)

**실측(devpath-gitops `origin/main`)**: 웹 승격 계약이 서명 모바일 빌드를 필수 입력으로 묶고 있다.

- candidate spec 의 `quality_evidence_inputs.mobile_test_artifacts`
  (`leva.mission-spine.signed-android-build-binding.v2`: 서명 APK sha256 · build provenance · 워크플로 실행·아티팩트 식별자).
- `scripts/release/validate_release_manifest.py`: `mobile.repository` 가 `frontend.repository`
  (`DevPathAi/devpath-frontend`)와 같아야 하고(1029–1030행), 워크플로 경로가
  `.github/workflows/mission-spine-signed-mobile-build.yml` 로 고정돼 있다(262행).
- `scripts/release/verify_release_artifacts.py`: 서명 모바일 provenance·툴체인·`pubspec.lock` 해시·production 빌드
  구성을 검증한다. 테스트는 `tests/release/test_signed_mobile_manual_trust.py` 외 다수.

즉 현재 계약에서는 서명 모바일 빌드 없이 웹을 운영에 승격할 수 없고, 모바일이 다른 레포로 가면 검증이 실패한다.

**결정(사용자)**: **웹 릴리스 계약에서 모바일을 제거한다.** 모바일은 새 레포에서 독립적으로 서명·배포한다.
버린 것: 계약을 유지하고 바인딩만 새 레포를 가리키게 하기 · 분리를 S3 뒤로 미루기.

**S2 에 추가되는 작업(gitops)**: candidate spec 스키마에서 `mobile_test_artifacts` 제거(스키마 버전 상승) →
두 검증기와 `seal_release_manifest.py` 에서 서명 모바일 경로 제거 → 관련 테스트·픽스처 정리 → frontend 의 릴리스
증거 도구(`tools/mission_spine_release_evidence.mjs` 등)에서 모바일 입력 제거. ~~순서 제약: gitops 계약 변경이 main 에
들어간 뒤에야 frontend 에서 `apps/mobile` 과 서명 빌드 워크플로를 지울 수 있다.~~ → **§6.5 가 이 순서를 뒤집는다**
(frontend 먼저, gitops 가 그 최종 값을 미러).
gitops main 은 룰셋 2종 + classic 보호의 3중 잠금이라 머지 절차에 사람 단계가 낀다.

### 6.4 ET13 카탈로그 숫자 — 같은 gitops 변경에 묶는다 (2026-09-19)

frontend 릴리스 #221(main `03e0c13`)의 운영 승격을 시도하다 두 곳에서 12-fixture 시절의 숫자가 남아 있음을 실측했다.

1. **frontend `et13-baseline-approval.yml`** 이 원시 파일 `162` · visual 경로 `96` · `case_count: 96` · 번들 `98` 을
   리터럴로 고정했다. 2026-09-17 N06(#210)에서 카탈로그가 12 → 15 fixture(visual 120 · a11y 30 · 웹 fixture 11)로
   커졌고, 이 워크플로는 새 카탈로그로 처음 실행된 승인 run `35405819787` 에서 사람 승인 직후 죽었다.
   수정 = frontend PR #222(개수를 case catalog 에서 파생; 실제 원시 아티팩트 204 파일과 경로 단위 일치 확인).
2. **gitops `validate_release_manifest.py` 225–237행** 이 visual `case_count: 96`
   (`web 48 · admin 16 · mobile 16 · dp_design 16`), a11y `24`(`12 · 4 · 4 · 4`)를 기대한다. 따라서 1 을 고쳐도
   15-fixture 카탈로그는 gitops 승격 검증을 통과하지 못한다. 2026-09-17 핸드오프의 "ET13 승인 + Cloudflare
   토큰만 있으면 승격 가능"은 사실이 아니었다.

**결정(사용자, B)**: gitops 의 카탈로그 숫자 갱신을 §6.3 의 모바일 제거와 **한 번의 gitops 변경으로 묶는다.**
모바일 fixture 가 카탈로그에서 빠지면 표면별 개수가 다시 바뀌므로, 따로 하면 3중 잠금 해제와 baseline 재승인이
두 번 든다. 대가: #217·#219·#220 의 운영 반영이 S2 의 gitops 변경 시점까지 미뤄진다(급한 장애 수정 아님).
gitops 검증기의 표면별 개수도 가능하면 리터럴 대신 카탈로그에서 파생하도록 바꾼다 — 같은 결함이 세 번째다
(N06 의 `capture.mjs`·캡처 합계, 이번 승인 워크플로, gitops 검증기).

### 6.5 S2 의 실행 순서 교정 — gitops 는 frontend 카탈로그의 거울이다 (2026-09-19)

§6.3 은 "gitops 계약 변경이 main 에 들어간 뒤에야 frontend 에서 `apps/mobile` 을 지울 수 있다"고 적었다. 근거는
"먼저 지우면 웹 승격이 막힌다"였다. 실측으로 이 순서를 뒤집는다.

gitops `validate_release_manifest.py` 는 개수뿐 아니라 frontend ET13 카탈로그 자체를 미러로 고정한다:

| 항목 | gitops `origin/main` 이 고정한 값 | frontend `origin/develop` 현재 값 |
|---|---|---|
| `FRONTEND_FIXTURE_IDS` (101행) | 12개 (`mobile-today-available`·`mobile-content-reading` 포함) | 15개 (`web-community-{free,qna,feedback}` 추가) |
| `FRONTEND_PROJECTION_CONTRACT_SHA256` (117행) | `c66d08b6…ccf4bde3` | `106e8d29…51fde3ca` |
| `FRONTEND_PROJECTION_MATRIX` (120행~) | 12항목 | 15항목 |
| visual `surface_case_counts` | web 48 · admin 16 · mobile 16 · dp_design 16 | web 72 · admin 16 · mobile 16 · dp_design 16 |

따라서 (1) 웹 승격은 **이미 막혀 있다**(12 ↔ 15 불일치) — "먼저 지우면 막힌다"는 근거가 사라졌고, (2) gitops 가
고정할 **최종 값**(모바일 fixture 를 뺀 13개 목록과 그 투영 계약 해시)은 frontend 에서 카탈로그를 바꿔 생성해야만
존재한다. gitops 를 먼저 바꾸면 곧 다시 바꿔야 할 중간 값을 고정하게 된다.

**교정된 순서**: S2b(`devpath-mobile` 추출, 비파괴) → S2c(frontend: 모바일 ET13 fixture·`apps/mobile`·모바일
워크플로·릴리스 증거 도구의 모바일 입력 제거 → 새 카탈로그·해시 확정, develop 머지) → S2a(gitops: §6.3 의 모바일
제거 + S2c 가 확정한 fixture 목록·매트릭스·해시·개수를 미러) → frontend `develop → main` 재릴리스 → ET13 baseline
봇 디스패치·사람 승인 → gitops 승격. S2a 의 구현 계획은 S2c 의 산출값이 입력이므로 **S2c 실행 뒤에** 쓴다.

함께 제거되는 웹 릴리스 요구(실측, `validate_release_manifest.py`): `quality_evidence_inputs.mobile_test_artifacts`
(803·1024–1065·1647–1663행) · `SIGNED_MOBILE_*` 상수(244–266행) · 수동 접근성 증거 `manual-talkback`
(TalkBack+Android, `required_artifact: candidate_signed_apk`; 59·68·79·283–297행). `manual-nvda`(웹)는 남는다.

계획 문서: S2b = `docs/superpowers/plans/2026-09-19-s2b-devpath-mobile-repo-extraction.md`.

승인 재시도 절차: 보호 환경이 `prevent_self_review` 이고 이 PC 의 `gh` CLI 가 리뷰어 계정이므로 승인 워크플로는
`automation/dispatch-<release_id>` 브랜치의 디스패처 워크플로로 **봇이** 띄운다(직접 `gh workflow run` 금지).

## 7. S3 — 웹 재구성 구현

`develop` 에서 단계별 PR 로 진행한다(장수 빅뱅 브랜치 금지 — frontend 는 PR 마다 perf-gate 약 25분이 돌고, 단계별
PR 이어야 회귀 원인을 좁힐 수 있다).

| 단계 | 내용 | 비고 |
|---|---|---|
| P1 | 시맨틱 토큰 계약 **2.0.0**: 반경·밀도·레이아웃 폭, `rail*` → 헤더 토큰 | 값·이름이 바뀌므로 major. 홈 `tokens.css` 미러와 Claude Design 재동기화 동반(frontend `.design-sync/NOTES.md`「Rebuild」) |
| P2 | `DpWebShell` 신설(헤더·푸터·햄버거·계정 메뉴) → web `AppShellView` 교체. `DpAppShell`·`DpNavRail` 은 **`apps/admin` 이 쓰므로 남긴다**(실측: `admin_shell.dart`); web 만 쓰던 `compactDestinations` 배선과 `DpMobileNavigation` 은 admin 의 compact 동작을 확인한 뒤 정리 | 핸드오프 L3(`_AccountMenu` MenuAnchor a11y)는 여기서 흡수: 새 계정 메뉴는 열 때 첫 항목으로 focus 를 옮긴다. L4 문서 갱신도 같은 PR |
| P3 | 공용 위젯 웹화: `DpListRow`(구분선 목록)·`DpPageHeader`(`titleMenu` 제거)·카드→목록·링크 문법·FAB 제거 | `dp_design` 단위 테스트 + browser-ux |
| P4 | 화면군별 개편 3 PR: 학습(오늘·경로·콘텐츠·실습·멘토) / 커뮤니티 / 계정·온보딩(로그인·동의·진단·마이페이지·설정) | 시안과 1:1 대조 |
| P5 | 기준선 재기록: ET13 visual/a11y baseline, browser-ux `expectations.json`, perf baseline, DESIGN.md §3·§5 개정 | ET13 baseline 승인은 사람 단계 |

원칙:

- 시안에 없는 화면 요소를 구현 중에 즉흥으로 만들지 않는다. 시안이 부족하면 시안을 먼저 보강한다.
- 2026-09-17 의 Flutter 웹 시맨틱 함정 5건(heading+button 병합, `Semantics(container)`, 시맨틱 박스 크기,
  `MenuItemButton`=button, `MenuAnchor` focus)을 새 헤더·메뉴에 먼저 대조한다. 단위 테스트가 통과해도 CI
  `browser-ux` 로 판정한다.
- 무거운 검증(웹 빌드·Playwright)은 CI 에 맡기고 로컬은 analyze·단위 테스트까지.

## 8. 테스트와 게이트

- **S1**: 자동 게이트 없음. 사용자 시각 승인이 게이트다.
- **S2**: 모바일 레포 — analyze·test·android/ios 빌드 계약. frontend — 기존 전 게이트 녹색 + ET13 카탈로그 validate.
- **S3**: PR 마다 analyze-test · browser-ux · perf-gate(전송량 회귀 +5% 이내) · web-image-config-contract · ET13
  produce-atomic-pair. 셸 교체(P2)에서 browser-ux 시나리오(키보드 순회·게시판 이동·메뉴 focus 복귀)를 새 구조에 맞춰
  다시 쓴다.

## 9. 운영 반영

S3 가 develop 에 다 들어간 뒤 `develop → main` 릴리스 + gitops 승격(candidate → promotion → landing-last)으로
운영에 반영한다. 재구성은 ET13 baseline 을 전부 바꾸므로 **baseline 재승인(사람)** 이 한 번 필요하다. 중간 단계는
develop 에만 머물러 운영은 한 번에 바뀐다(반쯤 바뀐 셸이 운영에 나가지 않는다).

## 10. 이 설계가 하지 않는 것

- 네이티브 브라우저 동작(텍스트 선택·찾기·우클릭·SEO)을 얻지 않는다 — D1 의 대가다. 이것이 나중에 문제가 되면
  별도 결정으로 D1 을 다시 연다.
- 모바일 앱의 디자인·기능을 바꾸지 않는다. 분리만 한다.
- 관리자 앱을 바꾸지 않는다. 단 P1 의 토큰 2.0.0 은 `apps/admin` 에도 적용되므로 admin 회귀는 P1 PR 에서 확인한다.
