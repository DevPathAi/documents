# SDD ledger — plan: docs/superpowers/plans/2026-09-27-s3-p4-screen-groups.md

Plan source (documents 레포, develop `2d8ed3c` 로 머지됨): `/d/workspace/dpa/.worktrees/documents-s3p4-plan/docs/superpowers/plans/2026-09-27-s3-p4-screen-groups.md`
Spec: `documents/docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§7 P4·§8·§10 (읽음)
실행 방식: Native (사용자 결정 2026-09-27) — 이 세션이 18 Task 를 직접 구현하고 마지막에 독립 리뷰 한 번.
Worktree: `/d/workspace/dpa/.worktrees/frontend-s3p4a-20260927` · branch `feat/s3-p4-learning-screens` · base `92f8284`(develop)

## 환경 실측 (Task 1 전)

- 로컬 Flutter **3.47.2** (CI 핀은 3.44.1). `flutter pub get` 한 번에 `apps/admin/analysis_options.yaml`·`apps/web/analysis_options.yaml`·`packages/dp_design/analysis_options.yaml`·`pubspec.lock` **4파일을 다시 썼다** — 계획 Global Constraints 가 예고한 그대로다. `git checkout -- .` 로 되돌렸다.
- **이 4파일은 절대 `git add` 하지 않는다.** 명시 경로만 add 하고, 커밋 전 `git diff origin/develop HEAD --name-only` 목록으로 확인한다.

## Pre-flight: 공유 인터페이스 대조

| 생산 Task | 소비 Task | 생산물 ↔ 소비 | 결과 |
|---|---|---|---|
| 1 | 2·3·4·10·17 | `DpCols({main, side})` ↔ `DpCols(main:, side:)` | 일치. Task 6 이 `stretch` 를 더하지만 기본값 false 라 앞 소비처와 호환된다 |
| 1 | 2·3·4·8·10·15·16·17 | `DpPanelTitle(String)` ↔ `DpPanel(title: const DpPanelTitle('…'))` | 일치. `DpPanel.title` 은 `Widget?` 이라 그대로 받는다 |
| 1 | 2·3·8·17 | `DpWebTable({columns, rows, required empty, minWidth})` + `assert(cells.length == columns.length)` + **const 아님** ↔ 네 Task 의 표 호출 | 일치. **단 조건부 칼럼(`if (!compact)`)마다 같은 조건의 셀이 있어야 한다** — Task 2(유형)·3(목표)·8(답변/댓글)·17(게시판) 모두 같은 `compact` 판정을 양쪽에 쓴다. 확인함 |
| 1 | 전 화면 + `apps/admin` | `DpPageHeader` 좌우 패딩 0 ↔ 셸이 좌우 패딩을 준다 | **admin 은 셸이 패딩을 주는지 미확인** — Task 1 Step 25 가 실측해 결정한다(admin 화면이 왼쪽에 붙으면 `DpAppShell` 에 패딩을 넣는다) |
| 6 | 6 | `DpCols.stretch` ↔ 멘토 두 분기 | 자기 Task 안에서만 쓴다 |
| 8 | 8 | `communityBoardColumns`/`communityPostRow`/`communitySearchRow` ↔ 목록·검색 두 분기 + ET13 투영 | 세 함수 모두 `board` 로 상태 칼럼 유무를 정한다(검색 행의 `item.boardType` 은 **내용** 판정에만 쓴다) — 칼럼/셀 개수가 어긋나지 않는다 |
| 9 | 9 | `carryCommunityQuery({location, targetId})` ↔ `AppShellView.onSelect` + `DpCommandPalette.onInvoke` | 두 곳이 같은 시그니처로 부른다 |
| 13 | 15·16 | `DpSteps`·`DpOptionRow`·`DpCheckRow` ↔ 진단 3화면·동의 | 일치. `DpCheckRow.last` 는 Task 15 가 마지막 항목 판정에 쓴다 |
| 10 | 10 | `QnaRelatedPanel({questionId, title})` ↔ 질문 상세 사이드 | 자기 Task 안에서만 쓴다 |

Pre-flight 결과: **미확인 1건**(admin 본문 패딩) — Task 1 Step 25 가 실측으로 닫는다. 그 밖의 충돌 없음.

## 진행

### 기준선 (Task 1 전)

- `dp_design`: **346 pass · 2 fail** — `test/golden/state_golden_test.dart` 의 `DpKillSwitch 라이트 골든`·`다크 골든` 이 **100.00% 픽셀 불일치(1,474,200px)**. 워크트리는 손대지 않은 develop(`92f8284`)이므로 **기존 환경 실패**다: 로컬 Flutter 3.47.2 의 렌더러가 CI 3.44.1 이 만든 골든과 다르다. 로컬에서 골든을 재생성하면 CI 가 깨지므로 **손대지 않는다.** 판정은 CI(`analyze-test`)가 한다.
- Ruling: 기준선 2건 실패를 안고 Task 1 을 시작한다 — 골든은 이 PC 에서 잴 수 없고 계획 Global Constraints 가 「무거운 검증은 CI 에 맡긴다」로 이미 그 경계를 그었다. 비용: 골든이 실제로 깨져도 로컬에서 못 본다 → CI `analyze-test` 가 유일한 그물이다.

**정정 (같은 세션 안에서):** 위 「기존 환경 실패 2건」은 **내 오진이었다.** 이 레포의 테스트 명령은 `flutter test`가 아니라 **`flutter test --exclude-tags golden`**(레포 CLAUDE.md 「빌드·테스트」 · `dart run melos run test` 가 그렇게 실행한다)이다. 골든을 제외하고 다시 돌리니 **346/346 전부 통과**다(`baseline-dp_design-2.log`).

- 취소: 앞 Ruling(「기준선 2건 실패를 안고 시작한다」)은 근거가 사라졌으므로 무효다.
- 교훈: **레포의 테스트 명령을 먼저 읽는다.** 골든은 태그로 제외되어 있고, 로컬에서 골든을 재는 것 자체가 이 레포의 계약이 아니다.
- 이후 이 Task 들에서 쓰는 테스트 명령은 항상 `flutter test --exclude-tags golden` 이다(단일 파일 지정 시에도 붙인다 — 그 파일에 골든이 있으면 같은 함정에 빠진다).

## Task 1: dp_design 준비

기준선: dp_design 346/346 pass (`--exclude-tags golden`) · BASE `92f8284`

Task 1: Ruling: 계획 Step 5~6 은 「빈 표 테스트를 새로 쓴다」였으나 기존 테스트
`'행이 없고 empty 가 있으면 표 대신 empty 를 그린다'` 가 이미 같은 계약(헤더 감춤 포함)을
갖고 있었다 — 폐기 대상 `'행이 없고 empty 가 없으면 헤더만 남는다'` 만 지웠다. 비용: 없음(계약은 보존됨).

Task 1: Ruling: 계획 Step 24~25 는 「`DpPageHeader` 좌우 패딩을 0 으로 내리고, admin 이
깨지면 `DpAppShell` 에 패딩을 넣는다」였다. 실측하니 `DpAppShell` 은 본문에 좌우 패딩을
주지 않고(`Semantics` + `DpMaxWidth` 만), admin 화면은 `Scaffold > Column > [DpPageHeader,
형제들…]` 구조에서 **형제들이 각자 패딩을 갖는다**. 셸에 패딩을 넣으면 그 형제들이 이중이 된다
→ `DpPageHeader({bool gutter = false})` 파라미터로 가고 admin 6곳만 `gutter: true` 로
옛 거동을 유지했다(기본값을 false 로 둔 이유: 웹이 스펙의 타깃이고 호출부가 19곳 vs 6곳이다).
비용: 새 웹 화면이 셸 밖에 놓이면 `gutter: true` 를 잊어 거터가 사라질 수 있다 — 셸 밖 화면은
로그인·콜백·동의·베타·진단뿐이고 Task 14~16 이 각각 다룬다.

Task 1: Ruling: 리뷰 Minor 7(`DpRowLine` Wrap 좌측 낙하)·8(hover 대비 1.046:1)을 **기각**했다 —
둘 다 시안 CSS 와 같은 거동이다(`.rowline{justify-content:space-between;flex-wrap:wrap}` 는
한 run 에 항목이 하나면 브라우저도 좌측 정렬하고, `tbody tr:hover{background:var(--muted)}` 는
`surfaceMuted` 그 값이다). hover 는 대신 「`DpPanel` 안에서만 쓴다」는 계약을 위젯 doc 에 적었다.
비용: 사용자가 좁은 폭에서 컨트롤 위치를 어색하게 느낄 수 있다 — 시안을 벗어나는 교정은
시안 개정으로 다뤄야 한다.

Task 1: Ruling: 계획 Step 30 은 dp_design·admin 만 돌리게 했지만 `DpPageHeader` 는 web 도
19곳에서 쓴다. web 을 돌려 2건 실패를 찾았다 — 로그인(`login_header_test`)과
샌드박스(`sandbox_layout_test`)가 옛 거터를 단언했다. 로그인은 셸 밖이라 `gutter: true` 로
현 렌더를 보존했고(Task 14 가 걷어낸다), 샌드박스는 세그먼트의 자체 좌우 패딩을 제거해
테스트가 적어 둔 의도(「헤더와 같은 좌측선」)를 지켰다 — 하드코딩된 `24` 단언은 지우고
헤더와의 비교만 남겼다(Task 5 의 변경을 앞당김). 비용: Task 5 가 그만큼 줄어든다.

Task 1: Ruling: 새 시맨틱스 단언에서 `hasFlag`→`containsSemantics`→`flagsCollection` 이
모두 로컬 3.47 에서 deprecated 이거나 `Tristate` 라는 버전 의존 타입을 요구했다.
`DpLink` 포커스 단언은 **포커스 링(`dp-link-focus-ring`)** 을 보는 쪽으로 바꿨다 — 링과
`Semantics.focused` 가 같은 `_focused` 를 공유하므로 같은 것을 재고, 버전 의존이 없다.
그 단언이 실제로 red 인 것을 위젯을 되돌려 재확인했다. 비용: 시맨틱스 플래그 자체를
직접 재지는 않는다 — 링과 플래그가 갈라지면 놓친다(같은 한 필드라 갈라질 수 없다).

Task 1: 기록: `apps/web` analyze 경고 1건(`current_mission_controller.dart:273`
`unawaited_return_in_try_block`)은 **내가 손대지 않은 파일의 기존 것**이다. develop 의 CI
(`analyze-test`, Flutter 3.44.1)는 녹색이므로 로컬 3.47 전용 린트다. 손대지 않는다.

Task 1: complete (commits 92f8284..dd7e0b5, tests: flutter test --exclude-tags golden →
dp_design 356/356 · admin 156/156 · web 1011/1011+1skip 전부 pass, analyze dp_design 0 · admin 0)

## Task 2: 오늘 화면

Task 2: Ruling: 계획이 테스트 import 를 `package:web/src/...` 로 적었으나 앱의 패키지명은
**`devpath_web`** 이다(`package:web` 은 pub.dev 의 다른 패키지로 해석된다). 뒤 Task 들의
테스트 import 에도 같이 적용한다. 비용: 없음.

Task 2: Ruling: 계획 Step 13 은 `supportingContent` 를 차트 둘만 남기게 했다. 옛 코드에는
가용 폭 440 미만에서 추세를 숨기는 게이트가 있었는데, 새 사이드 칼럼은 본문 1120 의 1/3
(≈373px)이라 **그 게이트를 남기면 데스크톱에서도 추세가 사라진다**. 게이트를 걷어내고 좁은
폭에서도 두 차트를 남겼다. 비용: 390px 에서 차트가 작아 읽기 어려울 수 있다 — 숨기는 것보다
낫다고 판단했다(기능 보존 규칙).

Task 2: Ruling: 과제 제목이 `.next` 밴드와 「이번 주 과제」 표에 **함께** 나온다. 시안도 같은
제목을 두 곳에 두므로 의도된 반복이다 — `findsOneWidget` 단언 8곳을
`dp-mission-header-title` 키로 좁히거나 `findsWidgets` 로 바꿨다. 비용: 표의 제목이 사라져도
밴드 단언은 통과한다 — 표 자체는 `today_panels_test` 가 따로 잰다.

Task 2: Ruling: 지표 섹션이 최상위 sliver 에서 `.cols` 사이드 칼럼 안으로 들어가면서 두 가지가
깨졌다 — ① sliver 순서 단언(키가 최상위에 없다) → 「미션 밴드 → `.cols` → 광고」로 고쳤다
② 지표 실패 알림의 재시도 **탭이 빗나갔다**(기본 뷰포트 아래로 내려갔다) → `ensureVisible` 을
넣었다. ②는 테스트만의 문제가 아니라 **실제 사용자도 스크롤해야 닿는다**는 사실이다.
비용: 지표 실패가 접힌 아래에 있어 눈에 덜 띈다 — 시안이 사이드에 두라고 한 결과다.

Task 2: Ruling: 계획 Step 21 은 화면마다 documents 의 `baseline-impact.md` 에 한 줄씩
커밋하게 했다. 교차 레포 커밋을 20번 만드는 대신 **원장에 모아 PR 단위(Task 7·12·18)로
옮긴다**. 비용: documents 가 P4 진행 중에는 비어 있다 — 원장이 살아 있는 기록이다.

Task 2: baseline-impact: `/dashboard` 오늘 — Bento 4열 그리드 → `.cols` 2열. KPI 카드 2장·
진행 도넛·배지 스트립 위젯이 사라지고 그 숫자는 「진행」 키-값으로. 차트 패널의 그림자 제거.
추세 차트가 이제 좁은 폭에서도 보인다. 「이번 주 과제」 표·「왜 이 순서인가요」·「막히면」 신설.
ET13 visual baseline 재기록 대상.

Task 2: complete (commits dd7e0b5..f9d267a, tests: flutter test --exclude-tags golden →
web 1020 pass + 1 skip, dashboard 61/61, analyze 기존 경고 1건 외 0)

## Task 3: 학습 경로

Task 3: Ruling: `MilestoneProgressCard` 는 **소비처가 있다**(`path_plan_view.dart:94`, legacy
경로) — 계획이 열어 둔 「소비처 0이면 손대지 않는다」 분기는 해당 없다. 그대로 둔다.

Task 3: Ruling: 실측으로 계획보다 충실하게 만들 수 있음을 확인했다 — `LearningPath` 에
**`totalWeeks`·`track`** 이 있고 `PathDiagnosis` 에 **`strengthConcepts`·`weaknessConcepts`**
가 있다. 계획의 `PathDiagnosisPanel`(현재 수준·주차 수만)을 시안 `.side` 「진단 요약」
(강점·보강·트랙)에 맞춰 확장했다. 새 API 호출 없음. 비용: 없음.

Task 3: Ruling: 옛 `ExpansionTile` 목록을 표로 바꾸면 **비현재 주차의 `expectedOutcome` 이
사라진다**(접힘 안에만 있었다). 「목표」 칼럼을 두 줄로 만들어(시안 `.ex` 문법) 둘 다 올렸다.
비용: 목표 칼럼이 두 줄이라 표가 시안보다 세로로 길다.

Task 3: Ruling: 계획 Step 8 은 사이드의 완료 근거 패널을 `currentMilestone != null`
조건부로 두게 했다. 그러면 `plan` 이 없거나 현재 미션과 맞지 않을 때 **「다음 잠금
해제」 한 줄이 통째로 사라진다** — 기존 테스트 `'다음 unlock은 현재 뒤의 이미 완료된
task를 건너뛴다'`(plan 을 넘기지 않는다)가 red 로 드러냈다. `PathWeekOutcomePanel.
milestone` 을 nullable 로 만들고, 상세가 없으면 제목 「다음에 열리는 것」 + 잠금 해제
한 줄만 그린다. 「다음에 무엇이 열리는가」는 서버 미션만으로 계산되므로 상세가 없다는
이유로 지울 근거가 없다. 비용: 사이드에 패널이 항상 하나는 있다 — 상세가 없을 때는
한 줄짜리 패널이라 빈 카드처럼 보일 수 있다.

Task 3: Ruling: 계획 Step 11 의 「`BoxDecoration` 3곳」은 실측 **2곳**이었다(근거
`Container` + `_Tag` 의 `DecoratedBox`). 계획의 의도(「제목 문구를 패널 제목으로
올린다」)를 따라 블록 4개를 패널로 만들었다 — 근거·진단 요약·이번 주 과제·12주
타임라인. `_Tag` 는 `DpTag` 로 바꿔 지웠다. 비용: 강점(success)·약점(textSecondary)의
**테두리 색 구분을 잃었다** — 이 파일에는 이미 「색만으로 구분하지 않는다(DESIGN.md §1)」
주석과 「강점」·「보강할 점」 소제목이 있어 구분은 텍스트가 지고 있고, `DpTag` 가 tag*
토큰의 유일한 배선 지점이므로 tone 으로 색을 되살리면 Task 1 리뷰가 잡은 대비 문제를
다시 만든다.

Task 3: Ruling: **`DpPanel` 안의 Material `ListTile` 은 프레임워크 단언에 걸린다.**
패널은 색을 가진 `DecoratedBox` 이고 `ListTile` 은 **가장 가까운 Material**(여기서는
`Scaffold`)에 배경·잉크를 그리므로, 패널 표면이 그 잉크를 덮는다. Step 10·11 직후
실패 7건이 **전부 이 한 원인**이었다(좌측선·타임라인·라우트 이동 테스트까지). 패널
안쪽에 `Material(type: MaterialType.transparency)` 를 한 겹 뒀다. 근본 수정은
dp_design 의 `DpPanel` 이 스스로 잉크 표면을 갖는 것이지만, 356개 테스트를 가진 공용
위젯의 잉크 거동을 Task 3 범위에서 바꾸지 않았다. 비용: **뒤 Task 들이 legacy
`ListTile`·`Card` 를 `DpPanel` 로 감쌀 때 같은 함정을 다시 만난다** — 이 줄이 경고다.

Task 3: Ruling: 접힘 전제 테스트 2건을 표 기준으로 다시 썼다. ① `'미래 주차 상세는
기본 접힘이며 사용자가 열 때만 보인다'` → `'미래 주차의 목표와 기대 결과를 접지 않고
표에 함께 올린다'`(접는 것이 없으므로 「열 때만」이 성립하지 않는다 — 대신 접혀 있던
정보가 사라지지 않았음을 잰다) ② `'주차 목록 갱신 시 펼침 상태가 다른 weekNum으로
이동하지 않는다'` → `'주차 목록이 갱신되면 새 주차가 표에 바로 나타난다'`(막던 결함이
접힘 상태 누출이라 결함 자체가 성립하지 않는다). 비용: 둘 다 구현 뒤에 통과하는
특성화 테스트다 — 새 계약을 red→green 으로 얻은 것이 아니다.

