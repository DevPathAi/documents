# MD2 슬라이스 #5 — Sandbox(격리 코드 실행) 설계서

> **마일스톤/Tier**: MD2 · Tier-1(데모 필수). 의존: #4 콘텐츠 → **#5 Sandbox** → #6 AI 코드리뷰(2nd Aha).
> **상태**: brainstorming 확정(2026-06-22). 다음 단계 = writing-plans(빌드별 구현 플랜).
> **출처**: [17_스케줄 §2 슬라이스 #5](../../../17_스케줄.md) · [02_ERD §6 Sandbox 도메인](../../../02_ERD_문서.md) · 프론트 실측 계약(`apps/web/.../features/sandbox/*`).

---

## 1. 목표 (Goal)

콘텐츠 실습 코드를 **안전하게 격리 실행**하고 결과 로그를 **SSE로 실시간 스트리밍**하는 끝단간 경로를 web에서 실API로 완성한다. sandbox-svc는 현재 백지(스켈레톤만)이므로 이번 슬라이스에서 도메인을 처음부터 구축한다. 다음 슬라이스(#6 AI 리뷰)가 소비할 `SandboxRunSubmittedEvent` 연결점을 발행한다.

**완료 기준(DoD)**: web 에디터에서 코드 작성 → `POST /sandbox/run` → 격리 컨테이너 실행 → 실행 로그 SSE 수신·표시 → `sandbox_sessions` 기록 → `SandboxRunSubmittedEvent` 발행. Java21/Node20/Python3.12 각 언어 정상·실패·타임아웃 케이스가 CI(Docker)에서 검증된다.

---

## 2. 확정 결정 (brainstorming 2026-06-22)

- **D-1 격리 전략 = `RunnerBackend` 추상화 + plain Docker 백엔드.** 실행을 인터페이스로 추상화하고 MVP는 `DockerRunnerBackend`(plain Docker)로 구현. **gVisor(runsc)는 교체 구현으로 자리만 두고 MD4 보안강화로 이연.** 이유: ERD/스케줄은 gVisor를 명시하나 gVisor는 Linux 전용이라 Windows dev에서 직접 실행·검증 불가(Docker Desktop은 runsc 런타임 미지원). 추상화로 dev 검증 가능성과 운영 격리 교체성을 동시 확보.
- **D-2 실행 모델 = SSE(프론트 계약 확정).** 프론트 실측: `sandbox_run_source.dart`가 `client.sse('/sandbox/run', body:{code})`로 `Stream<SseEvent>`를 구독, `run_controller.dart`가 `event:'log'` data를 로그에 append, 스트림 종료=`RunDone`, `503 SANDBOX_UNAVAILABLE`=`RunUnavailable`(실행만 비활성·편집 유지). 동기/폴링 미채택.
- **D-3 언어 = Java21 / Node20 / Python3.12 다언어.** 계약에 `language` 추가(프론트 소폭 수정). 언어별 Docker 이미지·실행 커맨드.
- **D-4 컨테이너 = 온디맨드.** 요청마다 생성→실행→삭제(단순·격리 깨끗). 스케줄의 "컨테이너 풀"은 성능 최적화로 후속(관리·재사용 시 상태 오염 위험 회피).
- **D-5 영속 = `sandbox_sessions` 기록.** 매 실행을 세션으로 기록(상태머신·stdout/stderr·exit_code·리소스 사용량).
- **D-6 이벤트 = `SandboxRunSubmittedEvent` 발행(outbox).** 슬라이스 #1~#3 outbox 패턴 재사용. **이번엔 발행만**(소비자는 #6 AI 리뷰에서). 
- **D-7 Docker 접근 = 호스트 Docker socket(MVP).** `docker-java` 클라이언트로 호스트 데몬 제어. 운영 보안(소켓 프록시·전용 러너 호스트)은 후속.
- **D-8 제외(후속)**: `sandbox_quotas`(실행 제한)·컨테이너 풀·`sandbox_test_results`(과제 테스트 채점)·gVisor. 미생성/미구현.

---

## 3. 아키텍처 / 컴포넌트

```
RunController (POST /sandbox/run, produces text/event-stream)
   └─▶ SandboxRunService           세션 상태머신 · 영속 · 이벤트 발행 · SSE 오케스트레이션
          └─▶ RunnerBackend (interface)        run(spec) → 로그 스트림 + 실행 결과
                 └─▶ DockerRunnerBackend (plain Docker 구현, docker-java)
                        · 언어별 이미지: eclipse-temurin:21-jdk · node:20-alpine · python:3.12-slim
                        · 온디맨드 컨테이너 + 보안 옵션(§7)
                        · 임시 워크스페이스에 코드 파일 작성 → 컨테이너 마운트(ro) → 언어별 실행
                        · stdout/stderr 실시간 → 로그 콜백/스트림
                 └─▶ (후속) GvisorRunnerBackend · PooledRunnerBackend
```

- **단위 테스트는 `RunnerBackend` mock**(가짜 로그 스트림), **통합 테스트는 `DockerRunnerBackend` 실제 Docker**. 인터페이스 경계로 Docker 의존을 격리.
- sandbox-svc는 Spring Boot 4·Java 21(타 서비스 동형). 자체 JWT 자체검증(oauth2ResourceServer, gateway 엣지+Authorization 전달, `userId=jwt.getSubject()`) — 슬라이스 #2/#3 패턴.

---

## 4. 데이터 모델 (빌드 A = devpath-shared Flyway)

**`sandbox_sessions`** (ERD §6 기준 + `language` 보강):

| 컬럼 | 타입/비고 |
|---|---|
| id | PK |
| user_id | 소유자(jwt subject). **교차서비스 FK 없음**(슬라이스 #2 교훈) |
| content_id | nullable(실습 콘텐츠 연결, MVP 선택) |
| code_block_id | nullable |
| **language** | VARCHAR + CHECK(JAVA/NODE/PYTHON) — **ERD 미존재, 신규 추가** |
| container_id | VARCHAR nullable |
| status | VARCHAR + CHECK(ALLOCATING/RUNNING/COMPLETED/FAILED/KILLED) |
| started_at / finished_at | timestamptz |
| submitted_code | TEXT |
| stdout / stderr | TEXT |
| exit_code | INT nullable |
| cpu_ms_used / memory_mb_peak | 리소스 사용량 nullable |

- 인덱스: `(user_id, started_at DESC)`(실습 이력). `set_updated_at` 트리거(공통 규약).
- **`SandboxRunSubmittedEvent`**(shared 이벤트 클래스, 토픽 `sandbox.run.submitted`): runId·userId·language·contentId? 등 최소 payload.
- outbox: 슬라이스 #1~#3 패턴(서비스 로컬 outbox 테이블 + 릴레이). `sandbox_quotas`·`sandbox_test_results`는 **이번 미생성**.
- ⚠️ ERD 문서(02)에 `language` 컬럼 교차 갱신(문서 정합성).

---

## 5. API 계약

**`POST /sandbox/run`** (인증 필요, SSE)
- 요청 body: `{ "code": "<소스>", "language": "JAVA|NODE|PYTHON", "contentId"?: "...", "codeBlockId"?: "..." }`
- 응답: `text/event-stream` — `event: log`(data=로그 라인) 반복 → **스트림 종료=실행 완료**(프론트 `RunDone`).
- 오류: **`503 SANDBOX_UNAVAILABLE`**(Docker 불가/백엔드 비활성 → 프론트 `RunUnavailable`, 편집 유지). 인증 실패 401.
- ⚠️ **프론트 계약 변경**: 현재 `sandbox_run_source.dart`는 body `{code}`만 → **`language` 추가**(빌드 D). exit_code 등 상세 결과는 프론트가 로그로만 표시(계약 최소 유지), 정밀 데이터는 `sandbox_sessions`에 기록.

**gateway**: `/sandbox/**` → sandbox-svc 라우트(SANDBOX_URI), JWT 엣지 검증. 슬라이스 #3 `/learning-paths/**`·#4 `/contents/**` 라우트 추가 패턴 동일.

---

## 6. 실행 흐름 · 상태머신 · 에러

```
1. POST /sandbox/run {code, language}  (인증)
2. SandboxSession 생성 → status=ALLOCATING (user_id, language, submitted_code)
3. SandboxRunSubmittedEvent → outbox (발행만)
4. RunnerBackend.run:
     컨테이너 생성 → status=RUNNING
     코드 주입 → 언어별 실행
     stdout/stderr 실시간 → SSE 'log' 중계
     30s 타임아웃 → SIGKILL → status=KILLED
     정상 종료 → exit_code 수집 → status=COMPLETED(0) | FAILED(≠0)
     컨테이너 삭제(finally)
5. 세션 업데이트(finished_at·stdout·stderr·exit_code·cpu_ms·memory_mb_peak)
6. SSE 스트림 종료(done) → 프론트 RunDone
```

- **컴파일/런타임 에러는 정상 흐름**(stderr 로그 + exit_code≠0, FAILED) — 503 아님.
- **타임아웃**: 30s wall-clock 초과 시 컨테이너 강제 종료, "실행 시간 초과(30s)" 로그 + KILLED.
- **Docker 불가**: 컨테이너 생성 실패/데몬 미가동 → `503 SANDBOX_UNAVAILABLE`.

---

## 7. 보안 (다층 격리 — plain Docker)

| 항목 | 적용 |
|---|---|
| 네트워크 | `--network none`(외부 차단, 루프백만) |
| 메모리/CPU | `--memory 512m` · `--cpus 1` · `--pids-limit`(예: 128) |
| 권한 | `--user nobody`(비root) · `--cap-drop ALL` · `--security-opt no-new-privileges` |
| 파일시스템 | `--read-only` rootfs + tmpfs(`/tmp` 쓰기) · 코드 마운트 ro |
| 시간 | 30s wall-clock → SIGKILL |
| 입력 | 코드 크기 제한(예 64KB) · 동시 실행 기본 상한 |

- **gVisor(runsc)**: `RunnerBackend` 교체 구현으로 MD4 보안강화에서 추가. MD4 "Sandbox pentest(격리 탈출 자동 테스트)"와 연계.

---

## 8. 테스트 전략 (이전 슬라이스 핵심 교훈 반영)

- **단위(Docker 불요·항상 실행)**: `SandboxRunService` + `RunnerBackend` **mock** — 세션 상태머신, 이벤트 발행, 영속, 에러 매핑(503/타임아웃/exit_code), SSE 응답 형식(MockMvc/WebTestClient).
- **통합(`@Tag("docker")`·CI Docker)**: `DockerRunnerBackend` **실제 컨테이너 실행** — 언어별 hello-world(정상), 무한루프(타임아웃→KILLED), 네트워크 시도 차단, exit_code≠0(FAILED).
- ⚠️ **"로컬 Docker가 CI를 가린다"**(슬라이스 #2/#3 교훈): 통합은 **CI(GitHub Actions linux + docker)에서 실증**, 로컬 통과만 신뢰하지 않는다. 단위는 Docker 없는 job에서도 항상 녹색. 모든 `@SpringBootTest`는 `@ActiveProfiles("test")`, Boot4 모듈 분리(@AutoConfigureMockMvc 등) 승계.

---

## 9. 빌드 분해 (subagent-driven, 슬라이스 #1~#4 동형)

| 빌드 | 레포 | 핵심 | 비고 |
|---|---|---|---|
| **A** | devpath-shared | `sandbox_sessions` 마이그레이션(+`language`·CHECK·인덱스·트리거) + `SandboxRunSubmittedEvent` + FlywayMigrationTest | **develop→main 릴리스(publish) 선행** |
| **B** | devpath-sandbox-svc | RunController(SSE) + SandboxRunService(상태머신·세션·outbox 발행) + `RunnerBackend` + `DockerRunnerBackend`(다언어·보안·docker-java) + 단위/통합 테스트 + redis/kafka·docker deps 활성 | **큰 빌드** → writing-plans에서 **B1(코어 골격: 인터페이스·서비스·SSE·단위, Runner는 단일언어/mock 통합)** · **B2(DockerRunnerBackend 다언어·보안·CI Docker 통합)** 분리 판단 |
| **C** | devpath-gateway | `/sandbox/**` 라우트 + JWT 엣지 + 라우팅 테스트 | 슬라이스 #3/#4 패턴 |
| **D** | devpath-frontend | `sandbox_run_source`/`run_controller` 실API 전환(`language` 추가) + 위젯 테스트 | 프론트 계약 최소 유지 |

- **권장 순서**: A(릴리스) → B(B1→B2) → C → D.
- 실행 방식: executor(sonnet) + 컨트롤러 직접검증 + fresh DB/CI 검증 + 전체 브랜치 리뷰(opus). Scope Lock 준수.

---

## 10. 제외 범위 (이번 슬라이스 밖 — 후속)

- **gVisor(runsc) 격리** → MD4 보안강화(`RunnerBackend` 교체).
- **컨테이너 풀(웜 재사용)** → 성능 최적화 후속.
- **`sandbox_quotas` 실행 제한**(일/월) → 남용 방지 후속.
- **`sandbox_test_results` 과제 채점**(콘텐츠 code_block 테스트케이스) → #6 연계 또는 후속.
- **`SandboxRunSubmittedEvent` 소비** → 슬라이스 #6 AI 코드리뷰.

---

## 11. 관련 문서

- 스케줄: [17_스케줄 §2](../../../17_스케줄.md) · ERD: [02_ERD §6](../../../02_ERD_문서.md) · 아키텍처: [03](../../../03_프로젝트_아키텍처_정의서.md) · API: [04](../../../04_API_명세서.md)
- 선행 슬라이스 설계서: [#4 콘텐츠](2026-06-20-md2-slice4-content-design.md) · [#3 학습경로](2026-06-18-md1-slice3-learning-path-design.md)
- 프론트 실측: `devpath-frontend/apps/web/lib/src/features/sandbox/{data/sandbox_run_source,application/run_controller,state/run_state}.dart`
