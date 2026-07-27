# MD3 슬라이스 #9 — LCS(학습 맥락 자동 첨부) 설계서 (2026-06-26)

> 출처 권위 문서: `26_학습맥락_자동첨부_구현.md`(v1.0) + ERD `02_§8.5` + 스케줄 `17_§9`. 본 설계는 그 중 **MVP 골든패스 부분집합**을 구현한다(슬라이스 #8과 동일한 컷 철학).

## 0. 선행 brainstorming 결정 (2026-06-26, 사용자 승인)
- **① 아키텍처 = 전용 신규 마이크로서비스 `devpath-lcs-svc`** (사용자 결정). 문서의 "얇은 브릿지 서비스" 의도 + 교차서비스 FK 금지 원칙에 부합. `devpath-svc-template`에서 파생, 포트 8087, 패키지 `ai.devpath.lcs`.
- **② 스냅샷 소스 = on-demand 풀(Read Path fallback)**. 문서 §3 Hybrid의 fallback 동기 쿼리가 source-of-truth. 실시간 Kafka 이벤트 스트림 + Redis 7일 캐시는 **Phase 2 연기**(MVP가 쓸 `learning.content.opened/progressed` 이벤트는 아직 미구현 → 풀로 우회). ai-svc `MentorContextAssembler`(LearningClient + SandboxClient) 패턴 승계.
- **③ 에러 로그 수집 + 3단계 Sanitize = Phase 2 연기**(문서 §12-1이 명시: "Phase 1은 에러 로그를 수집하지 않는다 — 가장 민감한 필드를 Phase 2로"). MVP 스냅샷 필드 = current_content·current_path·active_tags·tag_reputation (errors 제외).
- **④ 식별자 = BIGINT**(문서는 UUID지만 실제 시스템은 `userId=jwt.getSubject()` Long·community ids long). 시스템 규약 준수.
- **⑤ 데이터 모델 = LCS 자체 DB**(교차서비스 FK 금지). `user_id`·`current_content_id`·`linked_question_id`는 **논리참조**(FK 없음). shared 중앙 Flyway에 마이그레이션 추가(슬라이스 #8 D-7 승계).

## 1. 시스템 개요
LCS(Learning Context Snapshot Service)는 질문 작성 시 작성자의 **현재 학습 맥락**(보던 콘텐츠·학습경로 진척·활성 태그·태그 평판)을 스냅샷으로 조립해, 작성자가 필드별 on/off로 선택 후 질문에 **불변 첨부**하고, 답변자가 맥락 패널로 본다. 목적 = 답변 품질↑ + 중복 질문↓(맥락 공유).

**책임**: 수집(풀)·조립·영속(불변)·프라이버시(필드/노출 제어). **비책임**: 콘텐츠 메타 관리(learning-svc)·답변자 UI 렌더(community 프론트)·질문 본문 저장(community-svc).

## 2. MVP 범위 (In / Out)
**In (Phase 1)**
- `devpath-lcs-svc` 신규 서비스(svc-template 파생, security/JPA/Redis/shared).
- 스키마(shared 중앙 Flyway): `learning_context_snapshots` + `user_context_preferences`.
- API: `POST /lcs/snapshots/draft`(미리보기 조립) · `POST /lcs/snapshots/{id}/commit`(영속) · `GET /lcs/snapshots/{id}`(답변자, 인가) · `GET/PUT /lcs/preferences`.
- 스냅샷 조립 = learning-svc(현재 콘텐츠·경로 진척)·community-svc(태그 평판은 MVP에선 생략 또는 0) 풀. **풀 실패 시 graceful**(해당 필드 unavailable).
- draft = Redis(TTL 10분) · commit = PostgreSQL(불변).
- 프라이버시 preferences 6필드 토글(기본값: recent_errors=OFF).
- gateway `/lcs/**` 라우트(JWT 엣지).
- 프론트: 질문 작성 폼 **맥락 카드**(필드 토글·미리보기·opt-in) + 질문 상세 **답변자 맥락 패널**.

**Out (Phase 2/3 연기 — 문서 §12-2·12-3)**
- 🔴 에러 로그 수집 + **3단계 Sanitize 파이프라인**(정규식 마스킹·AI 검증) → Phase 2.
- 🔴 실시간 **Kafka 학습활동 스트림 + Redis 7일 컨텍스트 캐시**(content.opened/progressed 이벤트 신규 포함) → Phase 2.
- recent_errors 필드 활성화 → Phase 2(Sanitize 선행 필수).
- Audit trail·Rate limiting·GDPR export/bulk delete·AES 저장암호화·이상행위 감지 → Phase 2/3.
- tag_reputation = 평판 엔진(슬라이스 #9 후속 "평판 기초")에 의존 → MVP는 생략(빈 맵).

## 3. 데이터 모델 (shared 중앙 Flyway, 다음 버전 `V20260626xxxx__lcs_snapshots.sql`)
> 교차서비스 FK 없음(user_id·content_id·path_id·question_id 논리참조). LCS 자체 도메인 테이블.

**`learning_context_snapshots`**
| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | BIGSERIAL PK | 영속 스냅샷 id |
| `user_id` | BIGINT NOT NULL | 논리참조(platform) |
| `purpose` | VARCHAR(32) NOT NULL | `question_attachment`(MVP), CHECK |
| `attached_to_type` | VARCHAR(32) | `question` |
| `attached_to_id` | BIGINT | community_questions.post_id 논리참조 |
| `content_snapshot` | JSONB NOT NULL | 불변 맥락(조립 결과) |
| `visibility` | VARCHAR(16) NOT NULL DEFAULT `answerers_only` | `public`/`answerers_only`/`private`, CHECK |
| `fields_included` | JSONB NOT NULL | 포함 필드 목록 |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
- 인덱스: `(user_id)`·`(attached_to_type, attached_to_id)`·`(created_at DESC)`. 불변(커밋 후 UPDATE 금지, 삭제는 physical delete).

**`user_context_preferences`**
| 컬럼 | 타입 | 기본 |
|---|---|---|
| `user_id` | BIGINT PK | 논리참조 |
| `collect_current_content` | BOOLEAN NOT NULL | TRUE |
| `collect_learning_path` | BOOLEAN NOT NULL | TRUE |
| `collect_active_tags` | BOOLEAN NOT NULL | TRUE |
| `collect_recent_errors` | BOOLEAN NOT NULL | **FALSE** |
| `collect_tag_reputation` | BOOLEAN NOT NULL | TRUE |
| `collect_level` | BOOLEAN NOT NULL | TRUE |
| `default_visibility` | VARCHAR(16) NOT NULL | `answerers_only` |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

(`sanitize_rules` 테이블은 Phase 2와 함께 — MVP 미생성.)

## 4. API 계약 (gateway `/lcs/**` → lcs-svc, JWT)
- `POST /lcs/snapshots/draft` — body `{purpose, requestedFields:[...]}` → 조립 미리보기. 응답 `{draftId, expiresAt, content:{...}, fieldsAvailable:[...], fieldsUnavailable:[{field, reason}]}`. draft는 Redis `lcs:draft:{token}` TTL 10분. `userId=jwt.subject`.
- `POST /lcs/snapshots/{draftId}/commit` — body `{attachedToType, attachedToId, visibility}` → PG 영속. 응답 201 `{snapshotId, status:"committed", immutable:true}`. 작성자 본인만(draft 소유자 검사).
- `GET /lcs/snapshots/{id}` — 답변자 조회. 인가: public=로그인전체 / answerers_only=로그인전체(MVP: 게시판 권한 단순화) / private=작성자 본인. 응답 `{id, createdAt, content, renderedFor:"answerer"}`. 권한 없으면 403.
- `GET /lcs/preferences` · `PUT /lcs/preferences` — 프라이버시 6필드 + default_visibility.

필드명 camelCase(시스템 규약). 에러는 community-svc 패턴(GlobalExceptionHandler: NotFound 404·Forbidden 403).

## 5. 스냅샷 조립 (풀, 멘토 패턴 승계)
- `SnapshotAssembler.assemble(userId, requestedFields, prefs)`:
  1. prefs로 필드 게이팅(off면 fieldsUnavailable에 `user_preference_off`).
  2. current_content/current_path → **learning-svc** 내부 호출(ai-svc `LearningClient` 패턴: `Optional` 반환·timeout 5s·실패시 graceful empty). 필요 신규 엔드포인트: learning-svc `GET /internal/users/{userId}/current-context`(현재 콘텐츠·경로·진척). 없으면 빈 필드.
  3. active_tags/tag_reputation → MVP 생략(빈)·후속 평판.
  4. recent_errors → MVP 미수집(Phase 2).
  5. JSON 직렬화(JsonMapper), draft Redis 저장.
- **graceful degradation**: 한 소스 실패해도 부분 스냅샷 반환(문서 §3-4·11). 멘토 assembler와 동일 fail-safe.
- ⚠️ learning-svc `/internal/users/{userId}/current-context` 미존재 가능 → Build B에서 learning-svc에 해당 내부 엔드포인트 추가(또는 기존 `user_content_progress` 조회 재사용). Build 시 실측 후 결정(추측 금지).

## 6. 프론트 (apps/web, melos 게이트)
- **맥락 카드**(질문 작성 폼): "내 학습 맥락 첨부" opt-in 토글 → on이면 `POST /lcs/snapshots/draft` 호출 → 필드별 칩 토글(현재 콘텐츠·경로·태그) + 미리보기 + 노출범위 선택. 질문 게시 시 draftId를 community `POST /community/questions`에 동봉(또는 게시 후 community가 commit 호출 — Build C에서 계약 확정).
- **답변자 맥락 패널**(질문 상세): 질문에 스냅샷 있으면 `GET /lcs/snapshots/{id}` → 맥락 패널(현재 콘텐츠·경로·태그) 렌더. 없으면 미표시.
- dp_core 모델 + provider(목 MockHttpAdapter 픽스처) + 위젯/컨트롤러 테스트. `melos run analyze/test/format` 녹색.

## 7. community-svc 연계 (Build C)
- `CreateQuestionRequest`에 `lcsSnapshotId`(옵션) 추가 → 질문 생성 tx 후 community가 lcs-svc `commit(snapshotId, questionId)` 호출(또는 프론트가 commit 후 questionId 동봉 — 순환 회피 위해 **게시 응답의 questionId로 프론트가 commit** 방식 채택, community 무변경 최소화). `community_questions.learning_context` JSONB에 `{"snapshotId": N}` 저장은 Build C에서 확정.
- ⚠️ commit 시점 questionId 필요 → 흐름: 프론트가 질문 게시(201, questionId 수신) → 프론트가 `POST /lcs/snapshots/{draftId}/commit {attachedToId: questionId}`. community-svc 변경 최소(learning_context 컬럼은 이미 존재).

## 8. 빌드 분해
- **A (shared)**: `learning_context_snapshots`·`user_context_preferences` 마이그레이션(다음 버전) + publishToMavenLocal. main 릴리스(shared는 develop 부재 → feature→main).
- **B (lcs-svc 코어)**: svc-template 파생 → 신규 레포 `devpath-lcs-svc`(security/JPA/Redis/shared) + 엔티티·리포지토리 + `SnapshotAssembler`(learning-svc 풀) + `LcsController`(draft/commit/get/preferences) + Redis draft + SecurityConfig + GlobalExceptionHandler. CI(postgres+redis) green. (learning-svc 내부 엔드포인트 필요 시 함께.)
- **C (gateway + community 연계)**: gateway `/lcs/**` 라우트 + commit 흐름 계약 확정. gitops app 등록.
- **D (frontend)**: 맥락 카드 + 답변자 패널 실API.
- **통합 릴리스**: lcs-svc·gateway·frontend(+필요시 learning-svc) develop→main + 신규 gitops app + image/deploy.

## 9. 환경/제약 (메모리 wsl-build-environment)
- JVM 빌드: JDK 21(`~/jdks`), shared 의존성은 mavenLocal 우회(GitHub Packages 401). CI가 1급 검증 경로.
- lcs-svc CI: postgres(pgvector pg17) + **redis 서비스 컨테이너 추가 필요**(community CI엔 redis 없음 → lcs ci.yml에 redis 추가).
- 포트 8087, gateway 라우트 `LCS_SVC_URI`.
- Test-First·추측금지·컨트롤러 직접검증(절대조건).

## 참고
- 권위: `26_학습맥락_자동첨부_구현.md`(§6 데이터·§7 API·§12 구현순서) · ERD `02_§8.5` · 스케줄 `17_§9`.
- 재사용: ai-svc `mentor/MentorContextAssembler`·`LearningClient`(풀 패턴) · community-svc(svc 골격·SecurityConfig·Outbox) · slice-8 D-7(shared 중앙 Flyway).
