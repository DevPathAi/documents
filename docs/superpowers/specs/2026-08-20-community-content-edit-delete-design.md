# 커뮤니티 콘텐츠 수정·삭제 설계

- 작성일: 2026-08-20
- 대상 레포: `devpath-shared`(마이그레이션) · `devpath-community-svc`(API·서비스) · `devpath-frontend`(web·mobile·admin)
- 배경 백로그: `handoff-2026-08-20-cleanup-and-backlog-triage.md` §4 「지금 가능」 ②

## 1. 문제

커뮤니티에 **수정·삭제가 없다.** `community-svc` develop 에 `@PutMapping`·`@DeleteMapping` 이 **0건**이다
(대조군 `@PostMapping` 은 `CommunityController` 에만 7건). 글을 잘못 올리면 지울 방법이 없고, 관리자도
신고를 받고 나서 콘텐츠를 내릴 수단이 없다 — `ReportService.resolve` 의 `action` 은 `RESOLVE|REJECT`
뿐이고 **콘텐츠 상태를 전혀 바꾸지 않는다.**

### 착수 전 실측 — 인프라의 절반이 이미 있다

| 조각 | 상태 |
|---|---|
| `chk_community_posts_status` | **`DRAFT`·`PUBLISHED`·`HIDDEN`·`DELETED` 를 이미 허용** |
| `CommunityPost.status` | 있음(기본 `PUBLISHED`) |
| `PostIndexEventPublisher.publish(postId, boolean deleted)` | **서명이 이미 삭제를 받는다** |
| `PostIndexConsumer` | `deleted → indexer.delete(postId)` **구현돼 있음** |
| `PostIndexer.index()` | `status != PUBLISHED` 면 색인에서 지운다 · `delete()` 는 멱등 |
| 목록 쿼리 3종 | `status = 'PUBLISHED'` 필터 있음 |
| **실제 호출** | `publish(id, false)` 2곳뿐. **`true` 는 0곳** |

즉 **삭제 경로가 만들어져 있고 아무도 쓰지 않는다.** `HIDDEN`·`DRAFT`·`DELETED` 는 코드에서 0건이고
`PUBLISHED` 만 10건 쓰인다. `community_posts` 는 community-svc 전용이라 다른 서비스와 결합이 없다.

### 착수 전 실측 — 함께 닫아야 할 구멍 둘

★**`postDetail(id)` 가 상태를 거르지 않는다**★ — `findById` 만 쓴다. 목록에서 사라진 글도 **ID 로 직접
열면 읽힌다.** 삭제 기능을 붙이는 순간 이것이 결함이 된다.

★**`ReportService.targetAuthorId` 도 상태를 거르지 않는다**★ — 삭제된 콘텐츠를 신고할 수 있게 된다.

## 2. 확정된 결정

| # | 결정 |
|---|---|
| 1 | 범위 = **넷 전부**(글 · 질문 · 답변 · 댓글) |
| 2 | 답변·댓글 `status` 컬럼 **마이그레이션을 지금 shared 에 넣는다** |
| 3 | 권한 = **수정은 작성자 / 삭제는 작성자 + 관리자** |
| 4 | 표시 = **글·질문은 완전 제거 / 답변·댓글은 비석** |
| 5 | 평판 = **작성자 삭제는 유지 / 관리자 삭제는 회수** |
| 6 | 수정 이력 = **리비전 테이블로 보존** |
| 7 | 반응 있는 콘텐츠 = **수용된 답변만 제한(409), 나머지는 허용** |
| 8 | 클라이언트 = **web · admin · mobile 전부** |

### 마이그레이션을 지금 넣어도 되는 근거

shared `develop` 은 릴리스 PR #67 의 head 다. 그러나 `release-manifests/candidates/` 와 `releases/` 는
**비어 있다**(`.gitkeep` 뿐). 스키마가 `source_sha`·`shared_jar_sha256` 을 요구하지만 **아직 아무것도
고정되지 않았다** — 깨뜨릴 고정 해시가 없다. 대가는 Mission Spine 릴리스에 무관한 변경이 실리는 것이고,
그것을 감수하기로 했다.

