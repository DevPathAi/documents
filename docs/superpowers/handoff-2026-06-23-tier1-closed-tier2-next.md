# 핸드오프 — Tier-1 종결 / Tier-2 진입 (2026-06-23)

> 다음 세션 이관용. **Tier-1(슬라이스 #1~6=MD1+MD2) 구현·릴리스·배포·종결 감사·잠재결함 fix까지 완료.** 다음은 Tier-2(#7 AI 멘토부터).

## 1. 지금까지 (이번 세션 종착점)

- **슬라이스 #6 AI 코드리뷰(2nd Aha)**: 빌드 A~E 구현 → 통합 릴리스·배포(main) → 최종 리뷰 → **Important #1 재시도복구** → **E2E 라이브 실증** → **골든 eval(qwen2.5-coder 24/24)** 전부 완료. (메모리 [[md2-slice6-ai-review-plan]])
- **Tier-1 종결 감사**: 3보고서 develop(documents PR #39) — `2026-06-23-tier1-{closure-verification,troubleshooting,refactoring-review}.md`. (메모리 [[tier1-closure-audit]])
- **잠재결함 4건 fix** develop 머지(전 CI 녹색): admin AuthInterceptor 결선(frontend #32) · WelcomeConsumer poison-skip(platform #13) · GuestAssessment `.equals`(learning #22) · OutboxRelay 무음→log.warn(platform·learning·sandbox 3레포).
- **GLM-5.2 provider 후보 검토**: `reports/2026-06-23-glm-5.2-provider-evaluation.md` — 로컬 dev 부적합(744B/241GB), 운영 provider 대안으로만 검토 가치(채택 전 골든 eval 실측).

## 2. 릴리스 상태 (중요)

- **main 릴리스 완료**: shared·sandbox-svc·ai-svc·gateway·frontend 슬라이스 #6까지(+배포).
- **미릴리스 develop**(다음 통합 릴리스 시 main): ai-svc(골든파일·리뷰복구는 이미 main)·**잠재결함 4건 fix(4레포)**·documents 보고서들(감사 3종·E2E·골든·GLM). 즉 **4개 fix와 문서는 develop에만 있음** → Tier-2 첫 릴리스 때 함께 main.

## 3. 다음 진입점 = Tier-2 (#7 AI 멘토부터)

- Tier-2 = 슬라이스 #7 멘토 · #8 커뮤니티 · #9 LCS · #10 모바일 · #11 랜딩 (MD3). 의존성상 **#7 AI 멘토** 먼저.
- **#7 AI 멘토**(스케줄 17): ai-svc `ai_mentor_sessions` + `context_snapshot`(현재 콘텐츠 + 최근 5 Sandbox 자동 주입) + SSE 스트리밍 + 참고자료 링크. 프론트 `MentorController` SSE 실API 전환(이미 web에 mock 멘토 SSE 존재).
- **패턴 승계**(슬라이스 #6대로): brainstorming(스킬) → 설계서(specs) → 빌드플랜(plans) → subagent-driven/inline 구현 → CI 검증 → develop 2단계 PR → 슬라이스 끝 통합 릴리스. TDD·추측금지·컨트롤러 직접검증.

## 4. 환경 사실 (다음 세션 필수 — 시간 절약)

- **ai-svc 로컬 빌드 불가**(GitHub Packages 인증 없음: `gh` 토큰 read:packages 결여). → **CI 검증이 1급 경로**. 로컬 실행 필요 시 `devpath-shared ./gradlew publishToMavenLocal` + ai-svc `repositories`에 `mavenLocal()` 임시추가(미커밋, 후 `git checkout build.gradle.kts` 복원). 다른 서비스(platform/learning/sandbox/gateway)는 캐시 shared로 로컬/ CI 가능.
- **브랜치 전략**: `main` 보호. 서비스/frontend = develop 2단계 PR(작업브랜치→develop→릴리스 시 main). **devpath-shared만 develop 부재 → feature→main**. fetch --prune로 stale origin/develop 주의.
- **로컬 인프라**: `devpath-shared/docker-compose.yml`(Kafka 9092·Postgres 5432·pgvector 5433·redis·ES). `devpath` DB는 마이그레이션 구버전일 수 있음 → 누락분 psql 직접 적용(flyway gradle 플러그인은 **Gradle 9 비호환**). E2E 시 sandbox-svc:8085·ai-svc:8084·gateway:8080.
- **Ollama**: `devpath-ollama` 컨테이너(11434). 보유: qwen2.5:7b·**qwen2.5-coder:7b**(골든 eval용)·nomic-embed-text. CPU ~35s/리뷰.
- **빌드/테스트**: Spring Boot 4.0.7·Java 21·Gradle KDSL(서비스), Flutter melos7(frontend: `melos run analyze/test/format`, **format은 CI 게이트**). docker exec 경로는 `MSYS_NO_PATHCONV=1`.
- 트러블슈팅 22건은 `reports/2026-06-23-tier1-troubleshooting.md`.

## 5. 백로그 (Tier-2 일정에 배치)

- **🔴 미수행/연기**: 결제(토스페이먼츠, 별도 사이클)·베타 100명·Google/카카오 OAuth(현재 GitHub만).
- **🟡 단순화 복원 검토**: gVisor 격리(MD4 pentest 연계)·운영 Claude 키 배선·frontend 완전 실API·골든 24→50.
- **리펙토링 횡단**(감사 보고서): Outbox 3레포 복제 공통화·status/track/language enum 골격(신규코드부터)·dead code 제거(SandboxSession.containerId·Assessment.bloomDistribution·web ReviewController.request).
- **provider**: GLM-5.2 운영 대안 골든 eval 비교(원하면).

## 6. provider 전략 현황

- **prod = Claude sonnet-4-6**: 추상화·키 주입 경로 완비, `ANTHROPIC_API_KEY` 미배선(dev=Ollama/Mock).
- **dev = Ollama qwen2.5-coder:7b**: 골든 eval 24/24 검증.
- **CI = Mock**: 외부 LLM 0.
- **후보 = GLM-5.2**: 운영 대안(저렴·오픈웨이트·코딩특화), 로컬 dev 부적합. 채택 전 골든 eval.

## 7. 참고 문서

- 스케줄/Tier: `17_스케줄.md`(§2 MD1-4, §3 Tier 컷라인) · MVP `27_MVP_설계서.md`(전략 컨텍스트).
- 슬라이스 설계서: `docs/superpowers/specs/2026-06-{17..23}-*`(slice1-6 + ai-review-transient-recovery).
- 빌드플랜: `docs/superpowers/plans/2026-06-*`.
- 감사·검증: `docs/superpowers/reports/2026-06-23-*`(closure-verification·troubleshooting·refactoring-review·slice6-e2e·slice6-golden-eval·glm-5.2-provider-evaluation).
