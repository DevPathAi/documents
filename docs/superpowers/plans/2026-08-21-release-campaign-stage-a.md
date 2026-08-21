# 릴리스 캠페인 Stage A 구현 계획 — 확정 결함 9건 + Codex 재리뷰

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 리뷰에서 확정했으나 미수정으로 남긴 결함 9건(shared 3 · frontend 6)을 고치고,
수정이 반영된 최종 diff 를 Codex 로 재리뷰해 Stage B(머지)의 입장권을 만든다.

**Architecture:** 기존 열린 PR 의 브랜치 위에 그대로 쌓는다(새 브랜치 없음). shared 는 테스트
판별력 보강(운영 코드 무변경), frontend 는 좁은 UI 수정 3건 + 테스트 판별력 보강 3건.

**Tech Stack:** Java 21 · JUnit 5 · Flyway · PostgreSQL 17 / Flutter · Riverpod 3 · melos

**Spec:** `docs/superpowers/specs/2026-08-21-release-campaign-design.md` §3

## Global Constraints

- 브랜치: shared 작업은 `feat/community-content-soft-delete`(PR #70) 위, frontend 작업은
  `feat/content-edit-delete`(PR #136) 위. **새 브랜치를 만들지 않는다**(열린 PR 갱신이 목적).
- ★shared #70 의 CI 는 수정 뒤에도 **불변 게시 계약 때문에 red 가 정상**★ — 게이트는 로컬
  전체 스위트다. 빈 DB 레시피:

  ```bash
  docker exec devpath-pg psql -U devpath -d postgres -c "DROP DATABASE IF EXISTS shared_v3" -c "CREATE DATABASE shared_v3 OWNER devpath"
  docker exec devpath-pg psql -U devpath -d shared_v3 -c "CREATE EXTENSION IF NOT EXISTS vector"
  cd /d/workspace/dpa/devpath-shared
  DB_URL=jdbc:postgresql://localhost:5432/shared_v3 DB_USER=devpath DB_PASSWORD=localdev \
  GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
    ./gradlew test > /tmp/s.log 2>&1; echo "GRADLE_EXIT=$?"
  ```

- frontend 검증: `dart pub global run melos analyze` · `melos test`(golden 제외 설정이 이미
  있음). Quill 본문은 `find.text` 로 안 보인다 — 저장 경로의 값으로 검증한다.
- 함정 리마인드: `grep | head` 의 `$?` 는 head 것 · 한글 파일에 perl 금지 ·
  `./gradlew | tail` 금지(`> log; echo $?`) · **"green 인 새 테스트"는 되돌림/사보타주로
  판별력을 실증한 뒤에만 완료**.
- 커밋은 Task 당 1개. push 는 레포별 태스크 묶음이 끝난 뒤(PR 갱신 시점을 모은다).
- Codex 실행 레시피(검증됨): diff 를 프롬프트에 인라인 · `-c 'mcp_servers={}'` ·
  `run_in_background` · 응답 추출 `awk '/^codex$/{f=1;next} f' | awk '/^tokens used/{exit} {print}'`.

---

## Part S — devpath-shared (PR #70 브랜치)

### Task S1: 상태 CHECK 가 "검증까지 끝난 정확한 어휘"임을 단언한다

**Files:**
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`
  (`communityContentStatusCheckRejectsUnknownValues` 끝부분)

현재 이 스위트는 ★`V202608201002` 를 통째로 비워도 green★ 이다 — 마이그레이션 하나가 어떤
테스트에도 안 걸려 있다. `convalidated` 단언은 이 레포의 다른 마이그레이션 테스트 5곳에 이미
있는 관행이다.

- [ ] **Step 1: 기존 테스트의 DELETE 정리 직전에 단언을 추가**

```java
      // 제약이 "존재" 를 넘어 "검증까지 끝난 정확한 어휘" 인지 단언한다. 이것이 없으면
      // V202608201002(VALIDATE) 를 통째로 비워도 스위트가 green 이다 — NOT VALID 제약도
      // 새 행은 거부하므로 위의 assertThrows 만으로는 구분하지 못한다.
      try (var rs = st.executeQuery(
          "SELECT conname, convalidated, pg_get_constraintdef(oid) FROM pg_constraint "
              + "WHERE conname IN ('chk_community_answers_status',"
              + "'chk_community_comments_status')")) {
        int seen = 0;
        while (rs.next()) {
          seen++;
          assertTrue(rs.getBoolean(2), rs.getString(1) + " 는 기존 행 검증까지 끝나야 한다");
          String def = rs.getString(3);
          assertTrue(def.contains("PUBLISHED") && def.contains("HIDDEN")
                  && def.contains("DELETED") && !def.contains("DRAFT"),
              rs.getString(1) + " 어휘가 정확해야 한다: " + def);
        }
        assertEquals(2, seen, "답변·댓글 상태 제약이 모두 있어야 한다");
      }
```

- [ ] **Step 2: 빈 DB 로 실행해 green 확인** (Global Constraints 의 레시피, `--tests '*FlywayMigrationTest*'`)
- [ ] **Step 3: ★판별력 실증★** — `V202608201002` 를 백업 후 주석 한 줄만 남기고 비운 뒤 같은
  테스트 실행(새 빈 DB). 기대: **red**, 사유에 `검증까지 끝나야` 포함. 복구 후 green 재확인.
- [ ] **Step 4: 커밋** — `test(db): 상태 CHECK 의 검증 완료와 정확한 어휘를 단언한다` +
  Step 3 관측을 본문에.

### Task S2: 채워진 스키마 업그레이드를 검증한다 (신규 클래스)

**Files:**
- Create: `src/test/java/ai/devpath/shared/db/CommunityContentSoftDeleteMigrationTest.java`

`SandboxDurableTerminalStateMigrationTest` 의 확립된 패턴(임시 스키마 + baseline + 실데이터)을
따른다. ★마이그레이션이 스키마 명시 바인딩(`to_regclass` 가드)으로 고쳐졌기 때문에 이 테스트가
비로소 가능하다★ — 임시 스키마의 테이블만 건드린다.

- [ ] **Step 1: 테스트 작성**

```java
package ai.devpath.shared.db;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.sql.SQLException;
import java.util.Map;
import java.util.UUID;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.postgresql.ds.PGSimpleDataSource;

/** 커뮤니티 소프트 삭제 마이그레이션이 기존 행을 보존하고 PUBLISHED 로 백필하는지. */
class CommunityContentSoftDeleteMigrationTest {

  /** V202608201001 바로 앞 버전. 여기까지 적용된 상태를 baseline 으로 삼는다. */
  private static final String PRIOR_VERSION = "202608161011";

  @Test
  void upgradesPopulatedTablesPreservingRowsAndBackfillingPublished() throws Exception {
    String schema = "community_sd_" + UUID.randomUUID().toString().replace("-", "");
    try {
      try (var c = dataSource().getConnection(); var st = c.createStatement()) {
        st.execute("CREATE SCHEMA " + schema);
        // 마이그레이션 이전 형태의 최소 테이블 — 대상 마이그레이션은 status 만 더하므로
        // 다른 컬럼은 필요 없다.
        st.execute("CREATE TABLE " + schema + ".community_answers ("
            + "id BIGSERIAL PRIMARY KEY, body_md TEXT NOT NULL)");
        st.execute("CREATE TABLE " + schema + ".community_comments ("
            + "id BIGSERIAL PRIMARY KEY, body_md TEXT NOT NULL)");
        st.execute("INSERT INTO " + schema + ".community_answers(body_md) "
            + "VALUES ('legacy-a1'),('legacy-a2')");
        st.execute("INSERT INTO " + schema + ".community_comments(body_md) VALUES ('legacy-c1')");
      }

      Flyway.configure()
          .configuration(Map.of("flyway.postgresql.transactional.lock", "false"))
          .dataSource(dataSource())
          .locations("classpath:db/migration")
          .schemas(schema)
          .defaultSchema(schema)
          .baselineOnMigrate(true)
          .baselineVersion(PRIOR_VERSION)
          .placeholderReplacement(false)
          .load()
          .migrate();

      try (var c = dataSource().getConnection(); var st = c.createStatement()) {
        try (var rs = st.executeQuery("SELECT count(*), "
            + "count(*) FILTER (WHERE status = 'PUBLISHED') FROM "
            + schema + ".community_answers")) {
          assertTrue(rs.next());
          assertEquals(2, rs.getInt(1), "기존 답변 행이 보존돼야 한다");
          assertEquals(2, rs.getInt(2), "기존 행은 PUBLISHED 로 백필돼야 한다");
        }
        try (var rs = st.executeQuery("SELECT count(*), "
            + "count(*) FILTER (WHERE status = 'PUBLISHED') FROM "
            + schema + ".community_comments")) {
          assertTrue(rs.next());
          assertEquals(1, rs.getInt(1));
          assertEquals(1, rs.getInt(2));
        }
        try (var ps = c.prepareStatement("SELECT convalidated FROM pg_constraint "
            + "WHERE conrelid = (? || '.community_answers')::regclass "
            + "AND conname = 'chk_community_answers_status'")) {
          ps.setString(1, schema);
          try (var rs = ps.executeQuery()) {
            assertTrue(rs.next(), "업그레이드 뒤 상태 제약이 있어야 한다");
            assertTrue(rs.getBoolean(1), "기존 행 검증까지 끝나야 한다");
          }
        }
        SQLException bad = assertThrows(SQLException.class, () -> st.execute(
            "INSERT INTO " + schema + ".community_answers(body_md,status) "
                + "VALUES ('x','DRAFT')"));
        assertEquals("23514", bad.getSQLState(), "어휘 밖 값은 CHECK 로 거부돼야 한다");
      }
    } finally {
      dropTemporarySchema(schema);
    }
  }

  private static void dropTemporarySchema(String schema) throws Exception {
    if (!schema.matches("community_sd_[a-f0-9]{32}")) {
      throw new IllegalArgumentException("refusing to drop unexpected schema: " + schema);
    }
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      st.execute("DROP SCHEMA IF EXISTS " + schema + " CASCADE");
    }
  }

  private static DataSource dataSource() {
    PGSimpleDataSource ds = new PGSimpleDataSource();
    ds.setUrl(System.getenv().getOrDefault("DB_URL",
        "jdbc:postgresql://localhost:5432/devpath"));
    ds.setUser(System.getenv().getOrDefault("DB_USER", "devpath"));
    ds.setPassword(System.getenv().getOrDefault("DB_PASSWORD", "localdev"));
    return ds;
  }
}
```

- [ ] **Step 2: 실행해 green 확인** (`--tests '*CommunityContentSoftDelete*'`)
- [ ] **Step 3: ★판별력 실증(사보타주)★** — `V202608201001` 끝에 임시로
  `UPDATE community_answers SET status = 'DELETED';` 한 줄을 붙이고 이 테스트만 실행.
  기대: **red**(`PUBLISHED 로 백필` 단언). 복구 후 green 재확인.
  (임시 스키마에 baseline 부터 새로 적용하므로 체크섬 충돌은 없다.)
- [ ] **Step 4: 커밋** — `test(db): 채워진 스키마 업그레이드의 행 보존·백필을 단언한다`

### Task S3: 리비전 테이블 테스트에 대조군과 컬럼 정체성을 세운다

**Files:**
- Modify: `src/test/java/ai/devpath/shared/db/FlywayMigrationTest.java`
  (`communityContentRevisionsTableExistsWithTargetCheck` 전체 교체)

현재는 `count(*)=8` + 대조군 없는 `assertThrows` 라, `body_md` 를 다른 이름으로 바꿔도
undefined-column 예외가 통과한다.

- [ ] **Step 1: 테스트 본문 교체**

```java
  /** 리비전 테이블 — 대조군(유효 삽입)을 먼저 세워야 "거부" 가 CHECK 때문이라 말할 수 있다. */
  @Test
  void communityContentRevisionsTableExistsWithTargetCheck() throws Exception {
    migrate();
    try (var c = dataSource().getConnection(); var st = c.createStatement()) {
      // 대조군: 세 대상 유형이 실제 컬럼 이름으로 들어간다 — 컬럼 정체성 검증을 겸한다.
      st.execute("INSERT INTO community_content_revisions"
          + "(target_type,target_id,title,body_md,body_html,edited_by) "
          + "VALUES ('POST',910001,'옛제목','옛본문','<p>옛본문</p>',7)");
      st.execute("INSERT INTO community_content_revisions"
          + "(target_type,target_id,body_md,edited_by) VALUES ('ANSWER',910001,'옛답변',7)");
      st.execute("INSERT INTO community_content_revisions"
          + "(target_type,target_id,body_md,edited_by) VALUES ('COMMENT',910001,'옛댓글',7)");

      SQLException bad = assertThrows(SQLException.class, () -> st.execute(
          "INSERT INTO community_content_revisions(target_type,target_id,body_md,edited_by) "
              + "VALUES ('QUESTION',910001,'본문',7)"));
      assertEquals("23514", bad.getSQLState(),
          "거부는 CHECK 위반이어야 한다(undefined column 이면 여기서 갈린다)");
      assertTrue(bad.getMessage().contains("chk_community_revisions_target"),
          "우리가 세운 그 제약이어야 한다: " + bad.getMessage());

      try (var rs = st.executeQuery(
          "SELECT indexdef FROM pg_indexes WHERE indexname='idx_community_revisions_target'")) {
        assertTrue(rs.next(), "대상별 조회 인덱스가 있어야 한다");
        String def = rs.getString(1);
        assertTrue(def.contains("target_type") && def.contains("target_id")
                && def.contains("created_at DESC"), def);
      }

      st.execute("DELETE FROM community_content_revisions WHERE target_id = 910001");
    }
  }
```

- [ ] **Step 2: green 확인** — 대조군 삽입 3건이 곧 판별력이다(컬럼 이름이 다르면 여기서
  즉시 깨진다). 별도 되돌림은 두지 않는다 — SQLSTATE 고정 + 제약명 단언이 "아무 예외" 구멍을
  이미 닫는다.
- [ ] **Step 3: 전체 스위트 green** (빈 DB, 99 + 신규) → **커밋** —
  `test(db): 리비전 테이블 테스트에 대조군·제약명·인덱스 단언을 세운다`
- [ ] **Step 4: push** — PR #70 갱신. ★CI 는 불변 계약으로 red 가 유지된다 — PR 본문에 이미
  설명돼 있으므로 추가 조치 없음★

---

## Part F — devpath-frontend (PR #136 브랜치)

### Task F1: 인라인 에디터가 열릴 때 본문을 동기화한다 (3곳)

**Files:**
- Modify: `apps/web/lib/src/features/community/presentation/qna_detail_page.dart` (답변 카드 onEdit)
- Modify: `apps/web/lib/src/features/community/presentation/post_detail_page.dart` (댓글 카드 onEdit)
- Modify: `apps/mobile/lib/src/features/community/presentation/qna_detail_page.dart` (답변 카드 편집 진입)
- Test: `apps/web/test/features/community/inline_edit_stale_body_test.dart` (신규)

세 곳 모두 `late final TextEditingController _ctrl = TextEditingController(text: widget.….bodyMd)`
라, 재조회로 본문이 바뀐 뒤 에디터를 열면 **옛 본문**이 뜨고 저장하면 최신을 덮는다.
백엔드 정렬 고정 + 비석 유지로 reorder 는 성립하지 않으므로 `ValueKey` 는 더하지 않는다 —
편집 진입 시 동기화가 최소·충분 수정이다. 대표 위젯 테스트는 web 답변 1곳에 세우고(계약 고정),
같은 수정을 3곳에 적용한 뒤 전체 회귀로 나머지를 덮는다.

- [ ] **Step 1: 실패하는 테스트** — 컨트롤러 계층이 아니라 **위젯**이 결함 자리이므로 위젯
  테스트다. `qna_detail_page_test.dart` 의 기존 pump 셋업(auth·lcs·detail 오버라이드)을 먼저
  읽어 아래 골격의 셋업부를 그 관례로 맞춘다:

```dart
    testWidgets('재조회로 본문이 바뀐 뒤 편집을 열면 새 본문이 보인다', (tester) async {
      var body = '원답변';
      // qnaDetailFetchProvider 가 body 변수를 읽게 오버라이드 (셋업은 기존 테스트 관례)
      // 1) load(3) 후 pump — 카드에 '원답변'
      // 2) body = '고친답변'; notifier.load(3); pump — 카드 갱신
      // 3) content-menu 탭 → '수정하기' 탭 → pump
      final field = tester.widget<TextField>(
          find.byKey(const ValueKey('answer-edit-field')));
      expect(field.controller!.text, '고친답변',
          reason: 'late final 컨트롤러가 옛 본문을 쥐고 있으면 여기가 원답변이다');
    });
```

- [ ] **Step 2: red 확인** — 기대 사유: `원답변 != 고친답변`. (다른 사유면 셋업을 먼저 고친다.)
- [ ] **Step 3: 수정 — 편집 진입 시 동기화 (3곳 동일 패턴)**

web 답변(`onEdit: () => setState(() => _editing = true)`):

```dart
                  onEdit: () => setState(() {
                    // 재조회로 본문이 바뀌어도 late final 컨트롤러는 처음 본문을 쥔다 —
                    // 여는 순간 동기화해 옛 본문으로 최신을 덮는 사고를 막는다.
                    _ctrl.text = widget.answer.bodyMd;
                    _editing = true;
                  }),
```

web 댓글은 `widget.comment.bodyMd`, mobile 답변은 해당 카드의 편집 진입 `setState` 에 같은 줄.

- [ ] **Step 4: green + `flutter test` (web·mobile 해당 파일)** → **커밋**

### Task F2: 관리자 내리기 성공 후 목록을 재조회한다

**Files:**
- Modify: `apps/admin/lib/src/features/reports/presentation/reports_page.dart` (`_confirmTakedown`)
- Test: `apps/admin/test/features/reports/reports_page_test.dart` (테스트 추가)

- [ ] **Step 1: 실패하는 테스트** — `reports_page_test.dart` 의 기존 fetch 오버라이드 관례를
  따라, 내리기 확정(타이핑 확인 포함) 후 **fetch 가 한 번 더 불리는지** 센다:

```dart
    // fetches 카운터 오버라이드 → 카드의 takedown-<id> 탭 → 다이얼로그에 확인값 입력 →
    // '내리기 확정' 탭 → pumpAndSettle → expect(fetches, 2)
```

- [ ] **Step 2: red 확인** (기대: `1 != 2`)
- [ ] **Step 3: 수정** — `_confirmTakedown` 의 스낵바 직전에:

```dart
    if (ok != true || !context.mounted) return;
    // 내린 카드가 계속 '내리기' 를 내밀면 같은 대상에 재요청 → 404. 목록을 새로 읽어
    // isTargetGone 이 버튼을 감추게 한다. 필터는 지금 보던 것을 유지한다.
    await ref.read(reportsProvider.notifier)
        .load(status: ref.read(reportsProvider).status);
    if (!context.mounted) return;
```

  (`ReportsState` 의 `status` 접근자가 base 에 없으면 variant 별 switch 로 — 구현 시 실물 확인.)

- [ ] **Step 4: green + admin 전체 테스트** → **커밋**

### Task F3: 빈 본문 인라인 저장이 조용히 닫히지 않는다 (3곳)

**Files:**
- Modify: web 답변·web 댓글·mobile 답변의 저장 버튼 핸들러
- Test: `inline_edit_stale_body_test.dart` 에 추가 (F1 과 같은 하네스 재사용)

- [ ] **Step 1: 실패하는 테스트** — 편집 열고 필드를 비운 뒤 저장 탭:

```dart
      expect(find.text('내용을 입력해 주세요'), findsOneWidget,
          reason: '컨트롤러가 조용히 삼키면 아무 안내도 없다');
      expect(find.byKey(const ValueKey('answer-edit-field')), findsOneWidget,
          reason: '실패했는데 에디터가 닫히면 입력이 사라진다');
```

- [ ] **Step 2: red 확인**
- [ ] **Step 3: 수정 — 저장 핸들러 (3곳 동일 패턴, 400 문구는 기존 계약 문자열 그대로)**

```dart
                        onPressed: () {
                          final body = _ctrl.text.trim();
                          if (body.isEmpty) {
                            // 컨트롤러는 빈 본문을 서버에 안 보낸다(왕복 낭비). 그 침묵을
                            // 사용자에게는 스펙의 400 문구로 표면화하고 에디터를 유지한다.
                            ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('내용을 입력해 주세요')));
                            return;
                          }
                          widget.onSave(body);
                          setState(() => _editing = false);
                        },
