# 04. API 명세서

> **Base URL**: `https://api.devpath.ai/api/v1`
> **인증**: JWT Bearer Token (`Authorization: Bearer <token>`)
> **스펙 문서**: SpringDoc OpenAPI → `/swagger-ui.html`
> **문서 성격**: v1 목표 API 계약. 현재 로컬 구현 완료 범위는 [42_전체_정합성_점검_2차](./42_전체_정합성_점검_2차.md)를 기준으로 확인한다(36번은 2026-06-19 시점 스냅샷).

---

## 공통 규약

### 요청/응답 포맷
- Content-Type: `application/json; charset=utf-8`
- Streaming(SSE): `text/event-stream` (AI 멘토, 학습 경로 생성 진행)

### 공통 에러 응답
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Learning path not found for user 42",
    "trace_id": "a1b2c3d4",
    "timestamp": "2026-04-22T10:30:00Z"
  }
}
```

### 주요 에러 코드
| 코드 | HTTP | 설명 |
|------|------|------|
| `UNAUTHORIZED` | 401 | 토큰 없음/만료 |
| `FORBIDDEN` | 403 | 권한 없음 (플랜 한도 포함) |
| `ONBOARDING_INCOMPLETE` | 403 | 온보딩 미완료 |
| `RESOURCE_NOT_FOUND` | 404 | 리소스 없음 |
| `VALIDATION_FAILED` | 400 | 입력값 오류 |
| `CONFLICT` | 409 | 중복/버전 충돌 |
| `QUOTA_EXCEEDED` | 429 | 계정 기본 한도 (멘토/Sandbox) |
| `AI_KILL_SWITCH_ACTIVE` | 503 | FinOps Kill-switch |
| `SANDBOX_UNAVAILABLE` | 503 | 풀 고갈, 30초 재시도 |
| `INTERNAL_ERROR` | 500 | 서버 오류 |

### 페이지네이션 공통 규약 (Cursor-based)

모든 목록 API는 아래 커서 기반 페이지네이션을 따른다.

**요청 파라미터**:
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `cursor` | string | null | 이전 응답의 `nextCursor` 값. 첫 페이지는 생략 |
| `limit` | integer | 20 | 한 페이지당 항목 수 (최소 1, 최대 100) |

**응답 포맷**:
```json
{
  "data": [ ... ],
  "nextCursor": "eyJpZCI6MTIzfQ==",
  "limit": 20
}
```
- `nextCursor`: 다음 페이지 커서. 마지막 페이지이면 `null`
- 커서 값은 opaque string (클라이언트는 해석하지 않음, Base64 인코딩된 내부 식별자)
- 정렬 기준: 각 API 엔드포인트별 명시 (기본: `created_at DESC`)

### 권한 역할
`PUBLIC`, `AUTHENTICATED`, `LEARNER`, `PRO`, `ADMIN`, `OWNER`

---

## 1. 인증 (OAuth2)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/oauth2/authorization/{provider}` | OAuth 리다이렉트 (github/google/kakao) | PUBLIC |
| GET | `/login/oauth2/code/{provider}` | OAuth 콜백 (Spring Security 처리) | PUBLIC |
| POST | `/auth/refresh` | 토큰 갱신 | AUTHENTICATED |
| POST | `/auth/logout` | 로그아웃 (refresh 무효화) | AUTHENTICATED |
| GET | `/users/me` | 내 프로필 | AUTHENTICATED |
| PUT | `/users/me` | 프로필 수정 | AUTHENTICATED |
| DELETE | `/users/me` | 계정 삭제 (14일 grace) | AUTHENTICATED |
| POST | `/users/me/restore` | 계정 복구 (14일 grace 기간 내) | AUTHENTICATED |
| GET | `/users/me/github-profile` | GitHub 수집 결과 | AUTHENTICATED |
| POST | `/users/me/github-profile/refresh` | GitHub 재수집 | AUTHENTICATED |

