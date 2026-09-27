# SDD ledger — plan: D:/workspace/dpa/.worktrees/documents-s3p3-plan/docs/superpowers/plans/2026-09-27-s3-p3-web-widgets.md

Spec: documents `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§7 P3·§8 (읽음)
Branch: feat/s3-p3-web-widgets, base origin/develop 309d0aa

## Pre-flight (공유 인터페이스 대조)

| 생산 | 소비 | 대조 결과 |
|---|---|---|
| Task 2 `DpLink.title({Key?, required String text, VoidCallback? onTap, int? maxLines})` | Task 8 `DpLink.title(text:, onTap:)` | 일치 |
| Task 8 `DpListRow(... accentColor 없음, last 추가)` | Task 9 커뮤니티 소비처 2곳 | 일치 — Task 9 가 accentColor 삭제를 담당 |
| Task 9 `DpPageHeader({title, description, actions, filters})` | Task 10 `DpPageHeader(actions:)` | 일치 |
| Task 9 `CommunityBoardHeader({board, onSelectBoard})` | Task 10 `CommunityBoardHeader(..., onCompose)` | 순차 — Task 9 가 titleMenu 를 지운 뒤 Task 10 이 onCompose 를 더한다. 충돌 없음 |
| Task 4 `DpTableColumn`·`DpTableRowSpec` | (P3 내 소비처 없음 — P4 가 쓴다) | 대조 불필요 |
| Task 1 `DpPanel` · Task 3 `DpStatusText` · Task 5~7 | (P3 내 소비처 없음) | 대조 불필요 |

경로 확인: Task 8 의 `import '../content/dp_link.dart'` 는 `lib/src/data/` 기준으로 올바르다.
토큰 확인: `DpDensity`·`DpRadius`·`DpSpacing` 은 모두 `lib/src/theme/dp_spacing.dart` 한 파일에 있다 — import 하나로 족하다.
실측 확인: `DpColors.light`(:118)·`DpColors.dark`(:153)·`DpTheme.light()`·`DpTheme.dark()` 존재. `dp_design.dart` 에 content(:47)·interaction(:34)·states(:37~46) 묶음 존재.

## 진행

Task 1: complete (commits 309d0aa..15448f7, tests: flutter test test/layout/dp_panel_test.dart → 5/5 pass)
Task 2: Ruling: 계획 테스트의 `getSemantics(find.byType(DpLink))` 는 루트 노드를 잡는다(DpLink 최외곽이 MouseRegion 이라 자체 노드가 없다) — `find.text(...)` 기준으로 고쳤다. 비용: 없음(단언 대상은 같다).
Task 2: Ruling: 계획 구현의 `Semantics(...) > GestureDetector > ExcludeSemantics(Text)` 는 노드를 두 겹으로 만든다(실측: 안쪽 tap 노드는 라벨이 빔) — `Semantics(excludeSemantics: true) > GestureDetector > Text` 로 구현을 고쳤다. 비용: 링크 내부에 별도 시맨틱스를 가진 자식을 넣을 수 없다(현재 자식은 Text 뿐이라 해당 없음).
Task 2: Ruling: 계획 테스트의 inline 단언 `decorationStyle isNull`·`height isNull` 은 테마가 값을 넣으면 깨지는 공허한 단언이라, `decorationColor`·`fontWeight` 로 바꿨다. 비용: 없음.
Task 2: complete (commits 15448f7..a6433f7, tests: flutter test test/content/dp_link_test.dart → 5/5 pass)
Task 3: complete (commits a6433f7..cf06349, tests: flutter test test/states/dp_status_text_test.dart → 4/4 pass)
Task 4: Ruling: 계획 Step 12 는 병합 시 `Semantics(explicitChildNodes: true)` 로 감싸라 했으나, 흡수하는 노드가 GestureDetector 의 것이라 바깥을 감싸도 소용없다. 행 제스처를 `excludeFromSemantics: true` 로 시맨틱스에서 제외했다 — 행 클릭은 포인터 보조 수단이고 접근성 컨트롤은 제목 링크다(시안도 행이 아니라 a.ttl 만 링크). 비용: 스크린리더 사용자는 행 아무 곳이나가 아니라 제목 링크로 이동해야 한다(시안과 같은 거동).
Task 4: complete (commits cf06349..44a82c8, tests: flutter test test/data/dp_web_table_test.dart → 11/11 pass)
Task 5: Ruling: 계획의 DpListLines 구현은 같은 `ValueKey('dp-list-line')` 을 Column 의 형제로 붙여 `Duplicate keys found` 로 죽는다(실측). 비공개 `_Line` 위젯을 끼워 키 소유 Container 들의 형제 관계를 끊었다(DpWebTable._Row 와 같은 모양). 비용: 위젯 한 겹 추가.
Task 5: complete (commits 44a82c8..390f3ce, tests: flutter test test/data/dp_list_lines_test.dart → 3/3 pass)
Task 6: complete (commits 390f3ce..4ee61c1, tests: flutter test test/data/dp_row_line_test.dart → 5/5 pass)
Task 7: complete (commits 4ee61c1..af718d4, tests: flutter test test/data/dp_key_values_test.dart → 4/4 pass)
Task 8: Ruling: Task 2 의 DpLink 가 키보드로 도달 불가임을 Task 8 착수 중 발견(기존 DpListRow 계약이 FocusableActionDetector 존재를 단언하고 있었다). 웹 링크로서 결함이라 Task 8 에 앞서 DpLink 를 고쳤다(FocusableActionDetector + 포커스 링 + 단일 시맨틱스 노드). 비용: DpLink 가 StatefulWidget 으로 무거워졌다.
Task 8: Ruling: 계획의 교체 build 는 compact(<520) 분기를 없앴으나, 기존 계약 테스트가 「좁은 폭에서 trailing 을 본문 아래로」를 단언하고 있고 시안도 이를 부정하지 않아 유지했다. 비용: 행 레이아웃 분기가 둘로 남는다(P4 에서 표로 갈아탈 때 정리 대상).
Task 8: complete (commits 045414d..db3c6fc, tests: flutter test --exclude-tags golden (dp_design) → 347/347 pass, analyze 0)
Task 9: Ruling: titleMenu 제거로 `onSelectBoard` 가 죽은 코드가 되어 함께 걷어냈다. 그 결과 **좁은 폭에서 검색 중 게시판 전환 시 검색어가 유지되지 않는다** — 유지하던 경로가 제목 메뉴뿐이었다. 셸 이동은 원래도 q 를 떨구며 그 계약은 기존 테스트가 이미 갖고 있다. 비용: 검색 중 게시판을 바꾸면 검색어를 다시 입력해야 한다(P4 에서 셸 헤더가 q 를 들고 가게 할 수 있다).
Task 9: Ruling: 계획이 몰랐던 소비처 2곳을 추가로 고쳤다 — web_community_board_projection_test 의 accentColor 단언 3건(→ 배지 단언)과 compact 제목 메뉴 테스트. 비용: 없음.
Task 9: complete (commits db3c6fc..0765a7a, tests: flutter test test/features/community (apps/web) → 188/188 pass, dp_design analyze 0)
Task 10: Ruling: 계획은 FilledButton.icon 을 썼으나 서브클래스라 find.byType 에 안 걸리고, 시안 `.btn.p` 는 아이콘이 없다 — 아이콘을 빼고 FilledButton 으로 갔다. 비용: 없음(시안에 더 맞다).
Task 10: Ruling: 빈 목록에서 같은 라벨의 액션이 둘이 된다(헤더 + 빈 상태 CTA). 하나를 지우는 것은 제품 결정이라 P3 범위 밖으로 보고 둘 다 유지했다. 비용: 빈 화면에 동일 라벨 버튼 2개 — 접근성상 권장되진 않는다(P4 에서 정리 후보).
Task 10: complete (commits 0765a7a..d002fb7, tests: flutter test test/features/community (apps/web) → 189/189 pass)

## P4 이월 (사용자 결정 2026-09-27)

- **검색 중 게시판 전환 시 검색어 유지** — P3 에서 titleMenu 와 함께 사라진 경로다. 되살리려면 셸 헤더(`DpWebShell`)의 커뮤니티 하위 목적지가 현재 `q` 를 들고 이동해야 한다. 사용자가 P4 로 넘기기로 결정했다(되돌리지 않는다).
- 빈 목록에서 같은 라벨 액션 2개(페이지 헤더 상시 버튼 + 빈 상태 CTA) 정리 — P4 후보.
- 화면 레이아웃 재구성: `cols`/`side`/`narrow`, Material `Card(` 25곳 → `DpPanel`, 커뮤니티 목록 → `DpWebTable`(칼럼 있는 표).
- **P5 기준선 재기록 대상 추가**: 커뮤니티 목록 렌더 변화(카드 → 구분선 행). P2 의 칩 폰트 변화에 이은 두 번째.

## 최종 리뷰 (독립, Opus / 보고서 = review-report.md)

Critical 0 · Important 4 · Minor 10. Review Focus 5건 판정: 1 OK(단서) · 2 조건부 · 3 OK(어포던스 결함) · 4 OK · 5 OK(라이트 대비 미달 1건).

Final: fixed apps/web/analysis_options.yaml 커밋 — git diff origin/develop HEAD 에서 소거 확인(2회차: 되돌린 직후 바로 커밋해야 한다)
Final: fixed DpKeyValues 긴 키 RenderFlex 오버플로 — '좁은 폭 + 긴 키 + 200% 배율' RED→GREEN, dp_design 346/346
Final: fixed DpWebTable 가로 스크롤 어포던스 부재 — '390px 의 가로 스크롤에는 항상 보이는 스크롤바' RED→GREEN
Final: fixed 표 헤더 textFaint(라이트 3.52:1, AA 미달) → textSecondary — '헤더 라벨은 본문 대비를 만족하는 토큰' RED→GREEN
Final: Ruling: 리뷰어 이견 3건 중 2건 수용(q 유지 계약을 skip 테스트로 보존 · 동일 라벨 버튼 단언에 P4 주석), 1건(Task 4 browser-ux 관측)은 P5 이월 목록에 추가. 비용: 없음.

### Minor (이월 — P4/P5 에서 처리)
1. `numeric: true` + `width: null` 조합에서 우측 정렬이 빠진다(`_cells` 의 Expanded 분기)
2. `DpWebTable.empty` 가 선택 파라미터라 기본 동작이 「헤더만 남기기」 — required 로 올리기 권고
3. 행 셀 개수 불일치가 RangeError 로만 드러난다 — assert 권고
4. 새 리터럴 치수 7곳(12·13·10·6·640) — `labelMedium`·`bodySmall` 로 묶거나 토큰 추가
5. `DpLink` 의 시맨틱스 `focused` 가 실제 포커스가 아니라 하이라이트 모드에 묶여 있다(touch 모드에서 어긋남)
6. `DpPanel.title` 이 자유 Widget 이라 heading+button 병합 함정이 열려 있다
7. 좁은 폭에서 `DpRowLine` 컨트롤이 우측이 아니라 좌측으로 떨어진다(Wrap spaceBetween, run 1개)
8. hover 배경 `surfaceMuted` 는 `bg` 위에서 1.046:1 — 패널 밖에 놓으면 사실상 안 보인다
9. `dp_list_row_test` 의 'FocusableActionDetector 존재' 테스트 이름이 더 이상 대상과 맞지 않는다
10. 구현 되읽기 단언 2건(`DpStatusText` 치수 · 표 칼럼 폭을 선언값으로 읽음 → `getSize` 권고)
    + DESIGN.md:177 이 `DpInteractiveCard` 를 여전히 「클릭 카드 베이스」로 가리킨다(프로덕션 소비처 0)

### P5 이월 추가
- 행 클릭이 접근성 트리에서 사라졌으므로, browser-ux 시나리오 중 「행이 클릭 대상」을 기대하는 것이 있으면 함께 고친다.
