# 핸드오프 2026-09-27 — S3-P3 공용 위젯 웹화 머지 완료 + admin 셸 시맨틱스 후속 처리

> 앞 문서 `handoff-2026-09-26-s3-p2-root-causes-fixed.md`(#176)가 §5 후속 과제로 남긴 admin 결함을 먼저 닫고, S3-P3 을 계획·실행·리뷰까지 완주했다.

## 1. 결론 먼저

| | |
|---|---|
| frontend `develop` | **`92f8284`** (PR #235 머지, 15커밋) |
| 그 직전 | `309d0aa` (PR #234 = admin 셸 시맨틱스 수정) |
| documents `develop` | **`96b8ae8`** (PR #177 = P3 계획) |
| 전 패키지 테스트 | admin 156 · web 1011(+1 skip) · dp_design 346 · dp_core 174 |
| CI | 6잡 전부 pass — `analyze-test` 4m54s · `browser-ux` 5m17s · `perf-gate` 22m39s · `produce-atomic-pair` 9m6s · `web-image-config-contract` ×2 |
| 독립 리뷰 | Critical 0 · Important 4(전부 수정) · Minor 10(이월) |

**다음 착수점 = S3-P4(화면군별 개편 3 PR).**

## 2. PR #234 — admin `DpAppShell` 도 같은 시맨틱스 결함이었다

P2 에서 `DpWebShell` 에 넣은 것과 **같은 한 줄**이다. `ShellRoute` 가 넘기는 중첩 Navigator 의 `ModalBarrier`(`BlockSemantics`)가 **먼저 그려진 형제**를 지운다. `DpAppShell` 은 `Row[DpNavRail, Expanded(Column[DpChromeBar, Expanded(content)])]` 이라 레일도 크롬바도 본문보다 먼저 그려져 **둘 다 사라졌다** — `DpWebShell` 은 푸터가 본문 뒤라 살아남았지만 여기는 살아남는 형제가 하나도 없었다.

본문을 `Semantics(container: true, explicitChildNodes: true)` 로 감쌌다. 새 테스트 4건이 수정 전 **4/4 red** 임을 실측했다(수정본을 되돌려 재확인 — 정규식으로 바꾼 단언까지 red 를 봤다).

★부수 발견: 펼친 레일 항목의 시맨틱스 라벨이 `'대시보드\n대시보드'` 로 **중복**된다. `DpNavRail` 이 `Semantics(label:)` 과 보이는 `Text` 를 함께 두어 병합된 결과다. 이번 결함과 원인이 다른 **기존 develop 의 별개 문제**라 손대지 않고 테스트에서 정규식으로 받았다 — 미해결 과제다.★

## 3. PR #235 — S3-P3

계획: `plans/2026-09-27-s3-p3-web-widgets.md`(11 Task). 치수는 시안 정본(Artifact `DWi8kMV6QcAzBEQwbrNPNd` v2)의 CSS 에서 직접 옮겼다 — 프레임 기본이 `data-hit="24"`(촘촘)라 행 여백 **8**(`DpDensity.rowPadding`).

| 구분 | 대상 |
|---|---|
| 신설 7 | `DpPanel`·`DpWebTable`·`DpListLines`·`DpRowLine`·`DpKeyValues`·`DpLink`(title/inline)·`DpStatusText` |
| 변경 2 | `DpListRow`(카드 → 구분선 행, `accentColor` 제거·`last` 추가) · `DpPageHeader`(`titleMenu` 제거) |
| 제거 1 | 커뮤니티 FAB → 페이지 헤더 액션 |

**`DpDataTable` 을 재사용하지 않았다** — admin 전용 `data_table_2` 래퍼이고 `TableBorder.all` 로 세로 테두리를 그리는데 시안의 표에는 세로선이 없다. admin 4화면이 쓰므로 존치한다.

## 4. 구현 중 실측이 뒤집은 것 — 계획에 없던 결함 3건

### ① `DpLink` 가 키보드로 도달 불가였다

Tab 이 건너뛰고 Enter 도 안 먹었다(`primaryFocus` 가 라우트 스코프에 머물렀다). **기존 `DpListRow` 계약이 `FocusableActionDetector` 존재를 단언하고 있어서 드러났다** — 그 테스트가 없었으면 통과했을 것이다. `FocusableActionDetector` + 시안의 2px 포커스 링을 넣었다.

### ② 행 제스처가 셀 시맨틱스를 삼킨다

`GestureDetector` 의 시맨틱스 노드가 셀 조각을 흡수해 행 전체가 `'제목 A\n7\n어제'` 한 덩어리가 됐다. **대조군이 같은 표 안에 있었다** — 헤더는 그 노드가 없어 셋으로 남았다. `excludeFromSemantics: true` 로 뺐다. 행 클릭은 포인터용 보조 수단이고 접근성 컨트롤은 제목 링크다(시안도 `a.ttl` 만 링크).

★계획이 지시한 `Semantics(explicitChildNodes: true)` 로 감싸기는 **소용없다** — 흡수하는 노드가 GestureDetector 의 것이라 바깥을 감싸도 그대로다.★

### ③ 시맨틱스 노드 두 겹 → `MergeSemantics` 는 라벨을 더럽힌다

`Semantics > GestureDetector` 는 라벨 빈 tap 노드를 따로 만든다. 합치려고 `MergeSemantics` 를 썼더니 이번엔 라벨이 `'이용약관\n'` 이 됐다(빈 자식 조각이 붙는다). 세 번째 모양 — `Semantics` 가 `focusable`·`focused` 를 **직접 선언**하고 자식 subtree 를 `excludeSemantics` 로 가리는 것 — 으로 갔다.

## 5. 독립 리뷰가 잡은 Important 4건 (전부 수정)

보고서: 워크트리의 `.superpowers/sdd/2026-09-27-s3-p3-web-widgets/review-report.md`(git-ignored).

1. **`apps/web/analysis_options.yaml` 이 커밋돼 있었다.** 계획 Global Constraints 가 커밋 금지로 못 박은 파일인데 `git add -A apps/web` 로 쓸려 들어갔고, 확인 단계에서 **파일 개수만 세고 목록을 안 봤다.** ★1차 되돌림이 무효였다 — 되돌린 뒤 `flutter test` 를 돌리자 로컬 Flutter 3.47 이 같은 블록을 다시 써 넣었다. **되돌린 직후 다른 명령 없이 바로 커밋해야 한다.**★
2. **`DpKeyValues` 가 긴 키에서 깨진다.** `Row` 는 비유연 자식에게 주축 제약을 무한대로 준다 → 280px 패널 + 200% 배율에서 RenderFlex 오버플로로 값이 통째로 사라졌다. 키를 `Flexible` 로.
3. **390px 에서 표가 잘리는데 표시가 없었다.** Flutter 는 shift+휠에만 가로 스크롤을 준다. ★`DpScrollbar` 가 레포에 정확히 이 용도로 이미 있었다 — 안 찾아봤다.★ `StatefulWidget` 으로 바꿔 `ScrollController` 를 공유한다.
4. **표 헤더가 WCAG AA 미달.** `textFaint` 는 라이트 **3.52:1**. 시안 `th` 가 실제로 `--faint` 를 지정하지만 `DpColors` 자신이 "본문 텍스트로 쓰지 않는다"고 못 박은 토큰이고, 칼럼 라벨은 장식이 아니다 → `textSecondary`(5.93:1). ★다크는 5.18:1 로 통과한다 — 다크만 봤으면 놓쳤다.★

리뷰어 이견 2건 수용: 삭제했던 「게시판 전환 시 q 유지」 테스트를 `skip: true` 로 되살려 계약을 보존했고(복원은 P4), 동일 라벨 버튼 2개 단언에 P4 이월 주석을 달았다.

## 6. 행동 변화 — 사용자 결정으로 P4 이월

**좁은 폭에서 검색 중 게시판을 바꾸면 검색어가 유지되지 않는다.** `titleMenu` 를 없애자 그것이 유일한 소비처이던 `onSelectBoard` 가 죽은 코드가 됐고, 셸 이동은 원래도 `q` 를 떨군다(기존 테스트 「셸 이동으로 q가 사라지면 …」가 그 계약).

복원 지점 = 셸 헤더(`DpWebShell`)의 커뮤니티 하위 목적지가 현재 `q` 를 들고 이동하게 한다. 셸이 할 일이라 위젯 층인 P3 범위 밖이다.

## 7. 방법으로 남길 것

- ★**되돌림은 되돌린 직후 커밋한다.** 로컬 툴이 파일을 쓰는 종류라면, 되돌리고 나서 테스트 한 번만 돌려도 원상복구된다. 1차 시도가 이 때문에 무효였다.★
- ★**`git add -A <경로>` 를 쓰지 말라.** 로컬 Flutter 3.47 이 `analysis_options.yaml` 3개와 `pubspec.lock` 을 명령마다 고친다(CI 는 3.44.1 핀). 명시 경로로만 add 하고, 검증은 개수가 아니라 **`git diff origin/develop HEAD --name-only` 목록**으로 한다.★
- ★**대조군은 같은 화면 안에 있을 수 있다.** 표 행이 한 덩어리로 읽힐 때, 같은 표의 헤더가 셋으로 남은 것이 원인을 가리켰다.★
- ★**다크만 보면 라이트 대비를 놓친다.** 그 반대도 마찬가지다 — 대비는 두 테마 모두 잰다.★
- ★**`python` 은 스텁이다(rc0·무출력). `py` 를 써라.** 패치 스크립트가 조용히 아무것도 안 하고 성공처럼 보였다.★
- ★**`dart format <디렉터리>` 는 무관한 파일까지 재포맷한다.** 로컬 3.47 과 CI 3.44 의 포매터가 4개 파일에서 갈린다 — 내 파일만 지정해 포맷한다.★
- ★**같은 `ValueKey` 를 형제로 두면 `Duplicate keys found` 로 죽는다.** 항목을 비공개 위젯 한 겹으로 감싸 형제 관계를 끊는다(`DpWebTable._Row` 가 통과한 이유).★
- ★`testWidgets` 의 `skip` 은 `bool` 이다(`package:test` 의 String 형태가 아니다).★
- ★`find.byType` 은 **정확한 런타임 타입**만 잡는다 — `FilledButton.icon` 은 서브클래스라 안 걸린다.★
- ★서브에이전트가 결과 본문 없이 두 번 종료했다. **보고서를 파일로 쓰게** 해 전달 경로를 우회했다.★

## 8. 이월

### P4 (화면군별 개편)
- 검색 중 게시판 전환 시 **검색어 유지 복원**(skip 테스트가 계약을 들고 있다)
- 빈 목록에서 같은 라벨 액션 2개 정리(헤더 상시 버튼 + 빈 상태 CTA — 접근명이 같아 스크린리더로 구분 불가)
- 화면 레이아웃: `cols`/`side`/`narrow`, Material `Card(` **25곳** → `DpPanel`, 커뮤니티 목록 → 칼럼 있는 `DpWebTable`
- 리뷰 Minor 10건(원장 `progress.md` 의 「Minor (이월)」 절)

### P5 (기준선 재기록)
- **커뮤니티 목록 렌더 변화**(카드 → 구분선 행) — P2 의 칩 폰트 변화에 이은 두 번째
- 행 클릭이 접근성 트리에서 사라졌으므로, browser-ux 시나리오 중 「행이 클릭 대상」을 기대하는 것이 있으면 함께 고친다

### 범위 밖 미해결
- `DpNavRail` 의 레일 항목 라벨 중복(`'대시보드\n대시보드'`) — develop 에 있던 기존 결함