```

- [ ] **Step 4: green** → **커밋**

### Task F4: 데이터 계층 테스트가 요청 본문을 단언한다

**Files:**
- Modify: `apps/web/test/features/community/community_source_edit_delete_test.dart`

- [ ] **Step 1: 캡처 어댑터를 테스트 파일에 추가**

```dart
/// 픽스처 키만 맞으면 통과하던 구멍을 닫는다 — 실제로 나간 본문을 기록한다.
class _CapturingAdapter extends MockHttpAdapter {
  _CapturingAdapter(super.fixtures);
  final Map<String, Object?> bodies = {};
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    bodies['${options.method} ${options.path}'] = options.data;
    return super.fetch(options, requestStream, cancelFuture);
  }
}
```

  (시그니처는 `MockHttpAdapter.fetch` 실물에 맞춘다 — `cancelFuture` 의 타입이 raw `Future?`
  면 그대로 따른다. `dio`·`dart:typed_data` import 필요.)

- [ ] **Step 2: 세 update 테스트에 본문 단언 추가**

```dart
    expect(adapter.bodies['PUT /community/posts/9'],
        {'title': '새제목', 'bodyMd': '새본문'});
```

  ★첫 실행에서 `options.data` 의 실제 타입을 확인한다 — dio 가 이 시점에 이미 JSON 문자열로
  직렬화해 두는 구현이면 `jsonDecode` 를 끼운다. "Map 이겠지" 로 넘어가지 말 것.★

- [ ] **Step 3: ★판별력 실증★** — `community_source.dart` 의 postUpdate 본문을 임시로
  `{'body': bodyMd, ...}` 로 바꿔 red 관측(기대: 본문 단언 실패) 후 복구.
- [ ] **Step 4: green** → **커밋**

### Task F5: 골든패스를 실제 위젯으로 세운다

**Files:**
- Rewrite: `apps/web/test/features/community/edit_delete_golden_path_test.dart`

현재 이 파일은 ★`pumpWidget` 이 0건★ — CRUD 프로바이더를 페이크로 갈아끼운 채 페이크의
상태기계만 검증한다. `post_edit_test.dart` 의 `_host`(GoRouter + Quill 로캘) 패턴으로
**실제 화면·메뉴·확인 다이얼로그·라우팅**을 구동한다.

범위(스펙 §3): 상세→메뉴→수정 진입(라우팅)→저장(PUT 본문 단언)→상세 복귀 / 상세→메뉴→삭제
확인 다이얼로그→DELETE 호출 단언→목록(`/community`) 이동. 생성 화면은 기존
`post_create_page_test` 가 이미 덮으므로 중복하지 않는다.

- [ ] **Step 1: 파일 전체 교체** — 핵심 골격(셋업은 `post_edit_test.dart` 의 `_host` 관례):

```dart
    // 라우트: '/community'(Text 스텁) · '/community/post/:id' → PostDetailPage ·
    //         '/community/post/:id/edit' → PostEditPage
    // 어댑터: F4 의 _CapturingAdapter 재사용 + MockSequence 로
    //         'GET /community/posts/9' 를 [수정 전 상세, 수정 후 상세] 순서 응답으로.
    // 흐름 1(수정): 상세 pump → content-menu 탭 → '수정하기' 탭 → pumpAndSettle
    //   → post-submit 탭 → PUT 본문 단언 + 현재 경로가 '/community/post/9' 인지
    // 흐름 2(삭제): content-menu 탭 → '삭제하기' → content-delete-confirm 탭
    //   → DELETE 키가 bodies 에 기록됐는지 + find.text 로 '/community' 스텁 도착 확인
