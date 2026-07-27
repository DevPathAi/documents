# 정합성 3차 — 축① 전체 구조 점검

## 기준

모든 실측은 각 레포 `origin/develop`의 아래 고정 SHA를 기준으로 한다(과제 지시 기준 SHA).

| 레포 | SHA |
|------|-----|
| platform-svc | 4c1ca4f |
| learning-svc | 0461c4f |
| community-svc | 043b830 |
| sandbox-svc | a6d802e |
| ai-svc | 69d5e0f |
| lcs-svc | bd64ada |
| notification-svc | 0afddfd |
| gateway | c8a1282 |
| frontend | e6be351 |
| shared | ff7f5a6 |
| svc-template | b6c33ee |
| gitops | ece471d |
| documents | 12fa43b |

참고: 본 점검은 각 명령을 `origin/develop` ref로 실행했다. 위 SHA는 과제가 지정한 고정값이며, 실행 시점 `origin/develop`이 이 SHA와 다를 경우 결과가 달라질 수 있으나, 본 세션에서는 지시대로 `origin/develop`을 대상으로 삼았다(SHA별 재고정은 수행하지 않음 — '관찰' 참조).

## 방법

실행한 git 명령 원문(전부 절대경로, 읽기 전용):

1. 03 아키텍처 문서 읽기
   - `git -C 'D:\workspace\dpa\documents' show origin/develop:03_프로젝트_아키텍처_정의서.md`
2. gateway 파일 목록 + 라우팅 설정
   - `git -C 'D:\workspace\dpa\devpath-gateway' ls-tree -r origin/develop --name-only`
   - `git -C 'D:\workspace\dpa\devpath-gateway' show origin/develop:src/main/resources/application.yml`
   - `git -C 'D:\workspace\dpa\devpath-gateway' show origin/develop:src/test/resources/application-test.yml`
3. 7개 svc 컨트롤러 base path 수집(각 레포별)
   - `git -C 'D:\workspace\dpa\devpath-platform-svc' grep -nE '@(Get|Post|Put|Delete|Patch|Request)Mapping' origin/develop -- '*.java'`
   - learning / community / sandbox / ai / lcs / notification 각 레포에 동일 명령
4. gitops 배포 앱 목록
   - `git -C 'D:\workspace\dpa\devpath-gitops' ls-tree -r origin/develop --name-only`

주: gateway 라우팅은 Java `RouteLocator` 자바설정이 아니라 YAML(`application.yml`)로 선언되어 있음을 파일 목록으로 확인(`config/` 아래는 `GatewaySecurityConfig.java`뿐, RouteLocator 없음).

## 실측

### (A) 03 문서가 주장하는 구조

- **서비스 목록**(문서 §2 모듈 구성, 03문서:96~110행 근방): devpath-shared, devpath-gateway, devpath-platform-svc, devpath-notification-svc, devpath-learning-svc, devpath-community-svc, devpath-lcs-svc, devpath-ai-svc, devpath-sandbox-svc, devpath-frontend, devpath-landing-page, devpath-gitops, devpath-svc-template.
- **라우팅/포트**: 03 문서는 gateway가 "Spring Cloud Gateway + JWT" 엣지라고만 기술하고, **구체적 path→svc 라우팅 표나 포트 번호를 명시하지 않는다**(§1 다이어그램 수준). 포트/경로 SSoT는 gateway `application.yml`.
- **의존 방향**(문서 §1.1 Mermaid): Gateway → Auth/Path/Content/Sbx/Com; Path → AIGW → LLM; Sbx → Docker, Sbx → AIGW; Core → PG/Redis/Kafka; Auth → GitHub.
- **AI Gateway 계약**(문서 §1.2-2, ADR 007): 개발 빌드 Ollama gateway `/ai/embed`, `/ai/path/generate` 경로를 명시.

### (B) gateway 라우트 표 (application.yml, SSoT)

| route id | Path predicate | 대상 svc(uri 기본값 포트) |
|----------|----------------|---------------------------|
| platform-auth | `/oauth2/**, /login/**, /auth/**, /users/**` | platform-svc (8081) |
| learning | `/onboarding/assessments/**, /learning-paths/**, /dashboard/**, /contents/**` | learning-svc (8082) |
| sandbox | `/sandbox/**` | sandbox-svc (8085) |
| ai-review | `/reviews/**, /ai-mentor/**` | ai-svc (8084) |
| community | `/community/**` | community-svc (8086) |
| notification | `/notifications/**` | notification-svc (8088) |
| lcs | `/lcs/**` | lcs-svc (8087) |

(test용 `application-test.yml`의 라우트 목록은 prod `application.yml`과 동일. 포트 8083은 어느 라우트에도 없음 — 갭 없음, 단지 미할당.)

### (C) 7개 svc 컨트롤러 base path (@RequestMapping)