### 채택하지 않은 접근

**`deleted_at TIMESTAMPTZ` 방식** — 더 단순하지만 한 서비스 안에 삭제 표현이 두 벌이 되고(`posts` 는
`status`), 결정적으로 **작성자 삭제와 관리자 삭제를 구분할 수 없다.** 결정 5를 표현할 방법이 없어
탈락했다.

**공통 `CommunityContent` 추상화** — 네 타입을 하나로 다루면 중복이 사라지지만 기존 4개 서비스·
리포지토리·DTO 를 전부 갈아엎어야 한다. 이 추상화가 지금 필요한 다른 문제를 풀어 주지 않는다. YAGNI.

## 3. 스키마

### 상태 어휘 — 삭제 주체를 상태로 구분한다

| 값 | 의미 | 평판 |
|---|---|---|
| `PUBLISHED` | 정상 | — |
| `DELETED` | **작성자**가 지움 | **유지** |
| `HIDDEN` | **관리자**가 내림 | **회수** |
| `DRAFT` | 미사용(`posts` CHECK 에만 존재) | 손대지 않음 |

결정 5 를 **별도 컬럼 없이 상태값만으로** 표현한다. 삭제 주체를 따로 저장할 필요가 없다.

### `V202608201001__community_content_soft_delete_and_revisions.sql`

```sql
-- 답변·댓글에 소프트 삭제 상태를 더한다. community_posts 는 이미
-- chk_community_posts_status 를 갖고 있으므로 어휘를 맞추되, 초안 개념이
-- 없는 두 테이블에서는 DRAFT 를 뺀다.
ALTER TABLE community_answers  ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED';
ALTER TABLE community_comments ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'PUBLISHED';

-- NOT VALID 로 마이그레이션 락 아래 전체 스캔을 피한다(V202608161007 과 같은 방식).
ALTER TABLE community_answers  ADD CONSTRAINT chk_community_answers_status
  CHECK (status IN ('PUBLISHED','HIDDEN','DELETED')) NOT VALID;
ALTER TABLE community_comments ADD CONSTRAINT chk_community_comments_status
  CHECK (status IN ('PUBLISHED','HIDDEN','DELETED')) NOT VALID;

-- 수정 이력. community_reports 와 같은 다형 대상 패턴(target_type + target_id).
-- 질문은 board_type='QNA' 인 게시글이므로 target_type 은 POST 다 — ReportTargetType 과
-- 같은 3값 어휘를 쓴다.
CREATE TABLE community_content_revisions (
  id          BIGSERIAL PRIMARY KEY,
  target_type VARCHAR(16) NOT NULL,
  target_id   BIGINT      NOT NULL,
  -- 글·질문만 제목이 있다(답변·댓글은 NULL). community_posts.title 과 같은 길이다.
  title       VARCHAR(120),
  body_md     TEXT        NOT NULL,
  body_html   TEXT,
  edited_by   BIGINT      NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_community_revisions_target CHECK (target_type IN ('POST','ANSWER','COMMENT'))
);
CREATE INDEX idx_community_revisions_target
  ON community_content_revisions(target_type, target_id, created_at DESC);
```

### `V202608201002__validate_community_content_soft_delete.sql`

```sql
ALTER TABLE community_answers  VALIDATE CONSTRAINT chk_community_answers_status;
ALTER TABLE community_comments VALIDATE CONSTRAINT chk_community_comments_status;
```

### 설계 판단 셋

**리비전은 「수정 직전 본문」을 담는다.** 현재 행이 최신을 들고 리비전이 과거를 쌓는다. 최초 작성분은
리비전에 없고, N 번 수정하면 리비전 N 개가 생긴다.

**`.sql.conf` 는 필요 없다.** 그것은 `CREATE INDEX CONCURRENTLY` 처럼 트랜잭션 밖에서 돌아야 하는
경우(`executeInTransaction=false`)에 붙인다. 이 마이그레이션은 전부 트랜잭션 안에서 안전하다.