Task 3: Ruling: `_AvailablePath`·`_CompletedPath` 의 `EdgeInsets.all(lg)` 를
`EdgeInsets.only(bottom: xl)` 로 바꿨다 — `DpWebShell` 이 본문에 좌우 패딩
(compact lg / 그 외 xl)을 주므로 화면이 또 주면 이중이 된다. 실측으로 확인했다
(`dp_web_shell.dart` `web-shell-main`). 빈 상태·오류 분기(`noActivePath`·
`malformedPath`·로딩·실패)의 `EdgeInsets.all` 은 P2 이전부터 같은 이중 상태였고
Task 3 의 대상이 아니라 그대로 뒀다. 비용: 같은 화면 안에서 상태에 따라 좌측선이
다르다 — 중앙 정렬 상태라 눈에 띄지 않는다.

Task 3: 기록: `PathPlanView.build` 의 `ListView(padding: all(lg))` 는 그대로 뒀다.
`/path` 운영 경로는 `PathPlanView.children` 만 쓰고(`path_page.dart`), 이 `build` 는
테스트와 `content_progress_smoke_test` 에서만 쓰인다.

Task 3: 기록: `ListView(children: …)` 는 뷰포트 밖 자식을 mount 하지 않는다 —
패널 4개를 한 번에 세는 테스트는 뷰포트를 1280×2400 으로 올려야 성립한다.

Task 3: baseline-impact: `/path` 학습 경로 — 접힘 목록(`ExpansionTile` 4종) → 「N주
계획」 표, 사이드 패널 3개(완료 근거·진단 요약·설계 근거) 신설, 2열 분기 기준이
수동 `wide`(840) 에서 `DpCols`(expanded 1240)로 바뀌어 **840~1239 구간이 1열이 된다**.
legacy 완료 화면(flag OFF)은 블록 4개가 패널 테두리를 갖고 태그 칩이 중립색이 된다.
좌우 패딩이 셸 것만 남아 본문 좌측선이 24px 왼쪽으로 옮겨진다. ET13 visual baseline
재기록 대상.
Task 3: complete (commits f9d267a..b9230f4, tests: bash -c 'cd apps/web && flutter test test/features/path --exclude-tags golden' → 00:02 +65: All tests passed!)

## Task 4: 콘텐츠 읽기 화면

기준선: content 46/46 pass · 안전망 = `content_page_test.dart` 의
`'스크롤 진행률(scrollPct)은 헤더 높이를 보정해 서버로 전송한다'` ·
`'헤더가 스크롤로 트리에서 걷어내진 뒤에도 scrollPct 보정이 유지된다'` ·
`content_progress_tracker_test.dart` · `mission_content_page_test.dart`

Task 4: Ruling: 브리프 Step 2 의 테스트 픽스처는 `LearningContent` 의 필수 필드
`track` 을 빠뜨렸다(`learning_content.dart` 실측). 넣어 맞췄다. 브리프가 적은
`package:web/...` import 도 Task 2 의 Ruling 대로 `package:devpath_web/...` 다.
비용: 없음.

Task 4: Ruling: 계획은 `ContentProgressPanel` 만 테스트하게 했지만 Produces 에는
`ContentMissionPanel` 도 있다. 완료·현재·다음 구분과 「현재 과제는 링크가 아니다」
계약, 미션이 없을 때 아무것도 그리지 않는 계약까지 5건으로 잰다. 비용: 없음.

Task 4: Ruling: `WebContentProjection` 은 전용 테스트가 없었다(ET13 증거 앱이
타입만 참조한다). `web_content_projection_test.dart` 를 새로 만들어 폭 760·
`DpTag`·「진행률 바가 본문에 없다」를 잰다. `adSlot` 은 provider 를 요구하므로
`SizedBox.shrink()` 를 넘긴다. 비용: 광고 슬롯이 본문에 있다는 사실은 이 파일이
재지 않는다 — `content_page_test` 가 화면 전체로 잰다.

