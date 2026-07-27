# 정합성 점검 2차 — documents 문서 주장 추출 (01~41 + README/Home)

> 수집일: 2026-07-02 / 기준: documents origin/develop(099d333)
> 수집: 읽기 전용 조사 에이전트 2분할(01~20 / 21~41+색인) / 섹션 수 20+23=43 확인
> 컨트롤러 표본 검증 통과 — 04_API 명세서 "api.devpath.ai" 인용 실존, 27_MVP "2026-04-23 멘토링 초안" 배너 인용 실존

# T6a — 01~20 문서 검증 가능한 주장 추출

> 기준: `origin/develop` (SHA 099d33394a1037cc8d9a853c7762298bee46841a)
> 방법: `git -C /d/workspace/dpa/documents show origin/develop:<파일명>` (워킹트리 미사용)
> 산출 원칙: 요약·평가·제안 없이 원문 인용 + 유형 + 검증 대상 레포만 기재

---

## 01_프로젝트_계획서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "기술 스택: Spring Boot 4 + Flutter 3.x(웹·모바일) + Claude API + pgvector + Docker Sandbox" | STACK | devpath-platform-svc / devpath-frontend / devpath-ai-svc / devpath-sandbox-svc |
| "Backend | Spring Boot 4 (GA 미확정 시 3.4.x 폴백), Java 21+, Spring Data JPA + QueryDSL, Spring Security 7 (OAuth2)" | STACK | devpath-platform-svc 등 각 서비스 build.gradle |
| "DB | PostgreSQL 17 (Source of Truth), Redis 7.x, pgvector (콘텐츠·GitHub 임베딩), Elasticsearch (BM25)" | STACK | devpath-shared/docker-compose.yml, 각 서비스 설정 |
| "메시징 | Kafka, Debezium (Outbox CDC)" | STACK | devpath-shared, 각 서비스 outbox 구현 |
| "LLM / AI | Claude API (Sonnet 4.6 주력, Haiku 4.5 경량), text-embedding-3-small" | STACK | devpath-ai-svc |
| "Sandbox | Docker + gVisor 샌드박스, 컨테이너 풀링" | STACK | devpath-sandbox-svc |
| "Frontend Web | Flutter Web (Dart), Riverpod 3, go_router, dio, Material 3(dp_design), Monaco Editor(Sandbox)" | STACK | devpath-frontend |
| "Mobile | Flutter 3.x + Riverpod, drift (로컬 캐시)" | STACK | devpath-frontend (apps/mobile) |
| "인프라 | Docker Compose, GitHub Actions, Prometheus + Grafana, Zipkin (OTel)" | STACK | devpath-gitops, .github/workflows |
| "개발 일정 (총 24주)" 표 — Phase 1~6, M1~M6 마일스톤 | STATUS | 전체 레포 (일정/마일스톤 주장, 17_스케줄.md과 상충 여부 확인 필요) |
| "팀 구성(예시)" — PM 1, Backend Lead 1, Backend Dev 3 등 인원 표 | STATUS | 해당 없음(조직 정보, 검증 대상 아님이나 문서상 명시) |

---

## 02_ERD_문서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 Flyway 구현 완료 범위는 사용자·인증·outbox·notifications·온보딩 진단까지" | STATUS | devpath-shared (Flyway migration 파일) |
| "users | id(PK), email(UK), nickname, role(LEARNER/ADMIN), status, onboarding_status(...), created_at" | SCHEMA | devpath-shared (Flyway) |
| "user_oauth_identities | user_id(FK), provider(GITHUB/GOOGLE/KAKAO), provider_user_id, access_token_encrypted, refresh_token_encrypted, scope, linked_at" | SCHEMA | devpath-shared |
| "user_profiles | user_id(FK), avatar, bio, learning_goal(...), target_track(...), experience_years" | SCHEMA | devpath-shared |
| "user_learning_prefs | user_id(FK), weekly_hours, preferred_time_slot(JSON), reminder_enabled, locale" | SCHEMA | devpath-shared |
| "OAuth 토큰은 AES-256-GCM 암호화 저장 (환경 변수 KMS 키)" | STATUS | devpath-platform-svc |
| "github_profiles | user_id(FK, PK), login, public_repos_count, followers, total_commits_last_year, fetched_at, fetch_status(...)" | SCHEMA | devpath-shared / devpath-platform-svc |
| "github_repositories | id, user_id(FK), repo_full_name, primary_language, stars, last_pushed_at, topic_tags(JSON)" | SCHEMA | devpath-shared |
| "github_language_stats | user_id(FK), language, bytes, proportion" | SCHEMA | devpath-shared |
| "assessments | id(PK), user_id(FK), track, status(...), started_at, completed_at, current_difficulty(FLOAT 0.0~1.0), bloom_distribution(JSON)" | SCHEMA | devpath-shared / devpath-learning-svc |
| "assessment_items | id(PK), question_bank_id(FK), assessment_id(FK), order_num, presented_at, answered_at, answer(JSON), is_correct, time_spent_sec" | SCHEMA | devpath-shared |
| "question_bank | id(PK), track, question_type(...), content(TEXT), options(JSON), answer_key(JSON), bloom_level(...), difficulty(FLOAT), concept_tags(JSON)" | SCHEMA | devpath-shared |
| "assessment_results | assessment_id(FK, PK), diagnosed_level(...), concept_scores(JSON), strength_concepts(JSON), weakness_concepts(JSON), confidence_weight(FLOAT)" | SCHEMA | devpath-shared |
| "적응형 알고리즘: 정답 시 난이도 +0.1, 오답 시 -0.05" | STATUS | devpath-learning-svc |
| "learning_paths | id(PK), user_id(FK), generated_at, track, total_weeks(default 12), claude_prompt_version, source_embedding_version, status(...), ai_rationale(TEXT)" | SCHEMA | devpath-shared / devpath-learning-svc |
| "path_milestones | id, path_id(FK), week_num, title, goal_description, target_skills(JSON), estimated_hours, why_this_order(TEXT)" | SCHEMA | devpath-shared |
| "path_weekly_tasks | id, milestone_id(FK), order_num, content_id(FK), task_type(...), required(BOOL), completed_at" | SCHEMA | devpath-shared |
| "생성 플로우: ... AI Gateway(개발: Ollama, 운영: Claude 등 provider 교체 가능) → JSON roadmap → pgvector로 콘텐츠 매칭" | STACK | devpath-ai-svc |
| "contents | id(PK), slug(UK), title, track, content_md(TEXT), estimated_minutes, difficulty(FLOAT), bloom_level(ENUM), concept_tags(JSON), status(...), author_id, published_at" | SCHEMA | devpath-shared / devpath-learning-svc |
| "content_code_blocks | id(PK), content_id(FK), order_num, language, starter_code(TEXT), test_cases(JSON), is_sandbox_runnable(BOOL)" | SCHEMA | devpath-shared |
| "content_embeddings | id(PK), content_id(FK), chunk_index, chunk_text(TEXT), embedding VECTOR(768), chunk_hash(SHA-256), metadata(JSONB), status(...)" | SCHEMA | devpath-shared |
| "HNSW on embedding WHERE status = 'ACTIVE'" | SCHEMA | devpath-shared (Flyway 인덱스) |
| "sandbox_sessions | id(PK), user_id(FK), content_id(FK), code_block_id(FK), container_id(VARCHAR), status(...), ... cpu_ms_used, memory_mb_peak" | SCHEMA | devpath-shared / devpath-sandbox-svc |
| "sandbox_test_results | sandbox_session_id(FK), test_name, passed(BOOL), expected(TEXT), actual(TEXT), duration_ms" | SCHEMA | devpath-shared |
| "sandbox_quotas | user_id(FK, PK), daily_run_count, daily_run_limit, monthly_run_count, last_reset_at" | SCHEMA | devpath-shared |
| "ai_code_reviews | id(PK), sandbox_session_id(FK), model_used, prompt_version, review_summary(TEXT), ... cost_usd, reviewed_at" | SCHEMA | devpath-shared / devpath-ai-svc |
| "ai_mentor_sessions | id(PK), user_id(FK), context_snapshot(JSON), title, created_at" | SCHEMA | devpath-shared |
| "ai_mentor_messages | id, session_id(FK), role(...), content(TEXT), token_used, references(JSON), feedback(...), created_at" | SCHEMA | devpath-shared |
| "community_posts | id(PK), author_id(FK), board_type(...), title, body_md(TEXT), body_html(TEXT), status(...), view_count, upvote_count, downvote_count, created_at" | SCHEMA | devpath-shared / devpath-community-svc |
| "community_questions | post_id(FK, PK...), is_solved, accepted_answer_id(...), bounty_amount, bounty_expires_at, learning_context(JSONB)" | SCHEMA | devpath-shared |
| "community_answers | id(PK), question_id(FK), author_id(FK), body_md, body_html, is_ai_generated(BOOL), is_accepted(BOOL), upvote_count, created_at" | SCHEMA | devpath-shared |
| "community_comments | id, parent_type(...), parent_id, author_id(FK), body(TEXT), created_at" | SCHEMA | devpath-shared |
| "community_votes | ... UNIQUE(user_id, target_type, target_id)" | SCHEMA | devpath-shared |
| "community_bookmarks | user_id(FK), target_type, target_id, folder_id(FK nullable), created_at" | SCHEMA | devpath-shared |
| "community_follows | follower_id(FK), target_type(...), target_id, created_at" | SCHEMA | devpath-shared |
| "community_tags | id(PK), name(UK), description, wiki_md, post_count, watcher_count" | SCHEMA | devpath-shared |
| "community_post_tags | post_id(FK), tag_id(FK) — UNIQUE 페어" | SCHEMA | devpath-shared |
| "user_tag_reputation | user_id(FK), tag_id(FK), reputation(INT) — UNIQUE 페어" | SCHEMA | devpath-shared / devpath-community-svc |
| "user_reputation_events | id, user_id(FK), action(...), points(INT), source_id, created_at" | SCHEMA | devpath-shared |
| "badges | id(PK), code(UK), name, tier(BRONZE/SILVER/GOLD), criteria(JSONB)" | SCHEMA | devpath-shared |
| "user_badges | user_id(FK), badge_id(FK), awarded_at — UNIQUE 페어" | SCHEMA | devpath-shared |
| "평판 남용 방지 — 일일 합산 +40 상한 (하루 가산 한도)" | STATUS | devpath-community-svc |
| "7일 신규 계정은 투표 제한 (users.created_at 기준 트리거)" | STATUS | devpath-community-svc |
| "community_reports | id, reporter_id(FK), target_type, target_id, category(...), reason, status(...), reviewed_by(...), created_at" | SCHEMA | devpath-shared |
| "moderation_queue | id, target_type, target_id, ai_severity(...), ai_reason(JSON), trust_votes(INT), created_at" | SCHEMA | devpath-shared |
| "user_sanctions | user_id(FK), sanction_type(...), reason, starts_at, ends_at, issued_by" | SCHEMA | devpath-shared |
| "CREATE TABLE learning_context_snapshots (...)" SQL 정의 전문 | SCHEMA | devpath-shared / devpath-community-svc |
| "community_ai_answers | question_id(FK, PK), model_used, prompt_version, content(TEXT), references(JSONB), generated_at, usefulness_rating_sum, rating_count" | SCHEMA | devpath-shared |
| "ALTER TABLE community_ai_answers ADD COLUMN escalation_status VARCHAR(20) DEFAULT 'NONE'" | SCHEMA | devpath-shared |
| "study_groups | post_id(FK, PK), subject, max_members, ..." (Phase 2 확장) | SCHEMA | devpath-shared |
| "study_applications | group_id(FK), user_id(FK), status(...), applied_at" | SCHEMA | devpath-shared |
| "project_showcases | post_id(FK, PK), github_url, demo_url, stack_tags(JSON), ..." | SCHEMA | devpath-shared |
| "커뮤니티 인덱스" 표 9개 항목 (예: community_posts (board_type, status, created_at DESC) 등) | SCHEMA | devpath-shared |
| "이벤트(Outbox)" 표 — CommunityPostCreatedEvent 등 8종 | API | devpath-community-svc / 각 Consumer 서비스 |
| "progress_events | id, user_id(FK), event_type(...), ref_id, xp_awarded, occurred_at (monthly partition)" | SCHEMA | devpath-shared |
| "user_streaks | user_id(FK, PK), current_streak_days, longest_streak_days, last_active_date, freeze_tokens" | SCHEMA | devpath-shared |
| "user_usage | user_id(FK), period_start, mentor_questions_used, sandbox_runs_used" | SCHEMA | devpath-shared |
| "announcements | id(PK), title, body_md(TEXT), display_type(...), target_audience(...), ..." | SCHEMA | devpath-shared |
| "admin_audit_logs | id, admin_user_id(FK), action(...), target_type, target_id, details(JSON), ip_address, created_at" | SCHEMA | devpath-shared |
| "golden_test_runs | id(PK), prompt_version, total_cases, passed, failed, accuracy(DECIMAL), triggered_by(FK), started_at, completed_at" | SCHEMA | devpath-shared |
| "sandbox_abuse_logs | id, user_id(FK), session_id(FK), abuse_type(...), details(JSON), ip_address, auto_banned(BOOL), created_at" | SCHEMA | devpath-shared |
| "outbox_events | id, aggregate_type, aggregate_id, event_type, dedup_key(UNIQUE), destination_topic, payload(JSON), status(...), retry_count, max_retries(default 5)" | SCHEMA | devpath-shared |
| "audit_logs | user_id, action, entity_type, entity_id, before_value(JSON), after_value(JSON), ip_address, created_at" | SCHEMA | devpath-shared |
| "ai_cost_logs | user_id, service(...), model, input_tokens, output_tokens, cost_usd, cache_hit(BOOL), request_id" | SCHEMA | devpath-shared |
| "주요 이벤트(Outbox)" 표 — UserRegisteredEvent 등 8종 | API | 각 서비스 |
| "물리 인덱스 전략 요약" 표 12개 항목 | SCHEMA | devpath-shared |

