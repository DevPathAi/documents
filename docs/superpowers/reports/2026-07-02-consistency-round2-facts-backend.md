# 정합성 점검 2차 — 백엔드 7개 svc 구현 사실

> 수집일: 2026-07-02 / 기준: 각 레포 origin/develop (baseline 참조: ./2026-07-02-consistency-round2-baseline.md)
> 수집: 읽기 전용 조사 에이전트 / 컨트롤러 표본 검증 3건 통과 — platform 엔드포인트 수 4(직접 재계수 일치), learning 컨트롤러별 합계 21(일치), notification 2(전체 Mapping 스캔으로 inbox HTTP API 부재 확인)

# T3 조사 사실 자료 (기준: 각 레포 origin/develop, 지정 커밋)

조사 방법: `git -C <repo> grep`/`git -C <repo> show`/`git -C <repo> ls-tree`로 지정 ref 트리만 조회. 워킹트리 파일은 읽지 않음.

---

## devpath-platform-svc (origin/develop @ 56bf8a6)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| POST | /auth/oauth/token | src/main/java/ai/devpath/platform/auth/AuthController.java |
| POST | /auth/refresh | src/main/java/ai/devpath/platform/auth/AuthController.java |
| POST | /auth/logout | src/main/java/ai/devpath/platform/auth/AuthController.java |
| GET | /users/me | src/main/java/ai/devpath/platform/user/UserController.java |

엔드포인트 수: 4

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/platform 하위 1~2단계)

- auth (+ auth/crypto, auth/dto, auth/jwt, auth/refresh)
- config
- onboarding
- outbox
- user
- (루트) PlatformApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `> 알림(FCM 디바이스 토큰, 인앱 알림) 모듈은 2026-07-01 devpath-notification-svc로 이관되었습니다.` |
| README.md | `- Spring Boot 4.0.x · Java 21 · Gradle (Kotlin DSL)` |
| README.md | `\| user \| 사용자 계정, OAuth2(GitHub) 연동, JWT \|` / `\| github \| GitHub 프로필/활동 수집 워커 \|` |
| CLAUDE.md | `- 스택: Spring Boot 4.0.7 · Java 21 · Gradle (Kotlin DSL)` |
| CLAUDE.md | `> \`notification\`(FCM 디바이스 토큰, 인앱 알림) 모듈은 2026-07-01 devpath-notification-svc로 이관되었다. 이 레포에는 더 이상 존재하지 않는다.` |

### 4. 테스트 존재 여부

src/test 하위 파일 수: 26 (그중 .java 파일 25개, 나머지 1개는 src/test/resources/application-test.yml)

---

## devpath-learning-svc (origin/develop @ caec735)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| POST | /onboarding/assessments | src/main/java/ai/devpath/learning/assessment/AssessmentController.java |
| GET | /onboarding/assessments/{id}/next | src/main/java/ai/devpath/learning/assessment/AssessmentController.java |
| POST | /onboarding/assessments/{id}/answer | src/main/java/ai/devpath/learning/assessment/AssessmentController.java |
| POST | /onboarding/assessments/{id}/complete | src/main/java/ai/devpath/learning/assessment/AssessmentController.java |
| GET | /onboarding/assessments/{id}/result | src/main/java/ai/devpath/learning/assessment/AssessmentController.java |
| POST | /onboarding/assessments/claim | src/main/java/ai/devpath/learning/assessment/claim/ClaimController.java |
| POST | /onboarding/assessments/guest | src/main/java/ai/devpath/learning/assessment/guest/GuestAssessmentController.java |
| GET | /onboarding/assessments/guest/{gid}/next | src/main/java/ai/devpath/learning/assessment/guest/GuestAssessmentController.java |
| POST | /onboarding/assessments/guest/{gid}/answer | src/main/java/ai/devpath/learning/assessment/guest/GuestAssessmentController.java |
| POST | /onboarding/assessments/guest/{gid}/complete | src/main/java/ai/devpath/learning/assessment/guest/GuestAssessmentController.java |
| GET | /contents/{idOrSlug} | src/main/java/ai/devpath/learning/content/ContentController.java |
| POST | /contents/{idOrSlug}/progress | src/main/java/ai/devpath/learning/content/ContentController.java |
| GET | /contents/me/progress | src/main/java/ai/devpath/learning/content/ContentController.java |
| GET | /internal/contents/{id} | src/main/java/ai/devpath/learning/content/InternalContentController.java |
| POST | /internal/contents/similar | src/main/java/ai/devpath/learning/content/InternalSimilarController.java |
| GET | /dashboard/me | src/main/java/ai/devpath/learning/dashboard/DashboardController.java |
| POST | /learning-paths/me/generate (SSE, produces=TEXT_EVENT_STREAM_VALUE) | src/main/java/ai/devpath/learning/path/LearningPathController.java |
| POST | /learning-paths/me/regenerate | src/main/java/ai/devpath/learning/path/LearningPathController.java |
| GET | /learning-paths/me | src/main/java/ai/devpath/learning/path/LearningPathController.java |
| GET | /learning-paths/me/this-week | src/main/java/ai/devpath/learning/path/LearningPathController.java |
| GET | /learning-paths/{id}/rationale | src/main/java/ai/devpath/learning/path/LearningPathController.java |

