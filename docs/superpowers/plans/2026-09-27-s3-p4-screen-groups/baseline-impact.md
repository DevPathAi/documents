# S3-P4 기준선 영향 누적 — P5 의 입력

> P4 의 각 Task 가 화면을 바꿀 때마다 한 줄씩 **추가만** 한다. P5(기준선 재기록)가 이 목록을 소비한다.
> P4 는 baseline 이미지를 재기록하지 않는다 — ET13 visual/a11y baseline 재승인은 사람 단계다.

## 렌더가 바뀐 화면

**세 PR 이 모두 끝났다** — 아래 세 절이 20화면 + 파생 5화면의 렌더 변화 전부다.

### PR-A — 학습 화면군 (Task 2~6)

- **`/dashboard` 오늘** (Task 2) — Bento 4열 그리드 → `.cols` 2열. KPI 카드 2장·진행 도넛·배지 스트립 위젯이 사라지고 그 숫자는 「진행」 키-값으로 옮겨졌다(데이터 손실 없음). 차트 패널의 그림자 제거. **추세 차트가 이제 좁은 폭에서도 보인다** — 옛 440 폭 게이트를 걷어냈다(새 사이드 칼럼이 본문 1120 의 1/3 ≈ 373px 이라 게이트를 남기면 데스크톱에서도 차트가 사라진다). 「이번 주 과제」 표·「왜 이 순서인가요」·「막히면」 신설.
- **`/path` 학습 경로** (Task 3) — 접힘 목록(`ExpansionTile` 4종) → 「N주 계획」 표, 사이드 패널 3개(완료 근거·진단 요약·설계 근거) 신설. 2열 분기 기준이 수동 `wide`(840) → `DpCols` 로 바뀌었다. **정정(독립 리뷰 I6)**: `DpCols` 는 `expanded || large` 를 2열로 보고 `expanded` 는 **840~1239** 이므로 840~1239 는 그대로 2열이다 — 「840~1239 가 1열이 된다」는 앞선 기록은 틀렸다. 분기 폭은 실질적으로 같다. legacy 완료 화면(flag OFF)은 블록 4개가 패널 테두리를 갖고 태그 칩이 중립색(`DpTag`)이 된다. 좌우 패딩이 셸 것만 남아 본문 좌측선이 왼쪽으로 옮겨진다.
- **`/content` 콘텐츠** (Task 4) — 본문 폭 **840 → 760**(`readableMaxWidth`), 진행률 바가 본문 위에서 사이드로, 개념 태그가 `Chip` → `DpTag`(글꼴이 번들 폰트로 바뀌고 배경이 `tagBg` 가 된다), 「현재 학습 미션」 패널 신설, 좌우 패딩이 셸 것만 남는다.
- **`/sandbox` 실습** (Task 5) — 페인 사이 테두리가 **2px → 1px**(페인마다 두르던 `Border.all` → 바깥 프레임 한 겹 + 사이 구분선), 바깥 프레임에 반경 8 과 넘침 자르기 적용, 페인 배경이 `surface` 로 명시된다. canonical 맥락 영역의 좌측선이 16 → 0(셸 거터 기준).
- **`/mentor` AI 멘토** (Task 6) — 맥락 캡슐이 **대화 위 → 사이드 칼럼**, 참고 자료도 사이드로, 말풍선 최대 폭이 **화면 비율(0.86) → 760**. legacy 는 참고 자료가 있을 때만 2열이 된다.

### PR-B — 커뮤니티 화면군 (Task 8·10·11)