**`community_posts` 는 손대지 않는다.** `status` 도 CHECK 도 이미 있다.

## 4. API 계약

### 경로로 권한을 가른다

메서드 안에서 role 을 파싱하지 않는다. `SecurityConfig` 가 이미 `/community/admin/**` 에
`hasRole("ADMIN")` 을 걸어 두었다. **경로가 곧 삭제 종류다.**

**작성자** (`/community`, 인증 필요)

| 메서드·경로 | 동작 | 응답 |
|---|---|---|
| `PUT /community/posts/{id}` | 글·질문 수정 | `200` + `PostDetailView` |
| `DELETE /community/posts/{id}` | 글·질문 삭제 → `DELETED` | `204` |
| `PUT /community/answers/{id}` | 답변 수정 | `200` + `AnswerView` |
| `DELETE /community/answers/{id}` | 답변 삭제 → `DELETED` | `204` |
| `PUT /community/comments/{id}` | 댓글 수정 | `200` + `CommentView` |
| `DELETE /community/comments/{id}` | 댓글 삭제 → `DELETED` | `204` |

**관리자** (`/community/admin`, `ROLE_ADMIN` 강제)

| 메서드·경로 | 동작 | 응답 |
|---|---|---|
| `DELETE /community/admin/posts/{id}` | → `HIDDEN` + 평판 회수 | `204` |
| `DELETE /community/admin/answers/{id}` | → `HIDDEN` + 평판 회수 | `204` |
| `DELETE /community/admin/comments/{id}` | → `HIDDEN` (평판 없음) | `204` |
| `GET /community/admin/revisions?targetType=&targetId=` | 수정 이력 조회 | `200` + `List<RevisionView>` |

★**질문에 별도 엔드포인트를 두지 않는다**★ — 질문은 `board_type='QNA'` 인 **같은 `community_posts`
행**이다. `/posts/{id}` 가 그대로 처리한다. 기존 `GET /community/questions/{id}` 는 조회 전용으로 남는다.

**리비전 조회를 관리자에게 연다** — 이력을 쌓아만 두면 쓸 데가 없다. 신고 처리 시 "답변 받고 질문을
통째로 바꿨는가" 를 확인할 근거가 된다. 이용자에게는 열지 않는다(이번 범위 밖).

### 요청·응답 본문

```
UpdatePostRequest(String title, String bodyMd)   // 글·질문 — 태그 없음
UpdateBodyRequest(String bodyMd)                 // 답변·댓글 (제목 없음)
```

`bodyHtml` 은 생성 때와 같은 경로로 서버가 렌더한다.

★**태그는 수정할 수 없다**★ — `CreatePostRequest`·`CreateQuestionRequest` 는 `List<String> tags` 를
받지만 수정 요청에서는 뺀다. 태그를 바꾸면 **과거 평판의 귀속이 어긋난다**: 평판 이벤트는 투표 시점의
태그로 `user_tag_reputation` 에 쌓였는데, 나중에 태그를 바꿔도 그 기록은 옛 태그에 남는다. 소급해서
재귀속하려면 이벤트별로 당시 태그를 되짚어야 하고 그것은 이 범위를 훌쩍 넘는다. 태그 수정은 §10
범위 밖으로 둔다.

`RevisionView(String targetType, long targetId, String title, String bodyMd, long editedBy, Instant createdAt)`
— 최신순. 페이지네이션은 두지 않는다(한 콘텐츠의 수정 횟수는 실무상 작다).

### 상태 코드

| 코드 | 에러 코드 | 언제 |
|---|---|---|
| `400` | `VALIDATION_FAILED` | 본문이 비었거나 제목 길이 초과 |
| `403` | `FORBIDDEN` | 작성자가 아님 |
| `404` | `RESOURCE_NOT_FOUND` | 없거나 이미 삭제됨 |
| `409` | `CONFLICT` | 수용된 답변 삭제 시도 |