Task 4: Ruling: **`mission_content_page_test` 의 `'진행 저장 중에도 최신 dwell을
보존해 후속 요청으로 합친다'` 는 「문서가 뷰포트에 다 들어가 스크롤이 불가능하다」에
의존하고 있었다.** `_scrollPct` 는 그때 `maxExtent <= 0` 분기로 **1** 을 돌려주고,
그 1 이 `tracker.record` 의 `advancedEnough`(0.1) 를 넘겨 첫 flush 를 띄운다
(dwell 만으로는 절대 flush 되지 않는다 — `ContentProgressTracker.record` 실측).
사이드 패널이 1열에서 본문 아래로 쌓이자 문서가 길어져 스크롤이 생기고, 최상단의
진행률은 정확히 0 이 되어 flush 가 사라졌다. 뷰포트를 1280×2000 으로 **명시**해
전제를 코드에 적었다(기본 800×600 에서 우연히 성립하던 것이다). 비용: 그 테스트는
이제 「스크롤 없는 짧은 문서」 시나리오만 잰다 — 스크롤이 있는 경우의 dwell 병합은
재지 않는다. 대신 아래 폭별 경계 테스트가 실제 스크롤 경로를 잰다.

Task 4: Ruling: 계획 Step 10 의 새 경계 테스트 문구(「1280 과 390 에서 같은 스크롤
위치가 같은 scrollPct 를 보낸다」)는 **성립하지 않는다** — 1열에서는 사이드가 본문
아래로 쌓여 문서 높이(분모)가 폭마다 다르다. 성립하는 계약으로 바꿔 적었다:
**각 폭에서 「그 폭의 본문 범위 50% 지점」이 0.5 로 전송된다**(헤더 높이만 빼고
나눈다는 계약). 390·1280 두 폭을 루프로 돈다. 비용: 없음 — 계획이 재려던 것
(사이드 패널이 진행률 보정을 깨지 않는다)을 더 정확히 잰다.

Task 4: Ruling: `'title, meta, progress, markdown, sandbox button을 렌더한다'` 의
`find.text('20% 진행')` 을 `find.textContaining('20%')` 로 바꿨다 — 그 문구는 이제
사이드 패널의 `'20% · 끝까지 읽으면 완료로 저장됩니다'` 다. 비용: 정확한 문구를
재지 않는다 — 문구 자체는 `content_panels_test` 가 잰다.

Task 4: baseline-impact: `/content` 콘텐츠 — 본문 폭 **840 → 760**, 진행률 바가
본문 위에서 사이드로, 개념 태그가 `Chip` → `DpTag`(글꼴이 번들 폰트로 바뀌고 배경이
tagBg 가 된다), 「현재 학습 미션」 패널 신설, 좌우 패딩이 셸 것만 남는다.
**`WebContentProjection` 은 ET13 결정적 투영(`web-content-reading`)이라 그 증거
기준선도 함께 바뀐다.** ET13 visual baseline 재기록 대상.
Task 4: complete (commits b9230f4..e63b43a, tests: bash -c 'cd apps/web && flutter test test/features/content test/content_progress_smoke_test.dart test/content_sandbox_smoke_test.dart --exclude-tags golden' → 00:02 +58: All tests passed!)

## Task 5: 실습 화면

기준선: sandbox 71/71 pass

Task 5: 기록: 계획 Step 4 의 「세그먼트의 좌우 패딩 제거」는 **Task 1 이 이미 했다**
(`sandbox_layout.dart` 의 주석이 그렇게 적혀 있고 패딩은 이미 세로만이다). 남은 것은
페인 테두리 문법뿐이었다.

Task 5: Ruling: 계획의 `frame()`·`vDivider()` 지역 헬퍼 대신 `_IdeFrame`·
`_PaneDivider` 위젯으로 뺐다 — **같은 `ValueKey` 를 단 `Container` 를 `Row` 의
형제로 두면 `Duplicate keys found` 로 죽는다**(dp_design `DpListLines` 가 `_Line`
래퍼를 둔 것과 같은 이유). 위젯이 한 겹 끼면 키를 가진 `Container` 들이 서로 형제가
아니게 된다. 비용: 없다 — 테스트가 키로 프레임·구분선 개수를 셀 수 있게 된다.

Task 5: Ruling: `hDivider()` 는 쓰지 않아 만들지 않았다(로그 페인은 자기 프레임을
갖는다 — 2페인 구간에서 로그는 별도 박스이고 세로로 이어 붙지 않는다). 비용: 없음.

Task 5: Ruling: `const` 프레임을 유지하려고 페인을 `_EditorSlot` 같은 위젯으로 빼서
`findAncestorWidgetOfExactType` 으로 꺼내는 설계를 한 번 썼다가 **되돌렸다** —
그 메서드는 의존을 등록하지 않으므로 부모가 새 `editor` 위젯을 넘겨도 슬롯이 다시
빌드되지 않을 수 있다(에디터 페인이 낡은 내용을 보일 위험). `const` 이득보다 정확성이
먼저다. 비용: 프레임 트리가 `const` 가 아니다 — 리빌드 비용은 무시할 수준이다.

Task 5: Ruling: 계획 Step 6 은 맥락 영역 패딩만 바꾸게 했다. 검증은 구조 단언
(`padding` 값 확인) 대신 **행동 단언**으로 갔다 — `DpMissionHeader` 의 좌측선과
`sandbox-ide-frame` 의 좌측선이 같은지 잰다. 실측 red 는 **16 vs 0**(`DpSpacing.lg`
= 16)이었다. 비용: 없음 — 사용자가 보는 어긋남 자체를 잰다.

Task 5: 기록: 로그 페인 내부의 `EdgeInsets.all(DpSpacing.md)`(`sandbox_page.dart`
`_RunLogPane`)는 페인 **내용물**의 패딩이라 그대로 뒀다. `_missionRecovery` 에는
패딩이 없다.

Task 5: baseline-impact: `/sandbox` 실습 — 페인 사이 테두리가 **2px → 1px**, 바깥
프레임에 반경 8 과 넘침 자르기 적용, 페인 배경이 `surface` 로 명시된다. canonical
맥락 영역의 좌측선이 16 → 0(셸 거터 기준)으로 옮겨진다. ET13 visual baseline
재기록 대상.
Task 5: complete (commits e63b43a..ff451e7, tests: bash -c 'cd apps/web && flutter test test/features/sandbox --exclude-tags golden' → 00:05 +76: All tests passed!)

## Task 6: 멘토 화면

기준선: mentor 88/88 pass · dp_design 356/356

Task 6: Ruling: 계획 Step 5 의 테스트는 `find.byType(ListView).first` 로 대화를
잡게 했다 — **메시지가 없으면 대화 영역은 `ListView` 가 아니라 `_Empty` 다**(실측:
390px 테스트가 `StateError` 로 죽었다). 좌측 칼럼의 기준을 작성칸
(`ValueKey('mentor-primary-action')`)으로 바꿨다. 비용: 없음 — 작성칸도 좌측
칼럼 안이고, 위치 관계를 재는 목적은 그대로다.

Task 6: Ruling: `contextual_mentor_page_test.dart` 에
`web_mentor_context_projection.dart` import 를 더했다 — 그 파일은
`mentor_page.dart` 가 re-export 하지 않는다. 비용: 없음.

Task 6: Ruling: 계획 Step 8 의 legacy 분기를 그대로 받아들였다(참고 자료가 없으면
1열). 그 계약을 잴 테스트를 더했다 — 빈 `DpSide` 로 사이드를 만들면 대화 폭만 2/3 로
줄고 오른쪽이 빈칸이 된다. 비용: 참고 자료가 생기는 순간 대화 폭이 줄어드는 레이아웃
점프가 있다 — 시안이 사이드를 쓰라고 한 결과다.

Task 6: Ruling: 계획 Step 10 이 요구한 killSwitch 위젯 테스트는 **legacy 쪽에
만들었다** — contextual 의 `_pump` 헬퍼는 상태를 강제할 통로가 없고
(`mentorControllerProvider` 를 덮지 않는다), legacy 테스트에는 이미 `_FakeMentor`
가 있다. killSwitch 분기는 두 경로에서 같은 위젯(`DpKillSwitch` + 작성칸 숨김)이다.
비용: contextual 경로의 killSwitch 렌더는 위젯 수준에서 재지 않는다 —
`mentor_controller_test` 가 상태 전이를 잰다.

Task 6: Ruling: `DpCols.stretch` 는 1열에서 `main` 을 `Expanded` 로 감싸므로
**부모 높이가 유한해야 한다**. 멘토는 `Scaffold > SafeArea` 아래라 유한하다.
높이가 무한한 곳(sliver·`SingleChildScrollView` 안)에서 `stretch: true` 를 쓰면
죽는다 — 위젯 doc 에 「내부에 자체 스크롤 위젯을 둔 화면이 쓴다」로 적었다.
비용: 다른 Task 가 잘못 쓰면 런타임에서만 드러난다.

Task 6: baseline-impact: `/mentor` AI 멘토 — 맥락 캡슐이 **대화 위 → 사이드 칼럼**,
참고 자료도 사이드로, 말풍선 최대 폭이 **화면 비율(0.86) → 760**. legacy 는 참고
자료가 있을 때만 2열이 된다. **`WebMentorContextProjection` 은 ET13 결정적 투영이라
그 증거 기준선도 함께 바뀐다.** ET13 visual baseline 재기록 대상.
Task 6: complete (commits ff451e7..2efd5be, tests: bash -c 'cd apps/web && flutter test test/features/mentor --exclude-tags golden' → 00:04 +92: All tests passed!)

## Task 7: PR-A 마무리

Task 7: 기록: Step 1 의 변경 파일 목록에 `apps/admin` 5곳과 `apps/web/.../login_page.dart`
가 있다. 브리프가 「그 파일만 되돌린다」고 한 대상이 아니다 — Task 1 의 Ruling 대로
`DpPageHeader({gutter})` 의 옛 거동을 유지하려고 `gutter: true` 를 넘긴 호출부들이다.
`analysis_options.yaml`·`pubspec.lock` 은 없다(매 `flutter` 호출마다 로컬 도구가 다시
쓰므로 커밋 직전마다 `git checkout` 했다).

Task 7: 기록: analyze 는 dp_design 0 · admin 0 · web **1건**이다 —
`current_mission_controller.dart:273` `unawaited_return_in_try_block`. 이 브랜치가
손대지 않은 파일이고(`git diff origin/develop HEAD` 에 없다) 그 파일의 마지막 커밋은
develop 의 `00a7943` 다. 로컬 Flutter 3.47 전용 린트이고 CI(3.44.1)는 녹색이다.

Task 7: Ruling: 계획에 없던 documents 커밋을 했다 — Task 2 의 Ruling(「baseline-impact
를 PR 경계에서 옮긴다」)을 이행해야 PR 본문이 참조하는 파일이 비어 있지 않다.
documents `docs/s3-p4a-baseline-impact` → PR #181. 비용: 교차 레포 PR 이 하나 늘었다.

### CI 가 드러낸 실제 결함 1건 (로컬 재현 → 수정 → 로컬 검증)

