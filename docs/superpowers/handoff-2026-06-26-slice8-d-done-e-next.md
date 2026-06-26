# 핸드오프 — MD3 슬라이스 #8 커뮤니티 Q&A (2026-06-26, D 완료)

> 다음 세션 이관용. 빌드 A~D 완료(A=main 릴리스, B1·B2·C·D=develop 머지). 남은 = E(frontend)·통합 릴리스. **이번 세션부터 WSL+Bash에서 메인 직접 도구 호출로 진행(antml 마찰 0건).**

## 진행 상태
| 단계 | 상태 | 근거 |
|------|------|------|
| 설계서 | ✅ 커밋 | `specs/2026-06-25-md3-slice8-community-qna-design.md` (브랜치 `docs/md3-slice8-community-spec`, 미PR) |
| 빌드 A (shared 스키마+이벤트2종) | ✅ main 릴리스·publish | PR #27, `V202606251001`, `CommunityQuestionPostedEvent`/`CommunitySeedReadyEvent` |
| 빌드 B1 (community 코어 CRUD) | ✅ develop 머지 | PR #9 → `e5f01aa` |
| 빌드 B2 (community 이벤트/유사질문) | ✅ develop 머지 | PR #10 → `f60bce4` |
| 빌드 C (ai-svc 시드 워커) | ✅ develop 머지 | PR #23 → `f36cca2` |
| 빌드 D (gateway `/community/**`) | ✅ develop 머지 | **PR #19 → `b73af5b`** (2026-06-26) |
| 빌드 E (frontend 실API) | ⬜ 미착수 | |
| 통합 릴리스 (develop→main + image/deploy) | ⬜ 미착수 | |

## 빌드 D에서 한 것 (이번 세션)
- gateway `application.yml`·`application-test.yml`에 `id: community` 라우트 추가: `uri: ${COMMUNITY_SVC_URI:http://localhost:8086}`(기본 포트 8080~8085와 비충돌), `Path=/community/**`. JWT 엣지는 기존 `anyExchange().authenticated()`가 그대로 보호(시큐리티 무변경).
- 테스트: `CommunityRouteTest`(미인증 401 + 인증 시 라우트 매칭) + `RouteConfigTest.communityRouteIsConfigured`. 슬라이스 #7 mentor E(`MentorRouteTest`) 미러.
- Test-First 적용(라우트 전 404 red→추가 후 green). `./gradlew build` GREEN(31 tests, 0 fail). CI `build` pass. CLAUDE.md 미커밋 변경은 사용자 지시로 working tree 복원(커밋 제외).

## develop에 완성된 것 (백엔드+게이트웨이)
- Q&A 백엔드 골든패스: 질문 작성·목록·상세·답변·채택(OWNER)·투표(UPSERT 집계)·태그 자동완성. 모두 `/community/**` 하위.
- AI 시드 이벤트 왕복: `community.question.posted`(community 발행) → ai-svc consume(`AiSeedClient` Claude `claude-haiku-4-5`/Ollama/Mock + `SeedPromptBuilder` 인젝션 방어 + 질문 임베딩) → `community.seed.ready`(ai-svc 발행) → community consume(답변·메타·임베딩 영속, 멱등 `UNIQUE(question_id)`)
- 유사질문: pgvector 거리<0.20, ai-svc `/ai/embed`(768)
- **gateway 엣지**: `/community/**` → community-svc, JWT 인증 보호(방금 머지)

