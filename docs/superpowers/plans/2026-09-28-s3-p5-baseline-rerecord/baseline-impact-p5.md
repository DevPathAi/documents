# S3-P5 가 만든 렌더 변화와 게이트 상태 — 릴리스 캠페인의 입력

> 앞 문서: `plans/2026-09-27-s3-p4-screen-groups/baseline-impact.md`(P4). 이 문서는 그 뒤 P5 가 바꾼 것만 적는다.
> 실행 상세·판정 전문: 같은 폴더 `execution-ledger.md`.
> 좌표: PR-1 = frontend #239 → develop `c8edb82` · PR-2 = frontend #240.

## 1. PR-1 이 바꾼 렌더 (이월 판단 12건)

| 무엇 | 변화 | 영향 화면 |
|---|---|---|
| `DpNextActionBand` | 그림자 제거 + 배경·테두리를 시안 `.next` 대로 | 오늘 · 진단 결과 |
| `DpNextActionBand`(비활성) | 「사용할 수 없음: 이유」를 읽는다 + 중복 hint 제거 | 오늘 |
| `DpSteps` | 세 단계가 같은 높이(`IntrinsicHeight` + stretch) | 진단 3화면 |
| `DpPanel` | 안쪽에 `Material(type: transparency)` — 잉크가 패널 경계 안에서 일어난다. `DefaultTextStyle` 도 `bodyMedium` 에서 리셋된다(소비처 21파일 확인, 오늘 영향 없음) | 패널을 쓰는 전 화면 |
| `dp_design` 리터럴 11곳 | `DpTypography`·신설 `DpWebDensity` 토큰으로 — **줄 높이가 바뀐다** | 구분선 행·키-값·상태·보기 행 |
| `DpNavRail` | 라벨 중복 제거 | **admin 전용** |
| 마이페이지 `.prof` | 배지/프로필 kv 의 자리를 시안대로 되돌림 | 마이페이지 |
| 진단 보기 목록 | 마지막 행 뒤 여분 8px 제거 | 진단 문항 |
| `PlaceholderPage` | 삭제(소비처 0) | 없음 |
| `DpCols` | **코드 불변**, 주석을 코드에 맞춤 + 경계 4값 고정 테스트 | 없음(회귀 방지) |

## 2. PR-2 가 바꾼 렌더

| 무엇 | 변화 | 영향 화면 |
|---|---|---|
| `apps/web` 리터럴 `TextStyle(fontSize:)` **14곳** | 파생 스타일 `context.dpMeta`(12 / 1.6)·`context.dpBody(크기)` 로 — **렌더 동일**(시안이 line-height 를 덮지 않으므로 리터럴이 이미 시안 값이었다) | 커뮤니티 상세·질문 상세·게시판 미리보기·학습 경로 패널·문의 다이얼로그 |
| `qna_detail_page` 배지 2개 | `labelMedium` 으로 — 행간 19.2 → **16**(이 PR 의 **유일한** 의도적 행간 변화) | 질문 상세 |
| `DpSteps._Step` | 시안 `.steps li{padding:6px 12px;font-size:13px}` — 세로 패딩 4 → **6**, 글자 14 → **13** | 진단 3화면 |
| `/settings` 스위치 5개 | `Semantics(label:)` 로 이름을 갖는다 — **시각 변화 없음**, 스크린리더만 | 설정 |
| 픽토그래픽 이모지 3개 | 제거(DESIGN.md §4 규칙 · 시안에도 없다) — 「📚 작성자 학습 맥락」·「🤖 AI 초안」·「💡 비슷한 질문」 | 질문 상세 · 질문 작성 |

**ET13 결정적 투영에 영향이 있는 것**: 1절의 `dp_design` 토큰 전환(줄 높이)과 2절의 `DpSteps`·배지 행간·이모지 제거. 커뮤니티 fixture 3종과 진단 fixture 가 걸린다 — **ET13 baseline 재승인은 릴리스 캠페인 단계다**(4절).