Task 7: **`browser-ux` 와 `produce-atomic-pair` 가 같은 한 노드로 실패했다** —
`/path` 의 `scrollable-region-focusable`(axe, **serious**, "Scrollable region must
have keyboard access"). ET13 쪽 이름은
`web-path-current-week--a11y--w320--light--text200` 이다.

- **증거 수집**: CI 로그에는 위반 상세가 없다. `browser-ux` 잡이 올린 아티팩트
  (`evidence/browser-ux/latest.json`)를 `gh run download` 로 받아 실패 시나리오만
  뽑아 읽었다 — 여기에 규칙 id·impact·노드 수가 그대로 있다. **다음에도 이 경로로
  본다**(잡 로그를 뒤지는 것보다 빠르고 정확하다).
- **원인**: `DpWebTable` 은 `minWidth`(640)보다 좁으면 표만 가로로 스크롤한다. 표
  안에 포커스 가능한 셀이 하나라도 있으면 axe 가 통과하는데, 「이번 주 과제」 표는
  제목이 `DpLink.title` 이라 통과하고 **「N주 계획」 표는 `onOpenWeek: null` 이라
  포커스 가능한 자식이 하나도 없다**. `/dashboard` 는 통과하고 `/path` 만 실패한
  이유가 정확히 이것이다. 즉 **Task 3 의 「링크로 만들지 않는다」 판정이 이 결함을
  만들었다** — 그 판정 자체는 옳았고(갈 곳이 없는 링크를 만들지 않는다), 빠진 것은
  스크롤 영역의 키보드 접근이었다.
- **수정 위치의 판정**: 포커스 노드를 **스크롤 뷰 안**에 둔다. 밖에 두면 웹
  시맨틱스가 tabindex 를 overflow 를 가진 요소가 아니라 그 부모에 붙여 axe 가 여전히
  잡고, 안에 두면 `Scrollable` 의 `ScrollAction` 이 화살표 키를 받는다(Actions 조회가
  포커스 노드에서 **위로** 올라간다). 포커스가 보이지 않으면 WCAG 2.4.7 을 대신
  어기므로 `DpLink` 와 같은 2px 전경 링을 그린다. 잘리지 않는 표는 포커스 노드를
  만들지 않아 **여분의 탭 정지가 생기지 않는다**(1440 `keyboard-traversal` 시나리오가
  정확한 탭 순서를 단언한다).
- **검증**: Docker 데몬이 꺼져 있었다(켜서 해소 — 「없다」가 아니라 「안 켰다」였다).
  CI 와 같은 핀 이미지로 수정 **전** 재현(axe 390 FAIL, 1분) → 수정 → dp_design
  362/362 · web 1053+1skip → 재빌드 → **browser-ux 17/17 PASS**.
- 비용: ET13 `produce-atomic-pair` 는 별도 증거 앱 빌드라 로컬로 재확인하지 않았다 —
  같은 한 노드이므로 같은 수정이 닫는다고 보고 CI 에 맡겼다.

Task 7: 기록: 같은 실행에서 `analyze-test`(5m2s)·`perf-gate`(22m45s)·
`web-image-config-contract` ×2 는 **이미 통과했다**. 즉 전송량·린트·이미지 계약은
이 PR 이 건드리지 않았다.
Task 7: complete (commits 2efd5be..4332718, tests: dart run melos run test →      └> SUCCESS)

# PR-B — 커뮤니티 (브랜치 `feat/s3-p4-community-screens`, base develop `7670447`)

## Task 8: 커뮤니티 목록 3종

기준선: community 189 pass + 1 skip (테스트 30파일)

Task 8: Ruling: 계획은 빈 검색 결과를 `SliverFillRemaining(key: 'search-empty')`
에서 표의 `empty` 로 옮기라 했고, 그 키를 찾는 테스트가 있으면 문구로 바꾸라 했다.
대신 **키를 `empty` 위젯에 그대로 달았다** — 구조는 계획대로 바뀌고 키 계약은
깨지지 않는다. 비용: 없음.

Task 8: Ruling: **칼럼 라벨은 게시판에서 나온다** — 칼럼은 행마다 다른 라벨을 가질
수 없다. 옛 `CommunityPostRow` 는 **행의** `post.boardType` 으로 답변/댓글을
골랐으므로, QNA 행을 자유게시판 목록에 넣은 테스트에서도 「답변」이 나왔다(실측:
`'목록을 렌더한다(작성자 이름 없이 메타 표시)'` 가 이 전제에 기대고 있었다).
그 테스트를 `?board=QNA` 로 게시판을 명시하게 고쳤다. 비용: 한 게시판 목록에 다른
게시판의 글이 섞여 오면 라벨이 그 게시판 것으로 읽힌다 — 게시판별 독립 페이지라
운영에서는 섞이지 않는다.

Task 8: Ruling: Q/A 「상태」 칼럼의 미해결 문구를 계획의 `'답변 ${replyCount}'` 대신
**`'답변 중'`** 으로 했다 — 답변 수는 이미 옆 숫자 칼럼에 있어 같은 값을 두 번
말하게 된다. 비용: 없음(0건은 여전히 「답변 대기」다).

Task 8: Ruling: `CommunityBadgeChip` 을 **삭제**했다 — 소비처가 목록 행과 검색 행
둘뿐이었고 둘 다 `DpStatusText` 로 바뀌었다(`git grep` 실측). 비용: 없음.

Task 8: Ruling: 빈 상태의 작성 액션을 없앴다. 기존 테스트가 **이미 그것을 예고**하고
있었다(`web_community_board_projection_test` 의 `NOTE(P4)`: 「한 화면에 접근명이 같은
버튼이 둘이다 — P4 에서 하나로 줄이거나 라벨을 다르게 둔다. 그때 이 단언도 함께
고친다」). 헤더 버튼 하나만 남겼고 단언을 `composed == 1` + 「빈 상태에는 없다」로
바꿨다. 비용: 빈 목록에서 작성까지의 거리가 조금 멀다 — 헤더 버튼이 상시 보인다.

Task 8: 기록: `search_highlight.dart` import 가 `community_home_page.dart` 에서
사용되지 않게 됐다(`_searchRow` 가 투영 파일의 `communitySearchRow` 로 옮겨졌다).
analyze 가 잡아 제거했다.

Task 8: 기록: ET13 증거·계약 테스트 44/44 통과 — `WebCommunityBoardProjection` 의
렌더가 바뀌었지만 계약 테스트는 구조를 단언하지 않는다. **baseline 이미지는 여기서
재기록하지 않는다**(P5 사람 승인 단계).

Task 8: baseline-impact: `/community` 목록 3종 — 카드 나열 → 표(칼럼·구분선·hover).
해결 배지가 「상태」 칼럼의 `DpStatusText` 로, 집계 한 줄이 숫자 칼럼 둘로. 빈 상태의
작성 버튼이 사라진다(헤더 버튼만). 피드 광고와 「더 보기」가 목록 중간 → 표 아래로.
좌우 패딩이 셸 것만 남는다. **ET13 커뮤니티 fixture 3종의 visual/a11y baseline 재기록
대상.** 후속(P4 범위 밖): `PostSummaryView` 에 `createdAt`·작성자 표시 이름 추가.
Task 8: complete (commits 7670447..f441b88, tests: bash -c 'cd apps/web && flutter test test/features/community test/evidence/et13_web_evidence_app_test.dart --exclude-tags golden' → 00:10 +210 ~1: All tests passed!)

## Task 9: 검색어 유지

Task 9: Ruling: 계획 Step 6 은 skip 테스트를 「셸을 포함하는 헬퍼로 바꿔」 셸 경유로
켜라고 했다. 대신 **계약을 두 반쪽으로 갈라 각자 있어야 할 곳에서 쟀다** — ① 셸이 q 를
들고 가는 것은 `carryCommunityQuery` 단위 7건 + `app_shell_view_test` 배선 2건(들고
가기·버리기), ② 게시판이 바뀐 URL 을 받은 화면이 새 게시판으로 다시 조회하는 것은
`community_home_page_test`(검색 provider 가 받은 `board` 를 기록해 확인). 커뮤니티
테스트에 셸+라우터를 통째로 띄우는 헬퍼를 새로 만드는 것보다 싸고, 실패 시 원인이
어느 쪽인지 바로 갈린다. 비용: 두 반쪽이 실제로 이어지는지를 한 테스트로 보지 않는다 —
셸이 만드는 문자열과 화면이 받는 문자열이 같은 형태(`?board=QNA&q=stream`)임을
두 테스트가 각자 리터럴로 고정해 둔다.

Task 9: Ruling: 계획에 없던 경계 2건을 더했다 — 「목적지에 이미 q 가 있으면 덮어쓰지
않는다」(계획에 있음)와 **「빈 q 는 붙이지 않는다」**(없었다). 후자는 검색을 지운
직후(`q=`)에 게시판을 바꾸면 빈 검색으로 들어가 목록이 아니라 빈 결과가 되는 경로다.
비용: 없음.

Task 9: 기록: 셸 테스트에서 `find.text('커뮤니티')` 가 **2건**이다 — 헤더 네비 항목과
브레드크럼. `DpWebHeader` 안으로 범위를 좁혔다(기존 브레드크럼 테스트가 반대 방향으로
같은 함정을 이미 피해 뒀다).

Task 9: baseline-impact: 렌더 변화 없음 — 라우팅 동작만 바뀐다.
Task 9: complete (commits f441b88..9fdcb33, tests: bash -c 'cd apps/web && flutter test test/features/shell test/features/community --exclude-tags golden' → 00:12 +241: All tests passed!)

## Task 10: 글 상세·질문 상세

기준선: post_detail + qna_detail 14 pass · `Card(` = lcs_context 2 · tombstone 1 ·
post_detail 1 · qna_detail 1 · question_create 1(Task 11)

Task 10: Ruling: 브리프가 `DpMaxWidth`(중앙 정렬)와 `Align(topLeft)`+`ConstrainedBox`
(좌측 정렬) 중 고르라 했다 — 시안 `.narrow{margin-inline:0}` 이 **좌측 정렬**이므로
후자로 갔다. 비용: 넓은 화면에서 본문이 왼쪽에 몰린다 — 시안 그대로다.

Task 10: Ruling: 「댓글 N」·「답변 N」 제목을 패널 제목으로 올리지 **않았다**. 항목
하나하나가 이미 면(`DpPanel`)이므로 그것들을 다시 면 안에 넣으면 면이 이중이 된다.
항목이 면인 이유는 인라인 수정(`TextField`)이 카드 안에서 열려 경계가 필요하기
때문이다(브리프가 이 선택을 요구했다). 비용: 시안 `.sec>h3` 와 달리 제목에 구분선이
없다.

Task 10: Ruling: 사이드가 빈칸이 되는 문제를 브리프 제안대로 **태그 패널을 사이드에
함께 두는 것**으로 해결했다 — 관련 질문은 없을 수 있지만 태그는 거의 항상 있다.
본문의 태그 `Wrap` 은 옮긴 것이므로 본문에서 지웠다(같은 태그를 두 번 그리지 않는다).
비용: 태그가 없고 관련 질문도 없는 질문은 사이드가 빈칸이다 — 그때 본문이 2/3 로
좁아진다. `DpCols` 를 쓰기 전에는 관련 질문 유무를 알 수 없어(비동기) 이 이상 줄일
수 없다.

Task 10: Ruling(실측 정정 2건): ① `SimilarQuestion` 의 식별 필드는 브리프가 적은
`id` 가 아니라 **`questionId`** 다(`packages/dp_core/.../community_post.dart`).
② `lcs_context.dart` 의 옛 `Card(color: c.surface)` — `DpPanel` 은 색 인자를 받지
않고 언제나 `surface` 라 같은 값이다(컴파일 에러로 드러났다). ③ 브리프 테스트가 쓴
`lcsAnswererSnapshotProvider` 는 실제로 **`lcsByQuestionProvider`** 다.
비용: 없음.

Task 10: Ruling: 「이 주제 학습하기」는 구현하지 않았다 — 질문 태그를 학습 콘텐츠에
잇는 데이터·엔드포인트가 없다. `baseline-impact.md` 의 후속 표에 이미 적혀 있다.
비용: 시안과 1:1 이 아니다.

Task 10: baseline-impact: `/community/post/:id` 글 상세 — 본문 폭이 셸 폭(1120)에서
**760**으로, 좌측 정렬. 댓글이 Material `Card`(그림자·둥근 모서리 12) →
`DpPanel`(테두리·반경 8). `/community/:id` 질문 상세 — `.cols` 2열이 되고 태그가
본문 아래 → 사이드 패널로 옮겨지며, 「관련 질문」 패널이 새로 생긴다(요청 1건 증가).
답변 카드·비석·LCS 맥락 카드도 `DpPanel` 이 된다. ET13 fixture 에는 상세 화면이
없으므로 그 baseline 은 영향받지 않는다.
Task 10: complete (commits 9fdcb33..d60a91b, tests: bash -c 'cd apps/web && flutter test test/features/community --exclude-tags golden' → 00:09 +207: All tests passed!)

## Task 11: 작성·수정 4화면

기준선: question_create + post_create + post_edit + question_edit 31 pass

Task 11: 기록: Step 1 의 실측 — **수정 화면 둘은 작성 화면의 폼을 그대로 재사용한다**
(`PostEditPage` → `PostCreatePage(editPostId:)`, `QuestionEditPage` →
`QuestionCreatePage(editPostId:)`). 작성 화면 둘만 고치면 넷이 함께 바뀐다. 수정
화면 껍데기는 로딩·실패 분기만 갖는다. 자유글 작성에는 **태그 필드가 있다**(브리프의
파생 표는 「없다」고 적었다 — 편집 모드에서만 감춘다).

Task 11: Ruling: 브리프는 sliver 를 **하나씩** `narrow(...)` 로 감싸라 했다. 그렇게
스크립트로 감쌌더니 블록 경계를 잘못 잡아 20 issues 가 났고, 백업에서 되돌린 뒤
**목록 전체를 `SliverMainAxisGroup` 하나로 묶고 그것만
`SliverConstrainedCrossAxis` 로 자르는** 쪽으로 갔다. 삽입 지점이 파일당 두 곳뿐이라
훨씬 안전하고, 결과는 같다(좌측 정렬 760). 비용: pinned 툴바가 그룹 안에서 고정된다 —
그룹이 목록 전체라 실질 차이가 없다.

Task 11: Ruling: **웹 앱 전체에서 `AppBar(` 를 쓰는 곳은 이 두 수정 껍데기뿐이었다**
(`git grep -c` 실측). 셸 문법과 어긋나므로 실패 상태를 `DpPageHeader` +
`SupportableError`(문의 연결·재시도)로, 로딩을 `DpLoading` 으로 바꿨다. 브리프 Step 7
이 「로딩을 DpLoading 으로, 실패는 SupportableError 를 쓰는지 확인」이라 한 범위 안이다.
그 두 분기는 **테스트가 전혀 없었다** — 각 화면에 로딩·실패 테스트를 새로 썼다
(기존 수정 테스트들은 껍데기를 건너뛰고 `PostCreatePage` 를 직접 띄운다).
비용: 없음.

Task 11: Ruling: 실패 테스트가 `Exception` 을 던졌더니 테스트 밖으로 샜다 —
컨트롤러의 `load()` 는 **`ApiException` 만 잡는다**(실측). `ApiException(code:
ApiErrorCode.network, …)` 으로 바꿨다. 「맨 Exception 은 상태로 바뀌지 않는다」는
사실을 테스트 주석에 남겼다. 비용: 없음(그 계약 자체는 이 Task 의 범위가 아니다).

Task 11: 기록: `DpLoading` 은 내부에 `CircularProgressIndicator` 를 품는다 —
「맨 것을 쓰지 않는다」는 `DpLoading` 의 존재로 재야 한다.

Task 11: baseline-impact: 커뮤니티 작성·수정 4화면 — 폼 폭 1120 → **760 좌측 정렬**,
유사질문 안내 `Card` → `DpPanel`, 좌우 패딩이 셸 것만 남는다. 수정 화면 둘의 로딩이
맨 스피너 → `DpLoading`(라벨 있음), 실패가 **`AppBar` + 평문** → `DpPageHeader` +
`SupportableError`(문의 연결·재시도)로 바뀐다.
Task 11: complete (commits d60a91b..577fbb6, tests: bash -c 'cd apps/web && flutter test test/features/community --exclude-tags golden' → 00:10 +216: All tests passed!)

## Task 12: PR-B 마무리

Task 12: 기록: 변경 파일은 `apps/web/lib/src/features/{community,shell}/**` ·
`apps/web/test/**` 뿐이다(설정 파일 없음). `dart format --set-exit-if-changed` 가
`question_create_page_test.dart` 하나를 잡아 포맷 뒤 `--amend` 했다.

Task 12: 기록: frontend PR **#237** · documents PR **#182**(기준선 영향).
1차 CI: `analyze-test` pass · `produce-atomic-pair` pass · `perf-gate` pass(22m57s) ·
이미지 계약 2건 pass · **`browser-ux` fail 1건**.

Task 12: Ruling: `browser-ux` 실패는 **계획이 예고한 시나리오 기대값 불일치**였다 —
`keyboard-traversal`(1440)의 목록 행 탭 정지가 「제목 + 집계 한 덩어리」
(`오늘 배운 것 공유\n댓글 4 · 추천 5`)에서 **제목 링크 하나**로 줄었다. 카드 나열이
표가 되면서 답변·추천이 각자 숫자 칼럼이 됐고 그 셀은 포커스 대상이 아니다. **정지
개수와 순서는 그대로**다. `expectations.json` 을 갱신했다 — 그 파일의 규칙이
「갱신은 실측 후 PR 리뷰 승인으로만」이므로 ① CI 아티팩트가 기록한 실제 순회 순서 ②
로컬에서 CI 와 같은 핀 이미지로 17/17 PASS ③ `run.test.mjs` 통과를 근거로 남기고
notes 에 경위를 적었다. 비용: 리뷰어가 이 갱신을 승인해야 한다 — PR 본문과 커밋
메시지에 근거를 실었다.

Task 12: 기록: 아티팩트 다운로드는 **런이 둘로 갈린다**(`produce-atomic-pair` 는
36319166720, 나머지는 36319166732). `gh api .../artifacts --jq '.artifacts[0].name'`
로 첫 아티팩트를 집으면 `.dockerbuild`(zip 아님)를 받아 실패한다 — 이름으로
`leva-browser-ux-*` 를 골라야 한다.

## PR-C (Task 13~18) — 브랜치 `feat/s3-p4-account-screens`, BASE `2c38bac`

Task 12: complete (commits f7ef216..931206c, PR #237 머지 = merge commit `2c38bac`;
전 잡 pass/skipping·실패 0 — analyze-test/browser-ux/perf-gate(21m42s)/produce-atomic-pair/
이미지계약2 SUCCESS, admin-image·web-image·web-image-release-contract·ET13auth SKIPPED).
앞 세션이 CI 대기 중에 끝나 완료선이 빠져 있었다 — `origin/develop` 이 `931206c` 를
포함하는 것을 실측해 소급 기록한다.

Pre-flight (PR-C, Task 13~18) — 공유 인터페이스 3행:
  row 1: Task 13 produces `DpCheckRow` → Task 15 consumes. 순서 정상(13 이 먼저). clean.
  row 2: Task 13 produces `DpSteps`·`DpOptionRow` → Task 16 consumes. 순서 정상. clean.
  row 3: Task 1(PR-A, 머지됨) produces `DpRowLine`·`DpKeyValues`·`DpWebTable`·`DpCols`·
         `DpSide` → Task 17 consumes. 실측: 그 5종 + P3 의 `DpPanel`·`DpListLines`·
         `DpLink`·`DpStatusText` 전부 BASE `2c38bac` 의 `packages/dp_design/lib` 에 존재. clean.
  Task 14·Task 18 은 「새 공개 API 없음」 — row 없음.

## Task 13: dp_design 온보딩 프리미티브 3종

Task 13: Ruling: 브리프의 테스트 호스트(`MediaQuery(data: MediaQueryData(size:…))`)는
`MaterialApp` 이 뷰에서 자기 MediaQuery 를 만들어 **덮는다** — 레포가
`dp_cols_test.dart` 주석에 이미 그 함정을 적어 뒀다. `tester.view.physicalSize` 로
바꿨다. 비용: 없다(같은 의도, 레포 관례).

Task 13: Ruling: `node.hasFlag(SemanticsFlag.…)` → `isSemantics(…)`. `SemanticsFlag`
는 이 Flutter 에 없고, 레포의 다른 관례(`flagsCollection`+`ui.Tristate`)는 로컬 3.47
전용 API 에 테스트를 묶는다(CI 는 3.44.1 핀). 1차로 쓴 `containsSemantics` 는 3.40
이후 deprecated 이고 `flutter analyze` 가 info 를 치명으로 다뤄 **rc=1 로 6건** 떴다
→ 대체 매처 `isSemantics` 로 옮겨 analyze 0. 비용: 3.44.1 에 `isSemantics` 가 없으면
컴파일 실패 — CI 가 즉시 드러낸다.

Task 13: Ruling: `DpOptionRow`·`DpCheckRow` 의 키보드 도달을 브리프의
`MouseRegion`+`GestureDetector` 대신 **`FocusableActionDetector`** 로 만들었다
(P3 의 `DpLink` 실측 수정과 같은 형태). 브리프 형태로 구현해 키보드 테스트를 돌려
**RED 를 실증**했다: Tab 뒤 `primaryFocus` 가 `_FocusScopeWithExternalFocusNode` —
행을 건너뛰고 포커스가 라우트 스코프에 머문다. 라디오·동의 체크는 폼 컨트롤이라
키보드 조작이 필수다. 비용: 포인터 클릭으로 포커스를 받아도 2px 링이 보인다
(`DpLink` 가 이미 같은 대가를 택했다 — 링과 시맨틱스가 `_focused` 하나를 공유).

Task 13: Ruling: 브리프의 `Semantics(container: true)` 만으로는 라벨·설명이 각자
노드로 남아 `getSemantics(find.text(…))` 가 checked 플래그를 보지 못한다 →
`MergeSemantics` 한 겹. 비용: 라벨과 설명이 한 문장으로 읽힌다 — 라디오·체크
항목에는 오히려 맞다(무엇을 고르는지 + 골랐는지를 한 번에 읽는다).

Task 13: Ruling: `DpCheckRow` 의 Material `Checkbox` 를 `IgnorePointer` +
`ExcludeFocus` + `ExcludeSemantics` 로 감쌌다 — 브리프는 `ExcludeSemantics` 만 걸어
체크박스가 **별도 탭 정지**로 남고(같은 항목에 두 번 멈춘다), `DpPanel` 안의 Material
위젯 함정(Task 3 실패 7건)에도 노출된다. 시각만 남기고 포커스·활성화는 행 래퍼가
갖는다. 비용: 체크박스 자체의 ripple·hover 오버레이가 사라진다(시안에 그림자·잉크가
없으므로 시안 충실도는 오히려 오른다).

Task 13: Ruling: 배럴 삽입 순서 — 브리프는 「알파벳 순서」라 했으나
`lib/dp_design.dart` 는 **디렉터리별 묶음** 순이다. 묶음에 맞춰 넣었다
(layout 묶음의 `dp_panel` 뒤, interaction 묶음의 `dp_interactive_card` 앞뒤).
비용: 없다.

Task 13: 기록: 리터럴 `vertical: 10`·`fontSize: 13` 은 Global Constraints 의
「새 리터럴 숫자 금지」와 충돌해 보이지만, P3 의 `dp_row_line.dart:59`·
`dp_list_lines.dart:44`·`dp_web_table.dart:208` 이 이미 쓰는 **시안 파생값**이다
(시안 `.chk{padding:10px 16px}`). 선례를 따랐다 — 토큰을 새로 만들지 않았다.

Task 13: 기록: `test/golden/state_golden_test.dart` 의 `DpKillSwitch` 라이트·다크
골든 2건이 이 PC 에서 **100% 픽셀 차**(1474200px)로 실패한다. 배럴을 BASE 로
되돌린 상태에서 다시 돌려 **같이 실패하는 것을 실측** — 내 변경과 무관한 로컬 렌더
환경 차이다. CI 는 `flutter test --exclude-tags golden` 이라 범위 밖이다.

Task 13: 기록: **Task 16 으로 넘기는 실측 항목** — `DpOptionRow` 가
`inMutuallyExclusiveGroup` 을 선언하므로 Flutter 웹이 `role="radio"` 로 투영하면
axe 의 `aria-required-parent` 가 radiogroup 부모를 요구할 수 있다. Task 16 에서
옵션 묶음을 감쌀 필요가 있는지 `browser-ux` 로 확인한다(로컬에서는 엔진 소스가
SDK 에 없어 매핑을 확인할 수 없다 — 실측만이 답이다).

Task 13: 기록: admin 156 PASS · dp_design 375 PASS(`--exclude-tags golden`) ·
`flutter analyze` (dp_design) No issues · `dart format` 8파일 중 4 changed 후 재포맷 완료.
커밋 `611a6da`. 로컬 툴이 다시 쓴 `analysis_options.yaml` 2개 + `pubspec.lock` 은
되돌린 직후 커밋했다(커밋에 포함되지 않았다). 골든 실패 산출물
`test/golden/failures/` 는 삭제했다.
Task 13: complete (commits 2c38bac..611a6da, tests: bash -c 'cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/packages/dp_design && flutter test --exclude-tags golden' → 00:14 +375: All tests passed!)

## Task 14: 로그인 + 인증 콜백

Task 14: Ruling: 브리프의 새 `build()` 와 `_LoginStory` 는 `brandRow` + 테마 토글을
**통째로 잃는다.** 유지했다(페이지 상단, 2열 그리드 위). 근거: 기존
`login_header_test` 가 `brand-row` 키와 「테마 전환」 툴팁을 둘 다 단언하고,
로그인은 셸 밖(bare 라우트)이라 브랜드·테마 전환이 갈 다른 자리가 없다.
Global Constraints 「기능 보존이 시안 충실도보다 앞선다」. 비용: 시안 `.login` 에는
상단 브랜드 행이 없다 — 시안과 한 줄 차이가 남는다.

Task 14: Ruling: compact(390)에서는 스토리를 그리지 않는다. 브리프의 1열 분기는
compact 에서도 스토리를 그리지만, 기존 테스트 「mobile login removes the story
panel and keeps one focused flow」가 반대를 단언한다(의도된 UX 결정).
`showStory = windowClass != compact` 로 두 요구를 모두 만족시켰다 — 브리프의
medium(800) 1열 테스트는 그대로 통과한다. 비용: 시안의 compact 1열과 다르다.

Task 14: Ruling: 브리프 Step 3 의 Expected(FAIL)가 **틀렸다.** 현재 코드도 1280 에서
스토리가 좌측·패널이 우측이라 「2열 배치」 테스트가 **그냥 통과**했다(판별력 0).
시안이 실제로 바꾸는 것 — `.flow` 가 칩 나열에서 제목+설명 2열 목록
(`DpListLines` + 설명 문구)으로 바뀌는 것 — 을 단언해 판별력을 만들었다.
비용: 없다(테스트가 더 정확해졌다).

Task 14: Ruling: 「그라디언트를 쓰지 않는다」 테스트에서 `leva-brand-mark` 를
제외했다. 실측: 남은 그라디언트 컨테이너는 브랜드 로고 하나뿐이고, 그것은 셸
전체가 쓰는 dp_design 위젯이라 이 화면의 장식이 아니다. 비용: 로고의
그라디언트 + boxShadow 는 Global Constraints 의 「그림자를 쓰지 않는다」와 어긋난
채 남는다 — **P5/후속 관찰 항목**(셸 헤더도 같은 위젯을 쓰므로 바꾸면 ET13
baseline 이 P4 범위를 넘어 움직인다).

Task 14: Ruling: 콜백 narrow 폭은 렌더 폭이 아니라 **제약**을 단언한다.
`ConstrainedBox(maxWidth: 760)` 의 렌더 폭은 자식의 고유 폭이다(실측 675) —
처음 쓴 `getSize(...).width == 760` 은 기대가 틀린 테스트였다. 중앙 정렬은
`getRect(...).center.dx` 로 따로 단언했다.

Task 14: Ruling: `auth_callback_page_test` 의 호스트 3곳에 `theme: DpTheme.light()`
를 줬다 — `context.appTokens` 가 `Theme.extension<AppTokens>()!` 이라 테마 없이는
`_TypeError` 로 죽는다(옛 리터럴 420 은 테마를 안 읽어 통과했다). CLAUDE.md 의
「`context.dpColors` 를 쓰는 위젯엔 `theme: DpTheme.light()` 를 준다」 관례.

Task 14: 기록: auth 39 → **44 PASS** · web 전체 **1094 PASS** · `flutter analyze`
(apps/web) 1건은 **기존** 경고(`current_mission_controller.dart:273`
`unawaited_return_in_try_block`, 로컬 3.47 전용 린트 — CI 3.44.1 은 녹색, 핸드오프
§6-11). 커밋 `7e0522d`. 로컬 툴이 다시 쓴 `analysis_options.yaml` 2개 +
`pubspec.lock` 은 되돌린 직후 커밋했다.

Task 14: 기록: **기준선 영향(Task 18 에서 baseline-impact.md 로 옮긴다)** —
`/login`: 장식 배경·원·칩 제거, 2열 경계 900 → **840**(정정: `DpWindowClass.expanded`
는 **840~1239** 다. 뒤집히는 구간은 840~899 이고 1240 에서는 구·신 모두 2열이라 차이가
없다 — 독립 리뷰 I6), 로그인 패널 480 폭 제약 제거,
페이지 헤더 → 패널 제목, `.flow` 제목+설명 목록 신설, 약관 문구 색
`textFaint` → `textSecondary`(WCAG). **랜딩과 함께 첫인상이 바뀌는 화면.**
`/auth/callback`: 중앙 narrow 420 → 760, 오류색 `colorScheme.error` → `DpColors.danger`,
진행 상태도 같은 프레임을 쓴다.
Task 14: complete (commits 611a6da..7e0522d, tests: bash -c 'cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/apps/web && flutter test' → 00:42 +1094: All tests passed!)

## Task 15: 동의 + 베타 대기

Task 15: Ruling: 동의 항목은 **4개가 아니라 5개**다(필수 TERMS·PRIVACY + 선택
MARKETING·LCS_ATTACH·ERROR_LOG). 브리프의 `findsNWidgets(4)` 를 5로 교정했다.

Task 15: Ruling: 브리프의 단일 `DpPanel`(`_ConsentKind.values` 전체를 한 패널에)은
기존 정보 구조를 지운다 — 현재 화면은 필수 2행 → **출생 연도 필드** → 「선택 동의」
라벨 → 선택 3행 순서다. 필수·선택 **두 `DpPanel`** 로 나눠 그 구조를 보존했다.
각 패널의 마지막 행에만 `last: true`. 비용: 시안의 단일 `.chk` 패널과 다르다 —
그 대가로 출생 연도 입력이 필수 동의 바로 뒤에 남는다.

Task 15: Ruling: 동의 화면의 `DpPageHeader` 는 **유지**한다. 브리프는 베타 화면에
대해서만 제거를 지시했고, 동의는 테스트 4건이 title·description 을 단언한다 —
재동의/신규 분기 문구(「서비스 이용약관 재동의」 ↔ 「가입 전 동의」)가 거기 있다.

Task 15: Ruling: `DpLink` 에 `semanticsLabel` 을 더했다(dp_design 변경 — Task 13 이
그 담당이었지만 필요가 여기서 드러났다). 근거: 기존
`TextButton(child: Text('전문 보기', semanticsLabel: '${k.title} 전문 보기'))` 를
`DpLink.inline` 으로 바꾸면 같은 라벨 「전문 보기」 2개가 되어 **접근성이 후퇴한다**.
RED→GREEN 으로 추가했다(dp_link 10 PASS). 비용: dp_design 공개 API 가 Task 13 밖에서
한 개 늘었다 — 최종 리뷰가 볼 수 있게 여기 적는다.

Task 15: Ruling: 베타 대기의 상태 아이콘(`hourglass_top`/`lock_clock`)을 `DpTag`
(`베타 대기`/`대기 만료`)로 바꿨다 — 상태를 **텍스트로** 알려 스크린리더가 읽을 수
있고 시안의 면 문법과도 맞는다. 브리프 스니펫은 pending 문구만 담고 `_expired`
분기(만료 문구 + 「다시 로그인」)를 잃었는데 **둘 다 보존**했다. 비용: 아이콘의
시각적 즉시성을 잃는다.

Task 15: Ruling: 베타 대기의 `brandRow` 를 유지했다 — 브리프 스니펫에는 없다.
기존 테스트가 `brand-row` 키를 단언하고, 셸 밖 화면의 유일한 제품 정체성이다
(Task 14 의 로그인과 같은 판정).

Task 15: Ruling: `CheckboxListTile` 을 읽던 테스트 3곳을 행 키
(`consent-<name>-row`)로 읽게 바꿨다 — `DpCheckRow` 의 라벨은 `Widget`(제목 +
필수/선택 태그)이라 `find.widgetWithText` 로 행을 특정할 수 없다.

Task 15: 기록: 「전문 보기」 링크가 갈 곳은 **있다**(`docUrl` =
`https://leva.ai.kr/terms`·`/privacy`, `externalLinkOpenerProvider` 로 새 탭). 브리프
Ruling 표의 「없으면 신설하지 않는다」 조건은 해당하지 않는다 — 이미 있는 링크를
`DpLink.inline` 으로 옮겼고 `consent-*-doc` 키를 유지해 기존 테스트가 그대로 돈다
(전문 링크 탭이 동의로 번지지 않는 계약도 `DpCheckRow` 구조가 지킨다 — trailing 은
행 제스처 밖이다).

Task 15: 기록: consent 25 PASS · beta 3 PASS · dp_design **376 PASS** · admin 156 PASS ·
web 전체 **1098 PASS** · analyze: dp_design 0, web 1건(기존
`current_mission_controller.dart:273`). 커밋 `ddd4218`. 설정 파일 4개
(`analysis_options.yaml` 3 + `pubspec.lock`)는 되돌린 직후 커밋했다.

Task 15: 기록: **기준선 영향(Task 18 에서 baseline-impact.md 로)** —
`/consent`: 폭 440 → 760, 체크 행 `CheckboxListTile` → `DpCheckRow`(테두리 패널 2개),
항목마다 필수/선택 태그 신설, 「전문 보기」가 버튼 → 인라인 링크, prefill 로딩이
맨 스피너 → `DpLoading`. 차단 화면 폭 360 → 760.
`/beta`: 페이지 헤더 → 중앙 태그 + 제목, 폭 440 → 760, 상태 아이콘 → 태그,
폴링 스피너 → `DpLoading`.
Task 15: complete (commits 7e0522d..ddd4218, tests: bash -c 'cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/packages/dp_design && flutter test --exclude-tags golden && cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/apps/web && flutter test' → 00:43 +1098: All tests passed!)

## Task 16: 진단 3단계

Task 16: Ruling: 트랙 선택은 라디오가 아니라 **`DropdownButtonFormField`** 였다
(브리프 Ruling 표가 Step 1 실측으로 갱신하라고 한 줄). 시안 `dstart` 의 `.opt` 대로
`DpOptionRow` 목록으로 바꿨다 — 트랙은 이 화면의 본 결정이라 접어 두지 않는다.
다만 트랙은 **8개**다(시안 예시는 3개). 비용: 시작 화면이 길어져 CTA 가 기본 테스트
뷰포트(800×600) 밖으로 나간다 — 페이지는 `SingleChildScrollView` 안이라 실제로는
스크롤되지만, 탭하는 테스트에 `tallView(1200×2400)`/`ensureVisible` 을 넣어야 했다.

Task 16: Ruling: `trackDescriptions` 는 **존재하지 않는다**(브리프 스니펫이 참조).
보기 행은 라벨만 둔다 — 없는 문구를 만들지 않는다(Global Constraints: 새 API·데이터를
추가하지 않는다).

Task 16: Ruling: 문항 보기는 「고른 뒤 제출」이 아니라 **누르는 즉시 제출**이다
(`OutlinedButton` 이 `submitAnswer` 를 바로 불렀다). `DpOptionRow` 의 라디오
시맨틱스를 그대로 쓰되, 트랙·보기 두 묶음을 `Semantics(role: SemanticsRole.radioGroup)`
으로 감쌌다 — Task 13 이 남긴 「`role="radio"` 에 radiogroup 부모가 필요할 수 있다」
(axe `aria-required-parent`)를 여기서 선제 처리한다. `SemanticsRole` 은
`dp_loading.dart` 가 이미 쓰므로 CI 3.44.1 에도 있다. 비용: 웹 렌더 매핑은
`browser-ux`(Task 18)에서만 실측된다 — 로컬에는 엔진 소스가 없다.

Task 16: Ruling: `DpOptionRow.onSelect` 를 nullable 로 바꿨다(dp_design 변경).
기존 `OutlinedButton` 은 `busy || answerFailed` 에 `onPressed: null` 로 잠겼고, 그
동작을 잃으면 **중복 제출**이 생긴다. 잠긴 보기는 포커스 순회에서도 빠진다 —
누를 수 없는 보기에 탭이 멈추면 원인을 알 수 없다. RED→GREEN 으로 추가(dp_design 377).

Task 16: Ruling: 시안 `.bars`(개념별 결과) 패널을 **만들지 않았다.** 실측:
`AssessmentResult` 는 `diagnosedLevel`·`confidenceWeight` 둘뿐이고 개념별 점수가
없다. 브리프가 「데이터가 없으면 만들지 말고 Ruling 에 적으라」고 한 경우다.
비용: 시안 `dresult` 의 `.bars` 는 P4 에서 구현되지 않는다 — 백엔드 계약이 먼저다
(baseline-impact.md 의 「구현하지 않은 시안 요소」에 더한다).

Task 16: Ruling: 「결과 형태 미리보기」 키-값 3행을 브리프 예시
(「강점·보강 개념」)가 아니라 **기존 세 문구**(`현재 레벨`·`진단 신뢰도`·
`맞춤 학습 경로`)로 만들었다. 테스트 3건이 그 문구를 단언하고, 개념별 점수가 없는데
「강점·보강 개념」을 약속하면 결과 화면이 그것을 못 지킨다.

Task 16: Ruling: `_primaryAction` 을 `DpNextActionBand` 로 옮겼다. 브리프가 예로 든
「경로 만들기」 단일 버튼은 **이 화면에 없다** — 상태에 따라 아홉 갈래다
(저장하고 계속·저장 다시 시도·결과 저장 중·학습 경로로 계속·기존 경로로 계속·
경로 상태 확인 필요·경로 확인 중·경로 상태 다시 확인·새 진단 시작·필수 동의 확인).
`DpNextActionState`(ready·pending·disabled·retry)로 남김없이 옮기고 문구는 그대로
뒀다. 비용 2건: ① 밴드는 `InkWell` 이라 `widget<FilledButton>` 으로 CTA 비활성을
읽던 테스트를 밴드 상태(`state`·`onPressed`)로 읽게 고쳤다 ② 밴드는 접근성 이름에
`, 예상 결과: …` 를 붙이므로 `bySemanticsLabel('새 진단 시작')` 을 정규식으로 고쳤다.

Task 16: Ruling: 답변 실패 시 보기에 붙던 `'✓ ${option}'` 글자를 없애고 `selected`
(시안 `.opt.sel`)로 표시한다 — 글자로 상태를 만들면 스크린리더가 「체크」를 문자로
읽는다. 키(`diagnostic-option-selected-$index`)는 그대로 두어 기존 테스트가 돈다.

Task 16: Ruling: `_QuestionView` 의 `DpSteps` 는 `missionSpineEnabled` 일 때만 그린다 —
legacy 흐름(`_legacyBody`·`_LegacyPreview`)에는 단계 표시가 없었고 그 흐름은 보존
대상이다. 세 단계가 시작·문항·결과에서 각각 0·1·2 다.

Task 16: 기록: diagnostic 77 → **88 PASS** · web 전체 **1104 PASS** ·
dp_design **377 PASS** · admin 156 PASS · analyze: dp_design 0, web 1건(기존
`current_mission_controller.dart:273`). 중간에 내가 만든 lint 2건(테스트 지역변수
`_stepLabels` · 이제 안 쓰는 `flutter/widgets.dart` import)은 고쳤다. 커밋 `f03d629`.

Task 16: 기록: **기준선 영향(Task 18 에서 baseline-impact.md 로)** —
`/diagnostic` 세 화면 전부. 시작: 칩 단계 표시 → `.steps` 테두리 한 겹, 온보딩
surface 가 `DpPanel`, 트랙 드롭다운 → 보기 행 8개, 기대 결과 패널 → 키-값 3행.
문항: 단계 표시 신설, 보기 버튼 → 보기 행(라디오 원), ✓ 글자 제거.
결과: 단계 표시 신설, 패널 2곳 반경 16·12 → 카드 8, 「결과 형태 미리보기」 →
키-값, primary action → `.next` 밴드(예상 결과 문구가 새로 보인다).
**구현하지 않은 시안 요소 추가**: `dresult` 의 `.bars` 개념별 결과 — `AssessmentResult`
에 개념별 점수가 없다(백엔드 계약 변경 필요).
Task 16: complete (commits ddd4218..f03d629, tests: bash -c 'cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/apps/web && flutter test' → 00:42 +1104: All tests passed!)

## Task 17: 마이페이지 + 설정 + placeholder

Task 17: Ruling: 마이페이지에 시안의 「커뮤니티 활동」 **표를 만들지 않았다.**
실측: 이 화면의 활동 데이터는 집계 수치뿐이다 — `MyActivity(questionCount,
answerCount)` + `DashboardSummary.completedContentCount`. 제목·게시판·링크가 아예
없어 `DpWebTable` 의 행을 만들 재료가 없다(브리프가 「작성」 칼럼만 없다고 본 것보다
한 단계 더 없다). 집계 두 줄을 `DpPanel('활동')` 로 감싸는 것으로 끝냈고 문구 4종
(성공 2 · 부분실패 2)은 그대로 뒀다. 비용: 시안 `mypage` 의 활동 표는 P4 에서
구현되지 않는다 — baseline-impact.md 의 「구현하지 않은 시안 요소」에 더한다.

Task 17: Ruling: 시안의 「프로필」 키-값 사이드 패널도 **만들지 않았다.** 이 화면의
프로필은 읽기 표시가 아니라 **편집 폼**이다(자기소개·학습 목표·목표 트랙·경력 +
저장). 같은 값을 kv 로 한 번 더 보이면 한 화면에 두 번 나온다. 대신 시안 `.prof` 의
태그 자리에 그 세 값을 `DpTag` 로 요약했다. 비용: 시안의 사이드 kv 패널이 없다.

Task 17: Ruling: `.prof` 에 **이름을 넣지 못했다** — 프로필 모델(`ProfileView`)에
표시 이름 필드가 없다(avatar·bio·learningGoal·targetTrack·experienceYears 뿐).
시안의 「이름」 자리에 소개(bio)를 `titleMedium` 으로 놓고, 없으면 「소개가 아직
없어요」로 둔다. 비용: 시안보다 한 줄 적다 — 이름은 백엔드 계약이 먼저다.

Task 17: Ruling: AI 멘토 패널은 브리프대로 사이드로 옮겼다(현재 화면에 이미 있었다 —
브리프의 「없으면 만들지 않는다」 조건은 해당하지 않는다). 네 상태 분기
(Loading·Failed·Ready(active)·Ready(waitlisted))를 그대로 보존했다.

Task 17: Ruling: 설정 진입 `ListTile` → `DpRowLine` + 인라인 링크(「열기」).
`leading: Icon(Icons.settings_outlined)` 는 **제거**했다 — 시안 `.rowline` 에 선행
아이콘이 없고, `mypage_header_test` 가 그 아이콘의 부재를 단언한다(헤더에 설정
버튼을 두지 않기로 한 앞선 결정). 링크에 `semanticsLabel: '설정 열기'` 를 줬다.

Task 17: Ruling: 설정 테스트의 `find.text('로그아웃')`·`find.text('계정 삭제')`
`findsOneWidget` 을 고쳤다. 시안 `.rowline` 은 **좌측 라벨과 우측 컨트롤을 둘 다**
두므로 같은 문구가 행 이름과 버튼에 한 번씩 나온다(설정 UI 의 통상 형태다).
버튼을 특정하는 `widgetWithText(OutlinedButton, …)` + 개수 `findsNWidgets(2)` 로
바꿨다 — 문구를 비틀어 테스트를 맞추지 않았다.

Task 17: Ruling: 브리프 스니펫의 `notifier.setConsent(type, v)` 는 **없는 이름**이다.
실제는 `revokeConsent(type)` 이고 「현재 동의된 항목만 철회 가능」이라는 기존 동작이
붙어 있다(재동의는 후속). 그 동작을 그대로 옮겼다.

Task 17: 기록: 동의 행의 설명 줄은 `ConsentItemView.agreedAt`(nullable String)을 쓴다 —
`'$agreedAt 동의'`. 브리프가 이름 확인을 남겨 둔 지점이다.

Task 17: 기록: mypage+settings 17 → **22 PASS**(신설 `settings_rowline_test.dart` 4건 +
마이페이지 `.cols` 1건) · web 전체 **1109 PASS** · analyze 1건(기존
`current_mission_controller.dart:273`). 커밋 `e8f66d6`.

Task 17: 기록: **기준선 영향(Task 18 에서 baseline-impact.md 로)** —
`/settings`: 절 순서가 바뀐다(동의 관리 → 알림 → 계정 ⇒ **알림 → 동의 관리 → 계정**),
`SwitchListTile`·`ListTile` → 테두리 패널 3개 + 구분선 행, 본문 폭 760 좌측 정렬,
동의 행에 필수/선택 태그 신설, 로딩·실패 표현 교체.
`/mypage`: 카드 5장 세로 나열 → `.cols` 2열, 프로필 카드 → 배경 없는 `.prof`,
AI 멘토·설정이 사이드로, 설정 행의 선행 아이콘 제거.
`/placeholder`: 중앙 narrow 760.
**구현하지 않은 시안 요소 추가**: `mypage` 의 커뮤니티 활동 표(목록 API 없음) ·
`mypage` 의 프로필 사이드 kv(편집 폼과 중복) · 프로필 표시 이름(모델에 없음).
Task 17: complete (commits f03d629..e8f66d6, tests: bash -c 'cd /d/workspace/dpa/.worktrees/frontend-s3p4a-20260927/apps/web && flutter test' → 00:43 +1109: All tests passed!)

## Task 18: PR-C 마무리

Task 18: 기록: 변경 파일 **28개** — `packages/dp_design/{lib,test}/**`(Task 13·15·16) +
`apps/web/lib/src/features/{auth,beta,common,consent,diagnostic,mypage,settings}/**` +
`apps/web/test/**`. 설정 파일 0건. 커밋 5개(`2c38bac..e8f66d6`).

Task 18: 기록: 전 패키지 검증 — analyze: dp_design 0 · dp_core 0 · admin 0 ·
web 1건(`current_mission_controller.dart:273`). 그 1건은 `git show
origin/develop:…` 로 **develop 에도 같은 코드가 있는 것을 실측**했고 그 파일은 변경
목록에 없다(로컬 3.47 전용 린트, CI 3.44.1 은 녹색). 테스트: dp_design 377 ·
dp_core 174 · admin 156 · web 1109 전부 통과. `dart format` 28파일 0 changed.

Task 18: frontend PR **#238**. 1차 CI: `analyze-test` pass(5m17s) ·
`browser-ux` **pass**(5m23s — Task 16 의 radiogroup 우려가 발현되지 않았다) ·
`produce-atomic-pair` pass(9m5s) · 이미지 계약 2건 pass · **`perf-gate` fail(22m52s)**.

Task 18: Ruling: `perf-gate` 실패는 **측정 하네스 flake** 로 판정하고 실패 잡만
재실행했다(`gh run rerun 36368408512 --failed`). 근거 3가지: ① 실패 지점이 앱 단언이
아니라 하네스의 부트스트랩 로케이터다 —
`locator('flt-semantics-placeholder').first()` waitFor 120000ms 초과
(`tools/perf/measure.mjs:223`) ② 같은 라우트(`desktop /mentor`)의 run 1/5·2/5 가
**같은 잡 안에서 통과**했고 run 3/5 에서 멈췄다 ③ `/mentor` 는 이 PR 이 건드리지
않았고, 실측으로 **변경된 위젯을 하나도 쓰지 않는다**
(`grep -rln "DpLink|DpSteps|DpOptionRow|DpCheckRow" apps/web/lib/src/features/mentor/`
= 0건). 기존 위젯 변경은 `DpLink.semanticsLabel` 하나뿐이고 `semanticsLabel ?? text`
라 null 인 기존 호출부에서 **완전 무동작**이다(diff 전문 확인). 비용: 재실행도
실패하면 flake 가 아니라는 뜻이므로 그때는 `measure.mjs` 의 대기 조건을 파야 한다
(이 측정기는 타임아웃 이력이 있다 — 2026-09-17 PR #212).

Task 18: 기록: `perf-gate` **재실행 pass(22m37s)** — flake 판정이 실측으로 확인됐다.
PR #238 최종 CI: `analyze-test` pass(5m17s) · `browser-ux` pass(5m23s) ·
`produce-atomic-pair` pass(9m5s) · `perf-gate` pass(22m37s) ·
`web-image-config-contract` 2건 pass(7m6s·6m38s) · SKIPPED 4건
(`admin-image`·`web-image`·`web-image-release-contract`·ET13 auth). **실패 0** ·
`mergeStateStatus=CLEAN` · head `e8f66d6`. 사용자 기준(전 잡 pass/skipping·실패 0)을
만족하지만 **최종 독립 리뷰 findings 를 받기 전에는 머지하지 않는다** — Critical 이
있으면 develop 에 들어간 뒤 고치게 된다.

## 최종 독립 리뷰 (Opus) 와 수정 패스

Final review: 서브에이전트(Opus) 독립 리뷰 — Critical 0 · Important 7 · Minor 11.
보고서: 같은 폴더 `review-report.md`. 리뷰어의 최종 메시지가 두 번 한 단어로만 와서
보고서를 파일로 쓰게 지시해 받았다(다음에 서브에이전트 리뷰를 쓸 때는 **처음부터
파일 경로를 지정**한다).

Final: Ruling: 재등급 — 리뷰의 Minor 중 **5건을 Important 로 올려** 수정 패스에 넣었다.
기준은 「사용자가 겪는 결과」다: M2(보이는 폼 라벨 소실)·M4(테스트 인자를 무시해
검증했다고 믿게 만든다)·M5(실재하지 않는 색 조합을 재 계약을 못 지킨다)·M6a/b(아바타
유무를 알 수 없고 500자 소개가 머리를 차지한다)·M10b/c(세로 중앙 정렬 상실·「저장 후」
선행 조건 문구 소실). 비용: 수정 범위가 커졌다 — 대신 전부 RED→GREEN 으로 닫았다.

Final: fixed I2 (DpCheckRow 라벨 짜부심) — 처음 쓴 위젯 단독 테스트가 **판별력이
없었다**(뷰포트만 390 으로 두면 행이 전폭을 받는다 — 커밋본에서도 통과했다). 프로브로
실제 화면을 재어 `Row` 형태 **폭 38.25 · 높이 495** vs `Wrap` 형태 **187.5 · 135** 를
확인하고, 위젯 테스트는 실제 행 폭(340)으로 좁히고 화면 테스트는 폭 측정으로 강화했다.
두 테스트 모두 커밋본에서 RED(110.75 · 38.25 < 150) → 수정본에서 GREEN.

Final: fixed I1 (로그인 폭 상한) — `login-content` 캡 테스트 2건 RED→GREEN.
Final: fixed I3 (원시 ISO 타임스탬프) — 포맷 테스트 + 해석 실패 테스트 RED→GREEN.
Final: fixed I4 (즉시 제출에 라디오 역할) — `DpOptionRole` 신설. dp_design 역할 테스트
2건 + 진단 소비처 테스트 2건 RED→GREEN.
Final: fixed I7 (셸 밖 헤더 gutter) — 동의·진단 좌측선 테스트 2건 RED→GREEN.
Final: fixed M2·M4·M5·M6a·M6b·M10b·M10c — 각각 테스트 RED→GREEN(M4·M5 는 테스트 자체
수정이라 새 테스트 없이 기존 단언을 바로잡았다).
Final: fixed I5 (baseline-impact 비어 있음) — documents 레포에 PR-A·B·C 25화면 +
1:1 불가 8건 + PR-C 함정 7건을 채웠다.
Final: fixed I6 (2열 경계 오기) — 원장·baseline-impact·핸드오프 세 곳을 「900 → 840,
뒤집히는 구간 840~899」로 정정했다.

Final: Ruling: `DpCols` 의 주석과 코드 모순(리뷰 I6 의 참고 지적)은 **P4 에서 고치지
않는다.** `dp_cols.dart:10-12` 주석은 「경계를 1240 에 둔다」고 적었는데 코드는
`expanded || large`(= 840부터) 2열이다. 어느 쪽이 의도였는지에 따라 6화면의 840~1239
레이아웃이 바뀌고 그 화면들의 테스트·기준선이 함께 움직인다 — PR-C 범위 밖이고
P5 가 기준선과 함께 확정해야 한다. baseline-impact 의 「P5 이월」에 적었다.
비용: 그 구간의 의도가 확정되기 전까지 6화면의 2열 판정이 문서와 어긋난 채 남는다.

Final: Ruling: M6c(`.prof` 태그가 편집 폼과 중복)를 **고치지 않는다.** 전체 패널을 한 벌
더 만드는 것(kv 사이드 패널)과 한 줄 요약 태그 3개는 성격이 다르고, 시안 `.prof` 의
태그 자리가 바로 그것이다. 비용: 원장 Ruling 의 「중복이라 만들지 않았다」는 문장이
태그에는 적용되지 않는다는 구분을 P5 가 시안과 대조해 확정해야 한다.

Final: minor (deferred): `DpSteps` 의 단계 높이가 서로 다를 수 있다(M1).
Final: minor (deferred): `PlaceholderPage` 는 소비처가 0곳이다(M3).
Final: minor (deferred): `.prof` 태그와 편집 폼의 중복(M6c — 위 Ruling 참조).
Final: minor (deferred): 비활성 밴드가 실행 불가한 예상 결과를 읽는다(M7).
Final: minor (deferred): `DpNextActionBand` 의 `boxShadow` 가 Global Constraints 와
어긋난다 — PR-A 도 같은 위젯을 쓴다(M8).
Final: minor (deferred): 폰에서 진단 시작 CTA 까지의 스크롤 깊이를 재는 단언이 없다(M9).
Final: minor (deferred): 보기 목록 마지막 행 뒤 여분 간격 8px(M10a).
Final: minor (deferred): 탭 정지 개수를 고정하는 테스트가 없다(M11).

Final: 기록: 수정 패스 뒤 dp_design **380** · dp_core 174 · admin 156 · web **1122**
전부 통과 · analyze dp_design 0 / web 1건(기존) · format 0 changed. 커밋 `9c3bdfa`.
리뷰가 「Declined to judge」로 남긴 2건은 **CI 가 답했다** — Flutter Web 의 ARIA 매핑은
`browser-ux` pass 로, CI 핀 3.44.1 의 `SemanticsRole.radioGroup` 존재는 `analyze-test`
컴파일 성공으로 확인됐다.