### 1.1 로그인 성공 응답
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token_cookie_set": true,
  "user": {
    "id": 42,
    "nickname": "지수",
    "onboarding_status": "PENDING",
    "plan": "FREE"
  }
}
```

---

## 2. 온보딩 · 진단

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/onboarding/profile` | 학습 목표 + 트랙 + 시간 약속 저장 | AUTHENTICATED |
| POST | `/onboarding/assessments` | 진단 세션 시작 | AUTHENTICATED |
| GET | `/onboarding/assessments/{id}/next` | 다음 문항 (적응형) | OWNER |
| POST | `/onboarding/assessments/{id}/answer` | 문항 답안 제출 | OWNER |
| POST | `/onboarding/assessments/{id}/complete` | 진단 종료 → `AssessmentCompletedEvent` | OWNER |
| GET | `/onboarding/assessments/{id}/result` | 결과 (강점·약점·diagnosed_level) | OWNER |
| POST | `/onboarding/assessments/guest` | **비회원 진단 체험** (결과 직전 가입 유도) | PUBLIC |
| POST | `/onboarding/assessments/claim` | **비회원→회원 전환**: guest_assessment_id로 진단 결과 이관 | AUTHENTICATED |

### 2.1 비회원 → 회원 전환 패턴
비회원 진단 완료 시 서버는 `guest_assessment_id` + 임시 결과를 Redis에 30분 저장. 로그인 완료 시 `POST /onboarding/assessments/claim` 으로 결과 이관.

```json
// POST /onboarding/assessments/claim 요청
{ "guest_assessment_id": "uuid-from-guest-session" }
// 응답: 200 OK + 이관된 assessment 정보
```

---

## 3. 학습 경로

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/learning-paths/me/generate` | 경로 생성 (SSE 진행 스트리밍) | LEARNER |
| GET | `/learning-paths/me` | 현재 활성 경로 | LEARNER |
| GET | `/learning-paths/me/this-week` | 이번 주 과제 3개 | LEARNER |
| POST | `/learning-paths/me/regenerate` | 재생성 (이유 입력) | LEARNER |
| GET | `/learning-paths/{id}/rationale` | "왜 이 순서인가" AI 멘토 코멘트 | OWNER |

### 3.1 `POST /learning-paths/me/generate` (SSE)
```http
POST /api/v1/learning-paths/me/generate
Accept: text/event-stream

// 응답 스트림
data: {"stage": "collecting", "message": "진단 결과와 GitHub 활동을 모으고 있어요"}
data: {"stage": "generating", "progress": 0.3, "message": "AI가 12주 로드맵을 설계 중입니다"}
data: {"stage": "matching", "progress": 0.7, "message": "콘텐츠를 매칭하고 있어요"}
data: {"stage": "done", "path_id": 1234, "first_week_tasks": [...]}
```

---

## 4. 콘텐츠

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/contents/{slug}` | 콘텐츠 상세 (Markdown + 코드 블록) | LEARNER |
| GET | `/contents/{slug}/code-blocks/{blockId}` | 코드 블록 상세 (starter_code + test_cases) | LEARNER |
| PUT | `/contents/{id}/progress` | 진척 갱신 (읽음/완료) | LEARNER |
| GET | `/contents/search?q=...&track=...` | 콘텐츠 검색 (BM25 + 임베딩) | LEARNER |

> **AR 관련 엔드포인트는 v1.0 범위 제외**. 참고 설계: [22_AR_아키텍처_체험_참고설계.md](./22_AR_아키텍처_체험_참고설계.md)

---

