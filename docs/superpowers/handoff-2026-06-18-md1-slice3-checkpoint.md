# 세션 핸드오프 — MD1 슬라이스 #2 완료 + 슬라이스 #3 설계·빌드A 플랜 (2026-06-18 체크포인트)

> **상태**: MD1 **슬라이스 #2(진단) 6개 빌드 전부 구현·develop 머지 완료**. **슬라이스 #3(학습경로/1st Aha) 설계서+검토반영+빌드A 플랜 완료(documents develop 머지)**, 빌드 B~E 플랜 미작성·실행 전.
> **원칙**: 각 레포 CLAUDE.md 절대조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock.

---

## 1. 이번 세션 완료

### 슬라이스 #1 끝단간 후속
- ✅ R4: dp_core `User.email` nullable (frontend PR #16, merge `e3e5699`).
- ✅ 끝단간 런북 `docs/superpowers/runbook-2026-06-18-md1-slice1-e2e.md` (documents PR #13).

### 🎉 슬라이스 #2(진단) — 6개 빌드 전부 develop 머지
| 빌드 | 레포 | PR | 머지 |
|---|---|---|---|
| A 스키마+이벤트 | devpath-shared | #11→develop, #12→main(publish) | 진단 4테이블 + AssessmentCompletedEvent |
| A' FK제거 | devpath-shared | #13→develop, #14→main(publish) | assessments.user_id 교차FK 드롭(서비스 경계) |
| B-1 엔진+회원API | devpath-learning-svc | #5 | 시큐리티·엔티티4·AdaptiveEngine·회원 API |
| B-2 이벤트+guest+claim | devpath-learning-svc | #6 | outbox→Kafka·guest Redis·claim(SETNX 멱등)·시드 |
| C status 소비 | devpath-platform-svc | #7 | 진단완료→onboarding_status IN_PROGRESS(조건부 update) |
| D-gateway | devpath-gateway | #6 | /onboarding/assessments/** 라우트+guest 공개경로 |
| D-frontend | devpath-frontend | #17 | dp_core 모델·API·DiagnosticController/Page·게이트 통일 |
- 설계서+5플랜+검토반영=documents PR #14. 전부 subagent-driven + 컨트롤러 직접검증 + fresh DB/CI 검증.

### 슬라이스 #3(학습경로) 설계 단계
- ✅ 설계서 `specs/2026-06-18-md1-slice3-learning-path-design.md` + 검토반영 §11-bis + 리뷰 보고서 `reports/...-design-review.md` + 빌드A 플랜 `plans/2026-06-18-md1-slice3-shared-schema.md` (documents PR #15 develop 머지 `19d34c5`).

## 2. 슬라이스 #3 다음 세션 진입점 (여기서 시작)

### 확정 설계 결정
- **범위 Full**: Claude→**로컬 Ollama** 경로생성 + contents 임베딩 + pgvector HNSW 매칭 + 소량 시드.
- **소유**: learning-svc가 path 도메인(테이블·SSE·LearningPathGeneratedEvent) 소유. **ai-svc = 로컬 Ollama 게이트웨이**(무상태).
- **AI = 로컬 Ollama**(API키 제거): 임베딩 `nomic-embed-text`(768), 생성 `qwen2.5:7b`. **Ollama 미설치 — docker-compose 추가+모델 pull 필요(사용자)**. CI는 Ollama mock.
- **진단 입력**: learning-svc 자체 `assessment_results`⋈`assessments` join 조회(user별 최신 COMPLETED).
- **DONE 전이**: platform이 LearningPathGeneratedEvent 소비→onboarding_status DONE.
- **pgvector**: 메인 devpath DB(5432) 이미지를 pgvector/pgvector:pg17로 전환, content_embeddings VECTOR(768)+HNSW. ERD 1536→768 변경.

### 검토 반영 핵심(§11-bis, 구현 시 우선)
R-1 Ollama chat `stream:false`+2단계 파싱 · R-2 API prefix bare path(/api/v1 미도입) · R-3 pgvector 전환범위(shared·learning·platform CI 이미지, ai-svc 제외) · R-4 프론트 breaking(stage·milestones·fromStep 제거) · R-5 milestone 3과제+expected_outcome · R-6 ai-svc 무상태화(JPA/DB 제거) · R-7 진단 join 쿼리 409 · R-8 Ollama는 tx 밖+partial unique 동시성 · R-9 임베딩 native(JdbcTemplate)·`<=>`.

### 빌드 분해 (A→릴리스→B→C→D→E)
- **A 스키마+pgvector**(devpath-shared): **플랜 작성 완료**. 다음 세션 첫 실행 대상(subagent-driven). V202606181006 + docker/CI pgvector + 릴리스.
- **B ai-svc Ollama**(devpath-ai-svc): 플랜 미작성. 스켈레톤→Ollama RestClient·`/ai/embed`·`/ai/path/generate`(stream:false structured)·MockWebServer·**JPA/DB 제거(R-6)**.
- **C learning 경로엔진**(devpath-learning-svc, **최대**): 플랜 미작성. path JPA·임베딩 native repo·HNSW 매칭·경로생성(진단조회→ai-svc→매칭→영속, tx 밖 AI)·SSE `/generate`·`/me`·`/this-week`·`/rationale`·LearningPathGeneratedEvent outbox·시드 콘텐츠. ai-svc 클라이언트 mock.
- **D platform DONE**(devpath-platform-svc): 플랜 미작성. LearningPathGeneratedEvent 소비→DONE(`where onboarding_status in('PENDING','IN_PROGRESS')`).
- **E gateway+frontend**(devpath-gateway·devpath-frontend): 플랜 미작성. gateway `/learning-paths/**` 라우트 / dp_core LearningPath 재생성·PathController stage SSE·O04/O05·골든 스모크.

## 3. 슬라이스 #2 끝단간 미완 (병행 가능)
- 실 콘텐츠/문항 대량(슬라이스 #4), 배포 env(LEARNING_URI·Redis/Kafka 브로커), 수동 끝단간(전 서비스 구동 guest→가입게이트→OAuth→claim→결과), 하드닝(claim 원자성 guest_claims·UI 정교화).

## 4. 핵심 교훈 (슬라이스 #2/#3 적용)
- **로컬 DB/인프라가 CI 실패를 가린다**: fresh DB(`devpath_citest`) + CI 서비스(postgres+redis(+pgvector 이미지)) 일치 확인 필수. Boot4 Flyway=spring-boot-flyway·Kafka=spring-boot-kafka 모듈, 모든 @SpringBootTest @ActiveProfiles("test").
- **교차서비스 FK 금지**(무결성=앱/이벤트). 서브에이전트 땜질(임의 마이그레이션) 거부→근본 수정.
- **CI에 AI/외부 실호출 금지**: Ollama는 MockWebServer, 다운스트림은 클라이언트 mock.
- 서브에이전트는 긴 최종메시지 안 돌려줌 → 파일 Write. Wave 셸 문제 시 컨트롤러가 테스트·커밋 인수.

## 5. 관련 메모리
- [[md1-slice1-progress]](SSoT, 슬라이스 #1/#2/#3 진행) · [[subagent-final-message-suppressed]] · [[no-guessing-test-first]] · [[w1-infra-postgres]]