- **platform-svc** (8081):
  - `/auth` (AuthController: /oauth/token, /refresh, /logout)
  - `/admin` (AdminUserController: /users, /users/{id}/approve, /allowlist)
  - `/beta/status` (BetaStatusController)  ← 정확히는 클래스 `@RequestMapping` 없이 메서드 `@GetMapping("/beta/status")`
  - `/consents` (ConsentController: POST, /me, /{type}/revoke)
  - `/users` (AccountController DELETE /me, UserController GET /me)
  - `/users/me/avatar` (AvatarController)
  - `/users/me/profile` (ProfileController)
- **learning-svc** (8082):
  - `/onboarding/assessments`, `/onboarding/assessments/claim`, `/onboarding/assessments/guest`
  - `/contents`, `/internal/contents` (InternalContent, InternalSimilar)
  - `/dashboard`
  - `/learning-paths`
- **community-svc** (8086):
  - `/community/users` (BadgeController)
  - `/community/me/activity` (ActivityController)
  - `/community` (CommunityController: /questions, /answers, /posts, /tags 등)
- **sandbox-svc** (8085):
  - `/internal/sandbox/sessions` (InternalSessionController)
  - `/sandbox` (RunController: /run SSE)
- **ai-svc** (8084):
  - `/ai-mentor` (MentorController: /sessions)
  - `/ai` (OllamaController: /embed, /path/generate)
  - `/ai` (ReEngagementController: /re-engagement)
  - `/reviews` (ReviewController: ?sandboxSessionId, /{id}, /{id}/feedback)