예외는 shared `ApiExceptionHandler` 가 스펙 §3.4 envelope 로 렌더한다. 기존 `ForbiddenException`·
`NotFoundException`·`ConflictException` 을 재사용한다.

### 읽기 경로 수정 (§1 의 구멍을 닫는다)

- `postDetail(id)` — `status != 'PUBLISHED'` 면 `404`
- `listComments(postId)` — 삭제된 댓글도 반환하되 **비석**
- `questionDetail(id)` — 답변 목록에 삭제된 답변을 **비석**으로 포함
- `GET /community/posts/{id}/comments` — **부모가 `PUBLISHED` 가 아니면 `404`**(자식 우회 조회 차단)

### 비석 표현

`AnswerView`·`CommentView` 에 `boolean deleted` 를 더한다. `deleted=true` 면 `bodyMd`·`bodyHtml` 은
`null` 이고 **작성자 정보도 비운다** — 비석의 목적은 스레드 맥락 보존이지 "누가 썼다 지웠다" 의 기록이
아니다. `upvoteCount` 같은 집계는 그대로 둔다(평판을 유지하기로 했으므로 일관된다).

## 5. 권한·규칙

### 수정

- **작성자만.** 다른 사람이면 `403`.
- **삭제된 것은 수정 불가** → `404`.
- ★**시간 제한을 두지 않는다**★ — "N 분 안에만 수정" 은 **이력이 없을 때** 왜곡을 막는 방어책이다.
  리비전을 남기므로 그 방어가 다른 방식으로 성립한다. 답변이 달린 뒤에도 수정할 수 있고, 통째로
  바꿔치기하면 리비전이 증거로 남는다.
- **본문이 실제로 바뀌지 않으면 리비전을 만들지 않는다.** 같은 내용 저장으로 이력이 부풀지 않게 한다.

### 삭제

- **이미 삭제된 것 재삭제 → `404`**(멱등 `204` 가 아니다). 근거: 프론트 `report_menu_button.dart` 가
  이미 `resourceNotFound` 를 `'이미 삭제된 콘텐츠예요'` 로 렌더한다. `404` 가 그 UI 와 맞물린다.
- **수용된 답변 삭제 → `409`.** 먼저 수용을 해제하라고 알린다.
- 관리자가 `HIDDEN` 으로 내린 뒤 작성자가 삭제 시도 → `404`.

### 자식 콘텐츠는 건드리지 않는다

글·질문이 삭제돼도 그 아래 댓글·답변의 상태를 **전파하지 않는다.**

**되돌릴 수 있어야 한다** — 전파하면 복구 시 자식들의 원래 상태를 잃는다. 자식이 스스로 삭제된 것인지
부모 때문인지 구분이 사라진다.

**도달 경로가 이미 막힌다** — 부모가 `404` 면 자식에 갈 길이 없다. 우회 조회는 §4 의 자식 목록 `404` 로
막는다.

### 관리자 삭제는 수용 제한을 받지 않는다

작성자에게는 `409` 를 걸지만 **관리자 `HIDDEN` 에는 걸지 않는다.** 규정 위반 답변이 하필 수용된 상태일
수 있고, 그때 내리지 못하면 모더레이션이 무력해진다.

대신 내릴 때 질문의 연결을 정리한다 — `accepted_answer_id` 를 `NULL` 로, `is_solved` 를 `false` 로
되돌린다. 그러지 않으면 질문이 "해결됨" 인데 답이 없는 상태가 된다.

### 신고와의 상호작용

- **삭제된 대상 신고 → `404`.** §1 의 구멍을 닫는다.
- **열린 신고가 있는 콘텐츠가 삭제돼도 신고는 `OPEN` 으로 둔다.** 콘텐츠는 사라져도 작성자 제재 여부는
  별개다. 관리자가 목록에서 보고 `RESOLVE` 한다.
- **관리자 `HIDDEN` 시에도 신고를 자동 `RESOLVED` 로 바꾸지 않는다.** `resolve` 는 `reviewed_by`·
  `reviewed_at` 을 남기는 별개 행위다. 두 행동을 묶으면 "누가 무엇을 판단했는가" 가 흐려진다.