## 5. Sandbox Runner

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/sandbox/sessions` | 실행 세션 시작 (코드 + 언어 + 테스트) | LEARNER |
| GET | `/sandbox/sessions/{id}` | 상태 조회 | OWNER |
| GET | `/sandbox/sessions/{id}/stream` | 실행 로그 SSE 스트리밍 | OWNER |
| POST | `/sandbox/sessions/{id}/kill` | 강제 중단 | OWNER |
| GET | `/sandbox/quotas/me` | 내 일/월 한도 | LEARNER |

### 5.1 제출 요청
```json
{
  "content_id": 45,
  "code_block_id": 120,
  "language": "java21",
  "submitted_code": "public class Solution { ... }",
  "run_tests": true
}
```

### 5.2 Rate Limit
- 무료: 일 10회 / 월 100회
- Pro: 일 50회 / 월 무제한

---

## 6. AI 코드 리뷰

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/ai-reviews/sandbox/{sandboxSessionId}` | 리뷰 조회 (비동기 완료 여부) | OWNER |
| POST | `/ai-reviews/{id}/feedback` | 👍👎 | OWNER |

### 6.1 리뷰 응답
```json
{
  "id": 501,
  "status": "COMPLETED",
  "summary": "전반적으로 깔끔한 구현. JPA fetch 전략 개선 여지 있음.",
  "strengths": [
    "Repository 계층 분리가 명확합니다.",
    "테스트 케이스 커버리지가 높습니다."
  ],
  "improvements": [
    {"severity": "MEDIUM", "line": 42, "comment": "LazyInitializationException 가능성 — OSIV 끄고 fetch join 권장"},
    {"severity": "LOW", "line": 67, "comment": "변수명 `tmp` 대신 `pendingOrders`가 의도를 드러냄"}
  ],
  "security_issues": [],
  "confidence": 0.91
}
```

---

## 7. AI 멘토

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/ai-mentor/sessions` | 세션 생성 (컨텍스트 스냅샷 포함) | LEARNER |
| POST | `/ai-mentor/sessions/{id}/messages` | 메시지 전송 (**SSE 스트리밍**) | OWNER |
| GET | `/ai-mentor/sessions` | 세션 목록 | LEARNER |
| GET | `/ai-mentor/sessions/{id}/messages` | 히스토리 | OWNER |
| POST | `/ai-mentor/messages/{id}/feedback` | 👍👎 | OWNER |

### 7.1 `POST /ai-mentor/sessions/{id}/messages` (SSE)
```http
POST .../messages
Content-Type: application/json

{ "content": "N+1이 왜 발생해?" }

// 응답
data: {"token": "N+1은"}
data: {"token": " 연관 엔티티를"}
...
data: {"done": true, "message_id": 9001, "references": [
  {"type": "CONTENT", "content_id": 45, "title": "JPA 페치 전략"},
  {"type": "RECENT_TASK", "sandbox_id": 1201, "title": "N+1 리팩토링 과제"}
]}
```

**컨텍스트 자동 주입**: 현재 진행 중 콘텐츠 + 최근 5개 Sandbox 결과 + 최근 실패 테스트.

---

## 8. 커뮤니티

> 5개 게시판 + 스택오버플로 평판. 상세: [20_커뮤니티_기능_설계서.md](./20_커뮤니티_기능_설계서.md)

### 8.1 게시판 공통

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/community/posts?board=QNA&tag=jpa&sort=newest&unanswered=true` | 게시글 목록 | LEARNER |
| GET | `/community/posts/{id}` | 상세 | LEARNER |
| POST | `/community/posts` | 작성 (board_type으로 분기) | LEARNER |
| PUT | `/community/posts/{id}` | 수정 (본인 또는 편집 권한) | OWNER/REP:500 |
| DELETE | `/community/posts/{id}` | 삭제 (soft) | OWNER |
| POST | `/community/posts/{id}/vote` | `{value: 1 or -1}` | LEARNER (upvote 평판 15+, downvote 125+) |
| POST | `/community/posts/{id}/bookmark` | 북마크 | LEARNER |
| POST | `/community/posts/{id}/report` | 신고 (category/reason) | LEARNER |

