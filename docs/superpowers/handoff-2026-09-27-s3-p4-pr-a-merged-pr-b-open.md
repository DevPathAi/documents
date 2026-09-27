# 핸드오프 2026-09-27 — S3-P4 PR-A 머지 완료 · PR-B 머지 대기 · PR-C(Task 13~18) 이관

> 앞 핸드오프: `handoff-2026-09-27-s3-p3-web-widgets-merged.md`(#178). 계획: `plans/2026-09-27-s3-p4-screen-groups.md`(PR #180, 18 Task · 219 Step).
> 실행 원장 전문: `plans/2026-09-27-s3-p4-screen-groups/execution-ledger.md`(이 PR에 함께 들어온다). 기준선 영향: 같은 폴더 `baseline-impact.md`.

## 1. 좌표

| 레포 | 브랜치 | 커밋 | 상태 |
|---|---|---|---|
| frontend | `develop` | **`7670447`** | PR **#236**(PR-A) 머지 완료 — CI 전 잡 녹색 |
| frontend | `feat/s3-p4-community-screens` | **`931206c`** | PR **#237**(PR-B) **열려 있음 · CI 재실행 중** |
| documents | `develop` | `445b274` | PR #181 머지 완료 |
| documents | `develop` | PR **#182** 머지 | 기준선 영향 + 실행 원장 + **이 핸드오프**가 그 PR 로 들어왔다 |

**워크트리 `D:\workspace\dpa\.worktrees\frontend-s3p4a-20260927` 를 지우지 말 것** — 실행 원장(`.superpowers/sdd/2026-09-27-s3-p4-screen-groups/progress.md`, 판정 40여 건)이 git-ignored 로 그 안에 있다. 사본은 위 `execution-ledger.md`. 현재 그 워크트리는 `feat/s3-p4-community-screens` 를 물고 있다.

documents 워크트리 `.worktrees/documents-s3p4a-baseline` 도 남겨 두었다(PR #182 브랜치).

## 2. 완료된 것 (Task 1~12)

### PR-A — 학습 화면군 (#236, develop `7670447`)

| Task | 무엇 | 커밋 |
|---|---|---|
| 1 | dp_design 준비 — `DpCols` 신설, P3 이월 Minor 5건, `DpPageHeader({gutter})` | `dd7e0b5` |
| 2 | 오늘 화면 — Bento 4열 → `.cols` 2열, 표·kv·「왜 이 순서」·「막히면」 신설 | `2f3fa6c`·`f9d267a` |
| 3 | 학습 경로 — `ExpansionTile` → 「N주 계획」 표 + 사이드 패널 3 | `f019bae`·`b9230f4` |
| 4 | 콘텐츠 — 본문 폭 840→760, 진행률을 사이드로, `Chip`→`DpTag` | `e63b43a` |
| 5 | 실습 — 페인 테두리 2px→1px(`_IdeFrame`+`_PaneDivider`) | `ff451e7` |
| 6 | 멘토 — 맥락을 사이드로, `DpCols.stretch` 신설, 말풍선 폭 → 760 | `2efd5be` |
| 7 | PR-A 마무리 + **a11y 결함 수정** | `4332718` |

### PR-B — 커뮤니티 (#237, 미머지)

| Task | 무엇 | 커밋 |
|---|---|---|
| 8 | 목록 3종 카드 나열 → 표, 빈 상태 중복 액션 제거(P3 이월) | `f441b88` |
| 9 | 검색 중 게시판 변경 시 `q` 유지(`carryCommunityQuery`) — P3 skip 테스트를 켰다 | `9fdcb33` |
| 10 | 글 상세 `.narrow` 760 · 질문 상세 `.cols` · 「관련 질문」 신설 · `Card` 6곳 제거 | `d60a91b` |
| 11 | 작성·수정 4화면 `.narrow` 760 + **웹 앱 마지막 `AppBar` 2곳 제거** | `f7ef216` |
| 12 | PR-B 마무리 + `browser-ux` 기대값 갱신 | `931206c` |

## 3. 다음 착수점 — PR-C (Task 13~18)

브랜치: `feat/s3-p4-account-screens` (base: `develop`, **PR-B 머지 뒤** 분기)

| Task | 무엇 |
|---|---|
| 13 | dp_design 온보딩 프리미티브 3종 — `DpSteps`·`DpOptionRow`·`DpCheckRow` |
| 14 | 로그인 + 인증 콜백 — `.login` 2열 / `.narrow.center` |
| 15 | 동의 + 베타 대기 — `.narrow` 760 + `.chk` 패널 |
| 16 | 진단 3단계 — `.steps` + `.opt` + `.bars` + `.next` |
| 17 | 마이페이지 + 설정 + placeholder |
| 18 | PR-C 마무리 |

재개 명령(워크트리에서):

```bash
# PR-B 머지 확인 뒤
cd D:/workspace/dpa/.worktrees/frontend-s3p4a-20260927
git fetch origin && git checkout -b feat/s3-p4-account-screens origin/develop
"C:/Users/deepe/.claude/plugins/cache/claude-plugins-official/superpowers/6.4.1/skills/executing-plans/scripts/task-start" \
  D:/workspace/dpa/.worktrees/documents-s3p4-plan/docs/superpowers/plans/2026-09-27-s3-p4-screen-groups.md 13
```

원장(`progress.md`)은 브랜치를 바꿔도 남는다(git-ignored). Task 13 브리프는 이미 생성돼 있다.

**Task 13 브리프의 실측 필요 지점**: 브리프 자체가 `DpOptionRow` 에서 `excludeSemantics` 를 쓰면 `find.text` 로 시맨틱스를 잡을 수 없다고 적고 `container: true` + `GestureDetector(excludeFromSemantics: true)` + `MouseRegion` 으로 가라고 스스로 교정한다 — 그 교정본을 따른다.

## 4. 사용자 결정 (이 세션)

- **CI 전 잡이 pass/skipping 이고 실패 0 이면 AI 가 머지한다** — PR-A·PR-B·PR-C 모두. 머지할 때마다 잡별 결과를 근거로 보고한다.
- 실행 방식은 Native(서브에이전트 없이 컨트롤러가 직접).

## 5. CI 가 드러낸 실제 결함 1건 (수정·검증 완료)

**`/path` 의 axe `scrollable-region-focusable`(serious)** — `browser-ux`(390)와 ET13 `web-path-current-week--a11y--w320--light--text200` 이 같은 한 노드를 잡았다.

- `DpWebTable` 이 `minWidth`(640)보다 좁은 폭에서 만드는 가로 스크롤 영역에 **키보드로 닿을 수 없었다.** 표 안에 포커스 가능한 셀이 있으면 axe 가 통과하는데(오늘 화면 표는 제목이 `DpLink.title`), 「N주 계획」 표는 주차 상세 라우트가 없어 링크를 만들지 않았으므로 숨은 칼럼이 키보드 사용자에게 **완전히 막혀 있었다**. `/dashboard` 는 통과하고 `/path` 만 실패한 이유가 이것이다.
- 수정(`4332718`): 스크롤 분기에만 포커스 노드(`_ScrollFocus`) + 2px 링. **포커스 노드는 스크롤 뷰 *안*에 둔다** — 밖에 두면 웹 시맨틱스가 tabindex 를 overflow 를 가진 요소가 아니라 그 부모에 붙여 axe 가 여전히 잡고, 안에 두면 `Scrollable` 의 `ScrollAction` 이 화살표 키를 받는다.
- Task 3 의 「갈 곳 없는 링크를 만들지 않는다」 판정은 옳았고, 빠진 것은 스크롤 영역 자체의 키보드 접근이었다.

## 6. 다음 세션이 알아야 할 함정

1. **`DpPanel` 안의 Material `ListTile` 은 프레임워크 단언에 걸린다** — 패널은 색을 가진 `DecoratedBox` 이고 `ListTile` 은 가장 가까운 Material 에 잉크를 그린다. Task 3 에서 실패 7건이 전부 이 한 원인이었다. 패널 안쪽에 `Material(type: MaterialType.transparency)` 한 겹. 근본 수정(`DpPanel` 이 스스로 잉크 표면을 갖기)은 **P5 판단 사항**.
2. **같은 `ValueKey` 를 `Row`/`Column` 의 형제로 두면 `Duplicate keys found` 로 죽는다** — 키는 자체 위젯으로 감싼다.
3. **`ListView(children:)` 는 뷰포트 밖 자식을 mount 하지 않는다** — 패널 개수를 세는 테스트는 뷰포트를 키운다.
4. **테스트가 「문서가 뷰포트에 다 들어간다」에 의존할 수 있다** — `/content` 의 `_scrollPct` 는 `maxExtent <= 0` 이면 1 을 돌려주고 그 1 이 진행률 flush 를 띄운다(dwell 만으로는 절대 flush 되지 않는다).
5. **`DpCols(stretch: true)` 는 부모 높이가 유한해야 한다**(1열에서 `main` 을 `Expanded` 로 감싼다).
6. **칼럼 라벨은 게시판/표에서 나온다** — 칼럼은 행마다 다른 라벨을 가질 수 없다.
7. **컨트롤러의 `load()` 는 `ApiException` 만 잡는다** — 테스트가 맨 `Exception` 을 던지면 테스트 밖으로 샌다.
8. **CI a11y·browser-ux 실패의 상세는 잡 로그가 아니라 아티팩트에 있다** — `gh run download <run> -n leva-browser-ux-*` → `latest.json` 의 실패 시나리오 `details`. **런이 둘로 갈린다**(`produce-atomic-pair` 는 별도 런) — `artifacts[0]` 을 집으면 `.dockerbuild` 를 받아 실패한다.
9. **로컬 재현 1~5분**: 목 릴리스 웹 빌드(약 80~100초) → 핀 이미지 `mcr.microsoft.com/playwright:v1.55.0-noble` 에서 `npm ci`(네트워크, 한 번) → `--network none` 으로 `node run.mjs --dist=… [--only=axe]`. Windows 는 `MSYS_NO_PATHCONV=1` + `D:/…` 경로. **Docker 는 꺼져 있을 뿐일 수 있다** — `Docker Desktop.exe` 를 먼저 띄운다.
10. **로컬 Flutter 가 매 호출마다 `analysis_options.yaml`·`pubspec.lock` 을 다시 쓴다** — 커밋 직전마다 `git checkout --` 로 되돌린다. `git add -A` 금지.
11. **`web` analyze 경고 1건은 기존**이다(`current_mission_controller.dart:273` `unawaited_return_in_try_block`) — 로컬 Flutter 3.47 전용 린트이고 develop CI(3.44.1)는 녹색이다.
12. **`expectations.json`(browser-ux) 갱신은 실측 + PR 리뷰 승인으로만** — 그 파일의 자체 규칙이다. Task 12 에서 갱신했고 근거를 notes 에 적었다.

## 7. 구현하지 않은 시안 요소 (백엔드 계약 변경이 필요하다)

`baseline-impact.md` 의 후속 표에 있다. 요약:

- 커뮤니티 목록의 「작성」 칼럼·작성자 이름 — 서버 `PostSummaryView` 가 작성 시각도 작성자 표시 이름도 보내지 않는다
- 마이페이지 활동 표의 「작성」 칼럼 — 같은 이유
- 오늘 화면 과제 표의 설명 줄 — `WeeklyTask` 에 설명 필드가 없다
- 오늘 화면의 「12주 중 N주차」 — 오늘 화면은 `LearningPath` 를 읽지 않는다
- 질문 상세의 「이 주제 학습하기」 — 태그 ↔ 콘텐츠 추천 엔드포인트가 없다

## 8. S3 전체에서 남은 것

- **P4**: Task 13~18 (PR-C)
- **P5**: 기준선 재기록 — ET13 visual/a11y baseline 재승인(사람 단계). `baseline-impact.md` 가 그 입력이다. ET13 결정적 투영 3종(`WebContentProjection`·`WebMentorContextProjection`·`WebCommunityBoardProjection`)의 렌더가 전부 바뀌었다.
- **S3 는 P5 까지 끝난 뒤에 릴리스에 태운다** — 다음 develop→main 은 랜딩 시각이 바뀌는 릴리스다.
