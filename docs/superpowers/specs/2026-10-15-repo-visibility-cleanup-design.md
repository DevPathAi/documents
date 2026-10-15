# 공개 저장소 정리 — documents 사업 문서 이동 · 표현 정리 · 구 랜딩 비공개 설계 (2026-10-15)

> 대상: GitHub 조직 `DevPathAi` — `documents` · `devpath-landing-page` · `devpath-gitops`(변경 없음) · 신규 비공개 저장소 `leva-business-docs`.
> 계기: 「Leva 제품·사이트 점검 수정 명세」(점검일 2026-10-11)의 P0 항목 G-2 · G-3 · G-4. 지원사업 심사위원이나 방문자가 조직 페이지를 열면 현재 신청서와 다른 내용(「최초」 표현, 구 모수, 구 가격)과 제3자 실명이 보인다.
> 선행: G-5(전 이력 비밀값 검사)는 2026-10-15 에 끝났다 — 유출 0건(§3.3).
> 사용자 결정(2026-10-15): 이력은 남아도 되고 최신 파일만 정리 · documents main 반영은 다음 릴리스에 묶음 · 사업 문서는 비공개 저장소로 이동 + 남는 문서 표현 수정 · 표현 정리 범위 = B(최상위 문서까지, `docs/` 날짜 기록 제외) · 설계 1/2 · 2/2 승인(「진행」).

## 1. 문제

점검 명세는 G-2 · G-4 의 권장 조치로 `documents` 와 `devpath-gitops` 의 **비공개 전환**을 제시했다. 그대로 실행하면 릴리스 승인 체계가 그 즉시 무력화된다(§3.1).
그래서 「무엇이 공개 화면에서 사라져야 하는가」를 기준으로 다시 설계한다.

공개 화면에서 사라져야 하는 것:

- 제출 시점의 사업 문서 — 「한국 최초」 · 「개발 학습자 25만명」 · 「월 14,900원」 등 현행 기준(P1 모수 104,600명 · 정식 초기 9,900원 · 「최초」 표현 금지)과 다른 주장
- 책임 멘토의 실명과 소속(제3자 개인정보) — `29_예비창업패키지_사업계획서.md` 두 줄
- 남는 문서의 「최초」 · 「유일한」 포지셔닝 문구와 구 가격
- 6월 검증용 구 랜딩 저장소(`devpath-landing-page`) — 「DevPath AI landing validation page」로 시작한다

## 2. 목표 · 성공 기준

| | 기준 |
|---|---|
| G1 | documents 기본 브랜치(main)의 **최신 트리**에 이동 대상 7개 파일과 멘토 실명이 없다 |
| G2 | documents 최상위 문서에 「최초의 개발자 교육」 · 「유일한 한국」이 없고, 17 · 27 에 현행 가격 머리말이 있다 |
| G3 | 이동한 7개 파일은 비공개 저장소에 **원문 그대로**(sha256 일치) 보존된다 |
| G4 | `devpath-landing-page` 는 보관(archived) · 비공개이며 로그아웃 상태에서 404 다 |
| G5 | 릴리스 승인 체계(룰셋 · 승인 환경 · 롤백 레인) · ArgoCD · 교차 저장소 워크플로 · workflow-guide 사이트가 그대로 동작한다 |

이력(과거 커밋)에는 원문이 남는다 — 사용자 결정으로 허용 범위다. 이력을 다시 쓰지 않는다.

## 3. 실측 근거 (2026-10-15)

### 3.1 비공개 전환이 깨뜨리는 것

- 조직 요금제 = **free**(좌석 1). 저장소 22개 전부 public.
- GitHub 문서: Free · Pro · Team 은 **required reviewers 를 공개 저장소에서만** 제공한다(비공개는 Enterprise). 비공개 저장소의 룰셋은 Team 이상, 비공개 저장소의 배포 브랜치 정책은 Pro · Team 이상.
- 지금 걸려 있는 것:

| 저장소 | 룰셋 | 승인자 지정 환경 |
|---|---|---|
| `devpath-gitops` | `mission-spine-main-governance` · `mission-spine-main-integrity`(둘 다 active) + main 브랜치 보호 | `mission-spine-production-on` · `-off` · `-landing` · `-rollback` · `mission-spine-staging` |
| `documents` | main 브랜치 보호 | `mission-spine-privacy-approval` |