- **lcs-svc** (8087):
  - `/lcs` (LcsController: /snapshots/**, /preferences)
- **notification-svc** (8088):
  - `/notifications/devices` (DeviceController)
  - `/notifications/internal/prefs` (InternalPrefsController)
  - `/notifications/prefs` (PrefsController)

### (D) gitops 배포 앱 목록 (apps/ 하위, ls-tree)

apps/_migration (Flyway Job), apps/devpath-admin, apps/devpath-ai-svc, apps/devpath-community-svc, apps/devpath-gateway, apps/devpath-lcs-svc, apps/devpath-learning-svc, apps/devpath-platform-svc, apps/devpath-sandbox-svc, apps/devpath-web.

→ 백엔드 svc 7개(platform/ai/community/lcs/learning/sandbox) + gateway → **notification-svc가 apps/에 없음**. frontend는 admin/web 2개 앱으로 배포.

## 불일치 후보

1. **notification-svc가 gitops 배포 앱에 없음** (P1 후보)
   - 문서위치: 03문서 §2 모듈 구성 — devpath-notification-svc를 정식 서비스로 명시(2026-07-01 platform-svc에서 이관).
   - 코드근거: `git -C ...gitops ls-tree -r origin/develop --name-only` → `apps/` 아래 devpath-notification-svc 디렉토리 부재(platform/ai/community/lcs/learning/sandbox/gateway + admin/web만 존재). 반면 gateway `application.yml`에는 notification 라우트(`/notifications/**` → 8088)가 존재하고 notification-svc 컨트롤러 3종도 실재.
   - P0/P1/P2: **P1** (라우트·서비스는 살아있으나 배포 매니페스트 누락 → 실배포 시 502 위험).
   - 수정방향: gitops `apps/devpath-notification-svc/base/{deployment,service,kustomization}.yaml` 추가 + `argocd/applicationset.yaml` 반영. (본 점검은 코드 읽기 전용 — 실제 수정은 gitops 레포 소관. applicationset 내용까지는 미확인, '관찰' 참조.)

2. **ai-svc `/ai/**` 경로가 gateway 라우트에 없음** (P2 후보 — 설계 의도일 가능성)
   - 문서위치: 03문서 §1.2-2 및 ADR 007 — AI Gateway 개발 빌드가 `/ai/embed`, `/ai/path/generate` 경로 노출을 명시.
   - 코드근거: ai-svc grep → `/ai` (OllamaController: /embed, /path/generate), `/ai` (ReEngagementController: /re-engagement) 실재. 그러나 gateway ai-review 라우트 predicate는 `/reviews/**, /ai-mentor/**`뿐 → `/ai/**`는 **엣지로 노출되지 않음**.
   - P0/P1/P2: **P2** (내부 svc-to-svc 호출 전용이면 정상. `/ai/embed`·`/ai/path/generate`는 learning-svc가 내부 호출하는 provider abstraction 엔드포인트로 보이며, 외부 미노출이 오히려 보안상 타당). 다만 03 문서가 이를 "AI Gateway 진입점"처럼 서술해 문서-라우팅 서술 톤 불일치.
   - 수정방향: 03 문서에 `/ai/**`는 내부 전용(비-엣지)임을 1줄 주석 추가, 또는 그대로 유지(오노출 아님). 코드 변경 불필요.

3. **platform-svc `/admin`, `/consents`, `/beta/status` 경로가 gateway platform-auth 라우트 predicate에 없음** (P1 후보)
   - 문서위치: gateway `application.yml` platform-auth predicate = `/oauth2/**, /login/**, /auth/**, /users/**`.
   - 코드근거: platform-svc grep → `/admin/**`(AdminUserController), `/consents/**`(ConsentController), `/beta/status`(BetaStatusController) 실재하나 gateway predicate에 매칭되는 prefix 없음 → 이 3개 경로군은 **gateway를 통해 도달 불가**.
   - P0/P1/P2: **P1** (admin 승인/allowlist·동의 관리·베타 상태는 프론트에서 호출되는 실경로일 가능성이 큼. 라우팅 누락이면 기능 단절). 단, admin은 별도 admin 앱이 직결 호출하거나 별도 라우트 설계일 수 있어 P0 단정 보류.
   - 수정방향: gateway platform-auth predicate에 `/admin/**, /consents/**, /beta/**` 추가 검토. 실제 프론트/admin 호출 경로 확인 후 확정(축② 코드/문서 정합성에서 교차검증 필요).

4. **learning-svc `/internal/contents`, sandbox `/internal/sandbox/sessions`, notification `/notifications/internal/prefs`가 gateway 미노출** (불일치 아님 — 정상, 기록용)
   - 코드근거: 각 svc grep에서 `/internal/**` 컨트롤러 확인. gateway 라우트에 `/internal/**` 없음.
   - 판정: **정상**. svc-to-svc 내부 호출 전용 엔드포인트이며 엣지 미노출이 설계 의도. 단 notification의 `/notifications/internal/prefs`는 `/notifications/**` predicate에 **매칭되어 버려** 엣지로 노출될 수 있음 → 아래 5번.

5. **notification `/notifications/internal/prefs`가 `/notifications/**` 라우트에 매칭되어 엣지 노출 위험** (P2 후보)
   - 문서위치: gateway `application.yml` notification predicate = `/notifications/**` (와일드카드).
   - 코드근거: notification-svc InternalPrefsController `@RequestMapping("/notifications/internal/prefs")` → `/notifications/**`에 포함 → gateway가 외부에서 이 내부 경로로 라우팅 가능. 다른 svc는 `/internal/**`를 base prefix 밖에 두어 회피했으나 notification만 `/notifications/` 안쪽에 internal을 둠.
   - P0/P1/P2: **P2** (내부 전용 엔드포인트가 엣지 노출. 인증/인가로 막혀 있으면 정보노출 수준, 아니면 상향). JWT 필터가 전역 적용되면 완화되나 internal 엔드포인트는 통상 무인증 가정일 수 있어 점검 필요.
   - 수정방향: notification internal 경로를 `/internal/notifications/prefs`로 이동(다른 svc 관례와 일치)하거나 gateway predicate를 `/notifications/**` 중 internal 제외로 좁힘.

## 관찰

- **RouteLocator 자바설정 부재**: gateway 라우팅은 전부 `application.yml` 선언형. `src/main/java/.../config/`에는 `GatewaySecurityConfig.java`만 존재. 따라서 path→svc SSoT는 YAML 단일 파일로 명확(감사 용이).
- **SHA 재고정 미수행(판정 보류 요소)**: 과제는 서비스별 고정 SHA(예 gateway=c8a1282)를 제시했으나, 본 점검은 지시의 명령 예시대로 각 레포 `origin/develop` ref로 실행했다. 실행 시점 `origin/develop` HEAD가 제시 SHA와 다르면 위 실측이 어긋날 수 있음. 정밀 재현이 필요하면 각 명령의 `origin/develop`을 제시 SHA로 치환해 재실행 권장(읽기 전용이라 안전).
- **gitops applicationset 미확인**: notification-svc 배포 누락(불일치 1번)의 확정 판정을 위해서는 `argocd/applicationset.yaml`이 apps/ 디렉토리를 어떻게 열거하는지(자동 디렉토리 스캔 vs 명시 목록) 확인이 필요. 본 축에서는 `ls-tree`상 디렉토리 부재만 근거로 삼았고 applicationset 내용은 미독. 축② 또는 후속에서 `git -C ...gitops show origin/develop:argocd/applicationset.yaml`로 보강 권장.
- **포트 8083 미할당**: 라우트/포트 관례상 8081~8088 중 8083만 어떤 svc/라우트에도 배정되지 않음. 과거 서비스 분리(notification 이관 등)의 잔재로 추정. 갭 아님, 기록용.
- **admin 앱 vs platform `/admin` 라우팅**: gitops에 devpath-admin(프론트 admin) 앱이 있고 platform-svc에 `/admin` 백엔드 컨트롤러가 있음. admin 프론트가 gateway 경유로 platform `/admin`을 호출한다면 불일치 3번이 P1로 확정. admin이 platform을 직결 호출하는 설계면 정상. 이 판정은 축②(프론트 실호출 경로) 교차검증에 의존 — **보류**.
