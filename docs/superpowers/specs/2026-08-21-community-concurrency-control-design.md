# 커뮤니티 콘텐츠 변경 경로 동시성 제어 — 설계

**목표:** `devpath-community-svc` 에서 실측으로 확인된 동시성 경쟁 네 건을 닫고, 그 과정에서
정한 방식을 조직 관례로 남긴다.

**범위:** community-svc 의 평판·채택·집계를 건드리는 변경 경로. 다른 여덟 서비스는 실측된
경쟁이 없으므로 손대지 않고, 관례 문서로 근거만 남긴다.

**출처:** 2026-08-21 Codex 외부 리뷰가 "락 없는 check-then-write" 두 건을 지적했고, 그것을
파일 대조로 확인하는 과정에서 경쟁 세 건이 더 드러났다.
상세 = `docs/superpowers/specs/2026-08-20-community-content-edit-delete-design.md` 의 후속.

---

## 1. 측정된 사실 (설계의 전제)

이 설계는 아래 다섯 가지 **측정 결과** 위에 서 있다. 추측이 아니다.

| # | 측정 | 결과 |
|---|---|---|
| M1 | `@Version`·`@Lock`·`LockModeType` 사용처 (9개 레포 전체) | **0건** |
| M2 | `DataIntegrityViolationException` 을 잡는 서비스 | **6개** — 이것이 집의 방식이다 |
| M3 | 격리 수준 설정 흔적 | 없음 → **READ COMMITTED**(PostgreSQL 기본) |
| M4 | READ COMMITTED 에서 `SELECT ... FOR UPDATE` 의 재읽기 | **재읽는다**(아래 M4 상세) |
| M5 | 테스트 프로파일 `hikari.maximum-pool-size` | **4** |

### M4 상세 — 대조군을 세운 측정

`FOR UPDATE` 가 락을 얻은 뒤 행을 다시 읽는지가 이 설계 전체의 주춧돌이다. PostgreSQL 16
에서 직접 쟀다. 세션 B 가 `UPDATE ... SET status='HIDDEN'` 을 커밋하지 않은 채 쥐고 있는
동안 세션 A 가 같은 행을 읽는다:

```
대조군  SELECT status FROM probe WHERE id=1              → PUBLISHED   (막히지 않는다)
본론    SELECT status FROM probe WHERE id=1 FOR UPDATE   → HIDDEN      (막혔다가 새 값을 본다)
```

★대조군이 없으면 이 관측은 증거가 아니다★ — `FOR UPDATE` 가 결과를 바꿨다는 것을 말하려면
바꾸지 않은 경우를 같이 봐야 한다. 대조군이 `PUBLISHED` 를 냈으므로 `HIDDEN` 은 락의 효과다.

### M2 가 만든 제약 — 이 자리에서 쓸 수 없는 수단

집의 방식(유니크 제약 + 예외 포착)을 **그대로 가져올 수 없다.** 이 레포가 이미 겪고
`ReportService` 주석에 박아 둔 트랩 때문이다:

> `@Transactional` 을 붙이지 않는다. (…) 트랜잭션 안에서 `DataIntegrityViolationException`
> 을 잡으면 **rollback-only 로 마킹돼 커밋 시점에 다시 터진다**(이 프로젝트의 광고 기능에서
> 겪은 트랩).

우리가 고칠 경로는 전부 `@Transactional` 이다. 따라서 **트랜잭션 안에서는 예외를 던지지 않는
수단**(행 락, 조건부 UPDATE)만 쓸 수 있다.

---

## 2. 경쟁 목록

내려간 콘텐츠의 변경을 막는 상태 가드는 이미 들어갔다(`97ad5ea`). 아래는 그 **뒤에 남은**
경쟁이다 — 둘 다 상태를 `PUBLISHED` 로 읽은 뒤 각자 커밋하는 창이다.