- 다른 저장소 워크플로 17개가 `documents` 또는 `devpath-gitops` 를 체크아웃하거나 API 로 읽는다(ai-svc · community-svc · frontend 3 · gateway · gitops 5 · lcs-svc · platform-svc · sandbox-svc · shared · documents · workflow-guide).
- ArgoCD 는 `https://github.com/DevPathAi/devpath-gitops.git` 을 **인증 없이** 읽는다(gitops 안에 repository 시크릿 0개).
- `workflow-guide` 는 빌드 때 documents 를 체크아웃하고, 등록되지 않은 문서는 GitHub 원본 URL 로 링크한다 — documents 가 비공개면 빌드와 링크가 함께 깨진다.

→ `documents` 와 `devpath-gitops` 는 **공개를 유지**한다. Team 으로 올려도 required reviewers 는 쓸 수 없으므로 요금제 변경으로 풀리지 않는다.

### 3.2 documents 현황

- origin/main `f52b4a9a`(롤백 창 동결 앵커) · origin/develop `72cd5fa`. 파일 454개(그중 `docs/` 388개).
- 멘토 실명: 22개 저장소 전체에서 **`29_예비창업패키지_사업계획서.md` 한 파일**에만 있다(67행 · 577행). 한 커밋에서 들어와 지워진 적이 없다. 점검 명세가 언급한 `handoff-2026-08-10-*` 두 파일에는 없다.
- `.github/workflows/`(`mission-spine-privacy-approval.yml` · `privacy-producer-ci.yml`)와 `tools/` 는 이동 대상 7개를 참조하지 않는다.
- workflow-guide 가 게시하는 문서는 6개(09 · 10 · 11 · 12 · 14 · 16)뿐이고, 이 6개도 이동 대상을 참조하지 않는다. 사이트: `https://devpathai.github.io/workflow-guide/`.
- 다른 저장소(홈페이지 소스 포함)는 이동 대상을 링크하지 않는다.

### 3.3 비밀값 (G-5 결과)

gitleaks 8.30.1 로 22개 저장소 미러(모든 브랜치 · 태그 · 공개 PR ref 1,259개, 커밋 4,703개) 전 이력을 검사했다. 후보 23건이 전부 오탐이었다
(localStorage 키 이름 · UUID 픽스처 · monaco 벤더 코드 · SHA-256 해시 · SealedSecret 암호문 · DevOps 문항 속 예시 값).
평문 `kind: Secret` 매니페스트와 키 · 자격증명 파일이 추가된 이력도 없다.
→ `devpath-gitops` 를 비공개로 돌릴 이유는 「클러스터 구성이 보인다」뿐이고, §3.1 의 비용이 더 크다.

### 3.4 구 랜딩 저장소

`devpath-landing-page`: GitHub Pages 없음(API 404) · 환경 0개 · 다른 저장소의 실제 참조 없음(홈페이지 `src/config.js` · `src/form-utils.js` 의 주석 두 줄뿐).
리드 수집은 Google Apps Script 웹앱이 처리하고, 홈페이지 Pages 환경변수 `APPS_SCRIPT_URL` 이 그 웹앱을 직접 가리킨다 — 저장소 공개 범위와 무관하다.

## 4. 변경 내용

### 4.1 신규 비공개 저장소 `DevPathAi/leva-business-docs`

| 항목 | 내용 |
|---|---|
| 가시성 | private |
| 파일 | 이동 대상 7개 — 원문 그대로 |
| README | 출처 — 원본 저장소 · 원본 커밋 SHA(documents develop 기준) · 이동일 · 파일별 sha256 |
| CLAUDE.md | 브랜치 전략(develop 통합, main 직접 푸시 금지, 2단계 PR) |
| 브랜치 | main(초기 커밋) · develop(main 에서 생성) |

Free 요금제 비공개 저장소라 브랜치 보호를 걸 수 없다. 승인 환경이 필요 없는 문서 보관용이라 문제없다.

이동 대상 7개(documents 최상위):

1. `28_장기_전략.md`
2. `29_예비창업패키지_사업계획서.md`
3. `30_발표_QA_스크립트.md`
4. `31_통계_출처_검증.md`
5. `32_영상_대본.md`
6. `35_모두의_창업_프로그램_참고.md`
7. `pitch-deck.html`