### 8.2 Q&A

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/community/questions` | 질문 작성 (학습 맥락 자동 첨부 옵션) | LEARNER |
| GET | `/community/questions/{id}/ai-answer` | AI 시드 답변 조회 | LEARNER |
| POST | `/community/questions/{id}/ai-answer/rate` | 👍👎 (도움됨/불충분) | OWNER |
| POST | `/community/questions/{id}/answers` | 답변 | LEARNER |
| POST | `/community/answers/{id}/vote` | `{value: 1 or -1}` | LEARNER |
| POST | `/community/answers/{id}/accept` | 채택 | OWNER (질문자) |
| POST | `/community/questions/{id}/bounty` | 현상금 걸기 `{amount: 50~500}` | REP:1000+ |

#### 8.2.1 `POST /community/questions` 요청
```json
{
  "title": "JPA fetch join으로 페이징 하면 경고가 뜨는 이유?",
  "body_md": "...",
  "tags": ["jpa", "spring-data"],
  "attach_learning_context": true,
  "attach_recent_errors": true,
  "visibility": "ANSWERERS_ONLY"
}
```
응답에 `ai_answer_pending: true` 포함 → 수 초 내 `/ai-answer` 엔드포인트로 조회 가능.

### 8.3 자유 게시판 · 프로젝트 공유

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/community/projects` | 프로젝트 등록 (GitHub URL 필수) | LEARNER |
| POST | `/community/projects/{id}/star` | 스타 | LEARNER |
| POST | `/community/projects/{id}/request-review` | Q&A로 자동 생성 후 링크 | LEARNER |

### 8.4 태그 · 평판

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/community/tags?q=...` | 태그 검색·자동완성 | PUBLIC |
| GET | `/community/tags/{name}` | 태그 상세 (위키, 상위 답변자) | LEARNER |
| GET | `/community/users/{id}` | 프로필 (평판, 태그별 평판, 배지) | LEARNER |
| GET | `/community/users/{id}/reputation-events` | 평판 이력 | OWNER |
| GET | `/community/leaderboard?tag=jpa&period=week` | 랭킹 (Phase 2) | LEARNER |

### 8.5 팔로우 · 알림

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/community/follow` | `{target_type, target_id}` | LEARNER |
| GET | `/community/notifications/me` | 내 알림 | LEARNER |
| PUT | `/community/notifications/{id}/read` | 읽음 | OWNER |

### 8.6 모더레이션 (신뢰 사용자 / Admin)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/community/moderation/queue` | 신뢰 사용자 큐 | REP:10000+ / ADMIN |
| POST | `/community/moderation/vote/{target_id}` | 3표 중 1표 | REP:10000+ |
| POST | `/admin/community/sanctions` | 제재 부여 | ADMIN |

### 8.7 피어 매칭 (유지)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/community/peers/this-week` | 같은 주차+개념 피어 | LEARNER |

### 에스컬레이션 (CEO 리뷰 보강 6)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/community/questions/{id}/escalate` | AI 불충분 → 커뮤니티 에스컬레이션 | LEARNER (본인 질문만) |

**`POST /community/questions/{id}/escalate`**

```json
// Request
{
  "attach_ai_answer": true,          // AI 답변도 함께 공개
  "attach_learning_context": true,   // 학습 맥락 첨부
  "bounty_amount": null              // null이면 일반 에스컬레이션, 50~500이면 현상금
}
// Response: 200 OK
{
  "escalation_status": "ESCALATED_TO_COMMUNITY",
  "estimated_response_time": "24h",
  "queue_position": 3
}
// Error: 409 CONFLICT — 이미 에스컬레이션됨
// Error: 400 VALIDATION_FAILED — bounty_amount 범위 초과 (50~500)
// Error: 403 FORBIDDEN — 평판 부족 (현상금 차감 불가)
```

