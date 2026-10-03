# 핸드오프 2026-09-28 — S3-P4 완결(3 PR 전부 머지) · 다음 = S3-P5 기준선 재기록

> 앞 핸드오프: `handoff-2026-09-27-s3-p4-pr-a-merged-pr-b-open.md`(#182). 계획: `plans/2026-09-27-s3-p4-screen-groups.md`(PR #180, 18 Task · 219 Step).
> 실행 원장 전문: `plans/2026-09-27-s3-p4-screen-groups/execution-ledger.md`(Task 1~18 판정 전부). 기준선 영향: 같은 폴더 `baseline-impact.md` — **P5 의 입력이다.**

## 1. 좌표

| 레포 | 브랜치 | 커밋 | 상태 |
|---|---|---|---|
| frontend | `develop` | **`eaa7f77`** | PR **#238**(PR-C) 머지 — CI 전 잡 pass/skipping·실패 0 |
| frontend | (그 직전) | `2c38bac` | PR **#237**(PR-B) 머지 커밋 |
| frontend | (그 직전) | `7670447` | PR **#236**(PR-A) 머지 |
| documents | `develop` | PR **#183** 머지 | 이 핸드오프 + 기준선 영향 + 실행 원장 |

**워크트리 `D:\workspace\dpa\.worktrees\frontend-s3p4a-20260927` 를 지우지 말 것** — 실행 원장 원본(`.superpowers/sdd/2026-09-27-s3-p4-screen-groups/`, 판정 60여 건 + 로그 80여 개)이 git-ignored 로 그 안에 있다. 사본은 위 `execution-ledger.md`. 현재 그 워크트리는 `feat/s3-p4-account-screens` 를 물고 있다.

documents 워크트리 `.worktrees/documents-s3p4a-baseline`(이 PR 브랜치)과 `.worktrees/documents-s3p4-plan`(계획 읽기용)도 남겨 두었다.

## 2. S3-P4 가 끝났다 — 18 Task 전부

| PR | Task | 무엇 | 머지 |
|---|---|---|---|
| PR-A | 1~7 | dp_design 준비(`DpCols`) + 학습 5화면(오늘·경로·콘텐츠·실습·멘토) | #236 → `7670447` |
| PR-B | 8~12 | 커뮤니티 9화면(목록 3·상세 2·작성·수정 3) | #237 → `2c38bac` |
| PR-C | 13~18 | dp_design 온보딩 3종 + 계정·온보딩 9화면 | #238 → `eaa7f77` |

PR-C 커밋 5개:

| Task | 무엇 | 커밋 |
|---|---|---|
| 13 | `DpSteps`·`DpOptionRow`·`DpCheckRow` 신설 + 대비 단언 4건 | `611a6da` |
| 14 | 로그인 `.login` 2열 · 인증 콜백 `.narrow.center` | `7e0522d` |
| 15 | 동의 `.narrow` 760 + `.chk` 패널 2개 · 베타 대기 중앙 정렬 | `ddd4218` |
| 16 | 진단 3단계 `.steps` + `.opt` + `.next` | `f03d629` |
| 17 | 설정 `.rowline` 패널 3개 · 마이페이지 `.cols` · placeholder | `e8f66d6` |
| 18 | 독립 리뷰 Important 7 + 재등급 Minor 5 수정(§7) | `9c3bdfa` |

## 3. 다음 착수점 — S3-P5 (기준선 재기록)

**입력은 `baseline-impact.md` 한 파일이다.** 그 문서가 담은 것:

- 렌더가 바뀐 화면 25개(PR-A 5 · PR-B 5 · PR-C 9 + dp_design 신설분)
- ET13 결정적 투영 3종(`WebCommunityBoardProjection`·`WebContentProjection`·`WebMentorContextProjection`)이 바뀌었다 → 계약 테스트와 baseline 둘 다 영향
- `browser-ux` 시나리오 수정이 필요한/필요했던 것
- **시안과 1:1 이 되지 못한 8건** — 전부 백엔드 계약 변경이 필요하다(아래 §5)
- P3 리뷰 Minor 중 P4 가 닫지 않은 3건
- PR-A·PR-C 실행이 드러낸 함정 9건

P5 의 성격: **ET13 visual/a11y baseline 재승인은 사람 단계다.** P1 의 홈 미러 재기록(`review id tokens-mirror-2-0-0-20260926`) 때 확립한 절차를 따른다 — `--update-snapshots=all` 만 따로 돌려 미리보기 → `git checkout` 되돌림 → 승인 → 정식 updater(렌더가 결정적이라 해시 동일).

**S3 는 P5 까지 끝난 뒤에 릴리스에 태운다** — 다음 `develop`→`main` 은 랜딩 시각이 바뀌는 릴리스다.

## 4. PR-C 에서 실측이 계획을 뒤집은 것 (계획 본문의 Ruling 표를 갱신해야 하는 내역)

원장에 `Ruling:` 으로 전부 남겼다. 계획을 읽는 다음 사람이 알아야 할 것만:

1. **계획의 `MouseRegion` + `GestureDetector` 형태는 키보드가 닿지 않는다.** 그 형태로 구현해 테스트를 돌려 RED 를 실증했다(Tab 뒤 `primaryFocus` 가 `_FocusScopeWithExternalFocusNode` — 포커스가 라우트 스코프에 머문다). P3 의 `DpLink` 와 같은 결함이라 같은 처방(`FocusableActionDetector`)을 썼다. 라디오·동의 체크는 폼 컨트롤이라 선택이 아니다.
2. **`Semantics(container: true)` 만으로는 라벨이 올라오지 않는다** — `MergeSemantics` 한 겹이 필요하다. 계획은 이 지점을 스스로 한 번 교정했지만(브리프에 교정문이 있다) 그 교정본도 부족했다.
3. **트랙 선택은 라디오가 아니라 `DropdownButtonFormField`** 였고 트랙은 **8개**(시안 예시 3개)다. `trackDescriptions` 는 존재하지 않는다.
4. **문항 보기는 「고른 뒤 제출」이 아니라 누르는 즉시 제출**이다. 1차 구현은 라디오 시맨틱스를 유지했지만 **독립 리뷰(I4)가 그것을 반박했다** — 라디오는 「고른 뒤 확정」을 약속하는데 그 화면에는 확정 단계가 없고, 정상 흐름에서 아무것도 `checked` 가 되지 않는다(답변 실패 때만 선택 상태가 남는다). `DpOptionRow` 에 `DpOptionRole`(radio·button)을 더해 **문항은 button, 트랙은 radio** 로 갈랐다. 트랙 묶음만 `SemanticsRole.radioGroup` 으로 감싼다(axe `aria-required-parent` 대비 — `browser-ux` 통과로 확인).
5. **진단 결과에 「경로 만들기」 단일 버튼이 없다** — 상태에 따라 아홉 갈래다. `DpNextActionState`(ready·pending·disabled·retry)로 남김없이 옮겼다.
6. **계획이 로그인의 `brandRow`·테마 토글을 통째로 지웠다** — 기존 테스트가 단언하는 기능이고 셸 밖 화면의 유일한 제품 정체성이라 유지했다. compact 에서 스토리를 접는 기존 동작도 유지했다.
7. **동의 항목은 4개가 아니라 5개**이고 필수 2 / 선택 3 사이에 출생 연도 필드가 있다 — 단일 패널이 아니라 두 패널로 나눴다.
8. **계획의 「2열 배치」 테스트는 판별력이 0 이었다** — 현재 코드도 1280 에서 스토리가 좌측이라 그냥 통과했다. 시안이 실제로 바꾸는 것(`.flow` 제목+설명 목록)을 단언해 판별력을 만들었다.
9. **`DpWindowClass.expanded` 는 840~1239 다** — 「2열 경계 900 → 1240」이라고 적었던 앞선 기록이 틀렸다(독립 리뷰 I6 이 잡았다). 구현은 계획대로였고 기록만 틀렸다. 실제 뒤집히는 구간은 **840~899** 이고, ET13 기준선 폭 어디에도 걸리지 않는다.
10. **`SemanticsFlag` 는 이 Flutter 에 없다** — `containsSemantics` 는 deprecated 이고 `flutter analyze` 가 info 를 치명으로 다룬다. 대체 매처 **`isSemantics`** 를 쓴다.

## 5. 구현하지 않은 시안 요소 8건 (전부 백엔드 계약이 먼저다)

`baseline-impact.md` 의 표가 정본이다. 요약:

| 시안 요소 | 왜 못 했는가 |
|---|---|
| 커뮤니티 목록의 「작성」 칼럼·작성자 이름 | `PostSummaryView` 8필드에 작성 시각도 작성자 표시 이름도 없다 |
| 오늘 화면 과제 표의 설명 줄 | `WeeklyTask` 에 설명 필드가 없다 |
| 오늘 화면의 「12주 중 N주차」 | 오늘 화면이 `LearningPath` 를 읽지 않아 총 주차 수를 모른다 |
| 질문 상세의 「이 주제 학습하기」 | 태그 ↔ 콘텐츠 추천 엔드포인트가 없다 |
| 진단 결과의 `.bars` 개념별 결과 | `AssessmentResult` 가 `diagnosedLevel`·`confidenceWeight` 둘뿐이다 |
| 마이페이지의 커뮤니티 활동 **표 전체** | 활동 데이터가 집계 수치뿐이고 제목·게시판·링크가 **아예 없다**(「작성」 칼럼만 없는 것이 아니다) |
| 마이페이지 `.prof` 의 표시 이름 | `ProfileView` 에 이름 필드가 없다 |
| 마이페이지의 프로필 사이드 kv | (데이터는 있다) 바로 옆 편집 폼이 같은 값을 보여줘 한 화면에 두 번 나온다 — 판단으로 만들지 않았다 |

## 6. 다음 세션이 알아야 할 함정 (PR-C 추가분)

`baseline-impact.md` §「PR-C 실행이 드러낸 함정」에 7건이 있다. 그중 가장 값비싼 셋:

1. **`MaterialApp` 은 뷰에서 자기 MediaQuery 를 만든다** — 바깥에 `MediaQuery` 를 씌워 폭·배율을 주는 테스트는 **조용히 무효**다. `tester.view.physicalSize` / `tester.platformDispatcher.textScaleFactorTestValue` 를 쓴다(레포가 `dp_cols_test.dart` 주석에 이미 적어 둔 함정인데 계획의 브리프가 그 함정에 빠진 코드를 담고 있었다).
2. **`context.appTokens` 는 테마 확장을 요구한다**(`Theme.extension<AppTokens>()!`) — 리터럴 폭을 토큰으로 바꾸면 `theme:` 없이 띄운 기존 테스트가 `_TypeError` 로 죽는다. 그 화면의 **모든** 테스트 호스트에 `theme: DpTheme.light()` 를 줘야 한다.
3. **`DpNextActionBand` 는 `InkWell` 이고 접근성 이름에 `, 예상 결과: …` 를 붙인다** — `widget<FilledButton>` 로 CTA 를 읽던 테스트와 `bySemanticsLabel('<라벨>')` 단언이 함께 깨진다. 밴드로 옮길 때 그 두 형태를 먼저 찾는다.

그리고 **`perf-gate` 의 측정 하네스는 타임아웃 flake 이력이 있다**(2026-09-17 PR #212 에서 한 번 고쳤다). PR-C 1차 CI 에서 `desktop /mentor run 3/5` 가 `locator('flt-semantics-placeholder')` 120초 초과로 죽었는데, 같은 라우트의 run 1·2 가 같은 잡에서 통과했고 `/mentor` 는 PR-C 가 건드리지 않았으며 변경된 위젯을 하나도 쓰지 않는다(grep 0건). 실패 잡만 재실행해 해소했다. **판정 근거를 원장에 남겼다 — 다음에 같은 실패를 보면 먼저 이 세 가지를 확인한다.**

## 7. 독립 리뷰 (Opus) — Critical 0 · Important 7 · Minor 11

보고서 전문은 워크트리의 `.superpowers/sdd/2026-09-27-s3-p4-screen-groups/review-report.md`(git-ignored) 에 있다. 리뷰가 **기능 손실 0** 을 원본과 한 갈래씩 대조해 확인한 것 셋: 진단 `_primaryAction` 9갈래(라벨 9개 동일·콜백 누락 0·중복 제출 불가) · 동의 제출 payload(`_ConsentKind.values` 전량 순회로 UI 구조와 무관) · 5화면의 상태 분기 전부 보존.

**Important 7건 + 재등급한 Minor 5건을 한 패스로 고쳤다**(커밋 `9c3bdfa`):

| # | 무엇이 잘못이었나 | 어떻게 고쳤나 |
|---|---|---|
| I1 | 로그인이 480 캡을 없애 1920px 에서 버튼이 **820px** 로 늘어났다. bare 라우트라 셸이 캡을 못 준다 | 화면이 `contentMaxWidth`(1120) 를 직접 두고 1열 분기 패널은 `readableMaxWidth`(760) 로 묶음 |
| I2 | `DpCheckRow` 의 non-flex `trailing` 이 주축 무한 제약으로 측정돼 390px·200% 에서 라벨이 **폭 38.25 · 높이 495**(글자당 한 줄)로 눌렸다(실측) | `DpRowLine` 과 같은 `Wrap` 으로 → 187.5 · 135. 200% 테스트도 폭 측정으로 강화 |
| I3 | 설정이 원시 ISO 문자열을 사용자 문구로 그렸다(`2026-07-01T09:00:00Z 동의`) | 현지 시각 `2026.07.01 동의`, 해석 실패 시 설명 생략 |
| I4 | 즉시 제출인 문항 보기가 라디오를 선언했다 | `DpOptionRole` 신설 — 문항 button / 트랙 radio |
| I5 | `baseline-impact.md` 가 플레이스홀더뿐이었다(P5 의 입력 계약 미충족) | 이 PR 로 채웠다(PR-A·B·C 25화면 + 1:1 불가 8건 + 함정) |
| I6 | 「2열 경계 900 → 1240」 기록이 틀렸다 | `expanded` = 840~1239 로 정정, 뒤집히는 구간 840~899 명시. `DpCols` 주석/코드 모순은 P5 이월 |
| I7 | 셸 밖 화면의 `DpPageHeader` 가 `gutter:false` 로 x=0 에 붙어 좌측선이 3개였다 | `/consent`·`/diagnostic` 에 `gutter: true` |
| M2 | 드롭다운의 보이는 라벨 '진단할 트랙' 이 사라졌다 | 보이는 제목 + `ExcludeSemantics`(그룹 이름과 중복 방지) |
| M4 | 테스트 헬퍼가 `textScaler` 인자를 무시하고 상수 2 를 썼다 | 인자를 그대로 사용 |
| M5 | 대비 테스트가 실재하지 않는 조합을 쟀다(`textSecondary` on `accentSoft`) | 비현재 단계의 실제 배경 `surface` 로 |
| M6 | 아바타 유무 문구가 사라졌고 500자 소개가 머리에서 무제한 렌더됐다 | 문구 복원 + `maxLines: 3` |
| M10 | 베타가 세로 중앙 정렬을 잃었고 「저장 후」 선행 조건 문구가 사라졌다 | `Center` 복원 + 문구 복원 |

**P5 로 이월한 Minor 9건** (전부 보고서에 근거가 있다):

- **M1** `DpSteps` 의 단계가 서로 다른 높이를 가질 수 있다(`crossAxisAlignment` 미지정 → 기본 center. 시안 `.steps` 는 CSS `align-items: stretch`). 라벨이 줄바꿈하는 폭에서만 드러난다.
- **M3** `PlaceholderPage` 는 레포에 소비처가 0곳이다 — 계획 대조표가 실재하지 않는 화면 한 줄을 잡고 있었다.
- **M6c** `.prof` 의 태그 3개가 아래 편집 폼의 같은 3필드를 반복한다. 원장 Ruling(「kv 패널은 중복이라 만들지 않았다」)과 논리가 어긋난다는 지적 — **판단으로 유지했다**: 전체 패널 중복과 한 줄 요약 태그는 성격이 다르고, 시안 `.prof` 의 태그가 그 자리다. P5 가 시안과 대조해 확정한다.
- **M7** 비활성 밴드가 사용자가 실행할 수 없는 예상 결과를 읽는다(`saved && pathBranch == unknown`).
- **M8** `DpNextActionBand` 가 `boxShadow` 를 갖는다 — Global Constraints 의 「그림자 금지」와 어긋난다. PR-A 의 `.next` 도 같은 위젯이라 P5 범위다.
- **M9** 진단 시작 화면이 폰에서 CTA 를 약 1.5화면 아래로 밀지만 그 깊이를 재는 단언이 없다(트랙 8개 때문).
- **M10a** 보기 목록 마지막 행 뒤에 여분 간격 8px.
- **M11** 탭 정지 **개수**를 고정하는 테스트가 없다 — `ExcludeFocus` 를 지워 체크박스가 다시 별도 정지를 가져도 테스트가 통과한다.
- 리뷰가 「Declined to judge」로 남긴 2건은 **CI 가 답했다**: Flutter Web 의 ARIA 매핑(axe) → `browser-ux` pass · CI 핀 3.44.1 에 `SemanticsRole.radioGroup` 존재 → `analyze-test` 컴파일 성공.

## 8. 검증 기록 (PR-C)

- analyze: dp_design 0 · dp_core 0 · admin 0 · web 1건(`current_mission_controller.dart:273` `unawaited_return_in_try_block` — `origin/develop` 에도 있는 기존 코드이고 로컬 3.47 전용 린트다. CI 3.44.1 은 녹색)
- 테스트(수정 패스 뒤): dp_design **380** · dp_core **174** · admin **156** · web **1122** 전부 통과
- `dart format` 0 changed · 변경 파일에 설정 파일 0건
- 390px 가로 넘침 없음 · 200% 배율에서 **라벨 폭을 직접 측정**(동의) · `DpSteps` 현재 단계 대비를 라이트·다크 둘 다 측정해 AA 확인
- CI 1차: `analyze-test` pass(5m17s) · `browser-ux` **pass**(5m23s) · `produce-atomic-pair` pass(9m5s) · 이미지 계약 2건 pass · `perf-gate` 1차 fail(하네스 flake) → 재실행 **pass**(22m37s). 수정 패스 뒤 2차 CI 결과는 아래 §9.

## 9. 수정 패스 뒤 2차 CI (머지 근거)

머지 커밋 `eaa7f77`. head `9c3bdfa` 에서 **실패 0 · `mergeStateStatus=CLEAN`**:

| 잡 | 결과 | 시간 |
|---|---|---|
| `analyze-test` | pass | 4m9s |
| `browser-ux` | **pass** | 5m43s |
| `perf-gate` | pass | 22m49s |
| `produce-atomic-pair` | pass | 7m18s |
| `web-image-config-contract` (off/on) | pass | 7m54s · 8m54s |
| `admin-image`·`web-image`·`web-image-release-contract`·ET13 auth | skipping | 0 |

`browser-ux` 가 **역할 변경 뒤에도 통과**한 것이 중요하다 — 문항 보기를 라디오에서
버튼으로 바꾸고 그 묶음의 `SemanticsRole.radioGroup` 을 걷어냈는데 axe 가 통과했다.
트랙 묶음의 radioGroup 은 남아 있고 역시 통과한다.
