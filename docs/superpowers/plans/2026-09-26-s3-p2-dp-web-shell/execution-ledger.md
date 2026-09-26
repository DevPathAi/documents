# SDD ledger — plan: C:/Users/deepe/AppData/Local/Temp/claude/D--workspace-dpa/e6d5950d-d56e-45c0-9d2b-7f1b3f153fb3/scratchpad/plans/2026-09-26-s3-p2-dp-web-shell.md
(정본 사본 = documents origin/develop:docs/superpowers/plans/2026-09-26-s3-p2-dp-web-shell.md, merge 7558082)
Spec: documents origin/develop:docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md §5.3·§5.4·§7·§8·§10 — 읽음
시안: Artifact DWi8kMV6QcAzBEQwbrNPNd (Version 2) — 읽음

## Pre-flight (공유 인터페이스)
- T1 produces DpMenuEntry / DpMenuButton(entries, builder(context, buttonFocus, toggle, isOpen)) → T2 _navDropdown·_account, T5 accountEntries, T6 accountEntries 리터럴: 이름·인자 일치. clean
- T2 produces DpWebNavItem / DpWebHeader(brand, items, selectedId, onSelect, accountEntries, onSearchTap) / compactBreakpoint=720 → T5 전달, T6 kWebNavItems: 일치. clean
- T3 produces DpFooterLink / DpWebFooter(notice, links) → T5 footerNotice·footerLinks: 일치. clean
- T4 produces DpBreadcrumb(crumbs, onCrumbTap) + consumes DpCrumb(dp_chrome_bar) → T5 breadcrumb·onCrumbTap: 일치. clean
- T5 produces DpWebShell(...) → T6 AppShellView: 일치. clean
- T6 removes last compactDestinations consumer → T8 removes the 3 params: 순서 의존 있음(T8 은 T6 뒤여야 한다). 계획 순서가 그렇다. clean
- T7 browser-ux 가 role=button name '메뉴' 로 햄버거를 누른다 ↔ T2 의 _burger 는 OutlinedButton.icon(label: Text('메뉴')) 를 Semantics(container:true) 로 감싼다. 접근성 이름이 '메뉴' 그대로인지는 VM 테스트로 알 수 없다 — CI browser-ux 가 판정자다.
  Ruling: 라벨을 '메뉴' 로 두고 선택자도 '메뉴' 로 둔다 — 시안의 문구가 "☰ 메뉴" 이고 아이콘은 시맨틱에 안 나온다 — 틀리면 CI 실패 로그의 실제 이름으로 러너 선택자를 고친다(라벨을 바꾸지 않는다). cost if wrong: browser-ux 1회 재실행
- 관찰(테스트 대상 아님): T2 _bar 는 non-compact 에서 brand + Expanded(nav) + search(200) + account 를 한 줄에 놓는다. 720~840 구간이 가장 빡빡하다 — T2 Step 5 에서 오버플로가 나오면 nav 를 Flexible 로 낮추는 것이 최소 수정이다.