### 활동 목록

`ActivityController` 는 내 글·답변을 모은다. **삭제된 것은 제외한다** — 내가 지운 글이 내 활동에 남아
있으면 "지워지지 않았다" 고 읽힌다.

## 6. 색인·평판 연동

### 색인 — 호출만 추가하면 된다

| 동작 | 호출 |
|---|---|
| 글·질문 **수정** | `publish(postId, false)` |
| 글·질문 **삭제** | `publish(postId, true)` ← 코드베이스에서 `true` 가 처음 쓰인다 |
| 답변·댓글 수정·삭제 | **호출 없음** — 색인 문서에 답변·댓글이 없다 |
| ★**관리자가 수용된 답변을 내릴 때**★ | `publish(postId, false)` |

`PostDocument` 는 제목·본문·태그·게시판·상태·작성자·**해결여부**·작성시각을 담는다. 마지막 줄이
놓치기 쉬운 지점이다 — 답변을 내리면 `is_solved` 가 `false` 로 바뀌고 **그 값이
`PostDocument.isSolved` 에 실려 있다.** 색인을 갱신하지 않으면 검색 결과는 "해결됨" 인데 실제로는 답이
없는 상태가 된다.

참고: `publish(postId, true)` 는 없어도 결과가 같다 — `PostIndexer.index()` 가 `status != PUBLISHED`
면 스스로 `delete()` 로 간다. 명시하는 이유는 DB 조회 한 번을 아끼고 의도를 드러내기 위해서이고, 두
경로가 같은 곳에 도달하므로 어느 쪽이 실패해도 색인이 어긋나지 않는다.

### ★평판 회수 — 역 이벤트를 그대로 재사용하면 틀린다★

`reverseVote` 는 **한 투표자의** 이벤트만 되돌린다(`findByActorIdAndSourceTypeAndSourceId`). 관리자
삭제는 그 콘텐츠의 **모든** 평판을 되돌려야 하므로 새 경로가 필요하다.

그런데 **"그 소스의 모든 이벤트를 하나씩 `-delta` 로 뒤집는다" 가 함정이다.** 이미 취소된 투표가 있으면
원본(`+10`)과 그 역산(`-10`)이 **둘 다 저장돼 있다.** 각각 뒤집으면 `-10` 과 `+10` 이 되어 순효과가
**0** — 아무것도 회수되지 않는다.

올바른 방법은 **순합을 회수**하는 것이다:

```java
@Query("""
    select e.userId, e.reason, coalesce(sum(e.delta),0) from ReputationEvent e
    where e.sourceType = :sourceType and e.sourceId = :sourceId
    group by e.userId, e.reason having coalesce(sum(e.delta),0) <> 0
    """)
List<Object[]> netBySource(@Param("sourceType") String sourceType, @Param("sourceId") Long sourceId);
```

`(userId, reason)` 별 순합이 0 이 아닌 것만 `-합` 으로 보상 이벤트를 1 건씩 발행한다. 기존
`countDistinctUpvotedSourcesByActorToUser` 가 `delta > 0` 으로 역산분을 걸러 내는 것도 같은 사실의
반영이다 — **역 이벤트는 같은 `reason` 에 음수 `delta` 로 쌓인다.**

**태그 점수도 같이 되돌린다.** `VoteService` 와 같은 방식으로 구한다 — POST 면
`postTags.findByPostId(postId)`, ANSWER 면 부모 질문의 `postId` 로. `DOWNVOTE_CAST` 만 태그 무관이라
총점만 되돌린다(기존 `reverseVote` 의 예외 처리와 동일).

**수용 보너스는 자동으로 포함된다** — `ACCEPTED`·`ACCEPT_BONUS` 도 같은 `(sourceType, sourceId)` 에
쌓이므로 순합에 자연히 들어온다.

**멱등하다** — 회수 후 순합이 0 이 되므로 같은 콘텐츠에 회수를 다시 돌려도 아무 일도 일어나지 않는다.