엔드포인트 수: 21

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/learning 하위 1~2단계)

- assessment (+ assessment/claim, assessment/dto, assessment/engine, assessment/guest)
- config
- content
- dashboard
- outbox
- path (+ path/ai)
- seed
- (루트) LearningApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `\| mentor \| AI 멘토 채팅 \|` (담당 도메인 표에 mentor 모듈 명시) |
| README.md | `**SLO**: 학습 경로 생성 p95 < 8초.` |
| README.md | `- Claude API 호출은 devpath-ai-svc를 경유` |
| CLAUDE.md | `\| mentor \| **ai-svc 소관**(\`/ai-mentor/**\`, 슬라이스 #7) — 1st Aha 초기 계획 잔재로 learning-svc 미구현 (M-9) \|` |
| CLAUDE.md | `- Claude 호출은 devpath-ai-svc를 경유한다. 프롬프트 품질은 골든 케이스 테스트로 회귀 검증한다.` |

주의: README.md는 mentor를 "AI 멘토 채팅" 담당 모듈로 표에 나열하지만, CLAUDE.md는 동일 모듈을 "ai-svc 소관, learning-svc 미구현"이라고 명시 — 실제 코드(§1, §2)에는 mentor 컨트롤러/패키지가 devpath-learning-svc에 존재하지 않음(devpath-ai-svc에 MentorController 존재, 별도 섹션 참조).

### 4. 테스트 존재 여부

src/test 하위 파일 수: 37 (그중 .java 파일 33개, 나머지 4개는 application-test.yml + seed SQL 3종)

---

## devpath-ai-svc (origin/develop @ f36cca2)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| POST | /ai-mentor/sessions | src/main/java/ai/devpath/aigw/mentor/MentorController.java |
| POST | /ai/embed | src/main/java/ai/devpath/aigw/ollama/OllamaController.java |
| POST | /ai/path/generate | src/main/java/ai/devpath/aigw/ollama/OllamaController.java |
| GET | /reviews (params=sandboxSessionId) | src/main/java/ai/devpath/aigw/review/ReviewController.java |
| GET | /reviews/{id} | src/main/java/ai/devpath/aigw/review/ReviewController.java |
| POST | /reviews/{id}/feedback | src/main/java/ai/devpath/aigw/review/ReviewController.java |

엔드포인트 수: 6

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/aigw 하위 1~2단계)

- community
- config
- mentor
- ollama (+ ollama/dto)
- outbox
- review
- (루트) AiApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `> **현재 구현 상태(2026-06-19)**: 로컬 개발 빌드는 Ollama gateway입니다. 실제 코드에는 \`POST /ai/embed\`, \`POST /ai/path/generate\`가 구현되어 있으며, 운영 목표는 Claude 등 외부 provider로 교체 가능한 AI Gateway입니다.` |
| README.md | `\| review-worker \| Kafka Consumer 기반 비동기 AI 코드 리뷰 (2nd Aha 핵심, 목표) \|` |
| README.md | `\| finops \| 토큰 사용량/비용 집계 (목표) \|` |
| README.md | `- 현재 구현 패키지: \`ai.devpath.aigw.ollama\`` |
| CLAUDE.md | `> **현재 구현 상태(2026-06-19)**: 이 레포의 dev 빌드는 Ollama gateway다. 현재 구현 API는 \`POST /ai/embed\`, \`POST /ai/path/generate\`이며, 운영 목표는 Claude 등 provider 교체 가능한 AI Gateway다.` |
| CLAUDE.md | `\| review-worker \| Kafka Consumer 비동기 AI 코드 리뷰 (목표) \|` / `\| finops \| 토큰 사용량/비용 집계 (목표) \|` |

