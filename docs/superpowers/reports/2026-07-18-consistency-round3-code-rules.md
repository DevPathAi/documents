# 정합성 3차 — 축③ 코드 규칙 점검

## 기준

### 기준 SHA (origin/develop 고정)
| 레포 | SHA | 레포 | SHA |
|------|-----|------|-----|
| devpath-platform-svc | 4c1ca4f | devpath-notification-svc | 0afddfd |
| devpath-learning-svc | 0461c4f | devpath-gateway | c8a1282 |
| devpath-community-svc | 043b830 | devpath-frontend | e6be351 |
| devpath-sandbox-svc | a6d802e | devpath-shared | ff7f5a6 |
| devpath-ai-svc | 69d5e0f | devpath-svc-template | b6c33ee |
| devpath-lcs-svc | bd64ada | devpath-gitops | ece471d |

전 12개 레포 baseline SHA는 `git rev-parse --short`로 실제 reachable함을 확인(모두 자기 자신으로 해석).

### 규칙 요지
- **09_Git_규칙_정의서 §2 (커밋)**: Conventional Commits `<type>(<scope>): <subject>`. type 화이트리스트 = feat/fix/refactor/perf/test/docs/style/build/ci/chore/revert. §2.5 금지: `WIP`·`fix typo` 단독, 여러 논리 변경 1커밋, 빌드 산출물 커밋. §8.1 금지: OAuth 토큰·Claude 키·결제 키 커밋. §8.2: 비밀 유출 시 즉시 revoke + `git filter-repo`.
- **12_코드_리뷰_규칙 §3.3 (데이터)**: Flyway 이름 컨벤션 `V{date_seq}__{snake}.sql`. §3.5 (보안): 비밀키 하드코딩 없음, OAuth 토큰 암호화 저장. §3.4 (API): 에러 코드 일관성.
- **에러 envelope SSoT** = 앞선 라운드에서 확립된 스펙 §3.4 중첩 envelope. shared 컨트랙트 = `ai.devpath.shared.error.ApiException` + `ApiExceptionHandler`(공용 @RestControllerAdvice) + `ErrorResponse`. svc는 `@Import(ApiExceptionHandler.class)`로 채택하거나 svc-local advice가 shared `ErrorResponse`로 envelope 통일해야 함.
- **10_환경_설정_템플릿 §3 원칙**: `.env` 절대 커밋 금지, `.env.example`만 커밋(플레이스홀더). staging/prod = AWS Secrets Manager + External Secrets. OAuth secret / LLM key / KMS 키 월 1회 회전.

## 방법
- 코드 레포는 **읽기 전용**. `git -C <절대경로>` 로만 접근(log/ls-tree/grep/show). 상태 변경 명령 미사용.
- Windows 경로 백슬래시가 Bash 툴에서 소실되어 전 명령을 **PowerShell + 절대경로**로 실행.
- (1) 커밋: `git -C <repo> log <SHA> --no-merges --format='%s' -30`.
- (2) Flyway: `git -C <svc> ls-tree -r <SHA> --name-only` 후 `.sql` / `db/migration` 필터.
- (3) envelope: `git -C <svc> grep -nE 'ErrorResponse|ProblemDetail|RestControllerAdvice|ExceptionHandler|ApiException' <SHA> -- '*.java'` + 컨트롤러 존재 여부 교차확인.
- (4) 시크릿: 지정 정규식 스캔 + 보강 광역 스캔(password|secret|apikey|token|credential|client-secret|private-key)으로 `.yml/.yaml/.properties/.env/.env.example` 전수.
- (5) 위생: `ls-tree`에서 `.omc/`·`build/`·`.gradle/`·`node_modules/` 추적 여부 + `git show <SHA>:.gitignore`의 `.omc/` 포함.
- grep이 매치 없을 때 exit 1, gitops의 `.gitignore` 부재 시 `git show` exit 128 — 모두 정상 신호(실패 아님)로 결과 해석에 반영.

## 실측