- **`/community` 목록 3종** (Task 8) — 카드 나열 → **표**(칼럼·구분선·hover). 해결 배지가 「상태」 칼럼의 `DpStatusText` 로, 「답변 N · 추천 M」 한 줄이 숫자 칼럼 둘로. **빈 상태의 작성 버튼이 사라진다**(헤더 버튼만 — P3 이월 접근성 과제를 닫았다). 피드 광고와 「더 보기」가 목록 중간 → 표 아래로. 좌우 패딩이 셸 것만 남는다. **ET13 커뮤니티 fixture 3종(`web-community-free`·`-qna`·`-feedback`)의 visual/a11y baseline 재기록 대상.**
- **`/community/post/:id` 글 상세** (Task 10) — 본문 폭이 셸 폭(1120) → **760 좌측 정렬**. 댓글이 Material `Card`(그림자·반경 12) → `DpPanel`(테두리·반경 8).
- **`/community/:id` 질문 상세** (Task 10) — `.cols` 2열이 되고 **태그가 본문 아래 → 사이드 패널**로 옮겨지며 「관련 질문」 패널이 새로 생긴다(질문 상세를 열 때 요청 1건 증가). 답변 카드·비석·LCS 맥락 카드도 `DpPanel`.
- **커뮤니티 작성·수정 4화면** (Task 11) — 폼 폭 1120 → **760 좌측 정렬**, 유사질문 안내 `Card` → `DpPanel`. 수정 화면 둘의 로딩이 맨 스피너 → `DpLoading`(라벨 있음), 실패가 **`AppBar` + 평문** → `DpPageHeader` + `SupportableError`(문의 연결·재시도). 이 둘이 웹 앱의 마지막 `AppBar` 였다.
- 렌더 변화 없음: 검색어 유지(Task 9)는 라우팅 동작만 바꾼다.

### PR-C — 계정·온보딩 화면군 (Task 13~17)

