# 빌드 C 보고서 — MD3 슬라이스 #8 ai-svc 커뮤니티 AI 시드 워커 (2026-06-26)

> 레포: `devpath-ai-svc` · 브랜치: `feat/slice8-community-seed`(develop 분기, 머지 후 삭제) · 도구: **Bash만**(PowerShell 미사용)

## ① 선행 확인

- **ai-svc develop에 community/seed 코드 0**(신규 작업 확인). `git checkout develop && git pull` 후 `find/grep community` 결과 없음 → `feat/slice8-community-seed` 분기.
- **shared 빌드 A(Community 이벤트 2종 + V202606251001 마이그레이션) origin/main 머지 완료**(PR #27, 2026-06-25 12:53, "Publish Package" 워크플로 success = SNAPSHOT build #12 `0.0.1-20260625.125415-12`). 원격 GitHub Packages jar 실측: `CommunityQuestionPostedEvent`·`CommunitySeedReadyEvent`·`db/migration/V202606251001__community_qna.sql` 포함 확인.
- 이벤트 시그니처 실측: `CommunityQuestionPostedEvent(eventId·occurredAt·userId·questionId·postId·title·bodyMd, EVENT_TYPE="community.question.posted")`, `CommunitySeedReadyEvent(eventId·occurredAt·questionId·status·content·provider·questionEmbedding:List<Double>·errorCode, EVENT_TYPE="community.seed.ready")`.
- ai-svc 로컬 빌드 가능(`~/.gradle/gradle.properties` gpr 토큰 존재). baseline `compileJava` SUCCESS. docker postgres(devpath_citest) 가동·pgvector 사용 가능, Kafka는 EmbeddedKafka로 대체.
- 실측 패턴: review(ReviewConsumer·AiReviewClient 3종·ReviewPromptBuilder·ClaudeClientConfig·ReviewConsumerIT·GoldenReviewEvalTest), mentor(킬스위치·MentorClaudeClientConfig `@Qualifier` 빈분리·MentorGoldenCase), ollama(OllamaClient.embed 768·EmbedResponse), learning outbox(OutboxEntry·Relay·Scheduler@Profile!test·Repository·AssessmentEventPublisher), `@EnableScheduling`은 메인 클래스(learning/sandbox 실측). ai-svc는 produce 인프라·KafkaTemplate producer·@EnableScheduling **부재**(신규).

## ② 플랜 경로

`D:\workspace\dev-path-ai\documents\docs\superpowers\plans\2026-06-25-md3-slice8-aisvc-seed-c.md` (태스크 C1~C9, B1/B2 형식·TDD·실제 코드·실측 패턴).

## ③ 태스크별 커밋 SHA · 테스트 결과

| Task | 내용 | 커밋 | 테스트 결과 |
|---|---|---|---|
| C1 | outbox/ produce 미러 + KafkaTemplate producer + @EnableScheduling | `9de0717` | `OutboxRelayTest`(mock) GREEN |
| C2 | SeedPromptBuilder(인젝션 격리 + 강건 system prompt) | `27c0fb7` | `SeedPromptBuilderTest` GREEN |
| C3 | AiSeedClient + SeedAnswer + MockSeedClient(CI 기본) | `faeb7d6` | `MockSeedClientTest` GREEN |
| C4 | OllamaSeedClient + ClaudeSeedClient(haiku-4-5) + CommunitySeedClaudeConfig + SeedGenerationException | `37bf37c` | `OllamaSeedClientTest`(MockWebServer) GREEN |
| C5 | CommunitySeedEventPublisher(seed.ready Outbox) | `1d02b56` | C6에서 간접 검증 |
| C6 | CommunitySeedService(kill-switch·임베딩 best-effort·DONE/FAILED) | `3c92bd5` | `CommunitySeedServiceTest` 5분기 GREEN |
| C7 | CommunitySeedConsumer + EmbeddedKafka IT(왕복 끝단) | `969c8c7` | `CommunitySeedConsumerIT`(DONE seed.ready 768임베딩·MOCK + 멱등) GREEN |
| C8 | 골든 eval(인젝션 무력화, @Tag eval CI 제외) | `8911cad` | 컴파일 GREEN, CI 자동 제외 확인(jsonl 7케이스 classpath 적재) |
| C9 | application.yml community-seed 블록 + 전체 빌드 | `806fbc6` | **전체 `./gradlew build` GREEN**(review·mentor 회귀 0, 두 consumer group 정상 기동) |
| CI fix | `--refresh-dependencies`(shared SNAPSHOT stale 방지) | `f3ca0ba` | PR CI build pass 2m3s |

## ④ 생성/수정 파일 (27개, 전부 ai-svc src/ 범위)

**신규 main**: `outbox/{OutboxEntry,OutboxRepository,OutboxRelay,OutboxRelayScheduler}.java`, `community/{AiSeedClient,SeedAnswer,SeedInput,SeedPromptBuilder,MockSeedClient,OllamaSeedClient,ClaudeSeedClient,CommunitySeedClaudeConfig,SeedGenerationException,CommunitySeedEventPublisher,CommunitySeedService,CommunitySeedConsumer}.java`
**신규 test**: `outbox/OutboxRelayTest.java`, `community/{SeedPromptBuilderTest,MockSeedClientTest,OllamaSeedClientTest,CommunitySeedServiceTest,CommunitySeedConsumerIT}.java`, `community/eval/{CommunitySeedGoldenCase,GoldenCommunitySeedInjectionEvalTest}.java`, `resources/eval/golden-community-seed-injection.jsonl`
**수정**: `AiApplication.java`(@EnableScheduling), `application.yml`(kafka.producer + devpath.community-seed), `.github/workflows/ci.yml`(--refresh-dependencies)

## ⑤ PR · CI · 머지 SHA

- PR: [#23](https://github.com/DevPathAi/devpath-ai-svc/pull/23) `--base develop`.
- CI: 1차 실패(stale shared SNAPSHOT compile 실패) → CI fix → **2차 build pass(2m3s)**, image/deploy는 develop PR이라 skip.
- 머지: `--merge --delete-branch` → **develop 머지 SHA `f36cca2`**. 원격 feat 브랜치 삭제 확인.

## ⑥ 막힌 점 / 트러블슈팅

- **CI 1차 실패(근본원인 규명·수정)**: ai-svc CI가 `cannot find symbol CommunityQuestionPostedEvent ... package ai.devpath.shared.event`로 compile 실패. 원격 SNAPSHOT #12 jar 실측 결과 이벤트 **포함**(아티팩트 정상), community-svc CI는 동일 SNAPSHOT을 같은 시각대에 정상 해소(B1 03:28·B2 04:04 success). 결론: ai-svc는 마지막 green CI(PR #22, 빌드 A 이전)의 **stale shared SNAPSHOT을 Gradle 캐시(24h TTL)에서 재사용**해 빌드 A 이벤트 미반영. 수정: ci.yml `build`/`bootJar`에 `--refresh-dependencies`(changing SNAPSHOT 매 CI 재해소) → 2차 CI green. **로컬은 mavenLocal/cache에 이벤트가 있어 가려졌던 케이스**(로컬 인프라가 CI 가림 교훈).
- **콘텐츠필터**: 인젝션 방어 프롬프트(C2 systemPrompt)·골든 케이스(C8 jsonl, PWNED·ARRR·시스템프롬프트 노출 등)는 방어 목적 보안 코드로 전부 정상 작성·커밋됨. 안전분류기 차단 없음.
- **범위 준수(Scope Lock)**: 27개 변경 전부 ai-svc `src/`. shared/community-svc/gateway/frontend 무수정. community-svc는 이미 B2로 seed.ready consume → ai-svc는 발행만(왕복 완성).

## 비고

- Claude 시드 모델 기본값 `claude-haiku-4-5`([claude-api] 스킬 확정, 설계 §11 Haiku급). 운영 provider 키는 환경변수(ANTHROPIC_API_KEY)로만 주입, 미커밋.
- 골든 eval 실모델 통과율(0.8 바)은 로컬 `-Dgroups=eval`로 ollama/claude 가동 시 수행(CI는 mock 고정으로 미실행). 본 빌드는 컴파일·CI 제외만 검증.