### (1) 커밋 컨벤션 위반 (각 레포 최근 30 non-merge)
전 12개 레포 최근 30개 non-merge 커밋 subject를 전수 확인. **Conventional Commits 위반 0건.** 모든 커밋이 `type(scope): subject` 또는 `type: subject` 형식이며 type이 화이트리스트에 속함.
- svc 7종·gateway·frontend·shared·svc-template: feat/fix/refactor/test/docs/ci/chore/style/perf만 관측. scope 활용 양호(`feat(path)`, `feat(mypage)`, `fix(sandbox)` 등).
- **devpath-gitops**: 최근 30개 중 다수가 `deploy(devpath-xxx): <full-sha>` 형태. 이는 ArgoCD Image Updater(또는 kustomize 태그 자동 write-back) **자동 생성 커밋**. `deploy`는 09 문서 type 화이트리스트에 **명시되지 않은 커스텀 type**이나, `type(scope): subject` 문법 자체는 준수. 사람 손 커밋(`docs(spec)`, `feat(platform)`, `feat(lcs)`, `ci:`)은 전부 표준 준수 → **관찰(판정 보류)** 로 분류.
- `WIP`/`fix typo` 단독 커밋: **0건**.

### (2) Flyway 네이밍 위반
**핵심 발견: 마이그레이션은 `devpath-shared` 단일 소스에 중앙집중.** 7개 svc(platform/learning/community/sandbox/ai/lcs/notification)는 `db/migration` 하위 `.sql`을 **하나도 보유하지 않음**(svc-local Flyway 파일 0). learning-svc만 `.sql` 7개 존재하나 전부 **seed 데이터**(`db/seed/`, `test/resources/seed/`, `tools/content-gen/generated/seeds/`)로 Flyway 대상 아님.
- `devpath-shared:src/main/resources/db/migration/` 에 **31개** 마이그레이션. 전수 대조 결과 **위반 0건.** 모두 `V{yyyyMMddHHmm}__{snake_case}.sql` 준수(예: `V202606150900__init_common.sql`, `V202607171001__beta_allowlist.sql`). 타임스탬프 12자리 단조 증가, 설명은 snake_case.
- 규칙 문서(§3.3)의 예시 `V{date_seq}__{snake}.sql`와 정합. **Flyway 네이밍 위반 0건.**

### (3) 에러 envelope 3분류

| svc | 분류 | 근거(파일:라인) |
|-----|------|----------------|
| platform-svc | **사용(shared)** | `PlatformApplication.java:12 @Import(ApiExceptionHandler.class)`; 도메인 예외 `ConsentRevokeConflictException extends ApiException` |
| community-svc | **사용(shared)** | `CommunityApplication.java:11 @Import(ApiExceptionHandler.class)`; `ForbiddenException extends ApiException` |
| sandbox-svc | **사용(shared)** | `@Import(ApiExceptionHandler.class)`; `SessionNotFoundException extends ApiException`; `RunControllerEnvelopeTest`로 envelope 회귀검증 |
| ai-svc | **사용(shared)+독자 병행** | `AiApplication.java:11 @Import(ApiExceptionHandler.class)` + Ollama 전용 `OllamaExceptionHandler`(@RestControllerAdvice) 병존. 도메인 예외 `MentorKillSwitchException`/`ReviewNotFoundException extends ApiException` |
| lcs-svc | **사용(shared)** | `LcsApplication.java:9 @Import(ApiExceptionHandler.class)`; `ForbiddenException`/`NotFoundException extends ApiException`; `LcsControllerTest`로 envelope 검증 |
| learning-svc | **독자구현(shared ErrorResponse 재사용)** | `config/GlobalExceptionHandler.java` = svc-local `@RestControllerAdvice`. 공용 `ApiExceptionHandler`를 @Import하지 **않고** shared `ErrorResponse`로 envelope만 통일(주석 L22~23 명시). body = `ErrorResponse.of(code, message, null, Instant.now())` |
| notification-svc | **미사용** | REST 컨트롤러 3종 존재(`DeviceController`, `PrefsController`, `InternalPrefsController`)하나 전역 핸들러·`ApiException`·`ErrorResponse` 참조 **전무**(grep 0 hit) |

요약: **사용(shared) 5** (platform·community·sandbox·ai·lcs) / **독자구현 1** (learning, 단 shared ErrorResponse 재사용) / **미사용 1** (notification).