- **`dp_design` 신설 3종** (Task 13) — `DpSteps`(단계 표시: 테두리 한 겹 안에 단계가 나란히, compact 에서 세로로 쌓인다)·`DpOptionRow`(선택 행: 행 전체가 타깃, 라디오 원)·`DpCheckRow`(동의 행: 체크 + 라벨·설명 + 우측 보조 링크). 세 위젯 모두 `FocusableActionDetector` 로 키보드 도달을 갖는다. 덧붙여 `DpLink.semanticsLabel`(Task 15)·`DpOptionRow.onSelect` nullable(Task 16)이 공개 API 에 늘었다. **대비 테스트에 `accentSoft` 위 `primaryTextStrong`·`textSecondary` 2조합 × 라이트·다크 = 4건을 더했다.**
- **`/login` 로그인** (Task 14) — 장식이 사라진다: 그라디언트 배경 패널·`_DecorativeOrb` 2개·`_StoryChip` 3개. 좌측이 배경 없는 글자 + `.flow` **제목+설명 2열 목록**(구분선)으로, 우측이 `DpPanel` 제목(시안 `.panel.signin`)으로 바뀐다. **2열 경계가 900 → 840**(`DpWindowClass.expanded` 는 **840~1239** 다)이므로 뒤집히는 구간은 **840~899**(구: 1열·480 중앙 / 신: 2열)다. 1240 에서는 구·신 모두 2열이라 차이가 없고, 그 구간은 ET13 기준선 폭(320/390/1240/1360) 어디에도 걸리지 않는다 — **눈에 가장 크게 띄는 변화가 기준선에서 누락된다.** 로그인 패널의 480 폭 제약이 사라져 우측 칼럼 폭(본문의 9/20)을 그대로 쓴다. 약관 문구 색 `textFaint` → `textSecondary`(WCAG). `brandRow` + 테마 토글은 화면 상단에 남는다. compact(390)에서는 스토리를 접는 기존 동작을 유지했다.
- **`/auth/callback` 인증 콜백** (Task 14) — 중앙 narrow **420 → 760**, 정렬이 stretch → center(버튼이 고유 폭이 된다), 오류색 `colorScheme.error` → `DpColors.danger`, **진행 상태도 같은 프레임**을 쓴다(옛 진행 상태는 폭 제약 없는 `DpLoading` 이었다).
- **`/consent` 동의** (Task 15) — 폭 **440 → 760**. 체크 목록이 `CheckboxListTile` 5개 → **테두리 패널 2개**(필수 2행 · 선택 3행)의 `DpCheckRow` 가 된다. 항목마다 **필수/선택 `DpTag` 가 새로 보인다**. 「전문 보기」가 `TextButton` → 인라인 링크. prefill 로딩이 맨 스피너 → `DpLoading`(라벨). 14세 미만 차단 화면 폭 **360 → 760**.
- **`/beta` 베타 대기** (Task 15) — 좌측 정렬 `DpPageHeader` 가 사라지고 **중앙 정렬 `DpTag` + `headlineSmall` 제목**이 그 자리에 온다. 폭 440 → 760. 상태 아이콘(`hourglass_top`/`lock_clock`) → 태그(`베타 대기`/`대기 만료`). 폴링 스피너 → `DpLoading('승인을 기다리는 중')`.
- **`/diagnostic` 진단 3화면** (Task 16) — **시작**: 칩 3개 단계 표시 → `.steps` 테두리 한 겹, 온보딩 surface 가 `DpPanel`, **트랙 선택 드롭다운 → 보기 행 8개**(화면이 그만큼 길어진다), 기대 결과 패널 → 키-값 3행. **문항**: 단계 표시 신설, 보기 `OutlinedButton` → 보기 행(라디오 원), 답변 실패 시 `✓ ` 글자 대신 선택 상태. **결과**: 단계 표시 신설, 패널 2곳의 리터럴 반경 16·12 → 카드 8, 「결과 형태 미리보기」 → 키-값, primary action 9갈래 → **`DpNextActionBand`**(예상 결과 문구가 새로 보이고 버튼이 `FilledButton` → 밴드의 `InkWell` 이 된다).
- **`/settings` 설정** (Task 17) — **절 순서가 바뀐다: 동의 관리 → 알림 → 계정 ⇒ 알림 → 동의 관리 → 계정.** `SwitchListTile` 4 + `ListTile` 3 → 테두리 패널 3개의 `DpRowLine`(우측 컨트롤). 본문이 **760 좌측 정렬**. 동의 행에 필수/선택 태그와 동의 시각 줄이 새로 보인다. 로딩 → `DpLoading`, 실패 → `SupportableError`(문의 경로).
- **`/mypage` 마이페이지** (Task 17) — 카드 5장 세로 나열 → **`.cols` 2열**. 프로필 카드가 배경 없는 `.prof`(아바타 + 소개 + 태그 3종)가 되고, AI 멘토·설정이 **사이드 칼럼**으로 옮겨진다. 설정 행의 선행 아이콘이 사라지고 우측 인라인 링크가 된다.
- **`placeholder`** (Task 17) — 중앙 narrow 760(옛 것은 폭 제약 없는 `DpEmpty`).

## ET13 결정적 투영이 바뀐 것

ET13 카탈로그가 고정한 투영은 렌더가 바뀌면 계약 테스트와 baseline 둘 다 영향을 받는다.

- `WebCommunityBoardProjection` (`apps/web/lib/src/features/community/presentation/web_community_board_projection.dart`) — Task 8
- `WebContentProjection` (`apps/web/lib/src/features/content/presentation/content_page.dart`) — Task 4
- `WebMentorContextProjection` (`apps/web/lib/src/features/mentor/presentation/web_mentor_context_projection.dart`) — Task 6

## browser-ux 시나리오 수정이 필요한 것