---

## 03_프로젝트_아키텍처_정의서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "스타일: 폴리레포 마이크로서비스(distributed modular monolith)" | STATUS | 전체 레포 구조 (org 레포 목록) |
| "DevPathAi/ (폴리레포)" 하위 devpath-shared, devpath-gateway, devpath-platform-svc, devpath-learning-svc, devpath-community-svc, devpath-ai-svc, devpath-sandbox-svc, devpath-frontend, devpath-gitops 9개 서비스 구조 | STATUS | 각 레포 존재 여부 |
| "devpath-shared는 GitHub Packages(Maven)로 배포되어 각 서비스가 의존한다" | STATUS | devpath-shared, 각 서비스 build.gradle |
| "API Gateway | Spring Cloud Gateway + JWT, OTel Sampling 10~30%" | STACK/API | devpath-gateway |
| "AI Gateway 단일 진입점 ... 현재 개발 빌드는 Ollama gateway(/ai/embed, /ai/path/generate)" | API/STATUS | devpath-ai-svc |
| "Learning Path Engine ... SLO: 생성 p95 < 8초" | STATUS | devpath-learning-svc |
| "AI Gateway 내부 구조 — Semantic Cache(Redis, TTL 7일), FinOps Kill-switch(3계층), Circuit Breaker(Resilience4j)" | STATUS | devpath-ai-svc |
| "Sandbox Runner 제출 플로우 — 언어별: java21-jdk, node20, python3.12" | STATUS | devpath-sandbox-svc |
| "OAuth2 & 인증 흐름 — JWT 발급(access 30min + refresh 14day)" | API | devpath-platform-svc |
| "토큰 저장: access는 메모리, refresh는 httpOnly Secure Cookie" | STATUS | devpath-frontend / devpath-platform-svc |
| "Transactional Outbox Pattern — Relay: Phase 1 Polling+ShedLock(30s), Phase 2 Debezium CDC" | STATUS | devpath-shared / 각 서비스 |
| "주요 이벤트 흐름" 표 14개 이벤트 | API | 각 서비스 |
| "Distributed Tracing(OTel) — Sampling: dev 100% / staging 50% / prod 10~30%" | STATUS | devpath-gitops / 각 서비스 |
| "데이터 스토어 전략" 표 — PostgreSQL 17, pgvector, Redis 7.x, Elasticsearch 8.x, Kafka, S3/CDN | STACK | devpath-shared/docker-compose.yml |
| "보안 아키텍처(6 Layer)" | STATUS | 전체 레포 |
| "OAuth 토큰 보호 — 저장: AES-256-GCM 암호화, KMS에서 키 회전" | STATUS | devpath-platform-svc |
| "기술 결정 기록(ADR) 001~013" 표 전체 | STATUS | 각 서비스 (Spring Boot 4/3.4.x, gVisor, Monaco, 폴리레포 등) |
| "009 폴리레포 채택 (2026-06-13 번복)" | STATUS | 레포 구조 이력 |
| "성능 SLO" 표 — API p95 < 500ms(AI 제외)/2.5s(AI 포함), Learning Path p95 < 8s, AI 코드 리뷰 p95 < 6s, Sandbox 할당 p95 < 2s, 실행 완료 p99 < 30s, 5xx < 0.1% | STATUS | 전체 레포 (성능 측정 결과) |

---

