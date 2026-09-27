# S3-P4 기준선 영향 누적 — P5 의 입력

> P4 의 각 Task 가 화면을 바꿀 때마다 한 줄씩 **추가만** 한다. P5(기준선 재기록)가 이 목록을 소비한다.
> P4 는 baseline 이미지를 재기록하지 않는다 — ET13 visual/a11y baseline 재승인은 사람 단계다.

## 렌더가 바뀐 화면

(Task 2·3·4·5·6·8·10·11·14·15·16·17 이 각자 한 줄씩 추가한다)

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
