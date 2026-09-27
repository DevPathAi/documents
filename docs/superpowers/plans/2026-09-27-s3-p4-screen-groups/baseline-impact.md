# S3-P4 기준선 영향 누적 — P5 의 입력

> P4 의 각 Task 가 화면을 바꿀 때마다 한 줄씩 **추가만** 한다. P5(기준선 재기록)가 이 목록을 소비한다.
> P4 는 baseline 이미지를 재기록하지 않는다 — ET13 visual/a11y baseline 재승인은 사람 단계다.

## 렌더가 바뀐 화면

(Task 8·10·11·14·15·16·17 이 각자 한 줄씩 추가한다 — PR-A 의 Task 2~6 은 아래)

### PR-A — 학습 화면군 (Task 2~6)

- **`/dashboard` 오늘** (Task 2) — Bento 4열 그리드 → `.cols` 2열. KPI 카드 2장·진행 도넛·배지 스트립 위젯이 사라지고 그 숫자는 「진행」 키-값으로 옮겨졌다(데이터 손실 없음). 차트 패널의 그림자 제거. **추세 차트가 이제 좁은 폭에서도 보인다** — 옛 440 폭 게이트를 걷어냈다(새 사이드 칼럼이 본문 1120 의 1/3 ≈ 373px 이라 게이트를 남기면 데스크톱에서도 차트가 사라진다). 「이번 주 과제」 표·「왜 이 순서인가요」·「막히면」 신설.
- **`/path` 학습 경로** (Task 3) — 접힘 목록(`ExpansionTile` 4종) → 「N주 계획」 표, 사이드 패널 3개(완료 근거·진단 요약·설계 근거) 신설. 2열 분기 기준이 수동 `wide`(840) → `DpCols`(expanded 1240)로 바뀌어 **840~1239 구간이 1열이 된다**. legacy 완료 화면(flag OFF)은 블록 4개가 패널 테두리를 갖고 태그 칩이 중립색(`DpTag`)이 된다. 좌우 패딩이 셸 것만 남아 본문 좌측선이 왼쪽으로 옮겨진다.
- **`/content` 콘텐츠** (Task 4) — 본문 폭 **840 → 760**(`readableMaxWidth`), 진행률 바가 본문 위에서 사이드로, 개념 태그가 `Chip` → `DpTag`(글꼴이 번들 폰트로 바뀌고 배경이 `tagBg` 가 된다), 「현재 학습 미션」 패널 신설, 좌우 패딩이 셸 것만 남는다.
- **`/sandbox` 실습** (Task 5) — 페인 사이 테두리가 **2px → 1px**(페인마다 두르던 `Border.all` → 바깥 프레임 한 겹 + 사이 구분선), 바깥 프레임에 반경 8 과 넘침 자르기 적용, 페인 배경이 `surface` 로 명시된다. canonical 맥락 영역의 좌측선이 16 → 0(셸 거터 기준).
- **`/mentor` AI 멘토** (Task 6) — 맥락 캡슐이 **대화 위 → 사이드 칼럼**, 참고 자료도 사이드로, 말풍선 최대 폭이 **화면 비율(0.86) → 760**. legacy 는 참고 자료가 있을 때만 2열이 된다.

## ET13 결정적 투영이 바뀐 것

ET13 카탈로그가 고정한 투영은 렌더가 바뀌면 계약 테스트와 baseline 둘 다 영향을 받는다.

- `WebCommunityBoardProjection` (`apps/web/lib/src/features/community/presentation/web_community_board_projection.dart`) — Task 8
- `WebContentProjection` (`apps/web/lib/src/features/content/presentation/content_page.dart`) — Task 4
- `WebMentorContextProjection` (`apps/web/lib/src/features/mentor/presentation/web_mentor_context_projection.dart`) — Task 6

## browser-ux 시나리오 수정이 필요한 것

- 커뮤니티 목록에서 **「행이 클릭 대상」을 기대하는 시나리오** — 행 제스처가 `excludeFromSemantics` 로 시맨틱스에서 빠졌다. 접근성 컨트롤은 제목의 `DpLink.title` 이다. (Task 8)

## 시안과 1:1 이 되지 못한 것 — 백엔드 계약 변경이 필요하다

P4 의 규칙(「새 API 호출을 추가하지 않는다」)에 걸려 구현하지 않았다. 각 항목은 **실측 근거**를 함께 적었다.