## 04_API_명세서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "Base URL: https://api.devpath.ai/api/v1" | API | devpath-gateway |
| "현재 로컬 구현 완료 범위는 [36_...]을 기준으로 확인한다" (문서 성격 배너) | STATUS | 전체 레포 |
| "인증(OAuth2)" 표 10개 엔드포인트 (GET /oauth2/authorization/{provider}, POST /auth/refresh, GET /users/me, DELETE /users/me 등) | API | devpath-platform-svc |
| "GET /users/me/github-profile", "POST /users/me/github-profile/refresh" | API | devpath-platform-svc |
| "온보딩·진단" 표 8개 엔드포인트 (POST /onboarding/profile, POST /onboarding/assessments, GET .../next, POST .../answer, POST .../complete, GET .../result, POST /onboarding/assessments/guest, POST /onboarding/assessments/claim) | API | devpath-learning-svc |
| "학습 경로" 표 5개 엔드포인트 (POST /learning-paths/me/generate 등, SSE) | API | devpath-learning-svc |
| "콘텐츠" 표 4개 엔드포인트 (GET /contents/{slug} 등) | API | devpath-learning-svc |
| "Sandbox Runner" 표 5개 엔드포인트 (POST /sandbox/sessions 등) | API | devpath-sandbox-svc |
| "Rate Limit — 무료: 일 10회/월 100회, Pro: 일 50회/월 무제한" | STATUS | devpath-sandbox-svc |
| "AI 코드 리뷰" 표 2개 엔드포인트 (GET /ai-reviews/sandbox/{id}, POST /ai-reviews/{id}/feedback) | API | devpath-ai-svc |
| "AI 멘토" 표 5개 엔드포인트 (POST /ai-mentor/sessions 등, SSE) | API | devpath-ai-svc / devpath-learning-svc |
| "커뮤니티" 8.1~8.7 다수 엔드포인트 (GET /community/posts, POST /community/questions, POST /community/questions/{id}/bounty 등) | API | devpath-community-svc |
| "에스컬레이션 — POST /community/questions/{id}/escalate" | API | devpath-community-svc |
| "알림" 표 5개 엔드포인트 (GET /notifications/me 등) | API | devpath-platform-svc (notification) |
| "대시보드·진척도" 표 4개 엔드포인트 (GET /dashboard/me 등) | API | devpath-learning-svc |
| "Admin" 10.1~10.8 다수 엔드포인트 (콘텐츠/사용자/운영대시보드/FinOps/AI품질/신고/진단문항/Sandbox·공지 관리) | API | 각 서비스 admin 컨트롤러 |
| "Rate Limit·사용량 한도" 표 — OAuth 콜백 10 req/min, 일반 API 300 req/min, Path 생성 3 req/hour, AI 멘토 20/month, Sandbox 10/day·100/month | STATUS | 각 서비스 rate limit 설정 |

---

## 05_화면_흐름_시퀀스_다이어그램.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "비회원 진단 체험 → 가입 → 1st Aha" 시퀀스 — POST /onboarding/assessments/guest, /oauth2/authorization/github, POST /learning-paths/me/generate | API | devpath-learning-svc / devpath-platform-svc |
| "Sandbox 실습 → AI 코드 리뷰(2nd Aha)" 시퀀스 — POST /sandbox/sessions, SandboxRunSubmittedEvent, AiReviewCompletedEvent | API | devpath-sandbox-svc / devpath-ai-svc |
| "AI 멘토 채팅" 시퀀스 — POST /ai-mentor/sessions, context_snapshot 조립 | API | devpath-ai-svc |
| "커뮤니티 피어 매칭" 시퀀스 — GET /community/peers/this-week | API | devpath-community-svc |
| "리텐션 트리거(3일 미접속)" 시퀀스 — Scheduler(Quartz) 매일 09:00, StreakBreakingSoonEvent | STATUS | devpath-learning-svc / devpath-platform-svc |
| "OAuth2 + GitHub 프로필 수집(상세)" 시퀀스 — UserRegisteredEvent, GithubProfileFetchedEvent | API | devpath-platform-svc |
| "시퀀스 A: Q&A 작성 → AI 시드 → 에스컬레이션" (LCS Worker, AI Seed Worker) | API | devpath-community-svc / devpath-ai-svc |
| "시퀀스 B: 평판 변동 + 권한 언락" (VoteService, ReputationWorker, BadgeWorker) | API | devpath-community-svc |
| "시퀀스 C: 3단계 모더레이션" (ModerationSvc, AI Moderation, RuleFilter) | API | devpath-community-svc |

---

## 06_화면_기능_정의서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 구현은 web/admin 목 API 골든패스와 일부 MD1 백엔드까지" (문서 성격 배너) | STATUS | devpath-frontend |
| "화면 인벤토리" 표 — SCR-W-LAND-001 ~ SCR-M-DEEP-001 다수 화면 ID, MVP 여부(✔/Phase 2/Should) | STATUS | devpath-frontend (apps/web, apps/admin, apps/mobile) |
| "SCR-A-COM-001 커뮤니티 모더레이션 큐 ... (신뢰 사용자 큐는 Phase 2)" | STATUS | devpath-frontend / devpath-community-svc |
| "접근성(A11y) — WCAG 2.1 AA 준수, 키보드 네비게이션 전 화면, 스크린 리더 ARIA" | STATUS | devpath-frontend |

---

## 07_요구사항_정의서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 구현 완료 범위는 인증/사용자 일부, 온보딩 진단, 로컬 Ollama AI Gateway 일부" (문서 성격 배너) | STATUS | devpath-platform-svc / devpath-learning-svc / devpath-ai-svc |
| "FR-AUTH-001~006" 표 (GitHub/Google/카카오 OAuth2, JWT+Refresh, 계정삭제 14일 grace) | STATUS | devpath-platform-svc |
| "FR-GH-001~006" 표 (GitHub 프로필 수집 요구사항) | STATUS | devpath-platform-svc |
| "FR-ONB-001~009" 표 (온보딩·진단 요구사항, 15문항 적응형, 비회원 체험) | STATUS | devpath-learning-svc |
| "FR-PATH-001~008" 표 (AI 생성 12주 로드맵, pgvector 매칭, SSE) | STATUS | devpath-learning-svc / devpath-ai-svc |
| "FR-CNT-001~006" 표 (Markdown 렌더, Sandbox 연동, 검색) | STATUS | devpath-learning-svc |
| "~~FR-CNT-003~~ AR 배지 (v2.0 — 현재 비활성)" | STATUS | devpath-shared (스키마 비활성 여부) |
| "FR-SBX-001~010" 표 (Monaco, gVisor, 리소스 제한, 테스트 러너) | STATUS | devpath-sandbox-svc |
| "FR-REV-001~006" 표 (Claude Sonnet 리뷰, 3분류, 심각도 태깅) | STATUS | devpath-ai-svc |
| "FR-MEN-001~005" 표 (자연어 Q&A SSE, 컨텍스트 자동 주입) | STATUS | devpath-ai-svc |
| "FR-COM-001~054" 다수 (Q&A/자유/프로젝트/스터디/수료자, 학습맥락, AI시드, 평판, 모더레이션 등) | STATUS | devpath-community-svc |
| "FR-PRO-001~005" 표 (스트릭, 주간 진행률, 리텐션 트리거) | STATUS | devpath-learning-svc |
| "FR-ADM-001~022" 표 (콘텐츠 CRUD, FinOps, Kill-switch, 사용자관리, 운영대시보드 등) | STATUS | 각 서비스 admin |
| "NFR-AHA-001~004" (가입→1st Aha p50 ≤8분, p95 ≤12분, 도달률 ≥70%, 2nd Aha D0 ≥40%) | STATUS | 전체 레포 (측정치 주장) |
| "NFR-PERF-001~006" (API p95, Sandbox 등 성능 목표) | STATUS | 전체 레포 |
| "NFR-AVAIL-001~005" (가동률 99.5%, RTO<1h, RPO<15min) | STATUS | devpath-gitops |
| "NFR-SEC-001~007" (OAuth 암호화, JWT 만료, Sandbox 격리 등) | STATUS | devpath-platform-svc / devpath-sandbox-svc |
| "NFR-COMP-001~004" (한국 PIPA 준수, GitHub 토큰 동의, 14일 삭제, AI 생성 결과 명시) | STATUS | devpath-platform-svc |
| "NFR-SCALE-001~004" (수평 확장, Sandbox HPA, Kafka 파티션, DB Read Replica) | STATUS | devpath-gitops |
| "NFR-OBS-001~005" (Prometheus+Grafana, OTel Zipkin) | STATUS | devpath-gitops |
| "NFR-MAINT-001~004" (도메인 커버리지 ≥80%, OpenAPI 자동생성, Flyway, Feature Flag) | STATUS | 각 서비스 |
| "추적성 매트릭스" — FR ID ↔ 화면 ↔ API ↔ 테스트 매핑 전체 표 | STATUS/API | 전체 레포 |

---