## 잔여 작업 (다음 세션)
1. **빌드 E (frontend)**: `apps/web/lib/src/features/community/` mock→실API(질문 작성 FAB·답변 스레드·채택·투표·🤖 AI 초안 뱃지·유사질문). 슬라이스 #7 F 패턴. `melos run analyze/test/format` 게이트. 베이스 URL은 gateway(`/community/**`). ⚠️ **WSL에 Flutter/melos 툴체인 유무 먼저 확인**(JDK처럼 별도 셋업 필요 가능 — 메모리 [[wsl-build-environment]]).
2. **통합 릴리스**: community·ai-svc·gateway·frontend develop→main PR + image/deploy(shared는 이미 main). + documents 브랜치(`docs/md3-slice8-community-spec`: 설계서+플랜4+보고서4+핸드오프2) develop PR.
3. **미커밋 정리**: 각 레포 CLAUDE.md "메인 도구 직접 호출 금지"+"PowerShell 금지·Bash만" 규칙이 working tree 미커밋(community-svc만 `817daaa` 커밋됨). gateway는 이번 세션에 사용자 지시로 working tree 복원함. ⚠️ 이 규칙은 Windows/PowerShell 전제 → WSL 작업 방침과 상충(아래 교훈·메모리 [[antml-prefix-windows-only]] 참조 후 정리 방향 결정).

## ⚠️ 환경/도구 교훈 (필수)
- **antml 프리픽스 누락은 Windows/PowerShell 한정**: 이번 WSL+Bash 세션에서 메인이 모든 도구(Read/Bash/Edit/Write/git/gh) 직접 호출로 빌드 D를 **antml 오류 0건으로 완주**. → WSL에선 메인 직접 진행 OK, 막히면 그때 서브에이전트 위임. (사용자 2026-06-26 지시. 메모리 [[antml-prefix-windows-only]])
- **PowerShell 전면 금지**: 메인·서브 모두 Bash만.
- **WSL 빌드 셋업**(이 WSL 최초 JVM 빌드, 메모리 [[wsl-build-environment]]):
  - JDK 없음·sudo 비번 필요 → Temurin 21을 `~/jdks/jdk-21.0.11+10`에 설치, `JAVA_HOME`을 `~/.zshrc`·`~/.profile`에 등록.
  - `devpath-shared:0.0.1-SNAPSHOT`는 GitHub Packages `read:packages` 필요 → `gh` 토큰(`VelkaressiaBlutkrone`, `gist,read:org,repo`)으로는 **401**. 우회: `devpath-shared`에서 `./gradlew publishToMavenLocal -x test` 후 `~/.gradle/init.gradle`에 `mavenLocal()` 전역 추가(repo build·CI 무영향, 비밀 미커밋). shared 변경 시 재publish.
  - git 신원 미설정 → global `Qahnaarin <deepestdark@gmail.com>`(기존 로컬 커밋 신원). push/PR은 `GITHUB_TOKEN=$(gh auth token)`로 동작(`repo` 스코프).
- 테스트 DB: 기본 `devpath`는 구버전 → `devpath_citest`(`DB_URL`). community 테스트는 fresh DB에 flyway 적용. CI postgres는 `pgvector/pgvector:pg17`.
- ai-svc CI: shared SNAPSHOT stale 캐시 → `ci.yml`에 `--refresh-dependencies`.
- 포트: gateway 8080·platform 8081·learning 8082·ai-svc 8083/8084·sandbox 8085·**community(gateway 기본값) 8086**. 클러스터는 내부 DNS.
- gateway route 테스트는 WebFlux+mock JWT라 DB/Kafka 불필요. community/ai-svc 테스트는 pgvector postgres·Kafka 필요.

## 참고 문서
- 설계서: `specs/2026-06-25-md3-slice8-community-qna-design.md`
- 빌드플랜: `plans/2026-06-25-md3-slice8-{shared-community-a, community-core-b1, community-events-b2, aisvc-seed-c}.md` (D는 플랜 없이 슬라이스 #7 패턴으로 구현, E 미작성)
- 보고서: `reports/2026-06-25-slice8-{b1-build, b2-build, b2-verify, c-build}-report.md`
- 직전 핸드오프: `handoff-2026-06-26-slice8-bc-done-de-next.md`

## 다음 세션 진입점
빌드 E(frontend 실API) → 통합 릴리스. WSL에서 메인 직접 진행 가능(antml 마찰 없음). E 시작 전 Flutter/melos 툴체인 확인이 첫 스텝.
