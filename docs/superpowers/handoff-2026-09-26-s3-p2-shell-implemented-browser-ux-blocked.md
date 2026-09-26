# 핸드오프 2026-09-26 — S3-P2 셸 교체 **구현 완료**, `browser-ux` 2건으로 **머지 차단** · 원인 특성화까지 완료

> 앞 문서 `handoff-2026-09-26-s3-p1-complete-home-mirror-merged.md` 의 §4-1(S3-P2 계획)을 이 세션이 계획→구현까지 진행했다. 계획서 = `plans/2026-09-26-s3-p2-dp-web-shell.md`(documents #174, develop `7558082`).
> **PR = frontend #233 `feat/s3-p2-dp-web-shell`, 커밋 15개, 미머지.** 워크트리 `D:/workspace/dpa/.worktrees/frontend-s3p2-20260926` 는 **남겨 뒀다**(실행 원장이 그 안에 있다).

## 1. 결론 먼저

| | |
|---|---|
| 계획 Task 1~9 | **전부 구현·커밋됨** |
| CI 5잡(`analyze-test`·`perf-gate`·`web-image-config-contract`×2·`produce-atomic-pair`) | **pass** |
| `browser-ux` | **15/17** — 2건 실패로 **머지 불가**(레포 규칙: CI 녹색) |
| 로컬 | `dart format --set-exit-if-changed` 무변경 · `melos run analyze` SUCCESS · `melos run test` 전 패키지 SUCCESS(dp_design 109 포함) |
| 운영 | 변동 없음. 전부 브랜치에만 있다 |

## 2. 무엇이 만들어졌나

`packages/dp_design` 신설 5종 — `DpMenuButton`(웹에서 실제로 닫히는 메뉴 버튼; 2026-09-19 핸드오프의 **L3 를 흡수**) · `DpWebHeader` · `DpWebFooter` · `DpBreadcrumb` · `DpWebShell`.

`apps/web` — 목적지 모델이 index → **id(경로)** 기반(`kWebNavItems`·`webNavSelectedIdFor`). `shellDestinationIndexFor`·`breadcrumbFor` 는 그대로. 브레드크럼은 본문 상단으로, 오류 신고·문의는 푸터 링크로. `_AccountMenu` 삭제. **화면 파일은 한 줄도 안 바꿨다**(P3/P4 범위 보존).

`apps/admin` — `DpAppShell`·`DpNavRail`·`DpChromeBar`·`DpMobileNavigation` 그대로(156/156 통과). 실측상 admin 은 `compactDestinations` 를 안 넘기고 `destinations` 폴백을 쓰므로 `DpMobileNavigation` 은 **남기고** web 전용 파라미터 3개만 제거.

문서 — `DESIGN.md` §5·§9(web/admin 이 다른 셸을 쓴다), `docs/design/browser-ux-contract.md`, `docs/community-information-architecture/handoff.md` §9.6-5·§11(**L4**).

## 3. 독립 리뷰가 잡은 결함 — 8건 수정 완료

신선한 컨텍스트 리뷰어(Opus)가 **실증 프로브**로 찾았다. 내 단위 테스트는 8건 모두 통과시켰다 — 배치·브라우저 시맨틱·외부 요청을 재지 않았기 때문이다.

| 결함 | 실측 | 수정 |
|---|---|---|
| 푸터가 `Wrap`+`Align` 확장으로 항목마다 한 줄 | 41px 이라 적어 둔 것이 **153px**(200% 에서 225px), 링크 히트박스가 줄 전체(1072px) | `Center(widthFactor: 1)` — 41px 복귀 |
| 브레드크럼도 같은 원인으로 세로 적층 | 3세그먼트 **120px**, 구분자가 혼자 뜸 | 같은 수정 |
| 720~839 헤더 가로 넘침 | 720 → **67px**, 드롭다운이 검색 위에 겹침 | nav·검색 둘 다 `Flexible` |
| 짧은 화면에서 접힘 메뉴 잘림 | 667×375 → **107px**, 계정 항목 도달 불가 | 높이 뷰포트 60% 제한 + 스크롤 |
| 메뉴가 외부 라우트 변경에 안 닫힘 | 프로브 재현 | `DpMenuButton.closeWhenChanged` |
| 계정 버튼에 ▾ 없음(사용자 결정과 불일치) | — | ▾ 복원 |
| 포커스 순회 정책 누락 | CI 실측: '글 작성' 이 목록 행 뒤로 밀림 | `FocusTraversalGroup(WidgetOrderTraversalPolicy)` 승계 |
| compact 에서 브레드크럼 전체 경로 | `DpChromeBar` 는 마지막 세그먼트만 | 같은 규칙 |

★**`Wrap` 안의 `Align`/`Container(alignment:)` 는 최대 폭까지 늘어난다** — 이 레포가 이미 `DpChromeBar._crumbs` 에 `widthFactor: 1` 로 주석까지 달아 피해 둔 함정을 그대로 밟았다★

리뷰어의 Critical 중 **1건은 재등급해 고치지 않았다**: 「푸터 저작권이 키보드 트랩(WCAG 2.1.2)」 — develop 기준선 실측에도 마지막 정지가 8번 반복된다(대상만 게시글 행). P2 가 만든 것이 아니다.

## 4. 남은 2건 — 둘 다 원인 미상, 특성화는 완료

### 4.1 헤더가 시맨틱스 트리에 없다 (Critical)

**사용자 영향**: 폰에서 스크린리더 사용자가 내비게이션에 **전혀** 도달할 수 없다. 마우스로는 눌린다. `browser-ux` 의 `back-forward-boards`(390) 가 `getByRole('button', {name:'메뉴'})` 30초 타임아웃으로 실패하는 것이 **정당하다** — 게이트를 완화하지 말 것.

실측(로컬 재현, 실험 6회):
- 헤더는 **그려진다**(스크린샷 확인) · 시맨틱스 노드 **0개** · 같은 셸의 **푸터 링크 4개는 정상**
- 배제: 헤더 위치(본문에 넣은 동일 버튼도 안 나옴) · 버튼 종류 4가지(`OutlinedButton.icon`·`OutlinedButton`·`TextButton`·`IconButton(tooltip)`) · 시맨틱스 활성화 타이밍(강제 리빌드 후에도 동일) · `FocusTraversalGroup` · 폭(1240 에서도 동일)
- **남은 규칙**: 각 `Column` 에서 **`Expanded` 앞에 오는 형제만** 빠진다. 헤더·브레드크럼·본문 Column 에 끼운 프로브 4개가 모두 빠지고, `Expanded` 와 그 뒤(푸터)는 남는다. 두 `Column` 에서 일관된다.

**다음 후보**: 셸 구조를 `Column[header, Expanded(main), footer]` 에서 `Scaffold(appBar:)` 또는 `Stack` 기반으로 바꿔 본다(P2 범위를 넘는다). 또는 Flutter 웹 시맨틱스 쪽 이슈를 찾아본다.

### 4.2 `/content` 390×200% 가 안 가라앉는다 (Critical)

`browser-ux` 의 `overflow-and-targets` 390×200% 가 `waitForLoadState` 30초 타임아웃. **develop 기준선에서는 같은 라우트·배율이 통과한다 = P2 회귀.**

실측: 차단된 외부 요청이 100% 에서 **29건**, 200% 에서 **624~724건**. URL 별로는 **695× `notosanssymbols`** — 재시도 폭주로 `networkidle` 이 오지 않는다. 라우트별 누적값은 1~7번이 각 3건(정상)이고 **`/content` 하나에서 폭발**한다. `page_errors` 는 비어 있다.

★**틀린 추론 2회**: 「구분자 `›` 가 원인」(구분자가 `·` 이던 실행에서도 같은 요청이 났다 = 증상) · 「compact 브레드크럼 수정이 멎게 한다」(584× 로 그대로). 어떤 글자가 심볼 폰트를 부르는지 아직 모른다★

**다음 후보**: 200% 에서만 새로 그려지는 글자를 찾는다(ellipsis `…` 가 유력하나 브레드크럼은 아니었다 — 화면 콘텐츠 쪽일 수 있다). 또는 `tools/fonts` 서브셋에 해당 글자를 넣는다(`docs/design/font-diet.md`).

## 5. 로컬 재현 레시피 (이번 세션이 확립)

CI 6분 왕복이 **2분 실험**으로 바뀐다. 사용자 승인 아래 수행했다(레포 상시 방침은 「무거운 검증은 CI」).

```bash
export PATH="/d/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin:$PATH"
WT="D:/workspace/dpa/.worktrees/frontend-s3p2-20260926"

# 1) mock 릴리스 웹 빌드(약 80초) — CI 와 같은 --dart-define
cd "$WT/apps/web" && flutter build web --release --no-pub --no-web-resources-cdn \
  --dart-define=USE_MOCK=true --dart-define=MISSION_SPINE_ENABLED=true \
  --dart-define=MOCK_PROFILE=onboarded --dart-define=HOME_BASE_URL=http://127.0.0.1:1

# 2) 핀 이미지에서 시나리오 하나만(약 40초)
export MSYS_NO_PATHCONV=1
IMG='mcr.microsoft.com/playwright:v1.55.0-noble@sha256:ffc33305f7b4b04057ae4a0caa70aad4fde87454fb403a1a22e7f931707dfcf9'
docker run --rm --platform linux/amd64 --network none --ipc=host \
  -v "${WT}:/work" -w /work/tools/browser_ux "$IMG" \
  node run.mjs --dist=/work/apps/web/build/web --out=/work/evidence/browser-ux/local.json \
  --built-from=0000000000000000000000000000000000000000 --only=back-forward-boards
```

시맨틱스 DOM 을 직접 보려면 같은 이미지에서 `page.evaluate` 로 `document.querySelectorAll('flt-semantics')` 를 덤프한다(호스트는 `flutter-view > flt-glass-pane > flt-semantics-host`, shadow DOM 아님). 이번 세션의 프로브 스크립트는 커밋하지 않고 지웠다 — 위 한 줄이면 다시 만든다.

**러너에 남긴 계측(영구)**: 라우트별 실패 지점 · 중복 제거 전 외부 요청 총 건수 · URL 별 재시도 상위 5 · 라우트별 누적값 · 실패 시점 시맨틱스 덤프 · **실패 화면 스크린샷**(CI 아티팩트가 디렉터리째 올라간다).

## 6. 이 세션이 내린 판단 (전문은 워크트리의 실행 원장)

원장 = `D:/workspace/dpa/.worktrees/frontend-s3p2-20260926/.superpowers/sdd/2026-09-26-s3-p2-dp-web-shell/progress.md`(git-ignored — **워크트리를 지우면 사라진다**). Task 1~8 완료 기록과 판단 21건이 들어 있다.

굵직한 것만:
- 계획 Step 1 의 bootstrap 명령이 틀렸다 — 핀 Flutter 를 **PATH 앞**에 둬야 lockfile 을 받아들인다
- 검증 명령을 bare `flutter test` 에서 프로젝트 자신의 `--exclude-tags golden` 으로 — 골든 2건은 P1 반경 변경 이후 낡은 **선행 실패**(P5 재기록 목록)
- 테스트의 `addTearDown(handle.dispose)` → 본문 끝 `handle.dispose()`(핸들 검증이 tearDown 보다 먼저 돈다)
- 계획이 열거하지 않은 테스트 4건도 새 구조로 이동(옛 셸을 단언하던 것들)
- 샌드박스 `w >= 1024` 2페인 세로 오버플로는 **선행 결함**(폭 1200·높이 1033 = 옛 셸 예산에서도 39px) — P4 로
- 리뷰어 Critical 1건 재등급(§3 끝)

## 7. 다음 착수점

1. **§4.1 헤더 시맨틱스** — 셸 구조 변경을 시도하거나 Flutter 웹 이슈를 찾는다. 이것이 머지의 1순위 차단이다.
2. **§4.2 `/content` 폰트 폭주** — 200% 에서만 나오는 글자를 찾거나 폰트 서브셋에 넣는다.
3. 둘이 풀리면 `browser-ux` 녹색 → develop 머지 → **S3-P3**(공용 위젯 웹화) 계획.
4. 운영 반영은 **P5 뒤**(스펙 §9). gitops `base_sha` `5427fe1e` · 홈 prior 배포 `6f7a7e2b-522f-4bf1-b134-2dd2b345f83c` · ai-svc 증거 만기 **10/08**.

## 8. 작업 환경 메모

- **워크트리 `frontend-s3p2-20260926` 을 지우지 말 것** — 실행 원장이 그 안에 있고 git 에 없다.
- Docker Desktop 이 켜져 있다(이번 세션이 켰다). 로컬 재현에 계속 필요하다.
- `apps/web/build/web` 에 mock 릴리스 빌드가 남아 있다 — 재현 1단계를 건너뛸 수 있다(코드를 바꿨으면 다시 빌드).