| | 경쟁 | 손해 | 도달성 | 이번 범위 |
|---|---|---|---|---|
| **R1** | 투표 ↔ 내리기 | 회수한 평판이 **복원**된다. 배지도 다시 나간다 | 창은 좁으나 평판은 다운보트 권한·배지를 여는 통화 | **포함** |
| **R2** | 채택 ↔ 삭제 | `solved` 가 사라진 답변을 가리키고 **+15/+2** 가 나간다 | 두 사람이 동시에 조작 | **포함** |
| **R3** | 내리기 ↔ 내리기 | 보정 이벤트 중복(총점은 `netBySource` 멱등이라 안전) | 1인 조직이라 사실상 없음 | 제외 |
| **R4** | 같은 사용자 동시 투표 | `upsert` 가 find-then-save 라 `uq_community_votes` 위반 → M2 트랩 → **500** | **더블클릭.** 가장 흔한 입력 | **포함** |
| **R5** | 두 사용자 동시 투표 | `refreshPostCounts` 가 `COUNT` 후 `set` → **lost update**. 다음 투표에 자가 치유되지만 그 사이 **배지가 잘못 나간다**(`answerNet >= 1`) | 인기 글이면 일상 | **포함** |
| **R6** 🆕 | 같은 작성자의 **서로 다른** 콘텐츠에 동시 투표 | `ReputationService.addTotal` 이 find-then-save 라, 평판 행이 없으면 둘 다 INSERT 해 `user_reputation_pkey` 위반 → M2 트랩 → **500**. 행이 있으면 둘 다 옛 총점을 읽어 **나중 것이 앞의 가산을 덮는다** | 신규 사용자의 **생애 첫 평판 이벤트**가 두 콘텐츠에서 겹칠 때. `addTag` 도 같은 모양 | **포함** |

★**R6 는 구현 중에 발견됐다**★ — Task 6 의 되돌림 관측이 집계 유실을 보러 갔다가 그 앞에서
`duplicate key ... user_reputation_pkey` 로 죽으며 드러났다. 계획에도 이 스펙의 초안에도 없었다.
**되돌림 관측을 넣지 않았다면 못 찾았다.**

R4 는 특히 아이러니하다 — 레포가 주석으로 경고해 둔 바로 그 트랩을 투표 경로가 이미 밟고 있다.

---

## 3. 접근 결정

**채택: 변경 경로 입구에서 대상 행을 비관적으로 잠근다(`SELECT ... FOR UPDATE`).**

★**단, 이것만으로는 부족하다 — 구현 중에 드러났다**★. 콘텐츠 행 락은 **같은 콘텐츠**에 대한
경쟁만 직렬화한다. R6 처럼 **서로 다른 콘텐츠**에서 같은 사용자의 평판 행으로 몰리는 경쟁은
잠글 공통 행이 없다(첫 요청 시점에는 그 행이 아직 없기까지 하다). 그래서 평판 가산만은
두 번째 기법을 쓴다 — **가산을 DB 안에서 원자적으로 끝내는 `ON CONFLICT DO UPDATE`**.
이것도 M2 제약을 지킨다(예외를 던지지 않는다).

콘텐츠 행 락이 덮는 것은 네 경쟁이다:

- **R1·R2** — 투표/채택과 내리기/삭제가 같은 행에서 직렬화되고, M4 대로 풀린 쪽이 새 상태를
  본다. 기존 상태 가드가 그제서야 신뢰할 수 있는 판정이 된다.
- **R4** — 같은 대상에 대한 두 요청이 직렬화되니 find-then-save 가 안전해진다. ★유니크 위반이
  **발생하지 않으므로** M2 트랩을 우회하는 게 아니라 아예 만나지 않는다★
- **R5** — 재집계가 직렬화되어 lost update 가 사라진다.

### 기각한 대안

**B. 조건부 UPDATE(compare-and-set) + `ON CONFLICT DO UPDATE`** — 각 쓰기가 전제를 `WHERE` 에
싣고 영향 행 수로 판정한다. 막힘도 교착도 없고 처리량이 낫다. 기각 이유: 유일한 강점인
처리량이 베타 규모에서 값이 없는 반면, R4 에서 `applyVote(old, new)` 에 필요한 **옛 투표값을
원자적으로 얻기가 까다롭다** — `RETURNING` 은 갱신 *후* 값을 주므로 CTE 나 `xmax` 같은 기교가
필요하다. A 에서는 그 문제가 사라진다.

**C. 하이브리드**(상태·평판은 A, 투표 행만 B) — A 가 이미 R4 를 덮으므로 기계 장치만 늘어난다.

### 정직한 대가

A 는 **조직 최초의 JPA 락 애노테이션**을 들인다(M1). 다만 B 도 조직 최초의 네이티브 upsert 를
들이므로 어느 쪽도 공짜가 아니고, A 가 더 작다. 그리고 되돌릴 수 있다 — 특정 지점이 뜨거워지면
그 지점만 B 로 바꾸면 된다.

---

## 4. 락 지점과 계약

### 잠그는 규칙

> 평판·채택·집계 중 하나라도 건드리거나, 그 판단의 근거가 되는 `status` 를 쓰는 경로.