**이벤트 (Kafka Outbox)**:
| 이벤트 | 토픽 | 파티션 키 | 트리거 |
|--------|------|-----------|--------|
| `community.ai_answer.escalated` | `community-escalation` | `question_id` | AI 불충분 평가 시 |
| `community.question.unanswered_24h` | `community-escalation` | `question_id` | 24시간 미답변 자동 승격 |
| `community.question.unanswered_72h` | `community-escalation` | `question_id` | 72시간 미답변 AI 재생성 |

---

## 9. 알림

> 소유 서비스: `devpath-notification-svc` (2026-07-01 platform-svc에서 이관). 현재 구현: 디바이스 토큰 등록/삭제 2종. 알림 목록·읽음 처리는 TARGET(미구현).

| Method | Endpoint | 설명 | 권한 | 상태 |
|--------|----------|------|------|------|
| GET | `/notifications/me` | 전체 알림 목록 (커뮤니티 + 학습 + 시스템) | AUTHENTICATED | TARGET |
| PUT | `/notifications/{id}/read` | 읽음 처리 | OWNER | TARGET |
| PUT | `/notifications/read-all` | 전체 읽음 | AUTHENTICATED | TARGET |
| POST | `/notifications/devices` | FCM 토큰 등록 (모바일 푸시) | AUTHENTICATED | 구현됨 |
| DELETE | `/notifications/devices` | FCM 토큰 삭제 | OWNER | 구현됨 |

---

## 10. 대시보드 · 진척도

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/dashboard/me` | 홈 대시보드 (스트릭·진척·다음 과제·배지) | LEARNER |
| GET | `/progress/me/streak` | 스트릭 상세 | LEARNER |
| GET | `/progress/me/weekly-report` | 주간 리포트 | LEARNER |
| GET | `/progress/me/badges` | 배지 목록 | LEARNER |

### 10.1 대시보드 응답 예시
```json
{
  "streak": {"current_days": 7, "longest": 12, "at_risk": false},
  "this_week_progress": {"completed": 2, "total": 3, "percentage": 66},
  "next_task": {
    "content_id": 47, "title": "JPA 캐시 전략",
    "estimated_minutes": 25
  },
  "recent_badges": [{"code": "FIRST_CODE_REVIEW", "awarded_at": "..."}]
}
```

---

## 10. Admin

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
### 10.1 콘텐츠 관리

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/contents` | 콘텐츠 목록 (상태 필터) | ADMIN |
| POST | `/admin/contents` | 콘텐츠 생성 | ADMIN |
| PUT | `/admin/contents/{id}` | 콘텐츠 수정 | ADMIN |
| DELETE | `/admin/contents/{id}` | 콘텐츠 삭제 (soft delete) | ADMIN |
| GET | `/admin/contents/{id}/preview` | Markdown 미리보기 렌더링 | ADMIN |

### 10.2 사용자 관리

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/users` | 사용자 목록 (검색·필터: 상태/플랜/가입일) | ADMIN |
| GET | `/admin/users/{id}` | 사용자 상세 (프로필+OAuth+경로+평판+제재이력) | ADMIN |
| POST | `/admin/users/{id}/sanctions` | 제재 부여 (warn/suspend_7d/suspend_30d/ban) + 사유 | ADMIN |
| DELETE | `/admin/users/{id}/sanctions/{sanctionId}` | 제재 해제 | ADMIN |
| POST | `/admin/users/{id}/restore` | 삭제 예정 계정 복구 (14일 grace 내) | ADMIN |

### 10.3 운영 대시보드

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/dashboard/overview` | DAU/WAU/MAU + 신규 가입 추이 | ADMIN |
| GET | `/admin/dashboard/aha-funnel` | Aha 퍼널 단계별 전환율 | ADMIN |
| GET | `/admin/dashboard/system-health` | 5xx, p95, Sandbox 풀, Consumer lag 실시간 | ADMIN |