### (4) 시크릿 전건 (플레이스홀더/실값 판정)
지정 정규식 + 광역 보강 스캔 전수. **실 프로덕션 시크릿 커밋 0건.** 전 hit이 플레이스홀더·CI 참조·k8s secretKeyRef·dev 로컬 자격증명·의존성 주석.

| # | 파일:라인 | 값 | 판정 |
|---|-----------|-----|------|
| 1 | gateway `src/test/resources/application-test.yml:36` | `JWT_SECRET: "test-secret-please-change-min-32-bytes-long-0123456789"` | 플레이스홀더(test-, please-change) — 테스트 전용 |
| 2 | platform `src/main/resources/application.yml:34` | `client-secret: ${GITHUB_CLIENT_SECRET:dummy-secret}` | env 참조 + dummy 기본값 |
| 3 | platform `application.yml:38` | `client-secret: ${GOOGLE_CLIENT_SECRET:dummy-secret}` | env 참조 + dummy 기본값 |
| 4 | platform `application.yml:52` | `jwt-secret: ${JWT_SECRET:test-secret-please-change-...}` | env 참조 + 플레이스홀더 기본값 |
| 5 | platform `application.yml:7` | `password: ${DB_PASSWORD:localdev}` | env 참조 + dev 기본값 |
| 6 | platform `src/test/resources/application-test.yml:3,16` | `jwt-secret: test-secret-...` / `client-secret: test-secret` | 테스트 전용 플레이스홀더 |
| 7 | platform/shared/frontend `.github/workflows/ci.yml` | `${{ secrets.GITHUB_TOKEN }}`, `${{ secrets.GITOPS_APP_ID }}`, `${{ secrets.GITOPS_APP_PRIVATE_KEY }}` | GitHub Actions secrets 참조(값 아님) |
| 8 | shared/platform `ci.yml` + shared `docker-compose.yml:15,30` | `POSTGRES_PASSWORD: localdev`, `DB_PASSWORD: localdev` | dev 로컬 자격증명 |
| 9 | shared `docker-compose.yml:78` | `MINIO_ROOT_PASSWORD: localdev123` | dev 로컬 MinIO 자격증명(로컬 compose 전용) |
| 10 | gitops `apps/devpath-platform-svc/base/deployment.yaml:29~49` | `secretKeyRef` (github/google-client-secret 등) | k8s Secret 참조(SealedSecret 복호화, 값 미포함) |
| 11 | frontend `apps/mobile/pubspec.yaml:28,42` | `flutter_secure_storage`, `firebase_messaging` 주석 내 token 언급 | 의존성/주석 — 값 아님 |

→ 전건 플레이스홀더/참조. **실값 의심 실질 0건.** (약한 의심 후보로 gitops의 dev-only `localdev123`을 관찰 항목에 기록.)

### (5) 레포 위생 표

| 레포 | .omc/ 추적? | build/ | .gradle/ | node_modules/ | .gitignore에 .omc/? | .gitignore |
|------|:----------:|:------:|:--------:|:-------------:|:-------------------:|:----------:|
| platform-svc | X | X | X | X | NO | 있음 |
| learning-svc | X | X | X | X | NO | 있음 |
| **community-svc** | **7 파일** | X | X | X | **NO** | 있음 |
| sandbox-svc | X | X | X | X | NO | 있음 |
| ai-svc | X | X | X | X | NO | 있음 |
| **lcs-svc** | **2 파일** | X | X | X | **NO** | 있음 |
| notification-svc | X | X | X | X | NO | 있음 |
| gateway | X | X | X | X | NO | 있음 |
| frontend | X | X | X | X | **YES** | 있음 |
| shared | X | X | X | X | **YES** | 있음 |
| svc-template | X | X | X | X | NO | 있음 |
| gitops | X | X | X | X | NO | **없음** |

추적된 `.omc/` 상세:
- community-svc(7): `.omc/sessions/48ea89e8-...json`, `.omc/state/agent-replay-48ea89e8-...jsonl`, `.omc/state/idle-notif-cooldown.json`, `.omc/state/last-tool-error.json`, `.omc/state/mission-state.json`, `.omc/state/sessions/51cb1195-.../hud-state.json`, `.omc/state/subagent-tracking.json`
- lcs-svc(2): `.omc/state/hud-stdin-cache.json`, `.omc/state/sessions/51cb1195-.../hud-state.json`

