# 핸드오프 2026-09-30 — S3-P5 완결 · 다음 = 릴리스 캠페인

> 앞 핸드오프: `handoff-2026-09-28-s3-p5-pr1-merged.md`(#187).
> 계획: `plans/2026-09-28-s3-p5-baseline-rerecord.md` — 18 Task. PR-1 = Task 1~11, **PR-2 = Task 12~17**.
> 실행 원장 전문: `plans/2026-09-28-s3-p5-baseline-rerecord/execution-ledger.md`(PR-1 절 + PR-2 절).
> 릴리스 캠페인의 입력: 같은 폴더 **`baseline-impact-p5.md`** — 캠페인을 시작하기 전에 이것부터 읽는다.
> 최종 전체 리뷰(Opus) 전문: frontend 워크트리 `.superpowers/sdd/2026-09-28-s3-p5-baseline-rerecord/final-review-pr2.md`.

## 1. 좌표

| 레포 | 브랜치 | 커밋 | 상태 |
|---|---|---|---|
| frontend | `develop` | **`023eb22`** | PR **#240**(PR-2) 머지 — CI 전 잡 pass/skipping · 실패 0 |
| documents | `develop` | `PENDING` | PR **#PENDING** — 핸드오프 · 원장 PR-2 절 · `baseline-impact-p5.md` · 스펙 §7 P5 정정 |

**지우지 말 워크트리**
- `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928` — PR-1 의 git-ignored SDD 산출물(브리프 11 · 보고서 9 · 리뷰 9 · diff 11).
- `D:\workspace\dpa\.worktrees\frontend-s3p5pr2-20260930` — **PR-2 의 실행 원장·최종 리뷰 전문·프로브 3종**이 git-ignored 로 그 안에 있다(`final-review-pr2.md` 454줄 · `probe-axe.mjs` · `probe-targets.mjs` · `probe-scroll.mjs`). 원장과 리뷰 요지의 사본은 documents 에 있지만 리뷰 **전문**은 여기뿐이다.
- `D:\workspace\dpa\.worktrees\documents-s3p5-plan` — 계획·원장·핸드오프의 작업 워크트리.

## 2. S3-P5 가 끝낸 것

**PR-1**(이월 판단 12건, develop `c8edb82`) — 앞 핸드오프 §2 그대로.

**PR-2**(9커밋) = 게이트를 참으로 만들었다.

| Task | 무엇 | 결과 |
|---|---|---|
| 12 | `browser-ux` 가 P4 가 바꾼 화면을 보게 한다 | 8항목(7화면) → **21 라우트/프로필 조합**. mock 프로필 `guest`·`consent` 신설 + CI 잡 `browser-ux-onboarding` 신설 |
| 13 | `expectations.json` provenance | **값 불변**(순회는 그대로) · `recorded_from` 을 실측 브랜치 커밋으로 |
| 14 | `perf/baseline.json` 재기록 | `built_from` `a4753024` → **`13d81c94`** · `samples` 3 → 5 |
| 15 | DESIGN.md §2·§3·§5 | `DpInteractiveCard` 소비처 0 실측 반영 · 파생 스타일 · `DpCols` 840 근거 |
| — | 시안 divergence #2·#3(사용자 결정으로 추가) | `DpSteps` 시안 치수 · `apps/web` 리터럴 14곳 → 파생 스타일 |
| 16 | PR 올리고 CI 판정 후 머지 | CI 3라운드 · 전 잡 pass/skipping |
| 17 | documents | 이 문서 · 원장 PR-2 절 · `baseline-impact-p5.md` · 스펙 §7 정정 |

테스트: dp_design **396** · dp_core **174** · admin **156** · web **1141** · `browser_ux` 20 · `perf` 11.

## 3. 다음 착수점 = 릴리스 캠페인

**`baseline-impact-p5.md` 를 먼저 읽는다.** 캠페인이 알아야 할 것이 거기 정리돼 있다. 요지만:

1. **ET13 baseline 재승인이 필요하다.** P5 가 커뮤니티·진단 fixture 의 렌더를 바꿨다. 승인은 P5 가 아니라 **캠페인의 단계**다 — 커밋된 카탈로그는 `baseline_status` 를 스키마 상수로 `pending_external_review` 에 고정하고(`catalog.schema.json:61`) 승인 워크플로가 입력에 `release_id` 를 요구한다. `gh` CLI 가 리뷰어 계정이라 **직접 `gh workflow run` 하지 말고** `automation/dispatch-<release_id>` 디스패처를 쓴다.
2. **홈 `tokens.css` 미러 재동기화는 불필요하다.** 토큰 계약 2.0.0 의 값을 바꾸지 않았다 — 새로 더한 것은 파생 스타일(`context.dpMeta`·`dpBody`)과 `DpWebDensity.stepVerticalPadding` 이고, CSS 투영 덤프는 `DpSemanticTokenManifest`·`AppTokens`·브레이크포인트만 읽는다(리뷰어가 독립 확인).
3. **다음 `develop`→`main` 이 랜딩 시각을 바꾸는 릴리스**다 — S3 전체가 한 번에 운영에 올라간다.
4. 릴리스 좌표(변동 없음): gitops main **`5427fe1e`** · 홈 prior 배포 **`6f7a7e2b-522f-4bf1-b134-2dd2b345f83c`** · ai-svc 증거 만기 **10/08** · governance 룰셋 설계 충돌(et11) 미해결.

## 4. ★ 캠페인이 반드시 알아야 할 사실 — 게이트는 어디서도 「필수」가 아니다

2026-09-30 실측:

- `develop` 은 **보호 설정이 아예 없다**(룰셋 0건 · classic protection 404).
- `main` 의 필수 체크는 **`analyze-test` 하나뿐**이다.

즉 `browser-ux`·`browser-ux-onboarding`·`perf-gate`·`produce-atomic-pair`·`web-image-config-contract` 는 **붉어도 머지를 막지 못한다.** 구속력은 머지하는 쪽이 결과를 읽는다는 사실뿐이고, 이 계획의 Global Constraints 가 바로 그 규칙(「CI 전 잡이 pass/skipping 이고 실패 0 이면 AI 가 머지한다」)이다.

PR-2 가 커버리지를 8→21 로 넓힌 값은 **그것을 필수 체크로 등록할 때** 온전해진다. 등록은 권한 변경이라 사용자 결정 사항이고(권한 자가 확장 금지), governance 룰셋 설계 충돌(et11)이 이미 열려 있는 자리다. PR-2 는 그날을 위해 체크 **이름만** 안정화해 뒀다(`browser-ux-onboarding (guest)` — 라우트 목록이 이름에 들어가지 않는다).

## 5. 다음 세션이 알아야 할 함정 (PR-2 가 새로 실증한 것)

1. **★ 로컬 통과가 CI 통과를 보장하지 않는 결함 부류가 있다 — 폰트 폴백이 그것이다.** `/community/1` 은 로컬에서 외부 요청 **+5** 로 정착해 통과했고 CI 에서 **2651건**으로 30초 타임아웃을 냈다. 자기지속 루프라 레이아웃 패스가 많은 환경에서만 폭발한다. 로컬 순회가 초록이어도 CI 를 한 번은 돌려야 한다.
2. **★ 픽토그래픽 이모지를 UI 문자열에 두면 안 된다.** 번들은 Pretendard·D2Coding 뿐이라 Noto Color Emoji 를 부르고, 차단된 다운로드는 재시도 금지 목록에 들어가지 않아 레이아웃마다 다시 나간다. 가드 테스트(`apps/web/test/app/no_pictographic_emoji_test.dart`)가 이제 막는다 — 기준은 `Emoji_Presentation=Yes` 이고 `✓`·`★`·`●` 는 Pretendard 에 있어 허용한다. **「U+2600–U+27BF 를 통째로 막자」는 안 된다**(이 레포가 쓰는 `✓ 완료` 가 오탐된다).
3. **★ 라우트를 늘리면 러너의 잠복 결함이 드러난다.** 외부 요청 상한이 컨텍스트 **총합**이었고(라우트당 +2 고정이라 16라우트면 넘는다), 최소 타깃을 **한 번만** 쟀다(Flutter 는 스크롤 폴드에 잘린 위젯의 시맨틱스 노드를 **잘린 rect** 로 낸다 — 「로그아웃」 80×8, 뷰포트만 높이면 80×30). 둘 다 S3-P5 가 만든 것이 아니다.
4. **★ 시안은 `line-height` 를 덮지 않는다.** `.meta`(12px)·`.ex`(13px)·`.steps li`(13px) 는 `font-size` 만 덮고 `body{line-height:1.6}` 을 물려받는다 ⇒ 시안의 12px 행간은 **19.2** 이고 토큰 `labelMedium`(12/16)이 시안과 다른 쪽이다. 앞 핸드오프가 이것을 거꾸로 적었고, 그대로 실행하면 6화면이 토큰 정리처럼 보이면서 시안에서 **멀어진다**. 파생 스타일(`context.dpMeta`·`dpBody`)이 그래서 있다.
5. **★ `page.mouse.wheel` 만이 Flutter 스크롤 뷰를 굴린다.** `scrollIntoViewIfNeeded()` 는 시맨틱스 노드에 **무동작**이다(절대 배치된 오버레이). 그리고 휠은 `flt-semantics` 노드를 더하고 지우므로, 스크롤을 건너 `nth(index)` 로 재측정하면 다른 요소를 잰다 — 요소 핸들로 붙잡아야 한다.
6. **★ `pull_request` 이벤트의 `GITHUB_SHA` 는 레포에 없는 임시 머지 ref 다.** 아티팩트의 `built_from` 을 그대로 커밋하면 **존재하지 않는 SHA** 가 기준선에 박힌다. provenance 는 측정이 이뤄진 **브랜치 커밋**으로 적는다(`git cat-file -t` 로 확인).
7. **★ 「LCP 가 있으면 LCP, 없으면 ready」 같은 폴백 판정은 조용히 죽는다.** 2026-09-17 부트 스플래시가 모든 행에 LCP 후보를 만들자 `ready_ms` 절대 검사가 통째로 멈췄다(모바일 cold 21.5초가 예산에서 사라졌다). PR-2 가 둘을 각각 보게 고쳤다.
8. **★ 게이트에 예외를 두면 그 예외가 낡는지 게이트가 감시해야 한다.** 에디터 4화면의 axe 유보는 (a) 라우트 + 규칙 + **노드 수 상한** 단위이고, (b) 위반이 사라졌는데 항목이 남으면 **그 자체가 실패**이고, (c) 이유와 후속 과제를 테스트가 요구한다. 낡음 판정은 **전 폭을 모아 한 번만** 한다 — 폭마다 하면 한 폭에서만 나는 규칙이 다른 폭에서 거짓 실패가 된다.
9. **★ `cmd | tail; echo $?` 는 `tail` 의 종료코드다.** 이 세션에서 `analyze` 와 `format` 의 실제 실패를 둘 다 0 으로 보고했다(출력을 눈으로 읽어서 잡았다). `set -o pipefail` 또는 `${PIPESTATUS[0]}`.
10. **로컬 Dart 3.13.2 ≠ CI 핀 3.12.1**(앞 핸드오프에서 이어짐). 전체 `dart format .` 은 이 브랜치가 건드리지 않은 파일 4개를 다시 쓴다. 확인은 항상 `dart format --output=none --set-exit-if-changed $(git diff --name-only <base>..HEAD -- '*.dart')`. `flutter analyze` 의 `current_mission_controller.dart:273` 1건도 로컬 전용이다(그 파일은 `origin/develop` 과 byte-identical).

## 6. 이월 (고치지 않고 기록한 것)

`baseline-impact-p5.md` §7·§8 이 정본이다. 요약:

- **백엔드 계약 변경이 필요한 시안 divergence 7건**(작성 시각·작성자 표시 이름·과제 설명·총 주차 수·태그↔콘텐츠 추천·개념별 진단 점수·마이페이지 활동 목록).
- **마이페이지 편집 폼 분리** — P4 M6c 는 「닫힘」이 아니라 **「부분 닫힘 + 남은 divergence」**다. 시안에는 편집 폼이 없고(헤더 버튼으로 빠진다) 구현은 인라인이라 세 값이 두 번 나온다. 프론트 범위, 이월(사용자 결정 2026-09-30).
- **토큰 계약이 시안보다 행간이 좁다** — `bodySmall`(13/20)·`labelMedium`(12/16) vs 시안 1.6. 계약 하나의 결정이고 통일하려면 **버전을 올려야 한다**.
- **에디터 툴바가 12버튼인데 시안 `.bar2` 는 5버튼**이고 툴팁이 영어다. `buttonOptions.childBuilder` 로 5버튼을 직접 그리면 axe 유보와 시안 divergence 가 함께 닫힌다. `flutter_quill` 11.6.0 에서 이중 툴팁이 고쳐졌는지도 확인.
- **게이트가 덮지 못하는 것**: 진단 문항·결과(URL 로 도달하지 않는다) · `apps/admin` 전체 · `/login` 의 perf · 에디터 4화면의 두 axe 규칙.
- **INP 는 런 간 비교가 성립하지 않는다** — 같은 행에서 값이 붙었다 떨어진다. 게이트로 쓰려면 측정 방식을 먼저 고쳐야 한다.
- 최종 리뷰의 이월 Minor 7건(M3·M5·M6·M8·M10 등)은 원장 「이월한 Minor」 절에 있다.