- 커뮤니티 목록에서 **「행이 클릭 대상」을 기대하는 시나리오** — 행 제스처가 `excludeFromSemantics` 로 시맨틱스에서 빠졌다. 접근성 컨트롤은 제목의 `DpLink.title` 이다. (Task 8)
- (PR-B 실측) 그 시나리오는 깨지지 않았지만 **기대값 갱신이 필요했다** — 목록 행의 탭 정지가 「제목 + 집계 한 덩어리」에서 **제목 링크 하나**로 줄었다(집계가 각자 숫자 칼럼이 되고 그 셀은 포커스 대상이 아니다). 정지 개수와 순서는 그대로다. `expectations.json` 을 실측 근거와 함께 갱신했다.
- (PR-B 실측) **`/path` 의 axe `scrollable-region-focusable`(serious)** — `DpWebTable` 이 `minWidth`(640)보다 좁은 폭에서 만드는 가로 스크롤 영역에 키보드로 닿을 수 없었다. 표 안에 포커스 가능한 셀이 있으면 통과하는데 「N주 계획」 표는 주차 상세 라우트가 없어 링크를 만들지 않았다. **포커스 노드를 스크롤 뷰 *안*에** 둬 고쳤다(밖에 두면 tabindex 가 overflow 요소가 아니라 그 부모에 붙는다).
- (PR-C 예고) **진단 화면의 보기 행이 `role="radio"` 로 투영되면 axe 의 `aria-required-parent` 가 radiogroup 부모를 요구한다.** 트랙·보기 두 묶음을 `Semantics(role: SemanticsRole.radioGroup)` 으로 감싸 선제 대응했다 — 웹 엔진의 실제 매핑은 로컬에서 확인할 수 없으므로 `browser-ux` 가 유일한 실측 수단이다.
- (PR-C 예고) **진단·결과 화면이 길어졌다** — 트랙 보기 8행과 `.steps` 가 더해져 기본 800×600 뷰포트에서 CTA 가 접힌다(페이지는 스크롤된다). 스크롤 위치를 가정하는 시나리오가 있으면 갱신이 필요하다.

## 시안과 1:1 이 되지 못한 것 — 백엔드 계약 변경이 필요하다

P4 의 규칙(「새 API 호출을 추가하지 않는다」)에 걸려 구현하지 않았다. 각 항목은 **실측 근거**를 함께 적었다.

| 시안 요소 | 왜 못 했는가 | 필요한 변경 |
|---|---|---|
| 커뮤니티 목록의 「작성」 칼럼·작성자 이름 | 백엔드 `PostSummaryView` 가 `long id, String boardType, String title, Long authorId, boolean solved, int upvoteCount, int replyCount, String excerpt` 8필드뿐이다 — 작성 시각도 작성자 표시 이름도 보내지 않는다 | `devpath-community-svc` 의 `PostSummaryView` 에 `createdAt`·작성자 표시 이름 추가 |
| 마이페이지 활동 표의 「작성」 칼럼 | 같은 이유 | 같음 |
| 오늘 화면 과제 표의 설명 줄(`.ex`) | `WeeklyTask` 에 설명 필드가 없다(`taskId·orderNum·taskType·title·required·contentId·contentSlug·completed·completedAt`) | 학습 경로 API 의 과제에 한 줄 설명 추가 |
| 오늘 화면의 「12주 중 N주차」 | 오늘 화면은 `LearningPath` 를 읽지 않아 총 주차 수를 모른다 | `GET /missions/current` 응답에 총 주차 수 추가 (또는 화면이 경로를 함께 읽게 — 요청이 늘어난다) |
| 질문 상세의 「이 주제 학습하기」 | 질문 태그를 학습 콘텐츠에 잇는 엔드포인트가 없다 | 태그 ↔ 콘텐츠 추천 엔드포인트 신설 |
| 진단 결과의 `.bars` 개념별 결과 | `AssessmentResult` 가 `diagnosedLevel`·`confidenceWeight` 둘뿐이다 — 개념별 점수가 없다 | 진단 완료 응답에 개념별 점수 맵 추가 |
| 마이페이지의 커뮤니티 활동 **표 전체** | 활동 데이터가 집계 수치뿐이다(`MyActivity(questionCount, answerCount)` + `DashboardSummary.completedContentCount`) — 제목·게시판·링크가 아예 없다. 「작성」 칼럼만 없는 것이 아니다 | 마이페이지용 최근 활동 목록 엔드포인트 신설 |
| 마이페이지 `.prof` 의 표시 이름 | `ProfileView` 에 이름 필드가 없다(avatar·bio·learningGoal·targetTrack·experienceYears) | 프로필 응답에 표시 이름 추가 |
| 마이페이지의 프로필 사이드 kv | (데이터는 있다) 같은 값을 바로 옆 **편집 폼**이 그대로 보여주므로 한 화면에 두 번 나온다 — 의도적으로 만들지 않았다 | 없음(판단) |