build/·.gradle/·node_modules/ 추적: **전 레포 0건**(양호).

## 불일치 후보

| # | 위치 | 근거 | 우선순위 | 수정방향 |
|---|------|------|:--------:|----------|
| C-1 | notification-svc (REST 컨트롤러 3종) | 전역 예외 핸들러·shared `ApiExceptionHandler`/`ErrorResponse` **전무**(grep 0). §3.4 에러 코드 일관성·envelope SSoT 미채택 | **P1** | `NotificationApplication`에 `@Import(ApiExceptionHandler.class)` 추가, 도메인 예외를 `ApiException` 파생으로 정리. envelope 회귀 테스트 추가 |
| C-2 | community-svc `.omc/` 7파일 추적 | OMC 런타임 세션/상태 아티팩트(session json, hud-state, mission-state 등) 커밋됨. §2.5 "빌드/도구 산출물 커밋 금지" 취지 위반 | **P1** | `git rm -r --cached .omc/` + `.gitignore`에 `.omc/` 추가(frontend/shared 선례). agent-replay·session json에 대화/도구 컨텍스트 노출 우려 있어 신속 처리 권장 |
| C-3 | lcs-svc `.omc/` 2파일 추적 | 동일 OMC 아티팩트(hud-stdin-cache, hud-state) 커밋 | **P1** | C-2와 동일 조치 |
| C-4 | 10개 svc/gateway/svc-template `.gitignore`에 `.omc/` 누락 | frontend·shared만 `.omc/` ignore. 나머지는 향후 재유입 위험(community·lcs가 실제 유입 사례) | **P2** | 전 레포 `.gitignore`에 `.omc/` 추가(svc-template에 먼저 넣어 신규 svc 상속) |
| C-5 | gitops `.gitignore` 부재 | 레포에 `.gitignore` 자체가 없음(`git show ...:.gitignore` → exit 128). 아티팩트 유입 방어선 없음 | **P2** | 최소 `.omc/`, `.DS_Store`, 에디터 캐시를 담은 `.gitignore` 신설 |

## 관찰 (판정 보류)

- **O-1 (gitops `deploy(...)` 커밋 type)**: 최근 30개 다수가 `deploy(devpath-xxx): <sha>` 자동 write-back 커밋. `deploy`는 09 문서 type 화이트리스트에 없으나 CI/ArgoCD가 자동 생성하는 커밋으로 사람 커밋 규칙 적용 대상이 아님. 위반으로 단정하지 않되, 문서 §2.2 type 표에 `deploy`(자동 배포 write-back) 명문화 여부는 정책 결정 필요.
- **O-2 (learning-svc 독자 advice)**: learning-svc는 공용 `ApiExceptionHandler`를 @Import하지 않고 svc-local `GlobalExceptionHandler`를 유지하되 shared `ErrorResponse`로 envelope는 통일(주석에 "전 상태 보존, 회귀 0" 의도 명시). envelope 형식은 SSoT 정합하나 **핸들러 코드가 svc마다 갈라져** 향후 매핑 드리프트 가능. 통일 여부(공용 advice로 수렴)는 리팩토링 트랙에서 재검토 권장.
- **O-3 (ai-svc `OllamaExceptionHandler` 병존)**: 공용 advice + Ollama 전용 advice 2개 @RestControllerAdvice 병존. 의도된 설계(Ollama 계약 예외 국소화)로 보이나 advice 우선순위/중복 매핑 여부는 실행 시 검증 필요.
- **O-4 (dev-only `localdev123`)**: shared `docker-compose.yml:78` MinIO 로컬 비밀번호. 로컬 compose 전용이라 실 위험 없음. 프로덕션 경로(SealedSecret/External Secrets)와 분리되어 있음을 확인. 실값 시크릿 아님.
- **O-5 (Flyway 중앙집중 구조)**: 마이그레이션이 shared 단독 관리 → svc-local Flyway 위반이 원천 차단되는 구조. 규칙 문서(§3.3)는 svc별 Flyway를 전제한 서술이라, "마이그레이션은 shared 소유" 원칙을 문서에 명문화하면 정합성↑.