## 3. 게이트 커버리지 — 8항목(7화면) → 21 라우트/프로필 조합

`browser-ux` 가 P4 가 바꾼 화면을 한 번도 보지 않았다. 도달 가능성을 `gateRedirect`(순수 함수)로 증명한 뒤 넣었다 — `onboarded` 빌드는 온보딩 라우트 5개를 **전부 돌려보내므로** 같은 `ROUTES` 에 적으면 리다이렉트 대상을 두 번 재는 테스트가 된다.

| 프로필 | 라우트 | 잡 |
|---|---|---|
| `onboarded` | 기존 8 + `/community/post/10` · `/community/post/10/edit` · `/community/1` · `/community/1/edit` · `/community/new` · `/community/new/post` · `/settings` · `/mypage` = **16** | `browser-ux` |
| **`guest`**(신설) | `/login` · `/diagnostic` · `/beta-pending` · `/auth/callback` | **`browser-ux-onboarding (guest)`**(신설) |
| **`consent`**(신설) | `/consent` | **`browser-ux-onboarding (consent)`**(신설) |

21개 조합 전부 자기 URL 에 도달했다(보고서 `location` 으로 확인, 리다이렉트 0건).

### 그 확장이 드러낸 결함 4건

| # | 무엇 | 성격 | 처리 |
|---|---|---|---|
| 1 | `/settings` 스위치 5개에 접근 가능한 이름이 없다 · axe `aria-toggle-field-name`(serious) | **앱 결함** | 고쳤다 |
| 2 | `/community/1` 폰트 폴백 폭주 — 외부 요청 **2651건**(notosanskr 3청크·notocoloremoji 2청크 × 약 435회). 원인 = 픽토그래픽 이모지 | **앱 결함** | 고쳤다(+5 → +2, 폰트 요청 0건) |
| 3 | 외부 요청 상한이 컨텍스트 **총합** 40 이었다 — 라우트당 +2 고정이라 16라우트면 넘는다. 러너가 그 자리에서 break 해 `/settings`·`/mypage` 를 아예 재지 못했다 | **러너 결함**(잠복) | 라우트별 증가분 + 라우트 수 비례 총합으로 |
| 4 | 최소 타깃을 한 번만 쟀다 — Flutter 는 스크롤 폴드에 잘린 위젯의 시맨틱스 노드를 잘린 rect 로 낸다(「로그아웃」 80×8 vs 뷰포트 높이면 80×30) | **러너 결함**(잠복) | 후보만 휠로 올려 다시 잰다 |

3·4 는 S3-P5 가 만든 것이 아니다. **라우트를 늘리는 어떤 PR 에서도 같은 일이 났을 것이다.**

### 좁게 유보한 것 — 에디터 4화면

`aria-command-name` · `aria-prohibited-attr`(둘 다 serious) on `/community/post/10/edit` · `/community/1/edit` · `/community/new` · `/community/new/post`.

원인은 `flutter_quill` **11.5.1 의 이중 툴팁**이다(`toggle_style_button.dart:121` 이 `Tooltip` 을 씌우고 그 안 `QuillToolbarIconButton` 이 `IconButton(tooltip:)` 으로 또 씌운다) — 바깥이 role 없는 라벨 노드, 안쪽이 라벨 없는 `role="button"` 노드가 되어 이름과 역할이 갈린다. 앱에 개별 버튼을 감쌀 자리가 없다.

유보는 라우트 + 규칙 id 단위로만 적었고, **낡으면 그 자체가 실패**다(위반이 사라졌는데 항목이 남으면 실패). 그 4화면의 다른 모든 serious·critical 과 오버플로·타깃은 그대로 게이트를 지난다.

## 4. ET13 판정 — 릴리스 캠페인의 단계다 (P5 의 작업이 아니다)

실측 근거:

- `evidence/et13/catalog.schema.json:61` 이 `baseline_status` 를 `"pending_external_review"` **상수**로 고정한다 ⇒ 커밋된 카탈로그는 `approved` 를 담을 수 없다.
- `evidence/et13/baselines/` 에는 README 하나뿐이고 승인된 기준선 이미지는 레포에 **없다**.
- 승인은 `.github/workflows/et13-baseline-approval.yml`(보호 환경 `et13-baseline-approval`, `workflow_dispatch`)이 만드는 외부 산출물이고 입력에 **`release_id`** 를 요구한다.

**캠페인이 할 일**: `produce-atomic-pair` 산출물로 `et13-baseline-approval` 을 디스패치한다(보호 환경 승인은 사람). `gh` CLI 가 리뷰어 계정이라 **직접 `gh workflow run` 하지 말고** `automation/dispatch-<release_id>` 디스패처를 쓴다.

**P5 의 몫**(완료): 카탈로그 정합성(13 fixture 의 `source_widget` 전부 실재) · `produce-atomic-pair` 녹색 유지.

## 5. perf 기준선

`built_from` **`a4753024`**(「font diet」 2026-09-17) → **`13d81c94`**(CI 36649266533 이 그 브랜치 커밋을 빌드했다) · `samples` 3 → **5**. 로컬 측정은 쓰지 않았다(머신 편차가 섞인다).

| 항목 | 옛 | 새 | 델타 |
|---|---|---|---|
| cold total | 17,611,459 | 17,617,612 | **+6,153 B (+0.03%)** |
| ┗ js | 6,031,309 | 6,036,419 | +5,110 — P2~P5 앱 코드 전부 = JS 의 0.08% |
| ┗ fonts | 5,718,459 | 5,718,071 | **−388** — P3·P4 위젯 교체로 아이콘 트리셰이킹이 더 줄었다 |
| ┗ other | 14,257 | 15,688 | +1,431 |
| warm total | 13,029 | 14,460 | +1,431 (**+10.98%**) — 회귀 아님(4 KB 바닥 아래) |
| `ready_ms` cold | — | — | **전 라우트 +0.0 ~ +1.7%** |

- `other` +1,431 은 cold·warm 에서 **같은 값**이고 원인은 develop 의 `c482b54`(2026-09-17 boot splash)가 `index.html` 에 더한 22줄이다. 같은 커밋이 `lcp_ms` 를 **`null` → 데스크톱 44~76 ms · 모바일 132~228 ms** 로 바꿨다(`fcp_ms` 는 `/dashboard` desktop cold 에서 5916 → 48) — 렌더가 빨라진 것이 아니라 브라우저에 LCP 후보가 생긴 것이다.
- **★ 그 LCP 가 절대 예산의 `ready_ms` 검사를 죽이고 있었다.** `tools/perf/gate.mjs` 는 「`lcp_ms` 가 있으면 LCP 를, 없으면 `ready_ms` 를」 판정했다. 옛 기준선은 20행 전부 `lcp_ms` 가 `null` 이라 모바일 cold 의 `ready_ms` 21.5초가 잡혔는데, 스플래시 뒤 전 행에 LCP 가 붙어 같은 21.5초가 **예산에서 사라졌다**. `enforce_absolute: false` 라 게이트 상태는 뒤집히지 않았지만, 나중에 그것을 `true` 로 켜는 사람은 작동하지 않는 임계를 믿게 된다. **PR-2 가 고쳤다** — 두 지표를 각각 본다(`gate.mjs` + `gate.test.mjs` + `budget.json` 주석). 고친 뒤 새 기준선은 `ready_ms` 경고를 다시 낸다(데스크톱 cold 약 3.85초 · 모바일 cold 약 21.5초).
- **provenance**: `built_from` 은 **`13d81c94…`**(브랜치 커밋)다. CI 의 `GITHUB_SHA` 는 `pull_request` 이벤트의 임시 머지 ref(`10f8a5b0…`)라 레포에 존재하지 않고 PR 이 닫히면 사라진다 — `expectations.json` 의 `recorded_from` 과 같은 관례(측정이 이뤄진 브랜치 커밋)로 적었다. 그 커밋은 **`f08ccdf`(픽토그래픽 이모지 제거) 이전**이다. perf 라우트 5개(`/login`·`/dashboard`·`/path`·`/mentor`·`/community`)에는 그 이모지가 없었고, **CI 2차가 최종 tip 을 이 기준선과 비교해 독립적으로 통과**했다(`perf-gate` 22m54s).
- **절대 예산 위반(예산을 올리지 않았다)**: `inp_ms` 6행이 200 ms 초과 — `/dashboard`(desktop cold 352 · warm 328 · mobile cold 608 · warm 520) · `/path`(desktop 304 · warm 304). `budget.enforce_absolute=false` 라 경고다.
- **★ INP 는 런 간 비교가 성립하지 않는다** — 같은 행에서 값이 붙었다 떨어진다(`/community` 4행은 옛 기준선에 값이 있었는데 이번엔 전부 null, `/dashboard/mobile/warm` 은 반대). 상호작용이 샘플 창에 잡혔을 때만 기록되기 때문이다. **INP 를 게이트로 쓰려면 측정 방식을 먼저 고쳐야 한다** — 캠페인 이후 과제.
- **★ `/login` 4행은 `/dashboard` 를 잰다** — `perf-gate` 가 `MOCK_PROFILE=onboarded` 로 빌드하고 그 빌드는 `/login` 을 돌려보낸다. 회귀 게이트로서는 매 실행 같은 것을 재므로 유효하지만 `/login` **자체** 렌더는 perf 게이트 밖이다. PR-2 가 axe·오버플로·타깃에는 `guest` 잡으로 넣었다. 정직한 해법은 guest 프로필 perf 레인이고 후속 과제다.