## P5 이월 (P3 리뷰 Minor 중 P4 가 닫지 않은 것)

- **`DpCols` 의 주석과 코드가 서로 모순이다**(독립 리뷰 I6 이 발견). `dp_cols.dart:10-12` 는 「경계를 `DpWindowClass.expanded`(**1240**) 에 두는 이유: 840~1239 에서 사이드가 약 270px 까지 눌려 2열이 읽히지 않는다」고 적었으나, 코드(`:32-35`)는 `expanded || large` 를 2열로 만들어 **그 840~1239 를 2열로 그린다**. 주석의 논증이 옳다면 코드가 `large` 만 2열이어야 하고, 코드가 옳다면 주석을 고쳐야 한다. `/dashboard`·`/path`·`/content`·`/mentor`·`/mypage`·질문 상세 6화면의 840~1239 레이아웃이 이 한 줄에 달려 있어 **P4 에서 고치지 않았다** — P5 가 어느 쪽이 의도였는지 정하고 기준선과 함께 확정한다.

- `dp_design` 의 새 리터럴 치수 7군데(`dp_status_text.dart:40`·`dp_web_table.dart:108`·`dp_row_line.dart:59`·`dp_row_line.dart:34`·`dp_list_lines.dart:44`·`dp_key_values.dart:34`·`dp_web_table.dart:25`)를 `DpTypography.labelMedium`/`bodySmall` 등 토큰으로. 렌더가 동일해야 하므로 기준선 재기록과 함께 확인하는 것이 싸다.
- `DpInteractiveCard` 가 프로덕션 소비처를 잃었는데 `DESIGN.md:177` 은 여전히 「클릭 카드 베이스」로 가리킨다 — DESIGN.md §3·§5 개정이 P5 의 명시 범위다.
- `DpNavRail` 의 레일 항목 라벨 중복(`'대시보드\n대시보드'`) — develop 에 있던 기존 결함이고 admin 전용이다.

## PR-A 실행이 드러낸 함정 (뒤 Task 와 P5 가 읽을 것)