주의: README/CLAUDE.md는 "현재 구현 패키지: ai.devpath.aigw.ollama"라고만 언급하지만, 실제 트리(§2)에는 mentor·review 패키지도 이미 존재하며 컨트롤러(MentorController, ReviewController)와 다수 테스트(§4)가 구현되어 있음 — 문서의 "review-worker/finops는 목표(미구현)" 표현과 실제 review 패키지 구현 정도 사이에 괴리가 관찰됨(해석·평가는 본 보고서 범위 밖, 사실만 기재).

### 4. 테스트 존재 여부

src/test 하위 파일 수: 44 (그중 .java 파일 40개, 나머지 4개는 application-test.yml + eval jsonl 3종)

---

## devpath-community-svc (origin/develop @ 3f9783a)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| GET | /community/users/{userId}/badges | src/main/java/ai/devpath/community/badge/BadgeController.java |
| POST | /community/questions | src/main/java/ai/devpath/community/post/CommunityController.java |
| POST | /community/questions/{id}/answers | src/main/java/ai/devpath/community/post/CommunityController.java |
| POST | /community/answers/{id}/accept | src/main/java/ai/devpath/community/post/CommunityController.java |
| GET | /community/questions/similar | src/main/java/ai/devpath/community/post/CommunityController.java |
| GET | /community/questions/{id} | src/main/java/ai/devpath/community/post/CommunityController.java |
| GET | /community/posts | src/main/java/ai/devpath/community/post/CommunityController.java |
| POST | /community/posts/{id}/vote | src/main/java/ai/devpath/community/post/CommunityController.java |
| POST | /community/answers/{id}/vote | src/main/java/ai/devpath/community/post/CommunityController.java |
| GET | /community/tags | src/main/java/ai/devpath/community/post/CommunityController.java |

엔드포인트 수: 10

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/community 하위 1~2단계)

- abuse
- badge
- config
- outbox
- post (+ post/dto)
- reputation
- seed (+ seed/dto)
- (루트) CommunityApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `\| moderation \| AI 모더레이션 + 신고 + 제재 + 이의제기 \|` |
| README.md | `\| learning-context \| 학습 맥락 스냅샷 수집/렌더 \|` |
| README.md | `\| ai-seed \| AI 시드 답변 파이프라인 (Claude) \|` |
| CLAUDE.md | `\| moderation \| AI 모더레이션 + 신고/제재/이의제기 \|` (도메인 표에 재기재) |
| CLAUDE.md | `- 스택: Spring Boot 4.0.7 · Java 21 · Gradle (Kotlin DSL)` |

주의: README/CLAUDE.md 도메인 표에 "moderation"과 "learning-context" 모듈이 명시되어 있으나, 실제 src/main/java/ai/devpath/community 하위(§2)에는 moderation·learning-context에 해당하는 패키지가 존재하지 않음(abuse/badge/config/outbox/post/reputation/seed만 존재). ai-seed는 seed 패키지로 실제 존재.

### 4. 테스트 존재 여부

src/test 하위 파일 수: 22 (그중 .java 파일 21개, 나머지 1개는 application-test.yml)

---

## devpath-sandbox-svc (origin/develop @ ee212b7)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| GET | /internal/sandbox/sessions/{id} | src/main/java/ai/devpath/sandbox/run/InternalSessionController.java |
| GET | /internal/sandbox/sessions/recent | src/main/java/ai/devpath/sandbox/run/InternalSessionController.java |
| POST | /sandbox/run (SSE, produces=TEXT_EVENT_STREAM_VALUE) | src/main/java/ai/devpath/sandbox/run/RunController.java |

엔드포인트 수: 3

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/sandbox 하위 1~2단계)

- config
- outbox
- run
- (루트) SandboxApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `\| runner \| Docker Pool + gVisor(runsc) 격리 실행 \|` |
| README.md | `\| submission \| 과제 제출 접수 → 실행 → 결과 회수 \|` |
| README.md | `로컬에서 gVisor 없이 개발할 때는 일반 Docker 런타임으로 폴백합니다 (프로덕션은 runsc 필수).` |
| CLAUDE.md | `- 보안상 코어와 무조건 분리된 격리 서비스. 실행은 네트워크 차단 + 리소스 제한 + gVisor 샌드박스로 구동한다.` |

주의: README/CLAUDE.md 도메인 표에 "submission"(과제 제출 접수 → 실행 → 결과 회수) 모듈이 명시되어 있으나, 실제 src/main/java/ai/devpath/sandbox 하위(§2)에는 submission 패키지가 없고 run 패키지만 존재(RunController, InternalSessionController 등).

### 4. 테스트 존재 여부

src/test 하위 파일 수: 13 (그중 .java 파일 12개, 나머지 1개는 application-test.yml)

---