| 대상 | 잠그는 경로 |
|---|---|
| 글 | `VoteService.votePost` · `ContentAdminService.hidePost` |
| 답변 | `VoteService.voteAnswer` · `AnswerService.accept` · `AnswerService.delete` · `ContentAdminService.hideAnswer` |
| 댓글 | **없음** — 평판도 채택도 집계도 없다 |

`PostService.deletePost` 는 **뺀다.** 상태를 쓰지만, `DELETED` 는 설계상 평판을 **유지**하므로
삭제 직전에 착지한 투표든 직후에 착지한 투표든 어느 쪽도 부당하지 않다. 잠글 이유가 없다.

본문 수정(`PostService.updatePost` · `AnswerService.update` · `CommentService.update`)은 셋 중
아무것도 안 건드리므로 잠그지 않는다. 편집이 내리기 직후에 착지하면 숨겨진 채 본문만 바뀌는데,
해가 없다.

### 리포지토리에 더하는 것 — 두 개뿐

```java
// CommunityAnswerRepository
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("select a from CommunityAnswer a where a.id = :id")
Optional<CommunityAnswer> findByIdForUpdate(@Param("id") long id);

// CommunityPostRepository — 같은 모양
```

호출부는 기존 `findById(...)` 를 `findByIdForUpdate(...)` 로 바꾸기만 한다. 뒤따르는
`.filter(status)` 판정은 **그대로 둔다** — 락이 생김으로써 그 판정이 비로소 신뢰할 수 있게 된다.

### 응답 계약: 한 글자도 바뀌지 않는다

| 진 쪽 | 응답 |
|---|---|
| 투표 | `404` (지금 상태 가드가 내는 것과 같은 답) |
| 채택 | `404` (이미 채택돼 있으면 기존대로 no-op) |
| 작성자 삭제 | `404`(이미 삭제) 또는 `409`(그 사이 채택됨) |
| 관리자 내리기 | `404`(이미 HIDDEN) |

**프론트는 손댈 것이 없다.**

### 교착 방지

> 명시적 락은 **직접 대상 한 행만** 잡는다. 이어지는 갱신은 **답변 → 질문** 순서로 고정한다.

현재 경로들이 이미 그 순서다(`accept` 도 `hideAnswer` 도 답변을 먼저 쓰고 질문을 나중에 쓴다).
바꿀 코드가 없고, 규칙은 앞으로를 위한 것이다.

### 락 대기는 반드시 유한해야 한다

무한 대기는 커넥션을 쌓아 서비스를 죽인다. 이 레포에 선례가 있다 —
`devpath-gitops/apps/devpath-migration/base/sandbox-preflight.yaml` 이 `lock_timeout=2000ms` 를
쓴다. 목표값은 **3초**.

★**미확인 전제**★ — `jakarta.persistence.lock.timeout` 힌트가 PostgreSQL 에서 실제로 먹는지
확인하지 않았다. PostgreSQL 은 역사적으로 `NOWAIT`/`SKIP LOCKED` 만 지원했다.
**계획의 첫 태스크가 이것을 실측한다.** 안 먹으면 `SET LOCAL lock_timeout` 으로 간다.
어느 쪽이든 "유한하다" 를 관측으로 증명한 뒤에만 다음으로 넘어간다.

---

## 5. 테스트 전략

### ★첫 구상이 틀렸다 — 판별력이 0이었다★

처음에는 "투표 스레드가 500ms 동안 막혀 있음" 을 락의 증거로 삼으려 했다. 그리고 그것이 락이
있든 없든 참일 거라 보고 판별력이 없다고 판단했다 — 락이 없어도 투표가 자기
`UPDATE community_answers` 에서 관리자의 미커밋 UPDATE 에 막힐 것이라고 봤기 때문이다.

★**구현하며 실측해 보니 그 판단이 틀렸다**★ (Task 2, `8a4bdee`). 락 없이 돌린 red 는
인터리빙 단언에서 났다 — 투표는 막히기는커녕 **500ms 안에 성공적으로 끝났다.** 원인은 JPA 다:

- `hideAnswer` 는 `save()` 로 엔티티를 더티로 만들 뿐 SQL 을 내지 않는다
- 뒤이은 `revokeAllForSource` 가 JPQL 질의를 날리지만, ★Hibernate 의 AUTO flush 는
  **테이블 범위로 판단**한다★. `ReputationEvent` 질의는 `CommunityAnswer` 의 더티 상태와
  겹치지 않으므로 flush 를 건너뛴다
- 그래서 `UPDATE` 는 커밋까지 미뤄지고 **그동안 행 락이 하나도 없다**

