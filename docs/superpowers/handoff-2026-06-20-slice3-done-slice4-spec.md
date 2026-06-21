# 세션 핸드오프 — 슬라이스 #3 전체 완료·main 릴리스 + 슬라이스 #4 설계 완료 (2026-06-20)

> **상태**: MD1 슬라이스 #3(학습경로/1st Aha) **5빌드 A~E + 커버리지 보강 + E2E 조치 전부 develop·main 릴리스 완료**. 하위 17개 CLAUDE.md에 **절대조건 4·5 규칙 추가**. **MD2 슬라이스 #4(콘텐츠 대량화+뷰어) 설계서 완료(검토 반영본)**.
> **다음 진입점**: 슬라이스 #4 **writing-plans**(빌드 A부터 빌드별 구현 플랜 작성).
> **원칙**: 각 레포 CLAUDE.md 절대조건(추측 금지·테스트 우선·문제 시 코드 분석·**신규 작업 신규 브랜치·결과 자화자찬 금지**) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock.

---

## 1. 이번 세션 완료

### 1.1 🎉 슬라이스 #3 5빌드 검증·정식화·릴리스
각 빌드는 **작업물이 develop working tree에 미커밋 방치**돼 있던 것을 검증→feat 브랜치 커밋→develop PR→CI 녹색→머지→**develop→main 릴리스**로 정식화. (이전 세션이 만들고 커밋 안 한 패턴 반복 → 검증으로 발견·정식화)

| 빌드 | 레포 | 핵심 | PR(develop·main) |
|---|---|---|---|
| A | shared | pgvector `V202606181006`(VECTOR768+HNSW) | #15·#16(publish) |
| B | ai-svc | Ollama 게이트웨이(`/ai/embed`·`/ai/path/generate`) | #5 |
| C | learning | 경로엔진(진단 join→ai-svc→pgvector 매칭→SSE→outbox) | #7 |
| C+ | learning | 커버리지 보강(edge 7종) | #8 |
| D | platform | `LearningPathGeneratedEvent`→onboarding DONE + **ci.yml pgvector 전환(R-3 누락 보완)** | #8→#9 |
| E | gateway·frontend | `/learning-paths/**` 라우트 + 경로 화면(O05) | #7·#18 |

- **develop→main 릴리스**: develop 있는 10개 레포 전부 main 반영(코드 8개 image/deploy 트리거). shared·ai-svc·learning·platform·frontend·gateway·community·sandbox·gitops·documents.

### 1.2 검증 중 잡은 핵심 이슈(전부 해결)
- **stale shared 캐시**(빌드 C): learning-svc gradle 캐시가 빌드 A 이전 shared(V…1005)에 고정→`--refresh-dependencies`로 V1006 받아 통과. CI(fresh)는 무관.
- **platform CI plain postgres**(빌드 D): 최신 shared V1006(`CREATE EXTENSION vector`)이 plain postgres CI에서 실패→ci.yml `pgvector/pgvector:pg17` 전환.
- **mockwebserver 의존성 누락**(C+): learning-svc에 없어 컴파일 실패→`build.gradle.kts` 추가.

### 1.3 CLAUDE.md 규칙 추가 (16 독립 레포 + 루트 .github)
절대조건에 **4. 신규 작업은 무조건 신규 브랜치**(세션 충돌 예방) + **5. 결과를 자화자찬하지 않는다(항상 검증·테스트)** 추가. 16 레포는 docs PR→머지(develop/main). 루트 `.github/CLAUDE.md`는 **빈 `.git`이라 커밋 불가, 파일만 적용**.