| 시안 요소 | 왜 못 했는가 | 필요한 변경 |
|---|---|---|
| 커뮤니티 목록의 「작성」 칼럼·작성자 이름 | 백엔드 `PostSummaryView` 가 `long id, String boardType, String title, Long authorId, boolean solved, int upvoteCount, int replyCount, String excerpt` 8필드뿐이다 — 작성 시각도 작성자 표시 이름도 보내지 않는다 | `devpath-community-svc` 의 `PostSummaryView` 에 `createdAt`·작성자 표시 이름 추가 |
| 마이페이지 활동 표의 「작성」 칼럼 | 같은 이유 | 같음 |
| 오늘 화면 과제 표의 설명 줄(`.ex`) | `WeeklyTask` 에 설명 필드가 없다(`taskId·orderNum·taskType·title·required·contentId·contentSlug·completed·completedAt`) | 학습 경로 API 의 과제에 한 줄 설명 추가 |
| 오늘 화면의 「12주 중 N주차」 | 오늘 화면은 `LearningPath` 를 읽지 않아 총 주차 수를 모른다 | `GET /missions/current` 응답에 총 주차 수 추가 (또는 화면이 경로를 함께 읽게 — 요청이 늘어난다) |
| 질문 상세의 「이 주제 학습하기」 | 질문 태그를 학습 콘텐츠에 잇는 엔드포인트가 없다 | 태그 ↔ 콘텐츠 추천 엔드포인트 신설 |

## P5 이월 (P3 리뷰 Minor 중 P4 가 닫지 않은 것)

- `dp_design` 의 새 리터럴 치수 7군데(`dp_status_text.dart:40`·`dp_web_table.dart:108`·`dp_row_line.dart:59`·`dp_row_line.dart:34`·`dp_list_lines.dart:44`·`dp_key_values.dart:34`·`dp_web_table.dart:25`)를 `DpTypography.labelMedium`/`bodySmall` 등 토큰으로. 렌더가 동일해야 하므로 기준선 재기록과 함께 확인하는 것이 싸다.
- `DpInteractiveCard` 가 프로덕션 소비처를 잃었는데 `DESIGN.md:177` 은 여전히 「클릭 카드 베이스」로 가리킨다 — DESIGN.md §3·§5 개정이 P5 의 명시 범위다.
- `DpNavRail` 의 레일 항목 라벨 중복(`'대시보드\n대시보드'`) — develop 에 있던 기존 결함이고 admin 전용이다.

## PR-A 실행이 드러낸 함정 (뒤 Task 와 P5 가 읽을 것)

- **`DpPanel` 안의 Material `ListTile` 은 프레임워크 단언에 걸린다.** 패널은 색을 가진 `DecoratedBox` 이고 `ListTile` 은 **가장 가까운 Material**(보통 `Scaffold`)에 배경·잉크를 그리므로 패널 표면이 그 잉크를 덮는다. Task 3 에서 실패 7건이 전부 이 한 원인이었다. 패널 안쪽에 `Material(type: MaterialType.transparency)` 를 한 겹 두면 해소된다. 근본 수정(`DpPanel` 이 스스로 잉크 표면을 갖기)은 359개 테스트를 가진 공용 위젯의 잉크 거동을 바꾸므로 **P5 판단 사항**이다.
- **같은 `ValueKey` 를 단 위젯을 `Row`/`Column` 의 형제로 두면 `Duplicate keys found` 로 죽는다.** 키는 자체 위젯으로 한 겹 감싼다(`dp_design` 의 `DpListLines._Line` 이 그래서 있다 — Task 5 의 `_PaneDivider` 도 같은 이유).
- **`ListView(children: …)` 는 뷰포트 밖 자식을 mount 하지 않는다.** 패널 개수를 세는 테스트는 뷰포트를 그만큼 키워야 성립한다(Task 3: 1280×2400).
- **테스트가 「문서가 뷰포트에 다 들어간다」에 의존하고 있을 수 있다.** `/content` 의 `_scrollPct` 는 `maxExtent <= 0` 이면 1 을 돌려주고, 그 1 이 진행률 flush 를 띄운다(dwell 만으로는 절대 flush 되지 않는다 — `ContentProgressTracker.record` 는 스크롤 전진 0.1 또는 완료 조건에서만 flush 한다). 사이드 패널이 1열에서 아래로 쌓이자 문서가 길어져 그 전제가 깨졌다 — Task 4 에서 뷰포트를 명시해 전제를 코드에 적었다.
- **`DpCols(stretch: true)` 는 부모 높이가 유한해야 한다**(1열에서 `main` 을 `Expanded` 로 감싼다). sliver 안이나 `SingleChildScrollView` 안에서 쓰면 죽는다.