## 08_스토리_보드.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "배포 순서(스토리 맵)" 표 — M1 가입 플로우(Week 4), M2 1st Aha(Week 8), M3 학습 실행(Week 12), M4 모바일·커뮤니티 확장(Week 16), M5 습관화(Week 17-20), M6 v1.0 출시(Week 24) | STATUS | 전체 레포 (마일스톤/일정 주장, 17_스케줄.md과 상충 여부) |
| "Story L4.9 Founding Contributor ... Go/No-Go: 30명 이상 GO, 10명 미만 NO-GO" | STATUS | 해당 없음(운영 계획, 커뮤니티 프로그램 진행 여부는 devpath-community-svc 외부) |

---

## 09_Git_규칙_정의서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "저장소: Public-Project-Area-Oragans/devpath-ai (예시)" | STATUS | GitHub org/레포 목록 |
| "기본 브랜치: main" / "개발 흐름: GitHub Flow + Release 태그" | STATUS | 전체 레포 (각 레포의 default branch) |
| "브랜치 전략: GitHub Flow 기반. develop 브랜치는 사용하지 않음. 모든 작업 브랜치는 main에서 분기하고 main으로 머지한다." | STATUS | 전체 레포 (각 레포 브랜치 목록 — 17_스케줄.md "브랜치 전략(develop 경유)" 및 사용자 메모리 "svc-template에 develop 브랜치 신설"과 상충 여부 확인 대상) |
| "머지 정책 — Squash Merge 기본 ... Merge Commit 금지" | STATUS | 전체 레포 (PR 머지 이력) |
| "main 보호 — 직접 push 금지, 필수 상태 체크: build/test/lint/security/coverage/sonar, 리뷰 승인 2건" | STATUS | 전체 레포 (GitHub 브랜치 보호 규칙) |
| "커밋 훅 — husky+lint-staged, ktlint/Spotless, flutter analyze, detect-secrets, commitlint" | STACK | 전체 레포 (.husky, pre-commit 설정) |

---

## 10_환경_설정_템플릿.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 기준(2026-06-19): 로컬 인프라는 devpath-shared/docker-compose.yml의 PostgreSQL 17, pgvector, Redis, Kafka KRaft, Elasticsearch를 사용한다" | STATUS/STACK | devpath-shared |
| "postgres: image: postgres:17-alpine ... postgres-vector: image: pgvector/pgvector:pg17 ... redis:7-alpine ... kafka: apache/kafka:3.9.1 ... elasticsearch:8.19.4" | STACK | devpath-shared/docker-compose.yml |
| ".env.example" 템플릿 — OLLAMA_BASE_URL, ANTHROPIC_API_KEY, GITHUB/GOOGLE/KAKAO OAuth 변수, JWT_ACCESS_TTL_MIN=30, JWT_REFRESH_TTL_DAYS=14, SANDBOX_* 변수 | STACK | 각 서비스 .env.example |
| "application.yml — jpa.hibernate.ddl-auto: validate, flyway.enabled: true" | STATUS | 각 서비스 application.yml |
| "devpath.features: ai-mentor-context-injection: true, guest-assessment: true" | STATUS | devpath-ai-svc / devpath-learning-svc |
| "최초 셋업 명령 — cd devpath-platform-svc && ./gradlew bootRun, cd devpath-frontend && melos bootstrap" | STATUS | devpath-platform-svc / devpath-frontend |

---

## 11_테스트_전략서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 모든 테스트 계층이 구현·운영 중임을 의미하지 않으며" (문서 성격 배너) | STATUS | 전체 레포 |
| "테스트 피라미드 — E2E(5%) Playwright+Flutter integration_test, Integration(20%) Testcontainers+WireMock, Unit(75%) JUnit5+Flutter test" | STATUS | 전체 레포 |
| "커버리지 목표 — 도메인 Line≥85%/Branch≥80%, 애플리케이션 Line≥75%, 프런트엔드 Statements≥70%, Mobile≥65%" | STATUS | 전체 레포 (커버리지 리포트) |
| "CI 파이프라인(GitHub Actions) — unit/integration/e2e-smoke/security/quality-gate/ar-test(비활성)" | STATUS | .github/workflows (각 레포) |
| "골든 테스트 케이스 — 50개 기준, test/golden/ 디렉토리" | STATUS | devpath-ai-svc |

---

## 12_코드_리뷰_규칙.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "리뷰 지표(월간) — 1차 리뷰 응답 중앙값 <4시간, 머지까지 총 시간 중앙값 <24시간, PR 평균 크기 <400 라인, 머지 후 24h 롤백률 <2%" | STATUS | 전체 레포 (PR 이력/지표) |
| "PR 크기 기준 — <400줄 일반 리뷰(1인), 400~600줄 시니어 리뷰 필수(2인), >600줄 분할 필수" | STATUS | 전체 레포 (PR 운영 규칙 준수 여부) |
| "Kafka/Outbox 체크리스트 — dedupKey 구성: aggregateType:aggregateId:eventType:version" | SCHEMA | devpath-shared / 각 서비스 |

---

## 13_테스트_보고서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "릴리즈: v1.0.0-rc.1 / 대상 환경: staging / production" (문서 메타, §0) | STATUS | 전체 레포 (릴리즈 태그 존재 여부) |
| "총 테스트 건수: {count} / 통과·실패·스킵: {pass}/{fail}/{skip}" — 플레이스홀더 미치환 | STATUS | 해당 없음 (템플릿 미완성 자체가 검증 대상: §1, §3.1은 플레이스홀더인데 §3.2 이하는 구체값이 채워진 상태로 혼재) |
| "테스트 범위" 표 — OAuth2/GitHub/온보딩/학습경로/콘텐츠/Sandbox/AI리뷰/AI멘토/커뮤니티/진척 전부 ✅(단위/통합/E2E/부하/보안/AI품질) 체크 | STATUS | 전체 레포 (커뮤니티는 E2E/부하/보안 컬럼이 "—"로 비어 있어 다른 영역과 불일치) |
| "3.2 통합 테스트 — Path Engine Claude+pgvector 생성 p95 7.1s ✅" | STATUS | devpath-learning-svc |
| "3.4 모바일 실기기 회귀 — Pixel 6/Galaxy S22/A52/iPhone 15 Pro/11/SE 2 전부 ✅" | STATUS | devpath-frontend (apps/mobile) |
| "3.5 부하 테스트(k6) — 일반 API 1000 RPS p95 380ms, Path 생성 10동시 p95 7.4s 등 전부 ✅" | STATUS | 전체 레포 (부하테스트 실행 이력) |
| "3.6 보안 스캔 — Snyk/Trivy/OWASP ZAP/Sandbox pentest/SonarQube 결과 (Critical 0)" | STATUS | 전체 레포 (CI 보안 스캔 이력) |
| "3.7 AI 품질 — 코드 리뷰 👍 78%, 멘토 👍 72%, 컨텍스트 참조 정확성 93%" | STATUS | devpath-ai-svc |
| "5. 회귀 체크리스트 — 전부 [x] 체크 (Smoke/2 Aha 퍼널 72%/pentest/실기기/k6/Chaos/보안)" | STATUS | 전체 레포 |
| "8. 릴리즈 권고 — 결론: ✅ 배포 가능" | STATUS | 전체 레포 (실제 v1.0.0-rc.1 배포 여부) |
| "부록 A. 시그너처" — QA Lead/Tech Lead/PM 이름·날짜·서명 모두 공란("—") | STATUS | 해당 없음 (서명 미기재 자체가 문서 상태 증거) |

---

## 14_배포_가이드.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 운영 배포가 모두 완성되었음을 의미하지 않으며" (문서 성격 배너) | STATUS | 전체 레포 |
| "오케스트레이션: Kubernetes(EKS/GKE)+Helm / CI/CD: GitHub Actions+ArgoCD(선택)" | STACK | devpath-gitops |
| ".github/workflows/ci.yml, security.yml, ar-test.yml(비활성), deploy-staging.yml, deploy-prod.yml" | STATUS | 각 레포 .github/workflows |
| "charts/devpath-api, devpath-ai-gateway, devpath-sandbox-runner, devpath-ai-review-worker, devpath-web, devpath-admin" | STATUS | devpath-gitops (Helm charts 존재 여부) |
| "Feature Flag — ai-mentor-context-injection: 기본 On, ar-2d-fallback: (v2.0 비활성), guest-assessment: 기본 On, claude-haiku-mentor-routing" | STATUS | devpath-ai-svc / devpath-learning-svc |
| "DB 마이그레이션(Flyway) — 파일명 V{yyyyMMdd_seq}__{description}.sql, forward-only" | STATUS | devpath-shared |
| "비밀 관리 — K8s: External Secrets Operator+AWS Secrets Manager, CI: GitHub Actions OIDC" | STATUS | devpath-gitops |

---

