# 핸드오프 2026-09-28 — S3-P5 PR-1 머지 완료 · 다음 = PR-2(게이트 커버리지 + 기준선)

> 앞 핸드오프: `handoff-2026-09-28-s3-p4-complete.md`(#183).
> 계획: `plans/2026-09-28-s3-p5-baseline-rerecord.md`(PR #185, 펜스 수정 #186) — **18 Task · 103 Step**.
> 실행 원장 전문: `plans/2026-09-28-s3-p5-baseline-rerecord/execution-ledger.md`(456줄 · 판정 30여 건).
> 최종 전체 리뷰(Opus) 전문: 같은 폴더 `final-review-pr1.md`.

## 1. 좌표

| 레포 | 브랜치 | 커밋 | 상태 |
|---|---|---|---|
| frontend | `develop` | **`c8edb82`** | PR **#239**(PR-1) 머지 — CI 전 잡 pass/skipping · 실패 0 |
| documents | `develop` | `2327853` | PR #185 계획 · #186 펜스 수정 |

**워크트리 `D:\workspace\dpa\.worktrees\frontend-s3p5-20260928` 를 지우지 말 것** — SDD 실행 산출물(브리프 11 · 보고서 9 · 리뷰 9 · diff 패키지 11)이 git-ignored 로 그 안에 있다. 원장과 최종 리뷰 사본은 위 documents 경로에 있다. `documents-s3p5-plan` 워크트리도 남겨 두었다.

`git filter-branch` 가 남긴 백업 ref `refs/original/refs/heads/feat/s3-p5-carryover` 가 그 워크트리에 있다 — 푸시 대상이 아니고 정리해도 된다.

## 2. PR-1 이 끝났다 — 이월 판단 12건

frontend PR #239, **16커밋**(`eaa7f77..91c9964` → 머지 `c8edb82`).

| Task | 무엇 | 출처 |
|---|---|---|
| 1 | `DpCols` 주석/코드 모순 — **코드 불변**, 경계 4값(599/839/840/1240) 고정 테스트 | baseline-impact |
| 2 | `DpSteps` 동일 높이(`IntrinsicHeight` + stretch) | P4 M1 |
| 3 | `DpNextActionBand` 그림자 제거 **+ 배경·테두리를 시안 `.next` 대로**(최종 리뷰 I1) | P4 M8 |
| 4 | 비활성 밴드가 「사용할 수 없음: 이유」를 읽는다(+ 중복 `hint` 제거 + 릴리스 null 폴백) | P4 M7 |
| 5 | **`DpPanel` 이 스스로 잉크 표면을 갖는다** + 호출부 우회 2곳 제거 | PR-A 함정 |
| 6 | `dp_design` 리터럴 **11곳**(계획은 7곳) → `DpTypography`·신설 `DpWebDensity` | baseline-impact |
| 7 | 진단 두 루프 여분 간격 + 폰 CTA 깊이 단언 + `DpCheckRow` 탭 정지 개수 | P4 M9·M10a·M11 |
| 8 | 마이페이지 `.prof` — 시안과 **자리가 뒤바뀐** 배지/프로필 kv 되돌림 | P4 M6c |
| 9 | 소비처 0인 `PlaceholderPage` 삭제 | P4 M3 |
| 10 | `DpNavRail` 라벨 중복(admin 전용) | baseline-impact |

테스트: dp_design **392** · dp_core **174** · admin **156** · web **1127**.
CI: `analyze-test` 4m57s · `browser-ux` 5m17s · `perf-gate` 21m46s · `produce-atomic-pair` 9m16s · 이미지 계약 2 · SKIPPED 4 · **실패 0**.

## 3. 다음 착수점 — PR-2 (Task 12~17)

**계획 파일의 Task 12~17 을 그대로 실행하면 된다.** 사용자 결정으로 **PR-2 는 컨트롤러가 직접(Native) 수행**한다(PR-1 은 subagent-driven 이었다).

| Task | 무엇 |
|---|---|
| 12 | **`browser-ux` 가 P4 가 바꾼 14화면을 보게 한다** ← 이 단계의 실질 |
| 13 | `expectations.json` 의 `recorded_from` 갱신(아직 P2 커밋 `ff4a886` 를 가리킨다) |
| 14 | `perf/baseline.json` 재기록 — **CI `perf-gate` 아티팩트를 그대로 옮긴다**(로컬 측정 금지) |
| 15 | DESIGN.md §3·§5 개정 |
| 16 | PR-2 올리고 CI 판정 후 머지 |
| 17 | documents — 핸드오프 · 원장 · `baseline-impact-p5.md` · 스펙 §7 P5 행 정정 |

### Task 12 의 핵심 사실(실측 완료)

`tools/browser_ux/run.mjs:22` 의 `ROUTES` 는 **8항목 = 7화면**뿐이다. 도달 가능성은 `gateRedirect`(순수 함수)로 증명한다:

| mock 프로필 | 도달 가능한 라우트 |
|---|---|
| `onboarded`(기존) | `/community/post/10` · `/community/post/10/edit` · `/community/1` · `/community/1/edit` · `/community/new` · `/community/new/post` · `/settings` · `/mypage` |
| **`guest`(신설 필요)** | `/login` · `/diagnostic` · `/beta-pending` · `/auth/callback` |
| **`consent`(신설 필요)** | `/consent` |

`onboarded` 빌드는 온보딩 라우트 5개를 **전부 돌려보낸다**(`/login`→`/dashboard` · `/consent`→`/path` · `/diagnostic`→`/path` · `/beta-pending`→`/dashboard` · `/auth/callback`→`/dashboard`). 그 라우트를 기존 `ROUTES` 에 적는 것은 **다른 화면을 두 번 재는 테스트**가 된다.

- mock 프로필 정의: `apps/web/lib/src/data/web_mock_fixtures.dart`(현재 `pending|onboarded`, `consentStatus` 는 항상 `DONE`).
- `guest` 는 `POST /auth/refresh` 가 **401** 을 돌려줘야 미인증이 된다.
- `run.mjs` 에 `--routes=` 옵션이 없다 — 더해야 한다(`--only` 는 있다).
- 계획 Task 12 Step 8 에 `browser-ux-onboarding` 잡 YAML 전문이 있다.
- **덮지 못하는 것**: 진단 **문항·결과**는 `/diagnostic` 안의 단계라 URL 로 도달하지 않는다. 클릭하는 새 시나리오가 필요하며 Task 17 이 미커버로 기록한다.

## 4. PR-2 가 기준선으로 굳히기 전에 판단해야 할 divergence 3건

최종 리뷰(Opus)가 시안 정본을 직접 열어 찾았고, **범위 밖이라 고치지 않고 기록만 했다.**

1. **마이페이지의 중복은 닫힌 게 아니라 자리를 옮겼다.** 시안의 마이페이지에는 **편집 폼이 없다**(헤더 `프로필 편집` 버튼으로 빠진다). 이 화면은 편집이 인라인이라 목표 트랙·목표·경력 세 값이 사이드 kv 와 편집 폼에 두 번 나온다. compact(<840)에서는 위아래로 놓인다. → 코드가 아니라 `mypage_page.dart` 주석과 이 기록으로 남겼다. **P4 M6c 는 「닫힘」이 아니라 「부분 닫힘 + 남은 divergence」다.**
2. **`DpSteps._Step` 의 패딩·글자가 시안과 다르다** — 시안 `.steps li{padding:6px 12px;font-size:13px}` vs 구현 `vertical: DpSpacing.xs`(4)·`horizontal: DpSpacing.md`(12) + `bodyMedium`(14). 이 PR 의 어떤 Task 도 인용하지 않은 divergence 라 고치지 않았다(고치면 계획 밖 범위 확대).
3. **`apps/web` 에 리터럴 `TextStyle(fontSize:)` 가 10곳 남아 있다**(`dp_design/lib` 은 이제 **0곳**): `lcs_context.dart` 3 · `post_detail_page.dart` 2 · `web_community_board_projection.dart:210` · `path_panels.dart:107` · `support_dialog.dart` 3. 결과적으로 **같은 화면에서 12px 글자의 줄 높이가 둘**(토큰 16 vs 리터럴 19.2)이 된다. Task 6 의 명시 범위가 `dp_design` 이었다.

## 5. 다음 세션이 알아야 할 함정 (PR-1 이 새로 실증한 것)

1. **★ 로컬 Dart 는 3.13.2, CI 핀은 3.12.1 — 포매터 출력이 다르다.** 레포 전체에 `dart format .` 을 돌리면 **우리가 건드린 적 없는 파일 4개**가 3.13 의 인자 패킹 규칙으로 다시 쓰인다(`apps/admin/test/.../reports_async_order_test.dart` 등). 그것을 커밋하면 안 된다. **그러나 그 잡음 속에 진짜 dirty 파일이 숨을 수 있다** — PR-1 에서 실제로 한 건 있었고(접으면 74자로 80열에 들어가 CI 포매터도 같은 결과) 고치지 않았으면 `melos run format` 게이트가 실패했다. 확인은 반드시:
   ```
   dart format --output=none --set-exit-if-changed $(git diff --name-only <base>..HEAD)
   ```
   **구현자 보고의 「format 0 changed」는 세 번 다 부정확했다.** 컨트롤러가 직접 돌려야 한다.
2. **`flutter analyze` 가 스스로 `analysis_options.yaml` 을 다시 쓴다**(출력에 `Upgrading analysis_options.yaml to exclude build and platform directories.` 가 찍힌다). 그래서 **두 번째 실행에서는 이슈가 사라진다** — 두 번 돌려 「0 issues」를 보고하면 **거짓 음성**이다. 확인은 설정을 되돌린 뒤 한 번만.
3. **`apps/web` 의 `current_mission_controller.dart:273 unawaited_return_in_try_block` 1건은 로컬 3.13.2 전용이다.** 파일이 `origin/develop` 과 byte-identical 이고, 그 린트가 어떤 `analysis_options.yaml` 에도 명시적으로 켜져 있지 않으며, develop CI 가 녹색이다. **PR #239 의 `analyze-test` 통과가 이를 확증했다.**
4. **하네스가 커밋 트레일러에 구현 모델 이름을 주입한다**(`Claude Haiku 4.5`/`Claude Sonnet 5`). dispatch 에 확인 지시를 넣어도 **sonnet 은 세 번 다 따르지 않았다**(haiku 는 따랐다). 컨트롤러가 커밋 직후 확인해야 한다. 푸시 전이면 `filter-branch --msg-filter` 로 메시지만 고칠 수 있고, **트리 해시·커밋 수·브랜치 diff sha256** 세 지표로 내용 무변경을 검증하면 안전하다.
5. **superpowers 의 task-reviewer 템플릿은 「최종 메시지가 곧 보고서다」라고 지시하는데 이 하네스에서는 긴 최종 메시지가 유실된다.** PR-1 에서 실제로 한 번 통째로 잃었다(살아 있는 에이전트를 재개해 파일로 받아 복구). **리뷰어 dispatch 도 보고서 파일 경로를 지정하고 최종 메시지는 3줄로 제한하라.**
6. **컨트롤러가 그 Task 의 커밋을 건드렸으면(amend·rewrite) 리뷰 dispatch 에 반드시 명시하라.** 안 적으면 리뷰어가 구현자 보고서를 「검증 가능하게 거짓」으로 오판한다(PR-1 에서 실제로 발생).
7. **계획의 테스트 스니펫이 기존 헬퍼를 축자 중복한 사례가 3 Task 연속 나왔다.** 원인은 계획 작성 시 **소스 파일만 읽고 테스트 파일 상단의 헬퍼를 읽지 않은 것**. dispatch 전에 그 Task 가 건드릴 테스트 파일의 헬퍼를 컨트롤러가 먼저 읽고 교정형을 실어 보내야 한다.
8. **`task-brief` 추출기는 코드 펜스를 세어 Task 경계를 찾는다.** 계획에 닫히지 않은 펜스가 하나 있으면 그 뒤 전체가 코드 블록으로 보여 **Task 2 이후가 전부 `not found`** 가 된다(PR-1 착수 시 실제로 막혔다, PR #186 로 수정).

## 6. 최종 리뷰가 확인해 준 것 (교차 Task)

- **`DpPanel` 의 `Material` 과 `DpNavRail` 의 `ExcludeSemantics` 는 시맨틱스에서 간섭하지 않는다** — `Material` 은 시맨틱스 노드를 만들지 않는다(SDK 직접 확인). 두 경로도 겹치지 않는다.
- **Task 6 의 토큰 도입은 Task 2·7 의 치수 단언과 충돌하지 않는다** — 2는 단계 **서로의** 높이를, 7 M10a 는 사각형 **사이** 간격을 재므로 줄 높이 변화에 면역이다. 절대값을 쓰는 7 M9(CTA 깊이 1500)만 민감한데 **커밋 순서가 옳아**(Task 6 → Task 7) 실측 1337 이 토큰 전환 뒤 값이다.
- **`DpPanel` 의 `Material` 은 잉크만 바꾸지 않는다** — `DefaultTextStyle` 도 `bodyMedium` 에서 리셋한다(SDK `Material.build` 의 `AnimatedDefaultTextStyle`). 오늘 실제 영향은 없음을 소비처 21파일로 확인했으나, 코드 주석의 「잉크만」 단언은 불완전하다(deferred minor).

## 7. deferred minors (PR-2/PR-3 가 트리아지)

원장의 `minor (deferred)` 줄과 `final-review-pr1.md` 의 Minor 13건 · Declined 12건에 전부 있다. 최종 리뷰가 **「머지 전 수정 필요」로 꼽은 1건은 이미 고쳤다**(마이페이지 주석의 출처 과장).

## 8. 릴리스 좌표 (변동 없음)

S3 는 **P5 까지 끝난 뒤** 릴리스에 태운다 — 다음 `develop`→`main` 은 랜딩 시각이 바뀌는 릴리스다. **ET13 baseline 승인은 P5 가 아니라 릴리스 캠페인 단계**다(커밋된 카탈로그는 `baseline_status` 를 스키마 상수로 `pending_external_review` 에 고정하고, 승인 워크플로가 `release_id` 를 요구한다 — S3-P5 실측). 승인 워크플로는 `gh` CLI 가 리뷰어 계정이라 **직접 `gh workflow run` 하지 말고** `automation/dispatch-<release_id>` 디스패처를 쓴다.