`27_MVP_설계서.md` 는 옮기지 않는다 — 37 · 44 · 45 · README · Home · `.tier1-baseline.md` 와 날짜 기록 9개가 MVP 설계의 기준 문서로 참조한다. 머리말만 단다(§4.2).

### 4.2 documents — develop 대상 PR 1개

브랜치 `docs/*` 를 develop 에서 분기해 develop 으로 PR 한다.

**삭제**: 이동 대상 7개.

**링크**: 최상위 문서 중 이동 대상을 실제로 링크하는 4개(`17_스케줄.md` · `45_Tier3_확장_기능_카탈로그.md` · `Home.md` · `README.md`)에서 그 링크를 일반 텍스트 「(비공개 저장소로 이동, 2026-10)」로 바꾼다(16곳 — `Home.md` 는 `[[위키 링크]]`). `README.md` 의 읽기 경로 표 「심사 / 투자자 대응 | 27 → 29 → 30 → 31 → pitch-deck」도 같은 문구로 정리한다.
`27_MVP_설계서.md`(834행 `devpath-ai-pitch-deck.html`) · `37_전체_문서_전체_레포_정합성_점검.md`(275행 `` `35_….md` ``)는 링크가 아니라 코드 표기 언급이라 바꾸지 않는다(2026-10-15 계획 작성 때 실측 — 처음 이 스펙은 6개로 적었다).
`docs/` 아래 날짜 기록(핸드오프 · 계획 · 리포트 · 스펙)은 손대지 않는다. 그 안의 링크는 끊기지만 당시 기록으로 남긴다.

**문구**:

| 위치 | 현재 | 변경 |
|---|---|---|
| `README.md` 3행 · `Home.md` 3행 | 「내 수준에 맞는 다음 단계를 AI가 안내하는 최초의 개발자 교육」 | 「사수 없는 0~3년차 개발자의 첫 AI 사수」(랜딩 · 조직 프로필 초안과 같은 문구) |
| `01_프로젝트_계획서.md` 16행 | 「당신의 GitHub과 실력을 아는 유일한 한국 개발자 학습 플랫폼」 | 「유일한 」 삭제 |
| `20_커뮤니티_기능_설계서.md` 14행 | 「학습 맥락을 아는 유일한 한국 개발자 커뮤니티」 | 「유일한 」 삭제 |
| `21_유료_플랜_참고설계.md` 170행 | 「당신의 질문에 평판 5,000 이상 시니어가 답하는 유일한 한국 플랫폼.」 | 「유일한 」 삭제 |
| `06_화면_기능_정의서.md` 61행 | 「Pod 간 거리를 걸어서 이해하는 최초의 개발자 교육」(상자 그림 안) | 「최초의 」 삭제, 줄 끝 공백으로 상자 폭 유지 |
| `22_AR_아키텍처_체험_참고설계.md` 38행 | 같은 슬로건 | 「최초의 」 삭제 |
| `17_스케줄.md` · `27_MVP_설계서.md` 머리 | (없음) | 제목 아래에 `> 현행 가격: 정식 전환 시 월 9,900원 예정(2026-10 기준). 본문의 월 14,900원은 작성 당시 가설입니다.` — 본문은 바꾸지 않는다 |

줄 번호는 origin/develop `72cd5fa` 기준이다. 구현 때 문자열로 다시 찾는다.

### 4.3 `devpath-landing-page`

비공개로 돌린 뒤 보관(archive)한다. 순서는 **비공개 → 보관** — 보관된 저장소의 공개 범위를 바꿀 수 있는지 GitHub 문서(「Archiving repositories」)에 나와 있지 않아서다(2026-10-15 확인). 결과는 같다.

### 4.4 `devpath-gitops`

변경하지 않는다(공개 유지). 근거는 §3.1 · §3.3. 점검 명세 G-4 의 gitops 부분은 이 결정으로 닫는다.

## 5. 실행 순서

