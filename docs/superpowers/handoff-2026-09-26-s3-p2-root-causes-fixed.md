# 핸드오프 2026-09-26(밤) — S3-P2 머지 차단 2건 **근본 원인 규명·수정**, PR #233 develop 머지 완료

> 앞 문서 `handoff-2026-09-26-s3-p2-shell-implemented-browser-ux-blocked.md`(#175)가 「원인 미상·특성화만 완료」로 넘긴 두 건을 이 세션이 **둘 다 근본 원인까지** 규명해 고쳤다.
> **frontend PR #233 `feat/s3-p2-dp-web-shell` → develop 머지 완료(merge commit `7c12b5e5`, 20커밋).** CI 전원 통과.

## 1. 결론 먼저

| | |
|---|---|
| `browser-ux` | **17/17**(로컬·CI 모두). 직전 15/17 |
| CI 6잡 | `analyze-test` 4m9s · `browser-ux` 4m48s · `perf-gate` 22m50s · `produce-atomic-pair` 9m34s · `web-image-config-contract` off 7m14s / on 6m25s — **전부 pass** |
| 로컬 | `melos run analyze` 무이슈 · `melos run test` 전 패키지 통과(admin 156 · dp_design 299 · web 1011 · dp_core 174) · `melos run format` 0 changed |
| 운영 | 변동 없음. S3 는 P5(기준선 재기록)까지 끝난 뒤에 릴리스에 태운다(스펙 §9) |

앞 핸드오프의 직전 CI 실패 2건(`web-image-config-contract` ×2)은 코드 결함이 아니라 **레지스트리 502**였다(로그 실측). 이번 실행에서 그대로 통과했다.

## 2. 결함 ① 헤더가 시맨틱스 트리에 없다 — `BlockSemantics`

**근본 원인.** `apps/web` 은 `ShellRoute(builder: (_, _, child) => AppShell(child: child))` 로 셸을 두르고, go_router 가 넘겨 주는 `child` 는 **자체 Overlay 를 가진 중첩 Navigator** 다. `ModalRoute` 는 언제나 `ModalBarrier` 를 함께 올리며 `ModalBarrier.build` 는 무조건 `BlockSemantics(...)` 를 반환한다(`modal_barrier.dart:264`). 그 차단은 **같은 부모에서 먼저 그려진 형제**의 시맨틱스를 통째로 없앤다.

`Column[header, Expanded(body), footer]` 이므로 헤더와 (안쪽 Column 의) 브레드크럼만 사라지고 푸터는 남는다 — 앞 세션이 찾은 **「각 Column 에서 Expanded 앞 형제만 빠진다」 규칙의 정체**다. 기준은 `Expanded` 가 아니라 **페인트 순서**였다.

**수정.** 본문을 시맨틱 경계로 감싼다.

```dart
Expanded(
  child: Semantics(container: true, explicitChildNodes: true, child: body),
)
```

차단은 경계에서 멈춘다(`rendering/object.dart`: `if (configProvider.effective.isSemanticBoundary) return false;`, 그리고 `object.dart:4929` `config.isSemanticBoundary = container || …`). 루트 Navigator 로 뜨는 진짜 모달(`showDialog` 기본값)은 셸 **전체**보다 뒤에 그려지므로 여전히 정상으로 가린다.

★**앞 세션의 결론 「브라우저 한정이라 VM 으로 못 덮는다」는 틀렸다.** 본문을 중첩 Navigator 로 두면 **VM 위젯 테스트에서 몇 초 만에 재현**된다. 앞 세션의 셸 테스트는 본문이 `Text('본문')` 이라 Navigator 가 없었을 뿐이다. 그 경고 주석은 이번에 삭제하고 새 테스트로 대체했다★

**가른 방법.** 임시 엔트리포인트(`main_semdump.dart`)로 릴리스 웹 빌드에서 **프레임워크의 `SemanticsNode` 트리**를 콘솔로 덤프했다. 헤더가 프레임워크 트리에도 없음이 드러나 「엔진(DOM) 문제」 가설이 즉시 배제됐고, 그 뒤 VM 재현으로 넘어갔다.

**새 테스트** `packages/dp_design/test/shell/dp_web_shell_semantics_test.dart` 3건(compact 햄버거 · wide 주 메뉴/브랜드 · 브레드크럼) — 수정 전 red.

## 3. 결함 ② `/content` 390×200% 폰트 폭주 — `ChipThemeData.labelStyle` 의 `fontFamily` 누락

**근본 원인.** `chip.dart:1367` 은 `chipTheme.labelStyle ?? chipDefaults.labelStyle!` 로 고른다 — **병합이 아니라 대체**다. 앱 폰트는 기본값(`textTheme.labelLarge`)에만 있으므로, `DpTheme` 이 `labelStyle: TextStyle(color: c.tagText)` 를 주는 순간 **앱의 모든 칩이 `fontFamily: null`**, 즉 번들에 없는 패밀리로 그려진다.

연쇄:

1. 칩 라벨이 넘치면 Material 의 `TextOverflow.fade` 가 사라짐 폭을 재려고 **`'…'` 만 담은 문단을 따로 만든다**(`rendering/paragraph.dart:969`).
2. 그 글자가 등록 패밀리에 없으니 엔진이 Noto 폴백을 고른다. U+2026 의 후보 동점은 `_selectFont` 가 **`Noto Sans Symbols`** 로 깬다(`font_fallbacks.dart:284`) — 관측된 URL 과 일치.
3. **실패한 다운로드는 `downloadedFonts` 에도 `_codePointsWithNoKnownFont` 에도 기록되지 않는다** → 레이아웃마다 다시 요청 → 230건+ → `networkidle` 이 영영 안 오고 30초 타임아웃.

★배율 경계가 정확히 **2.0** 이었던 이유 = 그 배율에서만 칩이 넘친다(195% 는 3건으로 깨끗)★

**수정.** `DpTheme` 의 `chipTheme.labelStyle` 에 앱 폰트를 지정(`fontFamily: DpTypography.family`). **새 테스트** `packages/dp_design/test/theme/dp_chip_theme_font_test.dart` 3건 — 수정 전 red.

**성격.** 이 결함은 P2 가 만든 것이 아니다. `af1995c`(모바일 우선 재설계) 이후 줄곧 있었고 **develop 에도 동일**하다. P2 가 콘텐츠 열을 좁혀 드러냈을 뿐이다.

★**운영 렌더가 바뀐다** — 칩이 이제 (외부 gstatic Roboto 가 아니라) Pretendard 로 그려진다. **P5 기준선 재기록 대상에 포함해야 한다**★

**앞 세션 오진 2건 정정(코드 주석까지 수정).** 브레드크럼 구분자 `›` 도, compact 전체 경로 표시도 원인이 아니었다. compact 에서 마지막 세그먼트만 보이는 규칙 자체는 `DpChromeBar` 와 같은 설계 규칙이라 유지하되, 「폰트 폭주를 막는다」는 근거는 지웠다.

## 4. 남긴 가드

`tools/browser_ux/run.mjs` — 한 컨텍스트의 외부 요청이 **40건(정상 3~8)** 을 넘으면 그 라우트에서 멈추고 `external requests N > 40 (font fallback retry storm?)` 로 실패한다. 이 가드가 없으면 같은 결함이 다음에도 `waitForLoadState` 30초 타임아웃으로만 드러나 원인이 사라진다.

## 5. 후속 과제 — `apps/admin` 도 같은 결함(실측 확인)

`DpAppShell` 은 `Row[DpNavRail, Expanded(Column[DpChromeBar, Expanded(content)])]` 이고 `apps/admin` 도 `ShellRoute` 를 쓴다. VM 프로브로 확인한 결과 중첩 Navigator 본문에서 **레일·크롬바·브레드크럼이 전부 시맨틱스에서 사라지고 본문만 남는다**(web 보다 피해가 크다).

P2 는 web 셸 교체 범위라 이번 PR 에 넣지 않았다(사용자 결정). 수정은 같은 한 줄이다 — `DpAppShell` 의 본문을 `Semantics(container: true, explicitChildNodes: true)` 로 감싸고, 셸 테스트의 본문을 중첩 Navigator 로 바꿔 red 를 먼저 세운다.

## 6. 방법으로 남길 것

- ★**빌드 산출물 오염을 먼저 의심하라.** `apps/web/build/web` 에 앞 세션의 프로브 위젯이 남아 있었다(소스도 `git status` 도 깨끗). 스크린샷을 **눈으로 보고** 발견했다. 재현 전 깨끗한 재빌드가 첫 단계다★
- ★**mock 시퀀스는 호출마다 변한다.** 100%/200% 차이가 배율이 아니라 「두 번째 실행」일 수 있어 **순서를 뒤집어** 인과를 확인했다(폭주는 배율을 따라갔다)★
- ★**엔진 폴백 데이터는 오프라인에서 복호할 수 있다.** `flutter_web_sdk/lib/_engine/engine/font_fallback_data.dart` + `noto_font_encoding.dart` 의 인코딩을 옮기면 「어느 코드포인트를 어느 Noto 가 담당하는가」가 나온다(검증: 복호 총합 == 0x110000)★
- ★**서브셋이 요청한 범위 ≠ 폰트가 가진 글리프.** `UNICODES` 에 U+25A0–25FF 가 있어도 Pretendard 에 `▾`(U+25BE)가 없으면 안 담긴다. 실제 커버리지는 **패키지된 폰트의 cmap** 으로 확인한다★
- ★**구획 숨기기 쿼리 노브**: 화면에 `?hide=title,meta,progress,chips,markdown,ad` 를 임시로 달면 **리빌드 1회로 여러 조합**을 시험할 수 있다(칩까지 4회 실행으로 좁혔다)★
- ★**엔진은 다운로드에 성공한 폰트를 다시 요청하지 않는다.** 그래서 「합성 폰트를 응답해 폭주가 멎는지」는 커버리지 판정 신호가 **될 수 없다** — 이 이분탐색은 무효였고, 구획 제거로 갈아탔다★
- 결손 글리프가 **비가시**일 수 있다(여기서는 사라짐 측정용 `…`). 스크린샷에 두부(□)가 없다고 배제하면 안 된다.

## 7. 다음 착수점

1. **S3-P3**(공용 위젯 웹화) 계획 — P2 가 화면 파일을 한 줄도 안 건드렸으므로 범위가 그대로 남아 있다.
2. `apps/admin` 셸 시맨틱스(§5).
3. P5 기준선 재기록 목록에 **칩 렌더 변화**와 P1 반경 변경 골든 2건을 함께 올린다.
4. 운영 반영은 P5 뒤. gitops `base_sha` `5427fe1e` · 홈 prior 배포 `6f7a7e2b-522f-4bf1-b134-2dd2b345f83c` · ai-svc 증거 만기 **10/08**.
5. governance 룰셋 설계 충돌(et11)은 여전히 미해결.

## 8. 작업 환경 메모

- 워크트리 `frontend-s3p2-20260926` 에 실행 원장(git-ignored)이 있다. PR 은 머지됐으니 원장을 documents 로 옮기고 나면 지워도 된다.
- 로컬 재현 레시피(핀 Playwright `v1.55.0-noble` + `--network none` + `--only=<시나리오>`)는 앞 핸드오프 §5 그대로 유효하다. `--only` 는 쉼표로 여러 개를 받는다.
- Docker Desktop 은 켜 둔 상태다.
