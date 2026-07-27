# 정합성 점검 2차 — 인프라·공통 레포 구현 사실

> 수집일: 2026-07-02 / 기준: shared origin/main(a42f756), gateway origin/develop(c8a1282), gitops origin/develop(728e5c1), svc-template origin/develop(b6c33ee)
> 수집: 읽기 전용 조사 에이전트 / 컨트롤러 표본 검증 통과 — 마이그레이션 전체 24파일 재계수 일치(CREATE문 없는 2파일은 본문에 명시됨), gateway 라우트 7개 application.yml 대응 확인, 최신 3개 마이그레이션(reputation/badges/vote_abuse_suspicions) 직접 대조 일치

# T5 Facts — 4개 레포 조사 (읽기 전용)

기준 ref:
| 레포 | ref | commit |
|---|---|---|
| devpath-shared | origin/main (origin/develop 없음, 확인됨: `fatal: ambiguous argument 'origin/develop'`) | a42f756cd4d6225e4520bed0b5f7711a66366c41 |
| devpath-gateway | origin/develop | c8a1282614dfa13e13e0f121da1899c9b3490d89 |
| devpath-gitops | origin/develop | 728e5c14bda380c2ba1dabbf3bb633233d4b534c |
| devpath-svc-template | origin/develop | b6c33ee0e3c7fef616cd2ef6654e7f078c451681 |

모든 커밋 해시는 `git rev-parse`로 확인되어 명세와 일치함.

---

## devpath-shared

### Flyway 마이그레이션 전체 목록 (origin/main, `src/main/resources/db/migration`) — 24개 파일

```
V202606150900__init_common.sql
V202606150901__users_skeleton.sql
V202606150902__dormant_archives.sql
V202606171001__users_auth_extension.sql
V202606171002__user_oauth_identities.sql
V202606171003__user_profiles.sql
V202606171004__outbox.sql
V202606171005__notifications.sql
V202606181001__question_bank.sql
V202606181002__assessments.sql
V202606181003__assessment_items.sql
V202606181004__assessment_results.sql
V202606181005__drop_assessments_user_fk.sql
V202606181006__learning_path_schema.sql
V202606201001__user_content_progress.sql
V202606221001__sandbox_sessions.sql
V202606231001__ai_code_reviews.sql
V202606241001__ai_mentor_sessions.sql
V202606251001__community_qna.sql
V202606261001__lcs_snapshots.sql
V202606271001__device_tokens.sql
V202606301001__reputation.sql
V202606301002__badges.sql
V202607011001__vote_abuse_suspicions.sql
```

### 마이그레이션별 CREATE TABLE / CREATE EXTENSION 대상

(`V202606150900__init_common.sql`은 grep 결과에 CREATE TABLE/EXTENSION 매치 없음 — 파일은 존재하나 테이블/확장 생성문 없음)

| 파일 | 테이블/확장 |
|---|---|
| V202606150901__users_skeleton.sql | users |
| V202606150902__dormant_archives.sql | dormant_user_archives, dormant_archive_runs |
| V202606171002__user_oauth_identities.sql | user_oauth_identities |
| V202606171003__user_profiles.sql | user_profiles |
| V202606171004__outbox.sql | outbox |
| V202606171005__notifications.sql | notifications |
| V202606181001__question_bank.sql | question_bank |
| V202606181002__assessments.sql | assessments |
| V202606181003__assessment_items.sql | assessment_items |
| V202606181004__assessment_results.sql | assessment_results |
| V202606181005__drop_assessments_user_fk.sql | (매치 없음 — DROP 작업으로 추정되나 CREATE 문 없음) |
| V202606181006__learning_path_schema.sql | EXTENSION vector; learning_paths, contents, path_milestones, path_weekly_tasks, content_embeddings |
| V202606201001__user_content_progress.sql | user_content_progress |
| V202606221001__sandbox_sessions.sql | sandbox_sessions |
| V202606231001__ai_code_reviews.sql | ai_code_reviews |
| V202606241001__ai_mentor_sessions.sql | ai_mentor_sessions |
| V202606251001__community_qna.sql | EXTENSION vector; community_posts, community_questions, community_answers, community_votes, community_tags, community_post_tags, community_ai_answers |
| V202606261001__lcs_snapshots.sql | learning_context_snapshots, user_context_preferences |
| V202606271001__device_tokens.sql | device_tokens |
| V202606301001__reputation.sql | reputation_events, user_reputation, user_tag_reputation |
| V202606301002__badges.sql | badges, user_badges |
| V202607011001__vote_abuse_suspicions.sql | vote_abuse_suspicions |

