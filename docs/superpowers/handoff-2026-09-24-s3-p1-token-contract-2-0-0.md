# 핸드오프 2026-09-24 (밤) — S3-P1 토큰 계약 **2.0.0** 구현 완료(frontend PR #232) · 홈 미러는 시각 기준선 때문에 **차단**(PR #93 draft) · 다음 세션 이관

> 같은 날 앞 문서 `handoff-2026-09-24-r3-released-cors-env-published.md` 의 **§4 「다음 착수점」** 을 이 세션이 처리했다. 이 문서가 그 §4 만 대체한다 — 앞 문서의 §1(릴리스 r3 운영 상태)·§2(타임라인)·§3(결함과 교훈)·§5(좌표)는 **그대로 유효**하다.
> 정본: 계획 `plans/2026-09-24-s3-p1-semantic-tokens-2-0-0.md` · 설계 `specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §5.3·§5.4·§7 · 시안 https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd (Version 2).

## 1. 이 세션이 한 일 (2026-09-24 04:30Z ~ 08:00Z)

| # | 일 | 결과 |
|---|---|---|
| 1 | 캠페인 preflight 보강 | `promote_r2.py` + 신규 `release_ops.py` — TLS 잔여일·stale 게이트 부재 단언, `sandbox-migration-gate` 선배치/회수, main 감시 → Argo refresh, 수동 단계 5종. 단위 14건. **documents #168**(develop `a7b81b4`) |
| 2 | **et11 governance 룰셋 충돌 = 이미 해소돼 있었다** | shared `fcbc807`(2026-08-23)이 `_validate_governance_ruleset` 을 gitops 검증기와 같은 형상(`update` 단일 + App bypass + `current_user_can_bypass`)으로 맞췄고, 라이브 룰셋(21194270·21194269)도 그 형상이며, 9/24 migration-release `35941728847` 의 "Verify the exact App scope and effective main rulesets" 단계가 success. **8/22 핸드오프의 차단급 항목이 한 달간 문서에만 남아 있었다** |
| 3 | S3-P1 구현 계획 | **documents #169**(develop `61351b1`) — 9 Task, 시안 수치 고정 |
| 4 | 사용자 결정 | 홈 미러 **A안**(미러도 2.0.0 → 랜딩 시각 변경 + 기준선 재승인) · 실행 방식 **Native** |
| 5 | **S3-P1 구현** | frontend **PR #232**(9 커밋 `de316b4..e1bef21`, 28 파일 +569/−239). Task 1~8 완료 |
| 6 | 홈 미러 | home **PR #93 (draft)** — 코드·테스트는 끝났고 **시각 기준선 때문에 차단** |

## 2. 지금 상태 (2026-09-24 08:00Z 실측)

| 영역 | 상태 |
|---|---|
| 운영(app·leva.ai.kr) | **변동 없음.** S3 는 전부 `develop` 이하에만 있다 |
| gitops `main` | `5427fe1e`(9/24 CORS env publisher) 그대로 — 다음 candidate 의 `gitops.base_sha` |
| frontend `feat/s3-p1-semantic-tokens-2-0-0` | PR **#232** open(draft 아님). CI: `analyze-test` pass · `browser-ux` pass · `produce-atomic-pair` pass · `web-image-config-contract (on)` pass · `perf-gate`·`web-image-config-contract (off)` 진행 중. `mergeable=MERGEABLE state=UNSTABLE` |
| 로컬 게이트(frontend) | `dart format --set-exit-if-changed .` 무변경 · `melos run analyze` 4패키지 무이슈 · `melos run test` **1595건 통과**(dp_design 255 · web 1010 · admin 156 · dp_core 174) |
| home `feat/tokens-mirror-2-0-0` | PR **#93 draft**, 커밋 `44b8212`. CI `test`·`visual-a11y` **실패(예정된 실패)** — 아래 §3 |
| Claude Design | `Leva Design Tokens`(`19a7b5ca-6f2b-4d14-b291-ac9e47a31855`) **2.0.0 재동기화 완료**(텍스트 8파일, 97 토큰, 검증기 경고는 예상된 `_ds_sync.json` 1건) |
| 열린 PR | frontend #232(리뷰·CI 대기) · home #93(draft, 차단). documents·gitops 0 |

### 2.1 계약 2.0.0 의 내용 (코드 SSoT)

| 축 | 1.1.0 | **2.0.0** |
|---|---|---|
| 반경 `DpRadius` | 칩 999 · 버튼 12 · 카드 18 · 입력 12 · 다이얼로그 20 | **칩 4 · 버튼 6 · 카드 8 · 입력 6 · 다이얼로그 12** |
| 밀도 | (없음) | **`DpDensity` 신설** — 컨트롤 30 · 표 행 여백 8 · 최소 타깃 24(WCAG 2.2 AA 2.5.8) |
| 레이아웃 `AppTokens` | 1360/760/280/80, panelRadius 18 | **1120**/760/280/80, panelRadius **8**, **`headerHeight` 56 신설** |
| 어두운 색 6종 | `railBg·railText·railMuted·railFaint·railActive·railBorder` | **`headerBg·headerText·headerMuted·headerFaint·headerActive·headerBorder`(값 한 글자도 안 바뀜)** |
| CSS 투영 | `--dp-color-rail-*` | `--dp-color-header-*` + `--dp-density-*` 3종 + `--dp-layout-header-height` |
| 테마 | 컨트롤 52px, `tapTargetSize: padded` | 컨트롤 **30px**, `shrinkWrap`, `isDense` 입력, `iconButtonTheme` 신설 |
| 러너·문서 | browser-ux `MIN_TARGET` 44 | **24** + DESIGN.md §1·§3·§5·§6 |

**이 PR 에 없는 것**: 셸 교체(P2 `DpWebShell`) · 위젯 웹화·FAB 제거(P3) · 화면군 개편(P4) · 기준선 재기록(P5). `apps/admin` 은 이름만 바뀐 토큰으로 `DpAppShell`/`DpNavRail` 을 그대로 쓴다. 44px 을 하드코딩한 위젯 9곳(`dp_context_capsule`·`dp_next_action_band`·`dp_progress_spine`·`dp_chrome_bar`·`dp_nav_rail`·`dp_page_header`·`mentor_page`·`review_panel`·`sandbox_page`)도 P3/P4 로 남겼다.

## 3. 홈 미러가 차단된 이유 (정확히)

랜딩은 미러의 `--dp-radius-*`(39곳)·`--dp-color-rail-*`(22곳)·`--dp-layout-content-max`(4곳)를 **실제로 쓴다.** 그래서 A안(미러도 2.0.0)은 값 복사가 아니라 **랜딩 시각 변경**이다.

커밋 `44b8212` 는 값 미러·소비자 이름 변경·계약 테스트 2.0.0 을 담았고 `npm test` 는 로컬에서 496/496 통과했다. 그런데 **커밋한 뒤** 다시 돌리면 `tests/visual-evidence-audit-contract.test.js` 의 「allows evidence-only and non-rendering descendants while retaining runtime drift detection」 1건이 깨진다(495/496). 그 테스트는 이렇게 판정한다:

```js
const changedPaths = git diff --name-only <rendered_product_sha> HEAD
expect(changedPaths.every(p => isEvidenceOnlyPath(p) || isNonRenderingReleasePath(p))).toBe(true)
```

`assets/tokens.css`·`index.html`·`assets/styles.css`·`assets/public.css` 는 **렌더 입력**이라 허용 목록에 없다. 즉 **가드가 설계대로 동작한 것**이고, 홈 CI 도 같은 실패를 재현했다(`test` 495/496 · `visual-a11y` contracts 실패).

**해제 절차**(다음 세션):

1. Docker Desktop 시작(핀 이미지 `mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294a…` 필요).
2. 워크트리 `D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924` 에서 `npm run visual:evidence:docker` → `npm run visual:baseline:update` → `npm run visual:contracts` → `npm run visual:evidence:validate:diagnostic`.
3. 4폭(320·600·840·1240) PNG 와 `e2e/visual/baselines/review-metadata.v2.json`·`e2e/visual/candidate-spec.v2.json` 재바인딩분을 **커밋한 상태로** `npm test`·`visual:contracts` 를 한 번 더(이 레포 규칙 — 위 테스트가 git 상태에 민감하다).
4. **사람 기준선 승인**(`docs/visual-a11y-evidence.md` §Baseline updates — 승인 전 상태는 `diagnostic_pending_review` 가 정상).
5. CI 녹색 → draft 해제 → develop 머지. 운영 반영은 다음 릴리스 캠페인의 `develop→master` + gitops landing-last(홈 prior 배포 = **`6f7a7e2b-522f-4bf1-b134-2dd2b345f83c`**).

Docker 를 켜지 않은 이유: 이 레포의 상시 방침이 「무거운 Playwright 검증은 핀 이미지/CI 에서, 로컬은 analyze·단위 테스트까지」이고, 사용자가 같은 PC 를 쓰는 중이었다. 랜딩은 그동안 계약 1.1.0 으로 운영된다 — `.design-sync/NOTES.md` 에 「의도된 divergence」로 적어 뒀다.

## 4. 다음 착수점 (우선순위)

1. **frontend PR #232 마무리** — (a) 이 세션이 띄운 전체 브랜치 리뷰 결과 반영(아래 §6 「미결」), (b) `perf-gate`·`web-image-config-contract (off)` 녹색 확인, (c) **develop 머지(merge commit)**. 머지 뒤에도 운영은 안 바뀐다.
2. **홈 미러 차단 해제** — §3 의 5단계.
3. **S3-P2 계획 작성** — `DpWebShell`(헤더·푸터·햄버거·계정 메뉴) 신설 → web `AppShellView` 교체. `DpAppShell`·`DpNavRail` 은 admin 이 쓰므로 남긴다. 핸드오프 2026-09-19 의 L3(`_AccountMenu` MenuAnchor focus a11y)를 여기서 흡수한다. `headerHeight` 56 은 이미 토큰에 있다.
4. **다음 릴리스 캠페인** — gitops `base_sha` **`5427fe1e`** · 홈 prior 배포 **`6f7a7e2b…`** · ai-svc 이미지 증거 만기 **10/08**. preflight 보강(#168)이 TLS·게이트·Argo refresh 를 자동으로 본다. **단, S3 는 P5(기준선 재기록·재승인)까지 끝난 뒤에 릴리스에 태운다** — 중간 상태가 운영에 나가면 안 된다(스펙 §9).
5. (배경) S3-P3/P4/P5 계획, governance et11 은 §1-2 대로 **해소됨**.

## 5. 결함과 교훈 (이 세션 실측)

1. **`SegmentedButton` 은 `minimumSize` 를 무시한다.** 자체 하한을 `textButtonMinHeight(40) + visualDensity.baseSizeAdjustment.dy` 로 계산한다(`segmented_button.dart`). 30px 을 만들려면 세그먼트 테마에 `VisualDensity.compact`(dy −8 → 32px)를 준다.
2. **`IconButton` 에 `fixedSize` 를 주면 안 된다.** 30×30 고정 + 3px 패딩이 자식을 24×24 로 가두고, `flutter_quill` 의 `QuillSimpleToolbar` 합성 아이콘이 80px 오버플로(웹 커뮤니티 테스트 3파일에서 42건). `minimumSize` 만으로 계약을 만족한다.
3. **`sed 's/\brail…/…/'` 의 `\b` 는 한글 앞에서 안 걸린다.** 이름 변경 15곳(테스트 제목·주석)이 조용히 남았다 — 파이썬 정규식으로 마무리하고 `git grep` 으로 0건을 확인했다.
4. **`melos run analyze` 는 테스트 코드도 본다.** 계획이 그대로 준 테스트 코드에 `unnecessary_import`·`sort_child_properties_last`·`unnecessary_cast` 3건이 있어 CI 게이트를 못 넘었다. 계획의 코드도 린트를 통과해야 한다.
5. **핸드오프의 「차단급」 항목은 착수 전에 코드로 재확인한다.** et11 governance 충돌은 한 달 전에 해소됐는데 문서만 복사돼 왔다([[devpath-handoffs-lag-verify-first]]).
6. **백로그는 커밋 수가 아니라 `git diff --shortstat main develop` 로 잰다.** 11개 레포의 develop-only 커밋 4~42개는 전부 동기화 머지였고 실제 차이는 0이었다.
7. **Windows**: 텍스트 모드 stdin 은 CRLF 로 나가 원격 bash 값 끝에 `\r` 을 남긴다(원격 스크립트는 바이트로 보낼 것) · `kubectl run -i` 는 첫 출력 줄을 잃는다(`wait` 뒤 `logs`) · `melos bootstrap` 은 핀 Flutter(`.worktrees/_tools/flutter-3.44.1/bin`)를 PATH 앞에 둬야 lockfile 을 받아들인다.

## 6. 전체 브랜치 리뷰 — 완료, 지적 2건 반영됨

신선한 컨텍스트 리뷰어(서브에이전트; 1차 Fable 은 사용량 한도로 중단, 2차 Opus)가 두 레포를 4패스로 읽고 `dp_design` 테스트를 독립 재실행했다. 보고서 전문 = `plans/2026-09-24-s3-p1-semantic-tokens-2-0-0/REVIEW.md`. **판정: 머지 가능. Critical 0 · Important 2 · Minor 8.**

**Important 2건은 수정 커밋 `813dd9e` 로 반영했다.**

1. **게시된 `conventions.md` 가 옆의 토큰과 모순됐다.** 이 파일은 `config.json` 의 `readmeHeader` 라 `ds-bundle/README.md` 맨 앞에 **그대로** 붙고, 그 README 가 Claude Design 에 올라간다. 2.0.0 개명이 이 파일에 닿지 않아 **없는 이름 6개**(`--dp-color-rail-*`)를 가르치고, 같은 번들의 `guidelines/DESIGN.md` 가 24×24 라고 말하는데 44×44 를 인용하며, 레이아웃은 1.0.0 숫자(1440/880/256/72)였고, 스니펫은 `minHeight: 44` 를 박아 뒀다. CSS 커스텀 속성은 **조용히 실패**하므로 이 헤더를 따른 사람은 투명한 요소를 얻고 오류도 못 본다. → 색·레이아웃·접근성 줄 재작성, 밀도 행 추가, 스니펫을 밀도 토큰으로. **게이트 신설** `packages/dp_design/test/theme/design_sync_conventions_test.dart`(가르치는 모든 `--dp-*` 이름이 매니페스트 투영에 존재할 것 · 게시된 모든 패밀리를 가르칠 것 · 접근성 하한과 레이아웃 숫자가 계약과 일치할 것). 번들 재빌드·재검증·**재업로드 완료**.
2. **인접 간격 테스트가 동어반복이었다.** 세그먼트 테스트 3번째가 자기가 넣은 `SizedBox(width: 8)` 를 자기가 단언해, 테마에서 간격 규칙을 다 걷어내도 녹색이다. 즉 Review Focus 1 을 「커버됨」으로 보고했지만 **보장은 존재하지 않는다** — `shrinkWrap` 이 암묵적 48px 패딩을 없앴으므로 나란한 아이콘 버튼은 이제 맞닿는다. **리뷰어의 전제 교정**: WCAG 2.2 AA 2.5.8 은 24×24 이상이면 간격 없이도 충족이라 이것은 **접근성 위반이 아니라 조작성 변화**다. → 허위 단언을 지우고, DESIGN.md §6 에 「테마는 타깃 **크기**만 보장하고 **간격은 보장하지 않는다**; 간격은 화면·셸이 준다 — S3-P2/P3, `dp_chrome_bar` 가 첫 대상」을 명시.

**Minor 8건은 고치지 않고 기록만 했다**(원장 `execution-ledger.md` 의 `minor (deferred)` 줄). 다음 단계에서 쓸 것만 추리면: `dp_chrome_bar` 의 오버플로 예산이 아직 48px 기준이라 액션이 필요보다 일찍 메뉴로 접힌다(P2) · `dp_chrome_bar_account_gap_test` 와 `dp_nav_rail.dart:99-106` 의 주석이 48/44px 산술로 세상을 설명한다(P2 함정) · `test/golden/goldens/` 가 `--exclude-tags golden` 때문에 **아무도 안 보는 채로 낡았다**(P5 재기록 목록에 추가) · DESIGN.md §3 은 컨트롤 30px 이라 하지만 `TextField` 는 약 34px(입력 예외 미공개) · `DpDensity.rowPadding` 은 아직 소비자가 없다(P3).

리뷰어는 원장의 Ruling 11건을 전부 **동의**로 판정했고, 하나를 덧붙였다 — Task 7 의 판단이 `NOTES.md` 에서 멈추고 실제 산출물(업로드된 README)의 헤더를 놓쳤다는 것(위 1번).

## 7. 좌표

- frontend 브랜치 `feat/s3-p1-semantic-tokens-2-0-0`, 9 커밋: `19e790a`(반경·밀도·폭) → `83f7791`(rail→header) → `c5ca292`(매니페스트 2.0.0) → `9ac3b7c`(테마 30px) → `2c89ab1`(browser-ux 24) → `bbbd086`·`681d102`(DESIGN.md) → `390578c`(design-sync NOTES) → `e1bef21`(린트). base `de316b4`.
- home 브랜치 `feat/tokens-mirror-2-0-0`, 커밋 `44b8212`, base `17be1b8`.
- 워크트리(둘 다 **남겨 둠**): `D:/workspace/dpa/.worktrees/frontend-s3p1-20260924`(ledger·리뷰 패키지가 이 안에 있다 — 리뷰 끝나기 전에 지우지 말 것) · `D:/workspace/dpa/.worktrees/home-s3p1-mirror-20260924`(기준선 재기록을 여기서 한다). 그 밖에 `home-govtech-hotfix-20260917`(design-sync 검증기 `.ds-sync/` 스테이징 — 계속 필요) · `frontend-rebuild-20260923` · `gateway-sync-main-20260923` · `gitops-fix-applied-revision-20260924` · `gitops-fix-cors-env-20260924`(둘 다 로컬 전용 dev 브랜치, publisher 원본).
- 캠페인 스크립트 원본 `D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors/`(문서 레포에는 `plans/2026-09-23-release-campaign-…/` 로 복사돼 있다).
