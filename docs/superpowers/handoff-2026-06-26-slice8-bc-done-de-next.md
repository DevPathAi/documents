# 핸드오프 — MD3 슬라이스 #8 커뮤니티 Q&A (2026-06-26)

> 다음 세션 이관용. 빌드 A~C 완료(A=main 릴리스, B1·B2·C=develop 머지). 남은 = D(gateway)·E(frontend)·통합 릴리스.

## 진행 상태
| 단계 | 상태 | 근거 |
|------|------|------|
| 설계서 | ✅ 커밋 | `specs/2026-06-25-md3-slice8-community-qna-design.md` (브랜치 `docs/md3-slice8-community-spec`, 미PR) |
| 빌드 A (shared 스키마+이벤트2종) | ✅ main 릴리스·publish | PR #27, `V202606251001`, `CommunityQuestionPostedEvent`/`CommunitySeedReadyEvent` |
| 빌드 B1 (community 코어 CRUD) | ✅ develop 머지 | PR #9 → `e5f01aa` |
| 빌드 B2 (community 이벤트/유사질문) | ✅ develop 머지 | PR #10 → `f60bce4` |
| 빌드 C (ai-svc 시드 워커) | ✅ develop 머지 | PR #23 → `f36cca2` |
| 빌드 D (gateway `/community/**`) | ⬜ 미착수 | |
| 빌드 E (frontend 실API) | ⬜ 미착수 | |
| 통합 릴리스 (develop→main + image/deploy) | ⬜ 미착수 | |

## develop에 완성된 것
- Q&A 백엔드 골든패스: 질문 작성·목록·상세·답변·채택(OWNER)·투표(UPSERT 집계)·태그 자동완성
- AI 시드 이벤트 왕복: `community.question.posted`(community 발행) → ai-svc consume(`AiSeedClient` Claude `claude-haiku-4-5`/Ollama/Mock + `SeedPromptBuilder` 인젝션 방어 + 질문 임베딩) → `community.seed.ready`(ai-svc 발행, Outbox produce 신규) → community consume(답변·메타·임베딩 영속, 멱등 `UNIQUE(question_id)`)
- 유사질문: pgvector 거리<0.20, ai-svc `/ai/embed`(768)
- 테스트: community 21통과(B1 11 + B2 10), ai-svc 전체 build GREEN

## 잔여 작업 (다음 세션)
1. 빌드 D (gateway): `application.yml`에 `/community/**` → community-svc 라우트 + JWT 엣지 + `CommunityRouteTest`. 슬라이스 #7 mentor E(`/ai-mentor/**`)·#6 review D 패턴.
2. 빌드 E (frontend): `apps/web/lib/src/features/community/` mock→실API(질문 작성 FAB·답변 스레드·채택·투표·🤖 AI 초안 뱃지·유사질문). 슬라이스 #7 F 패턴. `melos run analyze/test/format` 게이트.
3. 통합 릴리스: community·ai-svc·gateway·frontend develop→main PR + image/deploy(shared는 이미 main). + documents 브랜치(설계서+플랜4+보고서4+핸드오프) develop PR.
4. 미커밋 정리: 각 레포 CLAUDE.md "메인 도구 직접 호출 금지" + "PowerShell 금지·Bash만" 규칙이 working tree 미커밋(community-svc만 `817daaa` 커밋됨). 나머지 레포 별도 chore 커밋 필요.

## ⚠️ 환경/도구 교훈 (필수)
- 도구 호출 `antml:` 누락: 메인 에이전트 출력에서만 발생(텍스트→호출 전환점). 서브에이전트 내부 도구 호출은 0오류(빌드 A~C 수백 호출 전부 성공). → 메인 도구 호출 최소화, 실제 작업은 서브에이전트 위임. (메모리 [[tool-call-antml-prefix]])
- PowerShell 전면 금지: 메인·서브 모두 Bash만(분류기 불안정, 사용자 2026-06-26 지시. 메모리 [[no-powershell-bash-only]])
- 메인 도구 직접 호출 금지 규칙이 모든 CLAUDE.md에 박힘 — 메인은 계획·위임·종합만.
- 테스트 DB: 기본 `devpath`는 구버전 → `devpath_citest`(`DB_URL`). community 테스트는 fresh DB에 flyway 적용(B1 CI fix: `@ActiveProfiles("test")` + `application-test.yml` flyway + `ci.yml` postgres를 `pgvector/pgvector:pg17`로).
- ai-svc CI: shared SNAPSHOT stale 캐시 → `ci.yml`에 `--refresh-dependencies`(빌드 C fix).
- shared 브랜치: develop 부재 → `feat`→`main`. 다른 서비스는 develop 2단계.
- 인프라: docker postgres(5432 pgvector)·kafka(9092). IT는 EmbeddedKafka.

## 참고 문서
- 설계서: `specs/2026-06-25-md3-slice8-community-qna-design.md`
- 빌드플랜: `plans/2026-06-25-md3-slice8-{shared-community-a, community-core-b1, community-events-b2, aisvc-seed-c}.md` (D·E 미작성)
- 보고서: `reports/2026-06-25-slice8-{b1-build, b2-build, b2-verify, c-build}-report.md`

## 다음 세션 진입점
빌드 D(gateway 라우트) → E(frontend 실API) → 통합 릴리스. 모두 단일 오케스트레이터 서브에이전트 위임으로 진행하면 antml 마찰 없이 무중단 가능.