- **`DpPanel` 안의 Material `ListTile` 은 프레임워크 단언에 걸린다.** 패널은 색을 가진 `DecoratedBox` 이고 `ListTile` 은 **가장 가까운 Material**(보통 `Scaffold`)에 배경·잉크를 그리므로 패널 표면이 그 잉크를 덮는다. Task 3 에서 실패 7건이 전부 이 한 원인이었다. 패널 안쪽에 `Material(type: MaterialType.transparency)` 를 한 겹 두면 해소된다. 근본 수정(`DpPanel` 이 스스로 잉크 표면을 갖기)은 359개 테스트를 가진 공용 위젯의 잉크 거동을 바꾸므로 **P5 판단 사항**이다.
- **같은 `ValueKey` 를 단 위젯을 `Row`/`Column` 의 형제로 두면 `Duplicate keys found` 로 죽는다.** 키는 자체 위젯으로 한 겹 감싼다(`dp_design` 의 `DpListLines._Line` 이 그래서 있다 — Task 5 의 `_PaneDivider` 도 같은 이유).
- **`ListView(children: …)` 는 뷰포트 밖 자식을 mount 하지 않는다.** 패널 개수를 세는 테스트는 뷰포트를 그만큼 키워야 성립한다(Task 3: 1280×2400).
- **테스트가 「문서가 뷰포트에 다 들어간다」에 의존하고 있을 수 있다.** `/content` 의 `_scrollPct` 는 `maxExtent <= 0` 이면 1 을 돌려주고, 그 1 이 진행률 flush 를 띄운다(dwell 만으로는 절대 flush 되지 않는다 — `ContentProgressTracker.record` 는 스크롤 전진 0.1 또는 완료 조건에서만 flush 한다). 사이드 패널이 1열에서 아래로 쌓이자 문서가 길어져 그 전제가 깨졌다 — Task 4 에서 뷰포트를 명시해 전제를 코드에 적었다.
- **`DpCols(stretch: true)` 는 부모 높이가 유한해야 한다**(1열에서 `main` 을 `Expanded` 로 감싼다). sliver 안이나 `SingleChildScrollView` 안에서 쓰면 죽는다.
- **가로로 잘리는 표는 axe `scrollable-region-focusable`(serious)에 걸린다.** `DpWebTable` 이 `minWidth` 보다 좁은 폭에서 만드는 가로 스크롤 영역은, 표 안에 포커스 가능한 셀이 하나라도 있으면(제목이 `DpLink.title` 인 표) 통과하지만 **링크가 없는 표에서는 숨은 칼럼이 키보드 사용자에게 완전히 막힌다**. PR-A 의 `browser-ux` axe 390 과 ET13 `web-path-current-week--a11y--w320--light--text200` 이 같은 한 노드를 잡았다. 수정은 `DpWebTable` 에 있다(스크롤 분기에만 포커스 노드 + 2px 링). **포커스 노드는 스크롤 뷰 안에 둬야 한다** — 밖에 두면 웹 시맨틱스가 tabindex 를 overflow 를 가진 요소가 아니라 그 부모에 붙여 axe 가 여전히 잡는다.
- **CI a11y 실패의 상세는 잡 로그가 아니라 아티팩트에 있다.** `browser-ux` 는 `evidence/browser-ux/latest.json` 을 업로드한다 — `gh run download <run> -n <artifact>` 로 받아 실패 시나리오의 `details.routes` 를 읽으면 규칙 id·impact·노드 수가 그대로 나온다. 잡 로그에는 규칙 이름만 있고 상세가 없다.
- **로컬 재현은 1~5분이면 된다**(Docker 가 켜져 있으면): 목 릴리스 웹 빌드(약 100초) → 핀 이미지 `mcr.microsoft.com/playwright:v1.55.0-noble` 에서 `npm ci`(네트워크 필요, 한 번) → `--network none` 으로 `node run.mjs --dist=... --only=axe`(axe 만 1분, 17 시나리오 전체 약 4분). Windows 에서는 `MSYS_NO_PATHCONV=1` + `D:/…` 형태 경로.

## PR-C 실행이 드러낸 함정 (P5 가 읽을 것)