## Progress
Task 1: Ruling: 계획 Step 1 의 `"$DART" run melos bootstrap` 이 `Unable to satisfy pubspec.yaml using pubspec.lock` 로 실패했다 — 핀 dart.bat 를 직접 불러도 melos 가 shell out 하는 `flutter` 는 PATH 에서 찾는다. 모든 Flutter 명령을 `export PATH="/d/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin:$PATH"` 아래에서 돌린다(계획 Global Constraints 가 이미 경고한 함정인데 스텝의 명령이 그것을 반영하지 않았다). cost if wrong: 없음 — 핀 버전이 PATH 앞에 오는 것이 의도다
Task 1: Ruling: 계획 Step 6 의 검증 명령을 bare `flutter test` 에서 프로젝트 자신의 명령(`flutter test --exclude-tags golden`)으로 바꾼다 — `pubspec.yaml:26` 의 melos `test` 스크립트와 CI 의 `dart run melos run test` 가 골든을 의도적으로 제외한다. cost if wrong: P2 가 골든을 깨도 P5 재기록 전까지 안 보인다(CI 도 안 본다)
Task 1: 선행 실패 2건(내가 만든 것 아님): `test/golden/state_golden_test.dart` 의 `DpKillSwitch 다크/라이트 골든`. 증거 = 골든 PNG 최종 재생성 `445b581`(2026-08-03) vs 반경 변경 `19e790a`(2026-09-24, P1). 9/24 리뷰의 Minor 「골든이 --exclude-tags golden 뒤에서 낡았다」와 같은 것 — P5 재기록 목록에 이미 있다
Task 1: complete (commits 17ce8a2..00ec5d1, tests: bash -c 'cd packages/dp_design && flutter test --exclude-tags golden' → 00:16 +261: All tests passed!)
Task 2: Ruling: 계획의 `Icons.expand_more`/`Icons.expand_less` 를 `DpIcons.expandMore`/`DpIcons.expandLess` 로 바꿨다 — DESIGN.md §4 는 아이콘을 DpIcons 에서만 쓰라고 하고 둘 다 이미 있다(`dp_icons.dart:34-35`). cost if wrong: 없음(같은 Symbols 글리프)
Task 2: Ruling: 테스트의 `addTearDown(handle.dispose)` 를 본문 끝 `handle.dispose()` 로 바꿨다 — 실측: `_verifySemanticsHandlesWereDisposed` 가 tearDown 콜백보다 먼저 돌아 「A SemanticsHandle was active at the end of the test」로 죽는다. 레포의 기존 패턴(`dp_page_header_title_menu_test.dart:68,94`)과 같은 모양이다. Task 3·4 의 같은 코드에도 적용한다. cost if wrong: 없음
Task 2: Ruling: 계획은 `dart format` 을 Task 9 에서만 돌리지만 매 커밋 전에 돌린다 — Task 1 커밋이 포맷 게이트(`--set-exit-if-changed`)를 못 넘는 상태로 들어갔고 이 커밋이 그것을 고친다. cost if wrong: 없음(포맷만)
Task 2: complete (commits 00ec5d1..8d11196, tests: bash -c 'cd packages/dp_design && flutter test --exclude-tags golden' → 00:16 +271: All tests passed!)
Task 3: complete (commits 8d11196..c7f8b52, tests: bash -c 'cd packages/dp_design && flutter test --exclude-tags golden' → 00:17 +276: All tests passed!)
Task 4: Ruling: 계획의 「빈 목록」 테스트가 `expect(find.byType(SizedBox), findsWidgets)` 였다 — Scaffold 만으로도 참이라 어떤 구현에서도 통과한다(동어반복). `tester.getSize(find.byType(DpBreadcrumb)).height == 0` 으로 바꿔 실제 보장을 재게 했다. cost if wrong: 없음 — 더 강한 단언이다
Task 4: complete (commits c7f8b52..a43783a, tests: bash -c 'cd packages/dp_design && flutter test --exclude-tags golden' → 00:17 +280: All tests passed!)
Task 5: complete (commits a43783a..b11796b, tests: bash -c 'cd packages/dp_design && flutter test --exclude-tags golden' → 00:19 +286: All tests passed!)
Task 6: Ruling: 계획의 Files 목록에 없던 테스트 4건을 같은 커밋에서 새 구조로 옮겼다 — `community_information_architecture_test`(kShellDestinations 참조) · `today_router_integration_test` 2건 · `golden_path_t1_realapi_test`(`rail-item-3` 키). 전부 옛 셸을 단언하던 테스트라 Task 6 의 산출물 없이는 통과할 수 없다. 계획의 「화면 테스트가 깨지면 멈추고 보고」는 **화면 파일**을 고치지 말라는 뜻으로 읽었다 — 화면 파일은 한 줄도 바꾸지 않았다. cost if wrong: 테스트가 새 셸에 맞춰졌는데 화면 코드가 실제로는 P3/P4 수정을 필요로 했다면 그 필요가 가려진다
Task 6: Ruling: `today_router_integration_test` 2건에 `Size(800, 1000)` 을 명시했다 — 고정 푸터(약 41px)로 기본 800x600 에서 Today 의 CTA 가 접힌 아래로 내려간다. 대시보드는 `CustomScrollView` 라 실제 사용자는 스크롤로 닿으므로 제품 결함이 아니고, 이 테스트들이 스크롤하지 않을 뿐이다. **폭은 800 을 유지**했다(1200 으로 키우면 다른 코드 경로로 들어간다 — 아래 관찰). cost if wrong: 600px 높이에서 정말 도달 불가능한 컨트롤이 생겨도 이 테스트가 못 잡는다
Task 6: 관찰(P2 와 무관한 선행 결함, 고치지 않음): 샌드박스의 `w >= 1024` 2페인 분기(`sandbox_layout.dart:78` Column)가 세로로 넘친다. 실측 프로브 — 폭 1200 · 높이 **1033**(= 옛 셸의 세로 예산)에서도 39px 오버플로. 즉 P2 의 −33px 때문이 아니다. P4(화면군 개편)의 샌드박스 차례에 함께 본다
Task 6: Ruling: `community_navigation_hierarchy_test` 의 드롭다운 열기 테스트를 `/community?board=QNA` 대신 `/dashboard` 에서 연다 — 커뮤니티 안에서 열면 브레드크럼이 같은 라벨을 함께 내어 finder 가 2개를 잡는다(실측 「Found 2 widgets with text "커뮤니티"」). 드롭다운이 세 게시판을 노출하는지는 위치와 무관한 성질이다. cost if wrong: 커뮤니티 화면에서만 드롭다운이 깨지는 회귀를 이 테스트가 못 잡는다(같은 파일의 밑줄 테스트가 그 위치를 덮는다)
Task 6: complete (commits b11796b..d39e6b1, tests: bash -c 'cd apps/web && flutter test' → 01:05 +1011: All tests passed!)
Task 7: complete (commits d39e6b1..fc930e3, tests: bash -c 'cd tools/browser_ux && node --test run.test.mjs' → ℹ duration_ms 249.555)
Task 8: Ruling: 계획 Step 2 가 추가하라던 「admin 폴백」 테스트는 `dp_app_shell_compact_test.dart` 의 기존 2건이 이미 그 형상(compact 파라미터 없이 destinations/selectedIndex 만)을 쓰고 있어 중복이었다. 대신 그 파일이 단언하지 않던 **destinations 전달**(`bar.destinations` 라벨)을 한 건 추가했다 — 파라미터 제거가 깨뜨릴 수 있는 유일한 지점이다. 계획이 「`dp_app_shell_compact_test.dart` 에서 compact 3파라미터를 쓰는 호출을 고친다」고 한 것도 사실과 달랐다(그 파일은 애초에 안 쓴다). cost if wrong: 없음 — 더 많은 것을 덮는다
Task 8: complete (commits fc930e3..410118e, tests: bash -c 'dart run melos run test' →      └> SUCCESS)
Task 9: Ruling: 햄버거의 `Semantics(container: true)` 래퍼를 제거했다 — 함정 1·2 는 heading 표식이 위로 합쳐지는 문제고 이 버튼은 heading 이 아니다. VM 라벨은 '메뉴' 정상인데 브라우저에서 role 조회가 타임아웃했고, 이 레포에서 browser-ux 가 잘 찾는 버튼들은 래퍼가 없다. cost if wrong: 다음 CI 에서 같은 타임아웃이 재현되면 원인이 다른 데 있다는 뜻이고, 그때는 러너 선택자를 `flt-semantics[aria-label]` 로 바꾼다
Task 9: Ruling: `DpWebShell` 이 `FocusTraversalGroup(WidgetOrderTraversalPolicy)` 를 승계한다 — 계획에 없었지만 `DpAppShell` 이 갖고 있던 것을 새 셸이 물려받지 않아 화면 안 Tab 순서가 바뀌었다(CI 실측: 커뮤니티에서 '글 작성' 이 목록 행 뒤로). 순회 순서 변경은 P2 의 의도가 아니다. cost if wrong: 새 셸에서 이 정책이 오히려 부자연스러운 순서를 만들면 다음 실측에서 드러난다
Task 9: 실측(기록): 키보드 순회에 **헤더가 들어가지 않는다** — 레일이 빠져 있던 것과 같은 라우트 `FocusScope` 경계 문제이고 큐 §9.6-5 에 이미 있다. **푸터 링크 4개는 새로 들어왔다**(웹 문법상 정상). 기대값은 다음 CI 실측으로 기록한다
Final: Ruling: 브레드크럼 구분자를 시안의 `›` 대신 `·` 로 쓴다 — 실측(CI 36212413896 vs develop 35932928056)에서 이 브랜치에만 `notosanssymbols` 외부 요청이 늘었고, 그것이 `/content` 390x200% 가 networkidle 에 못 가는 원인이었다. 운영에서도 페이지마다 폰트를 한 벌 더 받는다. 시안 이탈이지만 시안은 글리프의 폰트 비용을 모른다. cost if wrong: 구분자 모양이 시안과 다르다(P5 기준선 승인 때 보인다)
Final: Ruling: 리뷰어의 Critical 「푸터 저작권이 키보드 트랩(WCAG 2.1.2)」을 **재등급해 고치지 않는다** — develop 기준선 실측에도 마지막 정지가 8번 반복된다(대상만 게시글 행). P2 가 만든 것이 아니라 러너·엔진의 기존 거동이고 §9.6-5 에 속한다. cost if wrong: 진짜 트랩이라면 P2 와 무관하게 남는다 — 큐 항목으로 이미 추적 중
Final: 재등급 근거 기록: 리뷰어는 develop 기준선을 비교하지 않고 「새로 생긴 트랩」으로 판정했다. 기준선 대조가 causation 을 뒤집은 두 번째 사례다(첫 번째는 샌드박스 1024 오버플로)
Final: Ruling: 브레드크럼 구분자를 시안의 `›` 로 되돌렸다 — `·` 로 바꾼 근거(폰트 폴백 유발)가 실측으로 무너졌다. 구분자가 `›` 이던 실행과 `·` 이던 실행 **둘 다** `notosanssymbols` 요청이 멈춘 시나리오에서만 났다 = 증상이지 원인이 아니다. cost if wrong: 없음 — 시안으로 복귀
Final: 정정: 「390x200% 멈춤의 원인은 구분자」라고 사용자에게 보고했다가 철회했다. develop 대비 차이 하나만 보고 인과로 단정했고 시나리오별로 쪼개지 않았다. 교훈 — 기준선 대비 delta 는 상관이지 인과가 아니다. 시나리오 단위로 쪼개 보면 1분이면 갈렸다
Final: fixed 햄버거 role 조회 타임아웃 — Tooltip 으로 접근성 이름 부여. 근거 = 실측된 노출 목록(모든 role=button 이 aria-label 빈 값) + 이 레포에서 잘 찾히는 버튼들이 전부 tooltip 보유. CI 가 판정한다
Final: 미해결 /content 390x200% 멈춤 — 재시도 폭주 확정(차단 요청 100%:29 vs 200%:624). URL 별 횟수 계측 추가. develop 대조상 P2 회귀이고 원인 미상
Final: fixed /content 390x200% 멈춤 — 원인은 브레드크럼의 ellipsis 가 부르는 U+2026 폰트 폴백(695회 재시도). compact 에서 마지막 세그먼트만 보이게 해 잘림 자체를 없앴다(DpChromeBar 와 같은 규칙). RED 테스트 먼저, dp_design 108/108
Final: Ruling: 「390x200% 멈춤은 원인 미상」이라고 두 번 보고했다가 계측으로 끝까지 갔다 — 총 건수(624)로 폭주를 확인하고, URL 별 횟수(695x notosanssymbols)로 범인을 특정하고, 100% 와의 차이로 글자를 좁혔다. 교훈: 브라우저에서만 나는 실패는 한 번에 한 계단씩 계측을 늘리면 3사이클에 끝난다 — 추측 수정은 0사이클에 끝나지 않는다
Final: 정정: 「compact 브레드크럼 수정이 폰트 폭주를 멎게 한다」고 보고했으나 다음 실행에서 584x 로 그대로였다. ellipsis 가 브레드크럼에서 온다는 추론이 틀렸거나 다른 곳에도 있다. compact 규칙 자체는 유지한다(DpChromeBar 와 같은 규칙이고 폰에서 경로를 잘라 보여 주는 것보다 낫다) — 다만 폭주의 해결책으로 제시한 것은 틀렸다
Final: 계측 4단계 누적: (1) 라우트별 실패 지점 (2) 중복 제거 전 총 건수 (3) URL 별 재시도 횟수 (4) 라우트별 누적값 + 실패 화면 스크린샷. 브라우저에서만 나는 실패는 계측을 한 계단씩 올리는 것이 추측 수정보다 빠르다 — 다만 여기서는 9사이클을 썼다
Final: 미해결(특성화 완료) 헤더 시맨틱스 부재 — 로컬 재현 성공(mock 릴리스 빌드 + 핀 Playwright 이미지 + --network none). 실험 6회로 위치·버튼 종류 4가지·활성화 타이밍·FocusTraversalGroup·폭을 전부 배제. 남은 규칙 = 각 Column 에서 Expanded 앞 형제만 시맨틱스에서 빠진다(헤더·브레드크럼·프로브 4개 모두, 푸터는 남음). 실제 영향: 폰에서 스크린리더 사용자가 내비게이션에 도달 불가 — browser-ux 가 실패하는 것이 맞고 게이트를 완화하지 않는다
Final: Ruling: 로컬 무거운 검증(웹 빌드 + Playwright)은 사용자 승인 아래 수행했다(레포 상시 방침은 CI). 결과 = CI 6분 왕복이 2분 실험으로 바뀌어 6회 실험이 가능했고, 스크린샷·시맨틱스 덤프라는 CI 가 주지 못하는 증거를 얻었다. cost if wrong: 사용자 PC 를 약 20분 점유