### 댓글에는 회수할 평판이 없다

`ReputationEvent.sourceType` 은 `VoteService` 에서 `"POST"`·`"ANSWER"` 만 쓰이고, 컨트롤러에
`/comments/{id}/vote` 가 없다. `CommunityComment.upvoteCount` 컬럼은 있지만 **투표 경로 자체가 없다.**
따라서 댓글 관리자 삭제에는 평판 회수 단계가 아예 없다.

### 트랜잭션 경계

`PostIndexEventPublisher`·`ReputationService` 모두 `@Transactional`(REQUIRED)로 호출자 트랜잭션에
합류한다. 삭제 서비스 메서드를 `@Transactional` 로 두면 **상태 변경 · 리비전 저장 · 평판 회수 ·
아웃박스 적재가 한 트랜잭션에서 커밋**된다. 아웃박스 릴레이가 2 초 주기로 Kafka 에 내보내므로 색인만
결과적 일관성이다.

## 7. 프론트엔드

### apps/web

**데이터 계층** — `community_source.dart` 에 **10 개** 추가(작성자 6 + 관리자 4). 관리자 4 개(삭제 3 +
리비전 조회 1)는 admin 앱에서만 호출한다.

**메뉴** — `ReportMenuButton` 을 `ContentMenuButton` 으로 넓힌다. 새 위젯을 만들지 않는 이유는 **한
콘텐츠에 메뉴가 둘이 되면 안 되기** 때문이다. 작성자 여부로 항목이 갈린다 — 내 콘텐츠는 `수정`·`삭제`,
남의 콘텐츠는 `신고`(지금 그대로).

**수정 화면** — `post_create_page`·`question_create_page` 를 **편집 모드로 재사용**한다. 이미 제목
필드와 `RichEditor` 를 갖고 있다. 답변·댓글은 화면 전환 없이 **인라인 편집**(카드 안에서 `RichEditor`
가 열림)이 맞다 — 짧은 글에 페이지 전환은 과하다.

**삭제 확인** — `report_dialog.dart` 와 같은 결의 확인 다이얼로그. **되돌릴 수 없다**는 것을 문구에
명시한다.

**비석** — 답변·댓글 카드에서 `deleted == true` 면 본문 자리에 `'삭제된 내용입니다'` 를 흐린 색으로
렌더하고 작성자·투표 버튼을 감춘다. 카드 자체는 남아 스레드 순서가 보존된다.

**에러 문구** — `403` `'내가 쓴 글만 수정할 수 있어요'` · `404` `'이미 삭제된 콘텐츠예요'`(**기존 문구
그대로 재사용**) · `409` `'채택된 답변은 채택을 먼저 해제해 주세요'`.

### apps/admin

관리자 삭제 3 개를 붙인다. 신고 목록에서 대상으로 이동해 내릴 수 있으면 모더레이션 흐름이 완성된다.

★**착수 전 실측이 필요하다**★ — 메모리에 "admin 신고화면은 백엔드 없는 껍데기였음" 이라는 기록이 있다.
admin 앱의 신고 화면이 실제로 어떤 상태인지 확인하고 나서 이 부분의 작업량을 정한다.

### apps/mobile

**수정·삭제 둘 다 넣는다.** 모바일은 퀵 캡처 질문 작성·답변·채택을 하는 쓰기 클라이언트다.

모바일은 `TextField(maxLines: 10)` 로 본문을 받고 **Quill 이 없다**(`pubspec` 대조: mobile 0 · web 2).
따라서 편집 UI 가 웹보다 단순하다 — 같은 `TextField` 에 기존 `bodyMd` 를 채워 넣으면 된다.

**알려진 비대칭**: 웹에서 리치로 쓴 글을 모바일에서 열면 **원시 마크다운이 보인다.** 마크다운이므로
틀린 표시는 아니지만 이용자에게는 낯설 수 있다. 이번 범위에서 해결하지 않는다.

## 8. 테스트 전략

### 이 설계의 핵심 회귀 가드

