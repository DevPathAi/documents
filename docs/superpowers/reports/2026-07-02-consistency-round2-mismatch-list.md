# 정합성 점검 2차 — 불일치 목록

> 작성일: 2026-07-02 / 작성: 컨트롤러 직접 교차 대조 (위임 없음)
> 좌변: [claims-documents](./2026-07-02-consistency-round2-claims-documents.md) / 우변: [facts-backend](./2026-07-02-consistency-round2-facts-backend.md)·[facts-frontend](./2026-07-02-consistency-round2-facts-frontend.md)·[facts-infra](./2026-07-02-consistency-round2-facts-infra.md)·[facts-aux](./2026-07-02-consistency-round2-facts-aux.md)·[regression-check](./2026-07-02-consistency-round2-regression-check.md)
> 처리 후보 기준: P0=소비자가 먼저 보는 파일의 현황 왜곡 / P1=오해 방지 라벨·표기 / P2=과거 정리 / 관찰=코드 측(수정계획 제외)

## 1. 본표 — 문서-코드 불일치

| # | 문서 | 문서의 주장 | 코드 사실 | 근거(파일 경로/명령) | 처리 후보 |
|---|---|---|---|---|---|
| M-1 | documents/17_스케줄.md | "모바일(P6)·랜딩(P7) 미착수", 0.1 스냅샷(6-19): "학습경로 영속화·콘텐츠·Sandbox·AI 리뷰·멘토·커뮤니티 도메인 API 미구현" | mobile 라우트 8개 구현(frontend origin/develop apps/mobile/lib/src/app/router.dart), landing-page 검증 페이지 develop 가동, learning 21·ai 6·community 10·sandbox 3·lcs 6 엔드포인트 구현 | facts-frontend §frontend-2, facts-backend 요약표, `git -C devpath-frontend show origin/develop:apps/mobile/lib/src/app/router.dart` | P0 |
| M-2 | documents/02_ERD_문서.md 상단 배너 | "현재 Flyway 구현 완료 범위는 사용자·인증·outbox·notifications·온보딩 진단까지", 기준을 37번으로 지정 | 마이그레이션 24파일: learning_path/contents/embeddings·sandbox_sessions·ai_code_reviews·ai_mentor_sessions·community 7종·lcs 2종·device_tokens·reputation 3종·badges 2종·vote_abuse_suspicions까지 존재 | facts-infra §shared, `git -C documents show origin/develop:02_ERD_문서.md` L6 | P0 |
| M-3 | documents/13_테스트_보고서.md | "릴리즈 v1.0.0-rc.1", 부하/보안/실기기 표 구체 수치 전부 ✅, "결론: ✅ 배포 가능" — §1은 플레이스홀더({count} 등) 미치환인데 §3.2 이하는 구체값 혼재 | v1.0.0-rc.1 릴리즈·staging/production 환경·해당 테스트 실행 이력이 어느 레포에도 없음(코드 기준 MD1~MD3 진행 중) | claims T6a §13, `git show origin/develop:13_테스트_보고서.md` L12·L169 | P0 |
| M-4 | devpath-lcs-svc/README.md | 제목·본문이 "devpath-svc-template"(공통 스켈레톤 템플릿) 그대로 — LCS 서비스 서술 전무 | 레포는 LCS 6개 엔드포인트 구현 완료(LcsController), CLAUDE.md는 LCS 전용으로 갱신됨 | facts-backend §lcs-svc 주의, `git -C devpath-lcs-svc show origin/develop:README.md` L1 | P0 |
| M-5 | documents/09_Git_규칙_정의서.md §1.1 | "GitHub Flow 기반. develop 브랜치는 사용하지 않음. 모든 작업 브랜치는 main에서 분기·머지", "Squash Merge 기본, Merge Commit 금지" | 전 서비스 레포가 develop 통합 브랜치 운용(baseline 표: 13개 레포 중 15개 origin/develop 보유), 실제 머지는 merge commit(documents 099d333 "Merge pull request #55" 등), 17번도 "develop 경유" 명시 | baseline §1, `git show origin/develop:09_Git_규칙_정의서.md` L24, `git -C documents log --oneline origin/develop -3` | P0 |
| M-6 | devpath-ai-svc/README.md·CLAUDE.md | "현재 구현 상태(2026-06-19)... 현재 구현 API는 /ai/embed·/ai/path/generate", "현재 구현 패키지: ai.devpath.aigw.ollama", "review-worker(목표)·finops(목표)" | 실제 6개 엔드포인트: /ai-mentor/sessions(MentorController)·/reviews 3종(ReviewController) 추가 구현, mentor·review·community 패키지 존재, 테스트 44파일 | facts-backend §ai-svc 및 주의 | P0 |
| M-7 | documents/04_API_명세서.md | 검증 기준을 36번(6-19 스냅샷)으로 지정, "알림" 5개 엔드포인트 소유를 platform-svc(notification)로 표기 | 36번은 6-19 시점 스냅샷으로 현재와 불일치(하단 M-8), 알림 모듈은 2026-07-01 notification-svc로 이관·현재 구현은 디바이스 2종뿐(GET /notifications/me 미구현), gateway /notifications/**→8088 | facts-backend §notification-svc, facts-infra §gateway | P1 |
| M-8 | documents/36_현재_구현_..._점검.md | "community-svc·sandbox-svc 컨트롤러 없음", shared 마이그레이션 목록이 진단까지 | community 10·sandbox 3 엔드포인트 구현, 마이그레이션 24파일 — 문서는 6-19 시점 스냅샷인데 04·07번이 "현재 기준"으로 참조 | facts-backend, facts-infra §shared | P1 |
| M-9 | documents/03_프로젝트_아키텍처_정의서.md | 폴리레포 구조를 9개 레포(shared~gitops)로 명시 | 실제 서비스 레포 13개: lcs-svc·notification-svc·landing-page·svc-template 미기재 | baseline §1, claims T6a §03 | P1 |
| M-10 | documents/02_ERD_문서.md | "user_reputation_events" 테이블 | 실제 테이블명 reputation_events (V202606301001__reputation.sql: reputation_events, user_reputation, user_tag_reputation) | facts-infra §shared 마이그레이션 표 | P1 |
| M-11 | documents/20_커뮤니티_기능_설계서.md 배너 | "현재 devpath-community-svc는 스켈레톤 상태" | community-svc 10개 엔드포인트 + reputation·badge·abuse 모듈 구현, 테스트 22파일 | facts-backend §community-svc | P1 |
| M-12 | documents/26_학습맥락_자동첨부_구현.md 배너·본문 | "현재 LCS 스키마/API는 아직 미구현", API 경로 "/api/lcs/..." | lcs-svc 6개 엔드포인트 구현(경로 prefix는 "/lcs/...", "/api" 없음), learning_context_snapshots·user_context_preferences 마이그레이션 존재. 단 sanitize_rules 테이블은 미구현(문서 주장 중 이 부분은 여전히 목표) | facts-backend §lcs-svc, facts-infra §shared | P1 |
| M-13 | documents/01_프로젝트_계획서.md | 상단 상태 배너 없음 — Claude API·Elasticsearch·24주 일정 등 목표 스택/일정을 현재형 서술 | dev AI는 Ollama(36·37·Home 표기와 상충), 일정은 17번이 MD1~MD4로 재정의 | claims T6a §01 (LABEL 행 부재), facts-backend §ai-svc | P1 |
| M-14 | documents/15_사용자_메뉴얼.md | 상단 상태 배너 없음 — 15문항 진단·4~6초 리뷰·월 한도 등 기능을 현재형 서술 (04/06/07/11/14/16/20은 배너 보유) | AI 리뷰·월 한도·freeze 토큰 등 다수 기능 미구현/부분 구현 | claims T6a §15 LABEL 행 | P1 |
| M-15 | devpath-community-svc/README.md·CLAUDE.md | 도메인 표에 moderation·learning-context 모듈 명시 | 실제 패키지: abuse/badge/config/outbox/post/reputation/seed — moderation·learning-context 부재, learning-context는 별도 devpath-lcs-svc로 분리 구현됨 | facts-backend §community-svc 주의 | P1 |
| M-16 | devpath-sandbox-svc/README.md | 도메인 표에 submission(과제 제출 접수→실행→결과 회수) 모듈 명시 | 실제 패키지는 run만 존재(RunController·InternalSessionController) | facts-backend §sandbox-svc 주의 | P1 |
| M-17 | devpath-notification-svc/README.md | "참여 촉진 배치(스트릭·주간 리포트·정체 탐지·선호 시간대 리마인더)" 담당 서술 | 실제 패키지는 device·inbox뿐, 배치 모듈 부재(참여촉진 Build 2 이후 예정) | facts-backend §notification-svc 주의 | P1 |
| M-18 | devpath-frontend/HANDOFF.md | "다음은 P6(mobile)"(2026-06-16) — mobile 미착수 서술 | origin/develop에 mobile 라우트 8개·테스트 구현 존재 | facts-frontend §frontend-4 | P1 |
| M-19 | devpath-learning-svc/README.md | 담당 도메인 표에 "mentor(AI 멘토 채팅)" | learning-svc에 mentor 패키지 없음, CLAUDE.md 스스로 "ai-svc 소관(M-9 잔재)" 명시, MentorController는 ai-svc에 존재 | facts-backend §learning-svc 주의 | P1 |
| M-20 | documents/25_문서_정합성_점검_보고서.md | C1: "community-svc가 learning-context·ai-seed 명시"를 정합 근거로 사용 등 6-13 시점 판단 | learning-context는 lcs-svc로 분리, community README의 해당 표기는 현재 불일치(M-15) — 문서 전체가 시점 스냅샷 | facts-backend §community-svc·§lcs-svc | P1 |
| M-21 | .github/profile/README.md | (38번 P0-5 승계) 텍스트는 갱신 확인, 조직 프로필 실제 렌더링 미검증 | regression-check ⚠️ 판정 | regression-check P0-5 | P1 |
| M-22 | documents/05_화면_흐름_시퀀스_다이어그램.md | "시퀀스 A: Q&A 작성 → AI 시드 → 에스컬레이션(LCS Worker)" — LCS를 community 내 워커로 표기 | LCS는 별도 devpath-lcs-svc(8087, gateway /lcs/**)로 구현 | facts-infra §gateway, facts-backend §lcs-svc | P2 |
| M-23 | documents/23_PIA·33_개인정보_처리방침 | Anthropic(Claude API) 위탁·국외이전을 현재형 표기 | 백엔드 dev는 Ollama(위탁 없음)이나, **devpath-landing-page functions는 실 LLM 호출(callClaude) 가동 중** — 위탁 표기의 대상·시점 구분 필요 | facts-frontend §landing-page-1, facts-backend §ai-svc | P2 |
| M-24 | templates/README.md | "구성 (예정)" 표로 docs/·github/·config/ 디렉터리 소개 | 레포에 CLAUDE.md·README.md 외 파일 없음(빈 셸) — "예정" 라벨은 있으나 생성 계획 부재 상태 지속 | facts-aux §templates | P2 |

## 2. 회귀 항목 (38번 미이행·부분 — regression-check에서 승계)

| # | 38번 항목 | 현재 상태 | 처리 후보 |
|---|---|---|---|
| R-1 | P0-5 (.github/profile/README.md) | ⚠️ 부분 — 텍스트 갱신 확인, 웹 렌더링 미검증 | M-21로 통합(P1) |
| R-2 | P2-1~P2-4 (workflow-guide 정적 문서) | ➖ 대상 소멸 — 레포가 documents 원본 복사 빌드 구조로 재설계, 원본 문서(09/10/11/16) 정합 확인됨 | 조치 불필요(종결) |

## 3. 관찰 사항 (코드 측 — 43번 수정계획에 넣지 않음)

| # | 레포 | 관찰 내용 | 근거 |
|---|---|---|---|
| O-1 | workflow-dashboard | scripts/parse-prd.mjs REPO_FR_PREFIXES·parse-workflow.mjs trackAliasMap·skills 예시가 synapse-* 접두인데 data/config.json 실제 id는 전부 devpath-* — PRD 파싱 경로 사용 시 매칭 실패 가능 | facts-aux §workflow-dashboard-2 |
| O-2 | devpath-gateway / devpath-notification-svc | gateway가 /notifications/**를 8088로 라우팅하나 notification-svc HTTP API는 /notifications/devices 2종뿐(인박스 조회 API 부재) — 선행 라우트 상태 | facts-infra §gateway, facts-backend §notification-svc |
| O-3 | devpath-frontend | 기본 실행이 USE_MOCK=true(mock.devpath.ai) — 설계 의도로 문서화되어 있으나 "구현 완료" 서술 소비 시 목 기반임을 유의 | facts-frontend §frontend-3 |
| O-4 | devpath-landing-page | Cloudflare Functions에서 실 LLM(callClaude) 호출 + Turnstile/레이트리밋/예산 체크 가동 — 개인정보 문서(23·33)와의 연결은 M-23에서 문서 측 처리 | facts-frontend §landing-page-1 |

## 4. 검증 기록

- 모든 M 항목의 근거는 좌변(claims)·우변(facts) 보고서 표의 원문 인용 또는 컨트롤러가 직접 실행한 git 명령이다.
- 컨트롤러 재검증(무작위 3건 이상): M-2(02_ERD L6 배너 원문 재확인), M-4(lcs README L1 제목 재확인), M-5(09번 L24 규범 본문 여부 — 표·본문 맥락까지 확인), M-3(13번 L12·L169 재확인). 전부 재현됨.