```

- [ ] **Step 2: red 를 거쳐 green** — 처음 작성 시 라우팅·키에서 실패하는 지점이 실제 계약과
  다른 곳이다. **실패 사유를 읽고 테스트가 아니라 이해를 고친다**(화면 쪽 결함이 나오면 멈추고
  보고 — 이 태스크의 목적은 검증이지 화면 수정이 아니다).
- [ ] **Step 3: 커밋** — `test(web): 골든패스를 실제 화면·라우팅으로 구동한다`

### Task F6: mobile 삭제-후-재조회를 이름값대로 단언한다

**Files:**
- Modify: `apps/mobile/test/features/community/answer_edit_delete_test.dart`

- [ ] **Step 1: 기존 `deleteAnswer` 테스트 강화**

```dart
    var fetches = 0;
    // qnaDetailFetchProvider 오버라이드에 fetches++ 를 넣고, 삭제 후:
    expect(deletedId, 11);
    expect(fetches, 2, reason: 'load 1회 + 삭제 후 재조회 1회 — 이름이 주장하는 그것');
```

- [ ] **Step 2: ★판별력 실증★** — mobile `qna_detail_controller` 의 삭제 후 재조회 호출을
  임시 주석 처리해 red(`1 != 2`) 관측 후 복구.
- [ ] **Step 3: green** → **커밋**

### Task F-R: frontend 전체 회귀 + push

- [ ] `dart pub global run melos analyze` → 0
- [ ] `dart pub global run melos test` → 전 패키지 통과(1717 + 신규분; 숫자 증가가 실행 증거)
- [ ] push → PR #136 갱신, CI green 확인

---

## Part R — Codex 재리뷰

### Task R1: 최종 diff 재리뷰 (4 레포 직렬, 작은 것부터)

- [ ] gitops #66(작음) → shared #70 → community-svc #36 → frontend #136 순으로, 각 PR 의
  **머지 기준 대비 최종 diff** 를 프롬프트에 인라인해 실행(Global Constraints 레시피).
  community-svc 는 1차 리뷰 이후 diff 가 크게 자랐다(동시성 + Stage 0) — 전체 diff 로 다시.
- [ ] 지적은 전부 **파일·줄 대조로 확정 후** 수용/기각. critical/major 만 이 캠페인에서 수정
  (수정 시 해당 Part 의 TDD 규율 그대로), minor 는 기각 사유 또는 백로그 메모로 기록.
- [ ] 결과 보고: 레포별 지적 수 / 확정 / 기각(근거) / 수정 커밋. **이것이 Stage B(머지) 입장권.**