### 10.4 FinOps · Kill-switch

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/finops/dashboard` | AI 비용 대시보드 (일/월, 모델별, 사용자별) | ADMIN |
| PUT | `/admin/finops/kill-switch` | Kill-switch 토글 (멘토/리뷰/시드 개별) | ADMIN |

### 10.5 AI 품질 모니터링

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/ai/prompts` | 프롬프트 버전 목록 | ADMIN |
| POST | `/admin/ai/prompts/{id}/rollback` | 프롬프트 롤백 | ADMIN |
| GET | `/admin/ai/quality/code-review` | 코드 리뷰 품질 (👍👎 비율, 오탐률, 주차별 추이) | ADMIN |
| GET | `/admin/ai/quality/mentor` | 멘토 품질 (응답시간, 👍👎, 세션당 메시지) | ADMIN |
| GET | `/admin/ai/quality/seed-answer` | 시드 답변 품질 (도움됨/불충분, 에스컬레이션 비율) | ADMIN |
| POST | `/admin/ai/golden-test/run` | 골든 케이스 회귀 테스트 트리거 | ADMIN |
| GET | `/admin/ai/golden-test/results` | 골든 케이스 회귀 결과 목록 | ADMIN |

### 10.6 신고 · 모더레이션

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/reports` | 신고 목록 (상태/심각도/카테고리 필터) | ADMIN |
| GET | `/admin/reports/{id}` | 신고 상세 (원문+사유+AI판단+피신고자 이력) | ADMIN |
| PUT | `/admin/reports/{id}/resolve` | 신고 처리 (dismiss/warn/delete/suspend) | ADMIN |
| GET | `/admin/sanctions` | 제재 이력 통합 조회 (사용자별/기간별) | ADMIN |
| GET | `/community/moderation/queue` | 모더레이션 큐 | REP:10000+ / ADMIN |
| POST | `/community/moderation/vote/{target_id}` | 3표 중 1표 | REP:10000+ |
| POST | `/admin/community/sanctions` | 커뮤니티 제재 부여 | ADMIN |

### 10.7 진단 문항 관리 (Should)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/questions` | 진단 문항 목록 (Bloom 레벨/태그 필터) | ADMIN |
| POST | `/admin/questions` | 문항 생성 | ADMIN |
| PUT | `/admin/questions/{id}` | 문항 수정 | ADMIN |
| DELETE | `/admin/questions/{id}` | 문항 삭제 | ADMIN |
| POST | `/admin/questions/import` | CSV/JSON 일괄 가져오기 | ADMIN |

### 10.8 Sandbox · 공지 (Should)

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| GET | `/admin/sandbox/abuse-logs` | 악용 로그 (IP/사용자 필터) | ADMIN |
| PUT | `/admin/users/{id}/sandbox-suspend` | 사용자 Sandbox 정지 | ADMIN |
| GET | `/admin/announcements` | 공지사항 목록 | ADMIN |
| POST | `/admin/announcements` | 공지 생성 (노출 위치/예약 발행) | ADMIN |
| PUT | `/admin/announcements/{id}` | 공지 수정 | ADMIN |
| DELETE | `/admin/announcements/{id}` | 공지 삭제 | ADMIN |

---

## 11. Rate Limit · 사용량 한도

| 범위 | 기본 한도 |
|------|----------|
| OAuth 콜백 | 10 req/min per IP |
| 일반 API | 300 req/min per user |
| Path 생성 | 3 req/hour per user |
| AI 멘토 | 20 / month per user |
| Sandbox | 10 / day, 100 / month per user |

기본 한도는 FinOps 보호용 기본값이며 환경 변수로 조정 가능. 초과 시 `429 QUOTA_EXCEEDED` + `Retry-After` + `X-Quota-Reset-At` 헤더.

---

## 12. 관련 문서

- Swagger UI: `/swagger-ui.html`
- [03_프로젝트_아키텍처_정의서.md](./03_프로젝트_아키텍처_정의서.md)
- [05_화면_흐름_시퀀스_다이어그램.md](./05_화면_흐름_시퀀스_다이어그램.md)