## 15_사용자_메뉴얼.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| (문서 전체에 "문서 성격"/목표-현황 구분 배너 없음 — 04/06/07/11/14/16/20과 달리 현재형으로 기능을 설명) | LABEL | 전체 레포 (배너 없음. 04/06/07/11/14/16/20은 "v1 목표" 배너 보유, 15는 미보유) |
| "가입 없이 진단 테스트 15문항을 먼저 체험할 수 있습니다 (약 5분)" | STATUS | devpath-learning-svc |
| "제출 후 4~6초 내 결과" (AI 코드 리뷰) | STATUS | devpath-ai-svc |
| "제3자 PII: LLM 호출 시 자동 마스킹(이메일/주민번호/전화)" | STATUS | devpath-ai-svc |
| "월 한도(멘토 20/Sandbox 100) 초과 시 해당 기능만 다음 달까지 일시 중단" | STATUS | devpath-ai-svc / devpath-sandbox-svc |
| "긴급 상황 대비 월 1회 freeze 토큰(스트릭 깨지지 않음)" | STATUS | devpath-learning-svc |

---

## 16_운영_메뉴얼.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 운영 체계가 모두 가동 중임을 의미하지 않으며" (문서 성격 배너) | STATUS | 전체 레포 |
| "모니터링 스택 — Prometheus+Grafana, Loki(또는 ELK), OpenTelemetry+Zipkin, Alertmanager→Slack+PagerDuty, Micrometer" | STACK | devpath-gitops |
| "알람 규칙(발췌)" YAML — ApiP95High, FirstAhaRateDrop, SandboxPoolExhaustion 등 | STATUS | devpath-gitops (Prometheus 룰 파일) |
| "FinOps 운영 — Kill-switch 3계층(사용자별/이상패턴/전사)" | STATUS | devpath-ai-svc |
| "배치·스케줄러" 표 — GitHub 프로필 월간 리프레시, 스트릭 자정 체크, 주간 리포트, FinOps 집계, ShedLock 필수 | STATUS | devpath-platform-svc / devpath-learning-svc |
| "백업·복원 절차 — PostgreSQL RDS 자동 스냅샷 매일 03:00 KST 30일 보존" 등 표 | STATUS | devpath-gitops (인프라 설정) |

---

## 17_스케줄.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "총 기간(재정의): 모두의 창업 라운드 정렬(2026-06~12). 갱신일 2026-06-16." | STATUS | 해당 없음(일정 메타) |
| "0. 완료 기준선(DONE) — W1 인프라: MySQL→PostgreSQL(SSOT 5432+pgvector 5433), shared GitHub Packages(Maven), 중앙 Flyway 스키마" | STATUS | devpath-shared |
| "CI/CD: 9개 서비스 postgres service container CI + 이미지 빌드·push + gitops 배포 job + GitHub App 자동 SHA 갱신(node24 actions)" | STATUS | 각 서비스 .github/workflows, devpath-gitops |
| "React→Flutter 전환, melos 모노레포(dp_core·dp_design + apps/web·admin·mobile)" | STACK/STATUS | devpath-frontend |
| "목 API 기반 web 골든패스 전체(P4a~f) — 셸·인증/온보딩·경로 SSE/콘텐츠·Sandbox·Monaco/AI리뷰·KILL_SWITCH·Quota/멘토 SSE/대시보드·커뮤니티" | STATUS | devpath-frontend |
| "admin 대표 3화면(P5: 운영 대시보드·사용자 관리·신고 처리)" | STATUS | devpath-frontend (apps/admin) |
| "⚠️ web/admin은 목 API 중심 · 모바일(P6)·랜딩(P7) 미착수" | STATUS | devpath-frontend |
| "9개 서비스 W1 수준(PG 드라이버·shared 의존·DB 연결 테스트)" | STATUS | 9개 서비스 레포 전체 |
| "shared: users/auth/outbox/notifications + 진단(question_bank·assessments·items·results) Flyway" | SCHEMA | devpath-shared |
| "platform-svc: refresh/logout, /users/me, UserRegisteredEvent, AssessmentCompletedEvent 소비" | API | devpath-platform-svc |
| "learning-svc: 회원/비회원 진단, answer/complete/result, claim, AssessmentCompletedEvent" | API | devpath-learning-svc |
| "ai-svc: 로컬 Ollama gateway(/ai/embed, /ai/path/generate, 768차원 임베딩 계약)" | API/STACK | devpath-ai-svc |
| "학습경로 영속화·콘텐츠·Sandbox·AI 리뷰·멘토·커뮤니티 도메인 API 미구현" | STATUS | devpath-learning-svc / devpath-sandbox-svc / devpath-ai-svc / devpath-community-svc |
| "01~38 작성" (문서) | STATUS | devpath-ai/documents 레포 (본 레포) |
| "0.1 현재 구현 현황 스냅샷(2026-06-19)" 표 — 인증/사용자 부분구현, 진단 부분구현, AI Gateway dev Ollama gateway 구현, 학습경로·콘텐츠/Sandbox·AI리뷰/커뮤니티·LCS 목표 상태 | STATUS | 전체 서비스 레포 |
| "MD1 슬라이스#1 OAuth/인증 — [x] UserRegisteredEvent Outbox" (완료 체크) | STATUS | devpath-platform-svc |
| "MD1 슬라이스#2 진단 — [x] learning-svc: question_bank+Bloom 태깅 스키마, 적응형 진단 알고리즘 / [x] 비회원 진단 세션(Redis 30분)+결과→회원 이관" | STATUS/SCHEMA | devpath-learning-svc / devpath-shared |
| "MD1 슬라이스#3 학습경로 — ai-svc AI Gateway 경로 생성: dev Ollama 부분 구현, 운영 provider/SSE/Event 후속" | STATUS | devpath-ai-svc |
| "평판 기초 — 핵심 완료(2026-06-30~07-01, Build 1·2·3): 평판 엔진·태그평판·일일+40 상한(community-svc PR #13/shared #30)" | STATUS | devpath-community-svc PR #13, devpath-shared PR #30 |
| "Bronze 배지 9종 시드+6종 트리거+조회 API(PR #15/shared #31)" | STATUS/API | devpath-community-svc PR #15, devpath-shared PR #31 |
| "자기 글 투표 금지+행동 기반 담합 탐지(reputation_events 반복 upvote, 기록만)(PR #17/shared #32)" | STATUS | devpath-community-svc PR #17, devpath-shared PR #32 |
| "후속: 레벨 게이트 500/1000 미강제, Bronze 3종(FIRST_STEP·EDITOR·COMMUNITY) 시드만(프로필·편집·스트릭 기능 부재로 결선 대기), Silver/Gold 배지, IP·디바이스 기반 sockpuppet·신계정 7일 제한(platform-svc 신호 필요), moderation 자동 제재(suspicion 이벤트 소비자 미구현)" | STATUS | devpath-community-svc / devpath-platform-svc |
| "각 슬라이스... 브랜치 전략(develop 경유) 준수" | STATUS | 전체 서비스 레포 (브랜치 목록 — 09_Git_규칙_정의서.md "develop 브랜치는 사용하지 않음"과 상충 여부 확인 대상) |
| "셀프 체크 리듬: 슬라이스 완료 = 끝단간 통합테스트 통과 + develop PR 머지" | STATUS | 전체 서비스 레포 |
| "외부 의존성 타임라인" 표 — GitHub OAuth/카카오/Google/Anthropic/Apple/Google Play 일정 | STATUS | 해당 없음(외부 신청 상태, 코드 검증 대상 아님) |

---

## 18_온보딩_마이크로카피_가이드.md

검증 가능한 주장 없음 (마이크로카피/톤앤보이스 가이드 — 코드와 대조 가능한 STATUS/API/SCHEMA/STACK 주장 없음, 상단 상태 배너도 없음)

---

## 19_온보딩_와이어프레임_스펙.md

검증 가능한 주장 없음 (디자인 토큰·와이어프레임 픽셀 스펙 — 코드와 대조 가능한 STATUS/API/SCHEMA/STACK 주장 없음, 상단 상태 배너도 없음)

---