★**평판 순합 테스트**★ — 투표 → 취소 → 재투표로 이벤트를 여러 겹 쌓은 뒤 관리자 삭제를 돌린다.
**순효과가 정확히 0** 이어야 한다.

이 테스트가 중요한 이유는 §6 의 함정을 정확히 겨냥하기 때문이다. "각 이벤트를 하나씩 뒤집는" 순진한
구현이면 **이 테스트만 red 가 된다** — 이벤트가 한 겹뿐인 단순 시나리오에서는 두 구현이 똑같이 green
이라 구분되지 않는다. 판별력이 여기에만 있다.

### 구현 전에 red 여야 하는 테스트

★`postDetail` 로 삭제된 글 조회 → `404`★ — 지금 코드는 `200` 을 반환한다. 구현 전에 실제로 red 임을
확인하고 시작한다. 그래야 "고쳤다" 가 증거를 갖는다.

### 백엔드

| 대상 | 확인 |
|---|---|
| 엔드포인트 10 종 | 성공 / `403` 남의 것 / `404` 없음·이미 삭제 / `409` 수용된 답변 |
| 리비전 | 수정 N 회 → 리비전 N 개 · **같은 내용 저장 → 증가 없음** |
| 자식 우회 | 부모 삭제 후 `GET /posts/{id}/comments` → `404` |
| 신고 | 삭제된 대상 신고 → `404` |
| 색인 | **수용 답변 `HIDDEN` 시 `publish(postId, false)` 호출** — Mockito `verify` |
| 마이그레이션 | Flyway 적용 후 CHECK 가 잘못된 상태값을 거부 |

★**각 가드를 임시로 지워 red 가 나는지 실제로 돌린다.**★ 이 프로젝트에서 "판별력 없는 green" 을 반복해
겪었다.

**인프라 함정** — Postgres + Redis 컨테이너 둘 다 필요하다. `hikari.maximum-pool-size` 를 낮추지 않으면
`too many clients` flake 가 난다. JPA 캐시를 단언할 때 `em.clear()` 없이는 판별력이 없다.

### 프론트

- 메뉴 분기 — 내 콘텐츠 `수정`·`삭제` / 남의 것 `신고`
- 비석 렌더 — `deleted=true` 면 본문·작성자·투표 버튼 없음
- 에러 문구 3 종 매핑
- ★**골든패스 통합 테스트**★ — 작성 → 수정 → 삭제 → 목록에서 사라짐. 단위 테스트만 보고 통합 흐름을
  놓친 전례가 있어(진단 트랙 선택 때 골든패스 5 곳) 반드시 넣는다
- `web_mock_fixtures.dart` 에 새 엔드포인트 픽스처 — 없으면 테스트가 `등록되지 않은 픽스처` 경고를 내며
  조용히 다른 경로를 탄다
- mobile — `TextField` 프리필 + 삭제 확인 다이얼로그

## 9. 릴리스 제약

**shared 마이그레이션이 먼저 나가야 한다.** `community-svc` 가 `status` 컬럼을 읽는 코드를 들고
운영에 올라갔는데 컬럼이 없으면 시작조차 못 한다. 순서는 **shared 마이그레이션 → community-svc →
frontend** 다.

**릴리스 통제가 풀려야 한다.** 이 작업의 shared 부분은 HOLD 걸린 Mission Spine 릴리스에 실린다.
`qahnaarin` 초대 수락 → shared #67 → 게시 → 서비스 릴리스 순서를 거쳐야 운영에 도달한다.
**develop 까지의 개발·CI 는 HOLD 와 무관하게 진행할 수 있다.**

## 10. 범위 밖

- 이용자용 리비전 조회 화면(관리자만 연다)
- 삭제 복구(undelete) API — `HIDDEN`→`PUBLISHED` 전환은 상태값으로 표현 가능하지만 이번에 만들지 않는다
- 웹 리치 텍스트와 모바일 원시 마크다운의 비대칭 해소
- `ReportService.resolve` 에 "내리기" 액션을 합치는 것(§5 의 이유로 분리 유지)