(V202606171001__users_auth_extension.sql도 grep 매치 없음 — ALTER 계열로 추정, CREATE 문 없음)

---

## devpath-gateway

### 라우트 설정 (origin/develop, `src/main/resources/application.yml`)

| 라우트 경로 패턴 | 대상 서비스 (uri 환경변수) | 정의 파일 |
|---|---|---|
| /oauth2/**, /login/**, /auth/**, /users/** | ${PLATFORM_URI:http://localhost:8081} | src/main/resources/application.yml |
| /onboarding/assessments/**, /learning-paths/**, /dashboard/**, /contents/** | ${LEARNING_URI:http://localhost:8082} | src/main/resources/application.yml |
| /sandbox/** | ${SANDBOX_URI:http://localhost:8085} | src/main/resources/application.yml |
| /reviews/**, /ai-mentor/** | ${AI_SVC_URI:http://localhost:8084} | src/main/resources/application.yml |
| /community/** | ${COMMUNITY_SVC_URI:http://localhost:8086} | src/main/resources/application.yml |
| /notifications/** | ${NOTIFICATION_URI:http://localhost:8088} | src/main/resources/application.yml |
| /lcs/** | ${LCS_SVC_URI:http://localhost:8087} | src/main/resources/application.yml |

라우트 정의 Java 파일은 origin/develop 트리에 없음 (RouteLocator/`.route(`/predicates 패턴으로 검색 시 매치된 유일한 `*.java` 파일은 테스트 코드 `src/test/java/ai/devpath/gateway/RouteConfigTest.java`이며, 이는 application.yml 기반 라우트를 검증하는 테스트임 — 별도 Java 기반 라우트 정의 없음).

RouteConfigTest.java에서 확인되는 라우트 ID: `platform-auth`, `learning`, `sandbox`, `ai-review`, `community`, `lcs`, `notification` (7개 라우트 ID, application.yml의 7개 predicates 블록과 대응).

---

## devpath-gitops

### origin/develop 전체 파일 목록

```
.github/workflows/ci.yml
CLAUDE.md
README.md
apps/_migration/base/job.yaml
apps/_migration/base/kustomization.yaml
apps/devpath-admin/base/deployment.yaml
apps/devpath-admin/base/kustomization.yaml
apps/devpath-admin/base/service.yaml
apps/devpath-ai-svc/base/deployment.yaml
apps/devpath-ai-svc/base/kustomization.yaml
apps/devpath-ai-svc/base/service.yaml
apps/devpath-community-svc/base/deployment.yaml
apps/devpath-community-svc/base/kustomization.yaml
apps/devpath-community-svc/base/service.yaml
apps/devpath-gateway/base/deployment.yaml
apps/devpath-gateway/base/kustomization.yaml
apps/devpath-gateway/base/service.yaml
apps/devpath-lcs-svc/base/deployment.yaml
apps/devpath-lcs-svc/base/kustomization.yaml
apps/devpath-lcs-svc/base/service.yaml
apps/devpath-learning-svc/base/deployment.yaml
apps/devpath-learning-svc/base/kustomization.yaml
apps/devpath-learning-svc/base/service.yaml
apps/devpath-platform-svc/base/deployment.yaml
apps/devpath-platform-svc/base/kustomization.yaml
apps/devpath-platform-svc/base/service.yaml
apps/devpath-sandbox-svc/base/deployment.yaml
apps/devpath-sandbox-svc/base/kustomization.yaml
apps/devpath-sandbox-svc/base/service.yaml
apps/devpath-web/base/deployment.yaml
apps/devpath-web/base/kustomization.yaml
apps/devpath-web/base/service.yaml
argocd/applicationset.yaml
argocd/project.yaml
docs/project-management/workflow/WORKFLOW_team-lead_DONE.md
docs/project-management/workflow/WORKFLOW_team-lead_MD4.md
local-k8s/README.md
```

### 등록된 앱 목록 및 매니페스트 구조

레포 안에 `kind: Application` 매니페스트는 **존재하지 않음** (`git grep -nE "^kind: Application"` 결과 매치 없음). 대신 `argocd/applicationset.yaml` 1개 파일에 `kind: ApplicationSet`이 정의되어 `apps/*` 디렉터리를 자동 발견해 각각을 ArgoCD Application으로 생성한다 (`generators.git.directories: path: apps/*`, `template.metadata.name: "{{.path.basename}}"`).

`apps/` 아래 서비스별 디렉터리(각각 `base/deployment.yaml`, `base/kustomization.yaml`, `base/service.yaml` 보유) — 서비스명은 디렉터리명과 동일:

| 서비스명(디렉터리) | 이미지(kustomization.yaml newName) |
|---|---|
| devpath-admin | ghcr.io/devpathai/devpath-admin |
| devpath-ai-svc | ghcr.io/devpathai/devpath-ai-svc |
| devpath-community-svc | ghcr.io/devpathai/devpath-community-svc |
| devpath-gateway | ghcr.io/devpathai/devpath-gateway |
| devpath-lcs-svc | ghcr.io/devpathai/devpath-lcs-svc |
| devpath-learning-svc | ghcr.io/devpathai/devpath-learning-svc |
| devpath-platform-svc | ghcr.io/devpathai/devpath-platform-svc |
| devpath-sandbox-svc | ghcr.io/devpathai/devpath-sandbox-svc |
| devpath-web | ghcr.io/devpathai/devpath-web |

추가로 `apps/_migration/base/`에 `job.yaml`, `kustomization.yaml`만 존재 (deployment.yaml/service.yaml 없음 — Job 매니페스트, 서비스가 아님).

---

## devpath-svc-template

### 디렉터리 구조 (1~2단계, origin/develop)

```
.github/workflows/ci.yml
CLAUDE.md
README.md
Dockerfile
build.gradle.kts
settings.gradle.kts
gradlew, gradlew.bat
.gitattributes, .gitignore
docs/
  project-management/
    README.md
gradle/
  wrapper/
    gradle-wrapper.jar
    gradle-wrapper.properties
src/
  main/
    java/ai/devpath/template/SvcTemplateApplication.java
    resources/application.yml
  test/
    java/ai/devpath/template/SvcTemplateApplicationTests.java
```

### README.md 표준 규정 인용 (상태 주장 포함)

> **DevPath AI** 백엔드 서비스 공통 스켈레톤 템플릿입니다. 새 `devpath-*-svc` 레포는 이 템플릿을 복제해서 시작합니다.

> ## 구성
> - Spring Boot 4.0.x · Java 21 · Gradle (Kotlin DSL)
> - 기본 스타터: WebMVC, Actuator, Validation, Lombok
> - 선택 의존성(JPA + PostgreSQL, Redis, Security, Kafka)은 `build.gradle.kts`에 주석으로 포함 — 서비스 특성에 맞게 해제
> - `docs/project-management/` — [workflow-dashboard](https://github.com/DevPathAi/workflow-dashboard) 동기화 대상 디렉터리

> ## 새 서비스 만들기
> 1. 이 레포 내용을 새 레포로 복사
> 2. 치환:
>    - `settings.gradle.kts`의 `rootProject.name`
>    - `build.gradle.kts`의 `description`
>    - 패키지 `ai.devpath.template` → `ai.devpath.<도메인>`
>    - 메인 클래스 `SvcTemplateApplication` → `<도메인>Application`
> 3. `application.yml`의 `spring.application.name` 수정
> 4. 필요한 의존성 주석 해제

> ## 빌드 / 실행
> ```bash
> ./gradlew build        # 빌드 + 테스트
> ./gradlew bootRun      # 로컬 실행 (기본 포트 8080)
> ```
> 로컬 인프라(PostgreSQL, Redis, Kafka 등)는 [devpath-shared](https://github.com/DevPathAi/devpath-shared)의 docker-compose를 사용합니다.

> ## 개발 규칙
> - Git 규칙: [documents/09_Git_규칙_정의서](https://github.com/DevPathAi/documents/blob/main/09_Git_규칙_정의서.md)
> - 코드 리뷰: [documents/12_코드_리뷰_규칙](https://github.com/DevPathAi/documents/blob/main/12_코드_리뷰_규칙.md)
> - 테스트 전략: [documents/11_테스트_전략서](https://github.com/DevPathAi/documents/blob/main/11_테스트_전략서.md)

참고: `application.yml`의 실제 `spring.application.name` 값은 `svc-template` (기본값 그대로, 템플릿 자체이므로 미치환 상태 — README 절차 2번의 "치환 대상"임을 보여주는 현재 상태).

### CLAUDE.md 절대 조건 인용 (상태 주장 포함)

> ## 🚫 절대 조건 — 모든 작업에 예외 없이 적용
> 아래 세 가지는 이 레포의 **어떤 작업에도 우선하는 최상위 규칙**이다.
> 1. 추측·예상 금지 — "코드·설정·동작·의존성을 추측하지 않는다. 모르면 파일을 읽고 명령을 실행해 사실을 확인한 뒤 행동한다."
> 2. 테스트 코드 우선 (Test-First) — "모든 기능 추가·수정은 실패하는 테스트를 먼저 작성하고, 그 테스트를 통과시키는 최소 구현을 작성한다."
> 3. 문제 발생 시 코드 분석 우선 — "버그·테스트 실패·예상 밖 동작이 생기면 추측으로 고치지 않는다."
> 4. 신규 작업은 무조건 신규 브랜치 — "모든 신규 작업은 시작 전 `develop`에서 새 작업 브랜치(`feat/*`·`fix/*`·`chore/*`·`docs/*`)를 분기해 그 위에서 진행한다. `develop`·`main` 등 공유/통합 브랜치에서 직접 작업하지 않는다."
> 5. 결과를 자화자찬하지 않는다 — "작업 결과를 스스로 칭찬·과신하지 않는다. '완료했다', '문제없다'는 검증·테스트로 확인한 근거가 있을 때만 말한다."

> ## 빌드·테스트
> - 빌드: `./gradlew build` / 테스트: `./gradlew test` (JUnit 5) / 실행: `./gradlew bootRun` (포트 8080)
> - 스택: Spring Boot 4.0.7 · Java 21 · Gradle (Kotlin DSL)

> ## 🚫 서브에이전트 작업 범위 강제 (Scope Lock) — 모든 작업 공통
> - 서브에이전트(Task/Agent)에 위임 시 작업 경계를 명시적으로 못박는다: "이 작업만 수행하고 끝나면 보고 후 정지. 다른 Task로 진행하거나 명세에 없는 코드를 임의 구현 금지. 명세 부족 시 멈추고 NEEDS_CONTEXT 보고."
> - 위임 결과는 컨트롤러가 직접 검증한다(커밋 로그·파일 구조·테스트 실행). 완료 보고를 그대로 신뢰하지 않는다.