## 6. 게이트가 덮지 못하는 것

- **진단 문항·결과 화면**은 `/diagnostic` 안의 단계이고 URL 로 도달하지 않는다 ⇒ axe·타깃·오버플로 게이트가 보지 못한다. 클릭하는 새 시나리오가 필요하다(S3 이후 과제). PR-1 이 그 두 화면의 렌더를 바꿨으므로 **게이트 밖 변화**로 남는다.
- **`apps/admin`** 은 `browser-ux` 대상이 아니다. PR-1 의 `DpNavRail` 라벨 수정이 admin 전용이라 자동 게이트 밖이다.
- **에디터 4화면의 두 axe 규칙**(위 3절 유보).
- **`/login` 의 perf**(위 5절).

## 7. 시안과 1:1 이 되지 못한 것 — 갱신된 표

P4 의 9항목 중 **하나가 판단으로 닫혔고 하나가 「부분 닫힘」으로 정정된다.** 나머지 7항목은 **전부 백엔드 계약 변경**이 필요해 그대로다.

| 시안 요소 | 상태 | 필요한 변경 |
|---|---|---|
| 커뮤니티 목록의 「작성」 칼럼·작성자 이름 | 미해결 | `devpath-community-svc` `PostSummaryView` 에 `createdAt`·작성자 표시 이름 |
| 마이페이지 활동 표의 「작성」 칼럼 | 미해결 | 같음 |
| 오늘 화면 과제 표의 설명 줄(`.ex`) | 미해결 | 학습 경로 API 의 과제에 한 줄 설명 |
| 오늘 화면의 「12주 중 N주차」 | 미해결 | `GET /missions/current` 에 총 주차 수 |
| 질문 상세의 「이 주제 학습하기」 | 미해결 | 태그 ↔ 콘텐츠 추천 엔드포인트 신설 |
| 진단 결과의 `.bars` 개념별 결과 | 미해결 | 진단 완료 응답에 개념별 점수 맵 |
| 마이페이지의 커뮤니티 활동 **표 전체** | 미해결 | 마이페이지용 최근 활동 목록 엔드포인트 신설 |
| 마이페이지 `.prof` 의 표시 이름 | 미해결 | `ProfileView` 에 표시 이름 |
| 마이페이지의 프로필 사이드 kv 중복 | **부분 닫힘 — 자리를 옮겼다** | 아래 참조 |