## 20_커뮤니티_기능_설계서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "현재 devpath-community-svc는 스켈레톤 상태이며, 본 문서는 구현 완료 보고가 아니라 후속 구현 기준이다" (문서 성격 배너) | STATUS | devpath-community-svc |
| "3.2 레벨 및 권한 언락 — MVP 기준: 커뮤니티 글쓰기... 횟수 제한 없음" | STATUS | devpath-community-svc |
| "평판 점수(Reputation) 획득 규칙" 표 — 질문 upvote +5, 답변 upvote +10, 답변 채택 +15 등 | STATUS | devpath-community-svc |
| "레벨 및 권한 언락" 표 — 평판 15/50/125/250/500/1000/2000/3000/5000/10000/20000 임계값별 권한 | STATUS | devpath-community-svc |
| "배지 시스템 — Bronze 9종/Silver 7종/Gold 7종" 명단 | STATUS | devpath-community-svc / devpath-shared |
| "평판 남용 방지 — 같은 사용자로부터 하루 +40 점수 제한, 새 계정 첫 7일 upvote/downvote 불가, IP·디바이스 기반 sockpuppet 탐지" | STATUS | devpath-community-svc |
| "8.1 핵심 엔티티" — User/Post/Question/Answer/Comment/Vote/Bookmark/Follow/Tag/UserTagReputation/Badge/UserBadge/Notification/Report/LearningContextSnapshot/AIAnswer/StudyGroup/ProjectShowcase 필드 목록 | SCHEMA | devpath-shared / devpath-community-svc |
| "8.2 이벤트(Kafka Topics)" — community.post.created 등 8개 토픽 | API | devpath-community-svc |
| "8.3 검색 인덱스(Elasticsearch)" — posts/users/tags 인덱스 필드 | SCHEMA | devpath-community-svc |
| "11. Kafka 이벤트 계약" 표 — CommunityQuestionPostedEvent(토픽 community-questions, consumer group ai-seed-worker 등), 재시도 정책 | API | devpath-community-svc / devpath-ai-svc |
| "AI 병렬 처리 패턴 — 체감 시간: 병렬 처리로 3-5초(직렬 시 8-15초)" | STATUS | devpath-ai-svc / devpath-community-svc |
| "Graceful Degradation" 표 — AI 시드 답변/AI 모더레이션/품질 스코어링/역링크 추천 각각의 fallback | STATUS | devpath-community-svc / devpath-ai-svc |
| "보안: 프롬프트 인젝션 이중 방어" — 입력 살균, 출력 검증, 시스템 프롬프트 방어 | STATUS | devpath-ai-svc |

---

*(끝)*

# T6b — 문서 21~41 + README.md + Home.md 검증 가능 주장 추출

기준 ref: `origin/develop` (SHA 099d33394a1037cc8d9a853c7762298bee46841a)
추출 방법: `git show origin/develop:<파일명>` 으로 워킹트리가 아닌 기준 ref 내용을 직접 읽음.

---

## 21_유료_플랜_참고설계.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "본 문서는 01~20에 반영되지 않습니다... **상태**: 본 위키 범위에서는 **비활성**" | LABEL | documents (배너: REFERENCE/비활성, MVP 범위 제외 명시) |
| "GET \`/plans\`", "GET \`/plans/me\`", "POST \`/plans/me/checkout\`", "POST \`/plans/me/cancel\`", "POST \`/plans/me/pause\`", "POST \`/plans/me/resume\`", "POST \`/webhooks/billing\`" | API | 없음(설계 참고본, 구현 레포 없음 — devpath-*-svc) |
| "7.1 \`user_plans\`", "7.2 \`plan_usage\`", "7.3 \`billing_events\`" 테이블 정의 | SCHEMA | devpath-shared (Flyway 마이그레이션) |
| "결제(토스페이먼츠)" | STACK | devpath-*-svc (결제 연동 코드) |

---

## 22_AR_아키텍처_체험_참고설계.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "📎 아카이브 문서 (v2.0 — 현재 비활성)... 본 문서의 모든 기능은 **v1.0에 포함되지 않음**" | LABEL | documents (배너: REFERENCE/아카이브) |
| "GET \`/contents/{id}/ar-launch\`", "POST \`/ar/sessions\`", "POST \`/ar/sessions/{id}/interactions\`", "POST \`/ar/sessions/{id}/quiz-answer\`", "POST \`/ar/sessions/{id}/finalize\`", "GET \`/ar/scenes/{id}/manifest\`" | API | 없음(AR 서브시스템 미착수, v2.0 이후) |
| "4.1 \`scene_templates\`", "4.2 \`ar_sessions\`", "4.3 \`ar_quiz_attempts\`", "contents.scene_template_id" | SCHEMA | devpath-shared (Flyway) |
| "Flutter \`ar_flutter_plugin\` 통합", "ARCore 7.0+ / ARKit 13.0+ 지원" | STACK | devpath-frontend |

---

## 23_개인정보_영향평가_PIA.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "본 문서는 법적 의무 수행 증빙이 아닌 **자율 평가 기록**이다" | LABEL | documents (법적 성격 자기 규정, TARGET/계획 문서) |
| "**포함(v1.0 MVP)**... LCS (Learning Context Snapshot Service) — 집중 평가" / "**제외**: AR 서브시스템... 결제·유료 플랜" | STATUS | documents (21/22 참고본과의 스코프 정합) |
| "R-01 에러 로그 Sanitize 누락으로 민감정보 노출... Critical(20)" 등 위험 목록·등급 | STATUS | devpath-*-svc (Sanitize 파이프라인 구현 여부) |
| "Anthropic | AI 답변 생성 (Claude API) | 미국 | 위탁 계약" | STACK | devpath-ai-svc (실제는 Ollama, 36/37 문서 참조) |
| "User Service / Learning Path Engine / Content CMS / Assessment & Progress / Community Services / LCS / Sandbox Runner / Observability" 개인정보 처리 시스템 표 | STATUS | devpath-*-svc 전체 (각 서비스 존재·기능 구현 여부) |
| "R-01 Sanitize 파이프라인 3-Stage 구축... MVP 전 필수" 등 §6-1 조치 매트릭스(전부 "MVP 전 필수"로 표시) | STATUS | devpath-*-svc (실제 구현 여부 — 미구현 시 허위 완료 주장 아님, 계획 항목) |

---

## 24_선행_트러블슈팅_참고.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "**gradlew 권한 (#4)**... → \`git update-index --chmod=+x gradlew\`로 해결함. **신규 백엔드 레포 생성 시 즉시 적용**" | STATUS | devpath-svc-template, devpath-*-svc (실제 적용 여부) |
| "**gh-pages 서브경로 (#7)**... workflow-dashboard·guide에 적용됨" | STATUS | workflow-dashboard, workflow-guide 레포 |
| "출처: Synapse Project (team-project-final) — velka(팀장, Gateway·인프라) 개인 회고" (Notion 링크) | LABEL | 외부 레포(Synapse, 비검증 대상) — 배경 참고 문서, 배너 없음 |

---

## 25_문서_정합성_점검_보고서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "C1 **LCS 위치**... \`devpath-community-svc/README.md\` 담당 도메인 표에 \`learning-context\`·\`ai-seed\` 명시" | STATUS | devpath-community-svc |
| "C2 **AI Gateway 단일 진입점**... \`devpath-ai-svc/README.md\` '모든 Claude API 호출은 이 서비스를 경유'" | STATUS/STACK | devpath-ai-svc |
| "C4 **DB 전환 코드 선반영**... \`devpath-shared/docker-compose.yml\` = \`postgres:17-alpine\`(5432) + \`pgvector/pgvector:pg17\`(5433)" | STACK | devpath-shared |
| "C4... \`devpath-platform-svc/build.gradle.kts\` = \`org.postgresql:postgresql\` + \`spring-boot-starter-data-jpa\`" | STACK | devpath-platform-svc |
| "D1. 아키텍처 정의서(03)가 여전히 '모놀리식 코어'를 전제... 실제는 **폴리레포 마이크로서비스 9개**" | STATUS | documents/03 vs 실제 레포 구조 (9개 레포) |
| "D2... \`.github/profile/README.md\`의 레포 표는 \`documents\`·\`storyboard\`·\`prototype\`·\`templates\` 4개만 노출" | STATUS | .github (조직 프로필) |
| "D7... \`devpath-svc-template/build.gradle.kts:27\` \`// runtimeOnly(\"com.mysql:mysql-connector-j\")\`" | STATUS | devpath-svc-template |

---

## 26_학습맥락_자동첨부_구현.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "**문서 성격**: v1 목표 구현 스펙. 현재 LCS 스키마/API는 아직 미구현이며, 본 문서는 후속 구현 기준이다" | LABEL | documents (TARGET/목표 스펙, 37번 기준) |
| "POST \`/api/lcs/snapshots/draft\`", "GET .../draft/{id}", "PATCH .../draft/{id}", "POST .../{id}/commit", "GET \`/api/lcs/snapshots/{id}\`", "DELETE .../{id}", "GET/PUT \`/api/lcs/preferences\`" | API | devpath-community-svc (LCS 브릿지, 37번 기준 미구현) |
| "\`learning_context_snapshots\`", "\`user_context_preferences\`", "\`sanitize_rules\`" 테이블(SQL DDL) | SCHEMA | devpath-shared (Flyway — 37번 기준 미구현) |
| "이벤트 스트림 수집... \`learning.content.opened\` 등 9개 Kafka 토픽" | STACK | devpath-*-svc (Kafka Consumer 구현 여부) |
| "Redis 스키마... \`user:{userId}:context\`" 등 키 패턴 | SCHEMA | devpath-community-svc / Redis 사용 여부 |

---