**교훈: 쓰기가 암묵적으로 락을 잡아 주리라는 기대는 커밋 전 어느 시점에도 성립하지 않는다.**
명시적 `FOR UPDATE` 만이 그 시점에 락을 잡는다. 이 사실이 접근안 A 의 근거를 오히려 강화한다.

결과적으로 단언 두 개가 **둘 다 판별력을 갖는다**:
- `get(500ms)` 가 타임아웃한다 = 인터리빙이 일어났다는 증거이자, 락이 실제로 잡혔다는 증거
- 커밋 뒤의 404 · 평판 0 = 풀린 쪽이 새 status 를 본다는 증거

앞의 것 없이는 두 번째 요청이 커밋 *이후에* 통째로 실행돼도 404 가 나와, 테스트가 옳은
이유가 아닌 이유로 통과한다. 두 단언은 여전히 서로 다른 일을 한다.

### 기법 하나로 네 경쟁 전부 — 테스트가 첫 트랜잭션을 쥔다

```java
tx.executeWithoutResult(st -> {
  contentAdmin.hideAnswer(answerId);              // 락 획득 + 평판 회수, 아직 커밋 전
  voter = pool.submit(() -> vote.voteAnswer(v, answerId, 1));
  assertThatThrownBy(() -> voter.get(500, MILLISECONDS))
      .as("인터리빙 증거: 투표가 아직 진행 중이어야 한다")
      .isInstanceOf(TimeoutException.class);
});                                                // 커밋 → 해제
assertThatThrownBy(() -> voter.get(5, SECONDS)).hasCauseInstanceOf(NotFoundException.class);
assertThat(repOf(answerer)).as("락이 없으면 여기가 10 이 된다").isZero();
```

같은 틀로 나머지 셋이 **전부 결정적**이 된다. 원래 확률적인 R4·R5 도 첫 트랜잭션을 붙잡는
것만으로 매번 같은 결과가 나온다 — 반복 실행이 필요 없다.

**테스트 다섯 개다** — 리포지토리 메서드가 둘(답변·글)이고, 각각 투표 쪽과 내리기 쪽 양편에서
걸려야 하므로 답변 경로만으로는 글 락이 한 번도 실행되지 않는다.

| | 첫 트랜잭션을 쥔 채 | 락 없으면 (= red 여야 하는 관측) | 락 있으면 |
|---|---|---|---|
| **R1-답변** | `hideAnswer` 열어 둠 → `voteAnswer` 던짐 | ★실측★ 투표가 **막히지도 않고 500ms 안에 성공**한다(위 AUTO flush 절) | 404, 평판 **0** |
| **R1-글** | `hidePost` 열어 둠 → `votePost` 던짐 | 투표 성공, 회수한 글 평판이 복원 | 404, 평판 **0** |
| **R2** | `AnswerService.delete` 열어 둠 → `accept` 던짐 | 채택 성공, `solved` 가 삭제된 답변을 가리키고 **+15** | 404, `solved=false`, 평판 **0** |
| **R4** | 사용자 A 의 **답변** 투표 tx 열어 둠 → 같은 사용자·같은 답변에 재투표 | `currentValue` 가 미커밋 표를 못 봐 insert → 유니크 위반 → **rollback-only → 500** | 직렬화, 표 **1행**, 평판 한 번만 |
| **R5** | 투표자 A 의 **글** 투표 tx 열어 둠 → 투표자 B 던짐 | B 의 `COUNT` 가 A 를 못 봐 `upvote_count` 에 **1** 을 쓴다 | B 가 세기 *전에* 막힘 → **2** |

R4 를 답변 경로로, R5 를 글 경로로 두면 두 리포지토리 메서드가 투표 쪽에서도 모두 실행된다.

### 테스트가 지켜야 할 제약 셋 (전부 실측 근거)

1. ★**테스트 클래스에 `@Transactional` 을 붙이면 안 된다**★ — 테스트 트랜잭션이 커넥션을 쥐고
   있으면 워커 스레드가 커밋된 데이터를 못 본다. 그래서 **`@BeforeEach` 정리가 필수**다.
   이것은 같은 리뷰에서 `ContentAdminMockMvcTest` 에 지적된 결함과 정확히 같은 규율이다.
2. **`maximum-pool-size: 4`**(M5) — 이 방식은 동시 커넥션 2 개(쥔 tx + 워커)를 쓴다. 여유가
   있지만 스펙이 이 수치를 명시해, 나중에 4 를 낮추는 사람이 이유를 알게 한다.