| 단계 | 시점 | 내용 | 다음 단계 조건 |
|---|---|---|---|
| 1 | 지금 | 비공개 저장소 생성 → 7개 파일 원문 푸시 | sha256 이 documents develop 원본과 일치 · `visibility=PRIVATE` · 로그아웃 요청 404 |
| 2 | 1 뒤 | documents `docs/*` → develop PR, CI 녹색 뒤 머지 | §6 완료 조건(develop 트리) |
| 3 | 지금(1 · 2 와 무관) | 구 랜딩 비공개 → 보관 | `isArchived=true` · `PRIVATE` · 로그아웃 요청 404 · 홈 `/api/stats` 200 유지 |
| 4 | **다음 캠페인 candidate 생성 전** | documents develop → main 머지(기존 동결 규칙) — 공개 화면이 실제로 바뀌는 시점 | §6 완료 조건(main 트리) |

4단계를 candidate 생성 뒤에 하면 candidate 가 봉인한 `analytics_privacy.approval_source_sha` 와 documents main 이 어긋나 candidate 가 거부된다.
4단계를 지금(롤백 창 안에서) 하면 현재 운영 릴리스 `ms-20261003` 의 자동 롤백 레인이 닫힌다 — 그래서 다음 릴리스에 묶는다(사용자 결정).

## 6. 완료 조건 (documents 트리 — develop 에서 먼저, main 에서 다시)

- 이동 대상 7개 파일이 없다.
- 멘토 실명 0건(전체 트리 검색).
- 최상위 `*.md` 에서 「최초의 개발자 교육」 · 「유일한 한국」 0건.
- `17_스케줄.md` · `27_MVP_설계서.md` 에 현행 가격 머리말이 있다.
- 최상위 `*.md` 에서 이동 대상 7개를 가리키는 링크 0개, 그리고 **기준 커밋 대비 새로 끊긴** 상대 링크 0개(스크립트 검사).
  「끊긴 링크 0개」 절대 기준은 쓰지 않는다 — 이모지 이름의 설계 문서 2개(AI-LMS 계획서 · Knowledge Notes 설계)에 위키 링크 기능을 설명하는 `[[Note Title]]` 같은 예시 문법이 원래부터 수십 개 있고, 실제 링크가 아니다(2026-10-15 실측).
- `06_화면_기능_정의서.md` 상자 그림의 고친 줄(슬로건)은 상자 위 테두리와 표시 폭이 같다(64). 바로 윗줄(60행)은 원래부터 65 로 1칸 어긋나 있고 이번 범위 밖이라 두다.
  (처음 이 스펙은 60행을 기준으로 「64 → 65」라고 적었다 — 기준 줄을 잘못 잡은 것이었고, 2026-10-15 최종 리뷰가 잡았다.)
- workflow-guide 게시 6개 파일(09 · 10 · 11 · 12 · 14 · 16)은 바이트 단위로 변경 없음.
- `.github/` · `tools/` 변경 없음.

## 7. 되돌리기

| 대상 | 방법 |
|---|---|
| documents | PR revert — 파일은 이력에 그대로 있다 |
| `leva-business-docs` | 외부 의존 없음 — 그대로 두거나 삭제 |
| `devpath-landing-page` | `gh repo unarchive DevPathAi/devpath-landing-page --yes` 후 `gh repo edit DevPathAi/devpath-landing-page --visibility public --accept-visibility-change-consequences` |

## 8. 위험

| 위험 | 대응 |
|---|---|
| 4단계를 candidate 생성 뒤에 실행 | 이 스펙과 다음 캠페인 핸드오프에 「candidate 생성 전」을 명시한다 |
| 외부(지원사업 신청서 등)에서 `github.com/DevPathAi/documents/blob/main/<이동 대상>` 을 링크 | 4단계 뒤 404. 홈페이지 소스에는 없음을 확인했다. 볼 수 없는 외부 문서는 사용자 확인 사항 |
| 비공개 저장소가 비어 있는 채로 documents 에서 삭제 | 2단계는 1단계 검증(sha256 일치) 뒤에만 머지한다 |
| 공개 이력에 원문 잔존 | 사용자 결정으로 허용. 이력 재작성은 보호된 main 강제 푸시와 동결 앵커 SHA 무효화를 부른다 |

## 9. 범위 밖

- 브랜드 표기(「DevPath AI」 → 「Leva」) — 점검 명세 G-6(별도 하위 프로젝트 ③).
- 조직 프로필 README — G-1(③).
- GitHub secret scanning · push protection 활성화 — G-5 후속 권장(별도 승인).
- 공개 이력 정리(force-push · 저장소 재생성).