## 27_MVP_설계서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "**최신 실행 기준 안내(2026-06-19)**: 본 문서는 2026-04-23 멘토링 초안이다... 17_스케줄, 36_... 을 우선한다" | LABEL | documents (HISTORY/초안, 17·36이 최신 기준) |
| "실습 환경 (Sandbox Runner) | 기술 복잡도, 인프라 비용 | 베타 후반 (M2+)" — 8주 알파에서 의도적 배제 | STATUS | devpath-sandbox-svc (37번 문서에서 17번과 충돌 명시됨) |
| "백엔드 | Spring Boot 4, Java 21", "데이터베이스 | PostgreSQL 16 + pgvector", "프론트엔드 | Flutter 3.x (Dart) + Riverpod 3", "AI | Claude API (Sonnet 4.6)" | STACK | devpath-*-svc, devpath-frontend, devpath-ai-svc (실제는 Ollama — 36/37 참조) |
| "아키텍처 결정 노트... MVP는 **모놀리식**으로 시작(1인 개발 효율성)" | STATUS | 실제 레포 구조(폴리레포 9개 — 25번 D1과 상충) |

---

## 28_장기_전략.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| 검증 가능한 코드/스키마/API/스택 주장 없음(사업 전략·일정·멘토링 계획 문서) | — | 없음 |

검증 가능한 주장 없음(외부 프로그램 대응 전략 문서, 코드 대조 대상 아님).

---

## 29_예비창업패키지_사업계획서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "AI | AI Gateway 기반 구조화 생성·임베딩. 현재 개발 빌드는 Ollama 로컬 gateway, 운영 목표는 Anthropic Claude API + pgvector 기반 RAG" | STACK | devpath-ai-svc |
| "데이터베이스 | PostgreSQL 16 + pgvector, Redis 7" | STACK | devpath-shared |
| "메시징 | Apache Kafka (KRaft 모드)" | STACK | devpath-*-svc |
| "인프라 | Kubernetes, ArgoCD GitOps, Docker (폴리레포 MSA)" | STACK | devpath-gitops |
| "자율 개인정보 영향평가(PIA) 수행 ✅ 완료" | STATUS | documents/23 (문서 존재 여부로 검증 가능, 완료됨 — 확인됨) |
| "3단계 Sanitize 파이프라인 설계 ✅ 완료" | STATUS | devpath-community-svc/devpath-shared (실제 구현 여부, 26/37 기준 미구현) |
| "개인정보 처리방침 초안 ✅ 완료" | STATUS | documents/33 (문서 존재 — 확인됨) |

---

## 30_발표_QA_스크립트.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "제가 단독 개발 중인 **StockPilot**은 Spring Boot 4 기반... Docker Scout Health A 등급" | STACK | 외부 레포(StockPilot, dpa 레포 외부 — 검증 대상 아님) |
| "**LearnFlow AI**는 Claude API와 pgvector 기반 RAG 파이프라인" | STACK | 외부 레포(LearnFlow AI, dpa 레포 외부) |
| "지원금 배분 계획... 개발 외주 인건비 4,000만원(40%)" 등 자금 계획 | — | 없음(재무 계획, 코드 대조 불가) |

---

## 31_통계_출처_검증.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| 검증 가능한 코드/스키마/API/스택 주장 없음(외부 통계 출처 검증 문서) | — | 없음 |

검증 가능한 주장 없음(시장 통계 출처 검증, 코드 대조 대상 아님).

---

## 32_영상_대본.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| 검증 가능한 코드/스키마/API/스택 주장 없음(영상 대본·제작 가이드) | — | 없음 |

검증 가능한 주장 없음.

---

## 33_개인정보_처리방침.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "⚠️ **문서 상태 및 법적 면책**... **서비스 런칭 전 반드시 개인정보 전문 변호사... 검토**를 받아야 합니다" | LABEL | documents (초안/미검토 상태 명시, TARGET) |
| "Anthropic, PBC | AI 답변 생성 서비스 (Claude API) | 요청 처리 즉시 (Zero Data Retention 모드)" 위탁 표 | STACK | devpath-ai-svc (실제는 Ollama — 불일치 가능성) |
| "제9조 국외 이전... Anthropic, PBC | 미국... 이용자 질문 내용, 학습 맥락 정보" | STACK | devpath-ai-svc |
| "학습 맥락 정보 | 현재 학습 중인 콘텐츠, 경로, 태그 (질문 작성 시 자동 첨부) | 선택 동의" | STATUS | devpath-community-svc (LCS 미구현 — 26/37 참조) |
| "에러 로그 (선택) | ... | **명시적 별도 동의**" | STATUS | devpath-community-svc/sandbox-svc (Sanitize 파이프라인 미구현) |

---

## 34_동의화면_마이크로카피.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "본 초안은 실제 서비스 배포 전 개인정보 전문 변호사 검토 필수" | LABEL | documents (초안 상태, TARGET) |
| "학습 맥락 자동 첨부 동의 (LCS)... 최초 사용 시 팝업" UI 스펙 | STATUS | devpath-frontend (해당 화면 구현 여부 — 37번 기준 LCS 미구현) |
| "GitHub 연동... 실제 요청하는 GitHub OAuth 스코프: \`read:user\`, \`public_repo\`" | API | devpath-platform-svc (OAuth 스코프 실제 설정) |

---

## 35_모두의_창업_프로그램_참고.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| 검증 가능한 코드/스키마/API/스택 주장 없음(외부 프로그램 공식 자료 요약) | — | 없음 |

검증 가능한 주장 없음(외부 프로그램 정보, DevPath 레포와 무관).

---

## 36_현재_구현_프로토타입_스토리보드_문서_정합성_점검.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "\`devpath-platform-svc\` | \`POST /auth/refresh\`, \`POST /auth/logout\`, \`GET /users/me\`" | API/STATUS | devpath-platform-svc |
| "\`devpath-learning-svc\` | \`POST /onboarding/assessments\`, \`GET .../{id}/next\`, \`POST /answer\`, \`POST /complete\`, \`GET /result\`, \`POST .../guest\`, guest next/answer/complete, \`POST .../claim\`" | API/STATUS | devpath-learning-svc |
| "\`devpath-ai-svc\` | \`POST /ai/embed\`, \`POST /ai/path/generate\`" | API/STATUS | devpath-ai-svc |
| "\`devpath-community-svc\` | 컨트롤러 없음" / "\`devpath-sandbox-svc\` | 컨트롤러 없음" | STATUS | devpath-community-svc, devpath-sandbox-svc |
| "현재 코드 기준 \`ai-svc\`는 Claude 직접 클라이언트가 아니라 **Ollama gateway**다... \`/ai/embed\`는 768차원 임베딩을 검증" | STACK | devpath-ai-svc |
| "\`devpath-shared\`에는 \`users\`, \`user_oauth_identities\`, \`user_profiles\`, \`outbox\`, \`notifications\`, \`question_bank\`, \`assessments\`, \`assessment_items\`, \`assessment_results\` 마이그레이션이 있다" | SCHEMA | devpath-shared |
| "\`devpath-frontend/apps/web\`에는 \`/login\`, \`/diagnostic\`, \`/onboarding\`, \`/dashboard\`, \`/path\`, \`/content/:id\`, \`/sandbox\`, \`/mentor\`, \`/community\`, \`/community/:id\`, \`/auth/callback\` 라우트가 있다" | STATUS | devpath-frontend |
| "\`apps/mobile\`은 아직 제품 골든패스가 아니라 Flutter 기본 앱 수준" | STATUS | devpath-frontend (mobile) |
| "02 ERD | 갱신 완료 | \`content_embeddings\` 차원을 현재 구현/계획 기준 768로 정정" | SCHEMA | documents/02, devpath-shared |
| "17 스케줄 | 가장 정합 | DONE/MD1/MD2/MD3로 구현 상태와 목표를 분리함" | STATUS | documents/17 |

---