- **`SemanticsFlag` 는 이 Flutter 에 없다.** `containsSemantics` 는 3.40 이후 deprecated 이고 `flutter analyze` 가 info 를 치명으로 다뤄 rc=1 이 된다 — 대체 매처 **`isSemantics`** 를 쓴다. 레포의 다른 관례(`flagsCollection` + `ui.Tristate`)는 로컬 3.47 전용 API 에 테스트를 묶는다(CI 는 3.44.1 핀).
- **`MouseRegion` + `GestureDetector` 만으로는 키보드가 닿지 않는다** — P3 의 `DpLink` 와 같은 결함이다. 계획이 지시한 그 형태로 구현해 테스트를 돌려 **RED 를 실증**했다(Tab 뒤 `primaryFocus` 가 `_FocusScopeWithExternalFocusNode` — 포커스가 라우트 스코프에 머문다). 라디오·체크는 폼 컨트롤이라 `FocusableActionDetector` 가 필수다.
- **`Semantics(container: true)` 만으로는 라벨이 올라오지 않는다** — 라벨과 설명이 각자 노드로 남아 `getSemantics(find.text(…))` 가 checked 플래그를 보지 못한다. `MergeSemantics` 한 겹이 필요하다(대신 라벨과 설명이 한 문장으로 읽힌다 — 라디오·체크에는 오히려 맞다).
- **`MaterialApp` 은 뷰에서 자기 MediaQuery 를 만든다** — 바깥에 `MediaQuery` 를 씌워 폭·배율을 주는 테스트는 조용히 무효다. `tester.view.physicalSize` / `tester.platformDispatcher.textScaleFactorTestValue` 를 쓴다(레포가 `dp_cols_test.dart` 주석에 이미 적어 둔 함정).
- **`ConstrainedBox` 의 렌더 폭은 자식의 고유 폭이다** — `maxWidth: 760` 을 단언하려면 렌더 크기가 아니라 **제약**을 읽어야 한다(실측 675).
- **`context.appTokens` 는 테마 확장을 요구한다** — `Theme.extension<AppTokens>()!` 이므로 `theme:` 없이 `MaterialApp` 을 띄운 기존 테스트가 `_TypeError` 로 죽는다. 리터럴 폭을 토큰으로 바꿀 때 그 화면의 모든 테스트 호스트에 `theme: DpTheme.light()` 를 줘야 한다.
- **시안의 예시 개수를 앱의 실제 개수로 착각하면 안 된다** — 동의 항목은 4개가 아니라 5개, 진단 트랙은 3개가 아니라 8개다. 8행을 펼치면 화면이 길어져 CTA 가 뷰포트 밖으로 나간다(계획이 예상하지 못한 부수효과).
- **`DpNextActionBand` 는 `InkWell` 이고 접근성 이름에 `, 예상 결과: …` 를 붙인다** — `widget<FilledButton>` 로 CTA 를 읽던 테스트와 `bySemanticsLabel('<라벨>')` 단언이 함께 깨진다. 밴드로 옮길 때 그 두 형태를 먼저 찾아야 한다.
- **`Row` 의 non-flex 자식은 주축 무한 제약으로 측정된다** — 좁은 폭·큰 배율에서 우측 컨트롤이 좌측 라벨을 짜부순다. 실측: `DpCheckRow` 의 390px·200% 라벨이 **폭 38.25 · 높이 495**(글자당 한 줄)였고 `Wrap` 으로 바꿔 187.5 · 135 가 됐다. **오버플로 예외가 나지 않으므로 `expect(takeException(), isNull)` 은 이 결함을 못 본다** — 200% 테스트는 폭을 직접 재야 한다. `DpRowLine` 이 P3 에서 이미 `Wrap` 으로 푼 문제이고 `brand_row.dart` 주석도 같은 함정을 적어 뒀다.
- **위젯 단독 테스트는 화면보다 폭이 넉넉하다** — 뷰포트만 390 으로 두면 행이 전폭을 받아 위 결함이 재현되지 않는다(판별력 없는 테스트가 된다). 실제 행 폭(390 − 페이지 패딩 − 패널 테두리 = 340)으로 좁혀야 한다.
- **셸 밖 bare 라우트는 본문 폭 상한을 스스로 줘야 한다** — 로그인이 480 캡을 없앴더니 1920px 에서 버튼이 820px 로 늘어났다. `contentMaxWidth`(1120)는 셸이 주는 값이고 `/login`·`/consent`·`/diagnostic`·`/beta`·`/auth/callback` 에는 셸이 없다.
- **`DpPageHeader.gutter` 기본값은 false 다** — 셸 안에서는 셸이 거터를 주므로 맞지만, bare 라우트에서는 제목이 x=0 에 붙는다. PR-A 가 기본값을 뒤집으면서 bare 라우트 호출부를 갱신하지 않아 `/consent`·`/diagnostic` 이 좌측선 3개를 갖고 있었다(PR-C 에서 닫음).