### 1.4 E2E 수동검증(39번 보고서) 확인 + 조치 정식화
- **39번 보고서**(`documents/39_E2E_수동검증_보고서_2026-06-20.md`)는 이미 작성·정확(6항목 충족, 증적 inspect.png 실재). untracked였던 것을 develop·main 릴리스(documents #20·#21).
- ⚠️ **E2E 발견 조치 6.1~6.4가 미커밋→앞선 main 릴리스에 누락**을 검증으로 발견→정식화:
  - **6.1** ai-svc 빈 concept 허용(`@NotEmpty`→`@NotNull`) #8→#9
  - **6.2** learning SSE timeout 설정값(`devpath.path.sse-timeout-ms` 기본 180s) #11→#12
  - **6.3/6.4** frontend `loadOrStart`(기존 ACTIVE 경로 우선)+auth 경합 #21→#22
  - **D2 golden 충돌**: loadOrStart가 GET /me 먼저 호출→목 200 반환으로 "다시 생성" 시나리오 무효→**동적 페이크 apiClient**(GET /me 첫 404→이후 200)로 수정, web 100/100.
  - ⚠️ **서브에이전트 D2 위임 시 범위 이탈**(dashboard/auth/web_mock_fixtures 즉흥 수정)→Scope Lock대로 reset 후 직접 수정.

### 1.5 MD2 슬라이스 #4 설계 완료
- 브레인스토밍(결정 8개)→설계서 `documents/docs/superpowers/specs/2026-06-20-md2-slice4-content-design.md`→**사용자 검토 반영본**(실저장소 대조 보강, 결정 D-1~D-12, 빌드 6분해).
- **교차검증 완료**: 보강의 현재 상태 주장(gateway `/contents/**` 없음·Content `content_md` 미매핑·web ContentController `markdown` 기대·목 fixture `GET /contents/c1`) 전부 실저장소 일치. 추가 발견=Content 엔티티 `difficulty`도 미매핑(빌드 C에서 projection/매핑 보완).

## 2. 다음 세션 진입점 (여기서 시작)

**슬라이스 #4 writing-plans — 빌드별 구현 플랜 작성**(슬라이스 #1~#3 패턴: 설계서→빌드 플랜→subagent-driven 실행).

### 슬라이스 #4 확정 설계 (설계서 기준)
- 범위: 콘텐츠/문항 **데이터 대량화 + 콘텐츠 뷰어 API + 진척 추적**.
- 생성: **로컬 Ollama qwen2.5 오프라인 배치**(런타임 LLM 없음, CI Ollama 실호출 금지) + 자동 검증 + 사람 수검수. SSoT=승인 JSON+seed SQL.
- 규모: 문항 500(5 track×100, **MCQ 70%·CODE_READING 30%·SHORT_ANSWER 0%**) + 콘텐츠 150(5 track×30) + 임베딩.
- 진척: 신규 `user_content_progress`(scroll_pct·dwell_sec, **완료=scrollPct≥0.8 AND dwellSec≥45**)→ACTIVE path task 자동완료.
- **빌드 분해(6)**: A(shared `user_content_progress` 릴리스) → B1(문항 배치 500) → B2(콘텐츠 배치+임베딩 150) → C(뷰어 API+진척+Content `content_md`/`difficulty` 매핑) → D(gateway `/contents/**` 라우트) → E(frontend 뷰어 화면+진척). 권장 순서 A→C skeleton→D→E, B1/B2 병렬.
- 적재: **seed**로(shared 마이그레이션=스키마 전용). 슬라이스 #2 QuestionBankSeeder 패턴.

### 빌드 A 첫 작업 (writing-plans 산출)
shared `user_content_progress` 마이그레이션(`V20260620...` 또는 다음 번호) + FlywayMigrationTest(unique·check·trigger·cascade) → develop→main 릴리스(publish) 선행.

## 3. 잔여/선택
- 빌드 C 동시성 409 테스트(슬라이스 #3 의도적 미포함, 선택).
- 루트 `.github/CLAUDE.md` 버전관리(빈 .git — git init 여부 사용자 결정).
- 배포 env(슬라이스 #3 끝단간 staging): gateway `LEARNING_URI`, learning `AI_SVC_BASE_URL`·Redis/Kafka, ai-svc `OLLAMA_*`, platform 동일 `JWT_SECRET`.

## 4. 핵심 교훈 (이번 세션)
- **미커밋 작업물이 develop에 방치→릴리스 누락**: 검증(코드 git 상태·테스트 직접 실행)으로 발견. "이 세션에서 안 했다≠안 됐다"(추측 단정 금지=절대조건 5).
- **다운스트림 CI 이미지/shared 의존**: shared 릴리스가 learning(빌드 C)·platform(빌드 D) ci.yml pgvector 전환 유발. fresh DB로 CI 동등 검증.
- **서브에이전트 범위 이탈**: 위임 시 Scope Lock 명세+컨트롤러 직접 검증, 이탈 시 reset.
- **CLAUDE.md 일괄 편집**: Python 미설치(WindowsApps stub)→PowerShell(UTF-8 무BOM) 사용.

## 5. 관련 문서/메모리
- 설계서: `documents/docs/superpowers/specs/2026-06-20-md2-slice4-content-design.md`
- E2E 보고서: `documents/39_E2E_수동검증_보고서_2026-06-20.md`
- 메모리(SSoT): [[md1-slice1-progress]](슬라이스 #1~#3 진행+E2E) · [[subagent-final-message-suppressed]] · [[no-guessing-test-first]] · [[w1-infra-postgres]]

---

## 추신 — 슬라이스 #4 완료(2026-06-21)

빌드 A~E **6개 전부 develop 머지 완료**(상단 spec 작성 시점엔 D·E만 완료였으나 이후 A·B1·B2·C도 완료, 메모리 갱신만 누락됐던 것을 검증으로 확정): A=shared PR #19/#20(+publish), B1=learning PR #13(문항 500), B2=PR #14(콘텐츠 150+임베딩), C=PR #15(뷰어/진척 API), D=gateway PR #10, E=frontend PR #23. CI 전부 녹색, 산출물 실측 일치.

- **E2E**: 백엔드(learning)+gateway 경유 끝단간 실증 — 콘텐츠 조회·진척 monotonic·임계 완료·task 자동완료·대시보드 33→67%·404/400/401. web mock 렌더·인터랙션 확인. 콘텐츠 뷰어 화면 브라우저 캡처는 flutter web headless 자동화 한계로 미달(위젯 테스트로 검증). 보고서: `documents/40_E2E_수동검증_보고서_2026-06-21_슬라이스4.md`.
- **정리**: learning-svc 워크트리 b1/b2/c 제거·머지/빈 브랜치 삭제, frontend 누락 테스트 `path_sse_event_test.dart` 복구(PR #25 develop 머지).
- **빌드 A 첫 작업(위 §2)**: 이미 `V202606201001__user_content_progress.sql`로 완료됨(파일명 날짜 06-20). 위 spec의 "빌드 A 첫 작업" 지시는 종료.
- **잔여**: 빌드 C 동시성 409 테스트(여전히 선택). **신규 발견**: ① B2 콘텐츠 dev seeder 부재(메인 DB에 150 콘텐츠 미적재 — `QuestionBankSeeder`만 존재) ② frontend `dp_core` 생성파일 line-ending 노이즈(.gitattributes 후속).