## 37_전체_문서_전체_레포_정합성_점검.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "전체 추적 가능 파일 | 855", "Markdown/HTML 문서 | 207", "최상위 레포/디렉터리 | 18" | STATUS | 전체 워크스페이스(D:\workspace\dev-path-ai) |
| "\`devpath-platform-svc\` | \`POST /auth/refresh\`, \`POST /auth/logout\`, \`GET /users/me\` | MD1 인증/사용자 일부 구현" | API/STATUS | devpath-platform-svc |
| "\`devpath-learning-svc\` | ... 회원/비회원 진단, claim 엔드포인트" | API/STATUS | devpath-learning-svc |
| "\`devpath-community-svc\` | 없음 | 도메인 API 미구현", "\`devpath-sandbox-svc\` | 없음 | 도메인 API 미구현" | STATUS | devpath-community-svc, devpath-sandbox-svc |
| "\`devpath-shared\`의 실제 Flyway 마이그레이션... 공통/사용자/법적 보관/이벤트·알림/진단" 테이블 목록 | SCHEMA | devpath-shared |
| "아직 실제 마이그레이션에 없는 주요 목표 테이블: \`learning_paths\`... \`community_posts\`... 미구현" | SCHEMA | devpath-shared |
| "F4. AI provider 표현 불일치... \`devpath-ai-svc/README.md\` | Claude API 오케스트레이션/단일 진입점 | 현재 코드는 Ollama gateway" | STACK | devpath-ai-svc |
| "F5... \`02_ERD_문서.md\`... \`path_weekly_tasks.task_type\`에는 \`READ/PRACTICE/AR/QUIZ\`가 남아 있다" | SCHEMA | documents/02, devpath-shared |
| "F7... \`workflow-guide/docs/env-setup.md\`... MySQL 기반 문구가 남아 있다" | STACK | workflow-guide |
| "\`devpath-frontend\`의 실제 라우트: web \`/login\`, \`/diagnostic\`, \`/onboarding\`, \`/auth/callback\`... \`/dashboard\`, \`/path\`, \`/content/:id\`, \`/sandbox\`, \`/mentor\`, \`/community\`, \`/community/:id\`" | STATUS | devpath-frontend |

---

## 38_정합성_수정계획서.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "P0-2 | \`devpath-ai-svc/README.md\` | 현재 dev 빌드가 Ollama gateway임을 명시" (실행 계획, 상태 "본 계획에 따라 수정") | STATUS | devpath-ai-svc |
| "P0-4 | 레포별 MD1 workflow | platform/learning/ai/shared 진행 상태 갱신" | STATUS | devpath-platform-svc, devpath-learning-svc, devpath-ai-svc, devpath-shared |
| "P1-2 | \`documents/02_ERD_문서.md\` | \`task_type\`에서 AR 제거, v2 참고로 분리" | SCHEMA | documents/02 |
| "실행 상태... P0 | 본 계획에 따라 수정" 등 전 항목 "수정됨"으로 표시 | STATUS | documents(02,06,07,10,11,14,16,20,26,README,Home), devpath-ai-svc, .github, workflow-guide (실제 반영 여부 검증 필요) |

---

## 39_E2E_수동검증_보고서_2026-06-20.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "결과: 통과" (학습 경로 생성 플로우 E2E) | STATUS | devpath-*-svc, devpath-frontend (E2E 통합 동작) |
| "gateway 8080 / platform-svc 8081 / learning-svc 8082 / ai-svc 8083 / frontend release static server 5173" 최종 상태 UP | STATUS | devpath-gateway, devpath-platform-svc, devpath-learning-svc, devpath-ai-svc, devpath-frontend |
| "Ollama 모델: qwen2.5:7b(경로 생성), nomic-embed-text:latest(임베딩)" | STACK | devpath-ai-svc |
| "Flyway 컨테이너로 DB migration 상태를 확인... 14개 migration 검증, schema version: \`202606181006\`" | SCHEMA | devpath-shared |
| "6.1 ai-svc: 빈 strengths/weaknesses validation 실패... \`PathGenerateRequest\`에서 concept list는 null만 금지" (변경 파일: \`devpath-ai-svc/.../PathGenerateRequest.java\`, \`OllamaControllerTest.java\`) | API | devpath-ai-svc |
| "6.2 learning-svc: SSE 30초 timeout... \`devpath-learning-svc/.../LearningPathController.java\`" | API | devpath-learning-svc |
| "6.3 frontend: DONE 이후 /path 진입 시 무조건 재생성... \`PathController.loadOrStart()\`를 추가" (변경 파일 4건, dart) | STATUS | devpath-frontend |
| "최종 DB 확인 결과... path_id 8, user_id 73, track BACKEND_SPRING, total_weeks 12, milestones 3, onboarding_status DONE" | SCHEMA/STATUS | devpath-shared, devpath-learning-svc |

---

## 40_E2E_수동검증_보고서_2026-06-21_슬라이스4.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "GET /contents/2 | 200 · markdown·conceptTags 배열·progress 초기값 | ✅" 등 백엔드 API 표 10건 | API/STATUS | devpath-learning-svc |
| "gateway 경유(:8080)... 미인증 GET /contents/3 | 401(엣지 차단) | ✅" 등 4건 | API/STATUS | devpath-gateway |
| "인증: learning·gateway 동일 JWT secret(\`application.yml\`/\`GatewaySecurityConfig\` 기본값 일치 확인)" | STACK | devpath-learning-svc, devpath-gateway |
| "콘텐츠 뷰어 UI(빌드 E)는 위젯 테스트로 검증됨 — \`apps/web/test/features/content/content_page_test.dart\`·\`content_progress_smoke_test.dart\`(CI \`analyze-test\` 녹색)" | STATUS | devpath-frontend |
| "현재 메인 DB contents는 11개(슬라이스 #3 잔여)뿐, B2의 승인 콘텐츠 150 seed(\`content_md2_seed.sql\`)는 메인 DB에 미적재" | SCHEMA/STATUS | devpath-shared, devpath-learning-svc |
| "Kafka·Ollama 미가동... 본 검증 범위(콘텐츠 조회/진척)는 learning-svc 내부 DB 트랜잭션이라 불요" | STACK | devpath-learning-svc |

---

## 41_study-documents_연계_카탈로그.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "정본 경로 | \`D:\workspace\develop-study-documents\`" | LABEL | 외부 레포(develop-study-documents, dpa 레포 외부) |
| "스킬은 \`devpath-skillpack\` 플러그인으로 패키징되어 \`/devpath-skillpack:<skill>\` 형식으로 호출한다" | STATUS | devpath-skillpack 플러그인(별도 검증 Task 예정이라 명시됨) |
| "스킬 26개 SKILL.md | 전부 OK (26/26)", "Sample Codes 파일 수 | 150개 확인" 등 §⑦ 검증 결과 표 | STATUS | develop-study-documents (dpa 레포 외부, 참고 카탈로그) |
| "devpath-frontend 실측 패키지 | \`flutter_riverpod ^3.3.0\`, \`go_router ^14.6.0\`, \`dio ^5.0.0\`, Dart SDK \`^3.12.1\`" | STACK | devpath-frontend |

---

## Home.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "**배너 없음**" (문서 최상단에 TARGET/HISTORY/PROTOTYPE 등 상태 라벨 없음, 색인 문서 성격) | LABEL | documents (Home.md 자체) |
| "03 | [[03_프로젝트_아키텍처_정의서]] — 폴리레포 서비스 + 중앙집중 스키마 + gVisor Sandbox + AI Gateway" | STACK | documents/03, devpath-* (폴리레포 구조 실제 여부) |
| "**AI**: dev Ollama(\`nomic-embed-text\`, \`qwen2.5:7b\`) / 운영 목표 Claude 등 provider 교체" | STACK | devpath-ai-svc |
| "**Data**: PostgreSQL (SSOT) + pgvector (콘텐츠·GitHub 임베딩) + Redis + Kafka + Elasticsearch" | STACK | devpath-shared, devpath-*-svc |
| "**Sandbox**: Docker + **gVisor (runsc)** + 네트워크 차단 + 30초 limit" | STACK | devpath-sandbox-svc |
| "**Web**: Flutter Web (Dart) + Riverpod 3 + go_router + dio + Monaco Editor(Sandbox)" | STACK | devpath-frontend |
| "2 Aha | 가입 → 1st Aha(경로) p50 | ≤ 8분" 등 v1.0 KPI 표 | STATUS | devpath-*-svc, devpath-frontend (실측 지표 존재 여부) |
| "22 | [[22_AR_아키텍처_체험_참고설계]]... v2.0 이후 재검토. **아카이브**" | LABEL | documents/22 |

---

## README.md

| 주장 원문(1줄 인용) | 유형 | 검증 대상 레포 |
|---|---|---|
| "**배너 없음**" (최상단 상태 라벨 없음, 레포 소개 성격) | LABEL | documents (README.md 자체) |
| "**아키텍처**: 폴리레포 서비스 + 중앙집중 스키마 (distributed modular monolith)" | STACK | devpath-*-svc 구조 |
| "**AI**: dev Ollama(\`nomic-embed-text\`, \`qwen2.5:7b\`) / 운영 목표 Claude 등 provider 교체" | STACK | devpath-ai-svc |
| "**Data**: PostgreSQL (SSOT) + pgvector + Redis + Kafka + Elasticsearch" | STACK | devpath-shared |
| "**Sandbox**: Docker + gVisor (runsc) + 네트워크 차단 + 30초 limit" | STACK | devpath-sandbox-svc |
| "[devpath-shared](https://github.com/DevPathAi/devpath-shared) | 공유 스키마 + 공통 라이브러리 + 중앙 Flyway" 등 관련 레포 표(9개 레포 링크) | STATUS | devpath-shared, devpath-gateway, devpath-*-svc, devpath-frontend, devpath-gitops, storyboard, prototype, templates (레포 존재 여부) |