3. **`TransactionTemplate` 사용처가 이 레포에 0 건** — 새 기법이므로 계획이 정확한 모양을 싣는다.
   워커가 매달리지 않도록 모든 `get()` 에 타임아웃을 주고 `shutdownNow()` 를 `finally` 에 둔다.

### 완료 조건

각 테스트는 **`findByIdForUpdate` 를 `findById` 로 되돌렸을 때 위 표의 「락 없으면」 열이 실제로
관측되는지 확인한 뒤에야** 완료로 친다. "통과했다" 가 아니라 **"빼면 깨진다"** 가 완료 조건이다.

---

## 6. 관례 문서

`documents/48_동시성_제어_관례.md` 를 새로 쓴다(조직 표준은 최상단 번호 문서, 현재 `47_` 까지).

담을 것:

- **집의 방식은 "DB 가 심판"** — 앱 레벨 락 0 건(M1), 6 개 서비스가 유니크 제약 + 예외 포착(M2)
- ★**`@Transactional` 안에서 `DataIntegrityViolationException` 을 잡으면 rollback-only 로
  마킹돼 커밋 때 다시 터진다**★ — 트랜잭션 안에서는 **예외를 던지지 않는 수단**만 쓴다
- **언제 무엇을**
  - 중복 삽입을 막는다 → 유니크 제약 (단, 포착은 트랜잭션 **밖**에서)
  - read-modify-write 를 직렬화한다 → `SELECT ... FOR UPDATE`
  - 단일 문장으로 표현 가능하다 → 조건부 UPDATE + 영향 행 수 판정
- **락 순서 규칙**(직접 대상 한 행 → 정해진 순서로 갱신)
- **`lock_timeout` 은 반드시 유한**하며 그 값이 유한함을 관측으로 증명한다
- M4 처럼 **동시성 주장은 대조군을 세워 측정**한다

---

## 7. 수용 위험 (명시적으로 안 고치는 것)

| | 이유 |
|---|---|
| **R3** 관리자 중복 내리기 | 1 인 조직. 총점은 `netBySource` 멱등으로 이미 안전하고 보정 이벤트만 중복된다 |
| `voteAnswer` 의 **부모 글 창** | 부모를 내리는 동시에 답변에 투표하면 통과한다. 다만 `hidePost` 는 설계상 `POST` 소스만 회수하고 답변 평판은 건드리지 않으므로 **평판 복원 경쟁이 아니다** |
| **댓글 경로** | 평판도 채택도 집계도 없다 |
| `PostService.deletePost` | 상태를 쓰지만 `DELETED` 는 평판을 **유지**한다. 삭제 직전에 착지한 투표든 직후든 어느 쪽도 부당하지 않다 |
| **다른 8 개 서비스** | 실측된 경쟁이 없다. 추측으로 설계하지 않고 관례 문서를 따를 근거로 남긴다 |

### 미리 알리는 위험

`lock_timeout` 을 3 초로 두면 락을 오래 쥐는 경로가 생겼을 때 요청이 조용히 실패한다. 지금
잠그는 경로는 전부 짧지만(단일 행 + 몇 개 insert), **`revokeAllForSource` 는 회수 대상 이벤트
수에 비례한다.** 평판 이벤트가 아주 많은 콘텐츠에서 3 초를 넘길 수 있다.
**계획에 "이벤트 수가 큰 경우의 소요를 재는" 단계를 넣는다.**

---

## 8. 이 스펙이 하지 않는 것

- `@Version` 낙관적 락을 도입하지 않는다
- **API 계약을 바꾸지 않는다** → 프론트엔드 변경 0
- 격리 수준을 바꾸지 않는다(READ COMMITTED 유지)
- 다른 여덟 서비스의 쓰기 경로를 조사하거나 고치지 않는다

---

## 9. 성공 기준

1. 경쟁 테스트 **6 건**(R6 포함)이 green 이고, `findByIdForUpdate` → `findById` 로 되돌리면
   §5 표의 「락 없으면」 열대로 **red**
2. community-svc 기존 스위트 **182 건** 유지
2-1. ★평판 가산을 JPA 우회로 바꾼 부작용을 측정한다★ — `clearAutomatically` 가 영속성 컨텍스트
   전체를 비우므로, 평판 호출 **뒤에** 앞서 로드한 엔티티를 `save` 하는 곳이 없는지 메서드
   단위로 확인하고 전체 스위트로 재확인한다
3. `lock_timeout` 이 실제로 유한하다는 **실측 증거**(힌트가 안 먹으면 `SET LOCAL` 로 전환 후 재측정)
4. `documents/48_동시성_제어_관례.md` 가 존재하고 §6 의 항목을 담는다