## devpath-lcs-svc (origin/develop @ 212e588)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| POST | /lcs/snapshots/draft | src/main/java/ai/devpath/lcs/api/LcsController.java |
| POST | /lcs/snapshots/{draftId}/commit | src/main/java/ai/devpath/lcs/api/LcsController.java |
| GET | /lcs/snapshots/{id} | src/main/java/ai/devpath/lcs/api/LcsController.java |
| GET | /lcs/snapshots/by-question/{questionId} | src/main/java/ai/devpath/lcs/api/LcsController.java |
| GET | /lcs/preferences | src/main/java/ai/devpath/lcs/api/LcsController.java |
| PUT | /lcs/preferences | src/main/java/ai/devpath/lcs/api/LcsController.java |

엔드포인트 수: 6

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/lcs 하위 1~2단계)

- api
- client
- config
- domain
- draft
- service
- (루트) LcsApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `# devpath-svc-template` (제목 자체가 LCS가 아닌 템플릿 레포명) |
| README.md | `**DevPath AI** 백엔드 서비스 공통 스켈레톤 템플릿입니다. 새 \`devpath-*-svc\` 레포는 이 템플릿을 복제해서 시작합니다.` |
| CLAUDE.md | `> LCS(학습 맥락 자동 첨부) 서비스 — 질문 작성 시 현재 학습 맥락을 스냅샷으로 조립·불변 첨부(MD3 슬라이스 #9). \`devpath-svc-template\`에서 파생.` |

주의: 지정 ref(origin/develop @ 212e588)에서 devpath-lcs-svc의 README.md는 devpath-svc-template의 제네릭 템플릿 내용 그대로이며 LCS 관련 서술이 전혀 없음(레포명도 "devpath-svc-template"로 표기). 반면 CLAUDE.md는 LCS 전용 내용으로 갱신되어 있음 — README.md가 실제 서비스(LCS) 내용으로 치환되지 않은 상태.

### 4. 테스트 존재 여부

src/test 하위 파일 수: 5 (그중 .java 파일 4개, 나머지 1개는 application-test.yml)

---

## devpath-notification-svc (origin/develop @ f76acfb)

### 1. 실제 HTTP 엔드포인트

| HTTP 메서드 | 경로 | 컨트롤러 파일 |
|---|---|---|
| POST | /notifications/devices | src/main/java/ai/devpath/notification/device/DeviceController.java |
| DELETE | /notifications/devices | src/main/java/ai/devpath/notification/device/DeviceController.java |

엔드포인트 수: 2

### 2. 주요 도메인 모듈 (src/main/java/ai/devpath/notification 하위 1~2단계)

- config
- device
- inbox
- (루트) NotificationApplication.java

### 3. README.md / CLAUDE.md 구현 상태 주장 인용

| 파일 | 주장 원문(1줄) |
|---|---|
| README.md | `**DevPath AI** 알림 서비스 — FCM 디바이스 토큰 등록, 인앱 알림 인박스, 참여 촉진 배치(스트릭·주간 리포트·정체 탐지·선호 시간대 리마인더).` |
| README.md | `- 스타터: WebMVC, Actuator, Validation, JPA, Security(OAuth2 Resource Server), Kafka` |
| CLAUDE.md | `\| device \| FCM 디바이스 토큰 등록/해제 \|` / `\| inbox \| 인앱 알림(웰컴 등) 저장·조회, \`UserRegisteredEvent\` 등 구독 \|` |
| CLAUDE.md | `> 이 레포는 devpath-svc-template에서 파생되었다. \`device\`/\`inbox\` 모듈은 원래 devpath-platform-svc의 notification 패키지에 있던 코드를 이관한 것이다(2026-07-01).` |

주의: README.md는 "참여 촉진 배치(스트릭·주간 리포트·정체 탐지·선호 시간대 리마인더)"를 알림 서비스 담당 범위로 서술하지만, 실제 패키지(§2)는 device·inbox 두 개뿐이며 스트릭/주간 리포트/정체 탐지/리마인더에 해당하는 배치 관련 패키지·컨트롤러는 트리에 존재하지 않음.

### 4. 테스트 존재 여부

src/test 하위 파일 수: 6 (그중 .java 파일 5개, 나머지 1개는 application-test.yml)

---

## 전체 엔드포인트 수 요약

| 레포 | 엔드포인트 수 |
|---|---|
| devpath-platform-svc | 4 |
| devpath-learning-svc | 21 |
| devpath-ai-svc | 6 |
| devpath-community-svc | 10 |
| devpath-sandbox-svc | 3 |
| devpath-lcs-svc | 6 |
| devpath-notification-svc | 2 |