### P4 M6c 정정 — 「닫힘」이 아니라 「부분 닫힘 + 남은 divergence」

PR-1 Task 8 이 배지/프로필 kv 의 **자리**를 시안대로 되돌렸다. 그러나 **시안의 마이페이지에는 편집 폼이 자체가 없다** — 헤더의 「프로필 편집」 버튼으로 빠진다. 구현은 편집이 인라인이라 목표 트랙·목표·경력 세 값이 사이드 kv 와 편집 폼에 **두 번** 나오고, compact(<840)에서는 위아래로 놓인다. 중복이 사라진 것이 아니라 자리를 옮긴 것이다.

**필요한 변경**(백엔드 아님, 프론트 범위): 편집을 별도 라우트로 분리한다(라우트·상태·테스트 신설). **S3-P5 범위 밖으로 이월** — 사용자 결정 2026-09-30.

## 8. P5 가 새로 발견한 divergence (전부 미해결, 다음 단계 입력)

| 무엇 | 근거 | 성격 |
|---|---|---|
| **토큰 계약이 시안보다 행간이 좁다** — `bodySmall`(13 / 20)·`labelMedium`(12 / 16) vs 시안의 1.6(20.8 · 19.2) | 시안 CSS 가 `font-size` 만 덮고 `line-height` 는 `body` 의 1.6 을 물려받는다 | **계약 하나의 결정**이고 통일하려면 시맨틱 토큰 계약(현 2.0.0)의 **버전을 올려야 한다**. DESIGN.md §2 에 사실만 적었다 |
| `post_detail_page.dart:358` 의 **11px** | 시안에 11px 이 아예 없다 | 크기를 유지했다(근거 없는 값이 살아 있다) |
| 에디터 툴바가 **12버튼**인데 시안 `.bar2` 는 **5버튼**(B·I·코드·링크·목록)이고 툴팁이 영어다 | 시안 CSS · 로컬 DOM 실측(`aria-label="Bold"` 등) | `buttonOptions.childBuilder` 로 5버튼을 직접 그리면 위 axe 유보와 함께 닫힌다. `flutter_quill` 11.6.0 에서 이중 툴팁이 고쳐졌는지도 확인한다 |
| 마이페이지 편집 폼 분리 | 7절 M6c 정정 | 프론트 범위, 이월 |

## 9. 캠페인 착수 전 확인할 것

1. **ET13 baseline 재승인**이 필요하다 — 1·2절의 렌더 변화가 커뮤니티·진단 fixture 를 건드린다. 절차는 4절.
2. **홈페이지 미러**: S3 는 토큰 계약 2.0.0 값을 바꾸지 않았으므로 홈 `assets/tokens.css` 미러 재동기화는 **불필요**하다(`dpMeta`·`dpBody` 는 파생 스타일이고 CSS 투영 대상이 아니다). 8절의 계약 버전 결정을 하게 되면 그때 미러가 대상이 된다.
3. **랜딩 시각이 바뀌는 릴리스**다 — 다음 `develop`→`main` 이 S3 전체를 운영에 올린다.
4. **★ 이 게이트들은 어느 브랜치에서도 「필수」가 아니다**(2026-09-30 실측): `develop` 은 보호 설정이 아예 없고(룰셋 0건 · classic 404), `main` 의 필수 체크는 **`analyze-test` 하나뿐**이다. 즉 `browser-ux`·`browser-ux-onboarding`·`perf-gate`·`produce-atomic-pair` 는 붉어도 머지를 **막지 못한다** — 구속력은 머지하는 쪽이 결과를 읽는다는 사실뿐이다. PR-2 가 커버리지를 넓힌 값은 그것을 필수로 등록할 때 온전해진다. 등록은 권한 변경이라 사용자 결정 사항이고(권한 자가 확장 금지), governance 룰셋 설계 충돌(et11)과 같은 자리에서 다룰 일이다.
