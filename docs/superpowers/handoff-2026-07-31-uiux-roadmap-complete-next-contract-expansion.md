# Handoff — UI/UX 로드맵(Phase 0~5) 완결 · 다음 세션 = 백엔드 계약 확장 4건 (2026-07-31)

> 이번 세션은 핸드오프 인수 후 **③ UI/UX 고도화 로드맵을 Phase 2~5까지 순차 완결**(각 Phase brainstorming → spec → plan → TDD 구현 → PR → CI green → 사용자 승인 머지)했다. 다음 세션은 **로드맵이 "계약 확장 시 후속"으로 이월한 3건 + 서식 텍스트 에디터 도입**을 다룬다.

## 이 세션 결과 (요약)

### ③ UI/UX 고도화 로드맵 — Phase 0~5 전부 develop 머지 완료
| Phase | 산출 | PR | merge |
|---|---|---|---|
| 0 기반 토큰/인터랙션 | AppTokens·DpInteractiveCard 등 | #86 | 316d6bf |
| 1 앱 셸·명령팔레트 | DpAppShell·DpCommandPalette | #87 | 55b0b70 |
| 2 학습자 대시보드 | DpKpiCard·fl_chart 도넛·Bento(staggered)·skeletonizer | #90 | 331b049 |
| 3 커뮤니티 피드 | DpListRow·SegmentedButton·SliverList·PinnedHeader·URL 동기 | #91 | 1bd9a0f |
| 4 admin 운영 콘솔 | DpDataTable(data_table_2)·행 MenuAnchor | #92 | 9e46caa |
| 5 학습 여정(mentor) | 채팅 하단-근처 추종 자동 스크롤 | #93 | 221882c |

- **frontend develop 최신 = `221882c`**. dp_design 신규 재사용 컴포넌트: `DpKpiCard`·`DpListRow`·`DpDataTable`(전부 `packages/dp_design/lib/src/data/`) + mentor 자동스크롤 상호작용.
- 도입 패키지(전부 MIT/BSD-3): `fl_chart 1.2.0`·`flutter_staggered_grid_view 0.7.0`·`skeletonizer 2.1.3`·`data_table_2 2.7.2`.
- spec/plan/리포트: `devpath-frontend/docs/superpowers/{specs,plans,reports}/2026-07-3x-*uiux*` (Phase별).

### 이번 세션에서 확인된 "계약 확장 시 이월" 항목 (다음 세션 대상)
각 Phase에서 **백엔드 데이터 계약이 없어 제외**한 기능들. 프론트 컴포넌트는 이미 구축돼 있어 **데이터만 오면 얹으면 된다**.

---

## ⏭ 다음 세션 작업 (4건)

### A. 대시보드 시계열 차트 (Phase 2 이월 · 백엔드 계약 확장)
- **현재**: `DashboardSummary`(`packages/dp_core/lib/src/models/dashboard_summary.dart`) = 스칼라 5종(`streakDays`·`progressPercent`·`nextTaskTitle`·`badges`·`completedContentCount`). **시계열 없음** → Phase 2에서 KPI 추세선·라인/바 차트 제외.
- **계약 확장(백엔드)**: learning-content-svc `DashboardController`(`/dashboard/me`)에 주간 학습량·진행률 히스토리 추가. 예: `weeklyActivity: [{date, minutes}]`, `progressHistory: [{date, percent}]`.
- **dp_core**: `DashboardSummary`에 시계열 필드 추가(freezed 재생성). **⚠️ mobile 파급**: dp_core 모델 변경은 web+mobile 전 소비 앱에 파급 → `melos analyze`(전 패키지)로 전수 확인([[devpath-uiux-elevation-roadmap]] Phase 2 교훈).
- **프론트(적용처 준비됨)**: `DpKpiCard`에 이미 `progress`/`trend` 슬롯 인터페이스 존재(Phase 2 미사용) → 미니 스파크라인 활성화. `fl_chart` `LineChart`/`BarChart`로 추세 카드 추가(`apps/web/.../dashboard/presentation/widgets/dashboard_body.dart`의 Bento에 카드 1개 추가).
- **시작점**: learning-svc 백엔드 → dp_core 모델 → web dashboard_body.

### B. 커뮤니티 제목 미리보기 (Phase 3 이월 · 백엔드 계약 확장)
- **현재**: `CommunityPostSummary`(`packages/dp_core/lib/src/models/community_post.dart`) = `id`·`title`·`boardType`·`authorId?`·`solved`·`upvoteCount`·`replyCount`. **본문/요약 없음** → Phase 3에서 OverlayPortal 제목 hover 미리보기 제외(행별 상세 N+1 회피).
- **계약 확장(백엔드)**: community-svc `PostSummaryView`(`GET /community/posts`)에 `excerpt`(본문 앞 ~140자 요약) 추가.
- **dp_core**: `CommunityPostSummary`에 `excerpt` 추가.
- **프론트(적용처 준비됨)**: `DpListRow`(Phase 3 신설) 제목 hover 시 `OverlayPortal`로 `excerpt` 미리보기(웹 전용). `apps/web/.../community/presentation/community_home_page.dart`의 `_postRow`.
- **시작점**: community-svc `PostSummaryView` → dp_core → web community_home.

### C. admin 벌크 액션 (Phase 4 이월 · 백엔드 계약 확장)
- **현재**: users `sanction`/`approve`, ads `remove` 전부 **단건 API** → Phase 4에서 벌크 액션바 제외.
- **계약 확장(백엔드)**: 벌크 엔드포인트 신설. 예: `POST /admin/users/bulk-sanction {ids[], action}`, `POST /admin/ads/bulk-delete {ids[]}`(platform/learning-svc 중 소관 확인).
- **프론트(적용처 준비됨)**: `DpDataTable`(Phase 4 신설, data_table_2 래핑)에 **다중 선택 체크박스 열** 추가(`data_table_2`는 `showCheckboxColumn`·`onSelectChanged` 지원) + **벌크 액션바**(`AnimatedSwitcher`로 등장, 로드맵 §5 Phase 4 AC). `apps/admin/.../{users,ads}/presentation/*`.
- **시작점**: 백엔드 벌크 API → DpDataTable 선택 기능 → admin users/ads 페이지 벌크바.

### D. 서식 텍스트 에디터(rich text) 도입 — 패키지 조사 완료
- **현재**: 커뮤니티 작성(`apps/web/.../community/presentation/{post_create_page,question_create_page}.dart`)이 **`TextField`로 `bodyMd`(마크다운) 입력**. 렌더는 `markdown_widget`(`DpMarkdown`).
- **요구(사용자)**: 서식 있는 텍스트(WYSIWYG) 에디터.
- **★ 추천(Context7 조사 완료): `flutter_quill` + `markdown_quill`**
  - `flutter_quill`(`/singerdmx/flutter-quill`, High reputation): WYSIWYG 리치 에디터. `QuillController.basic()` + `QuillSimpleToolbar` + `QuillEditor.basic`. **웹 지원**(`kIsWeb ? FlutterQuillEmbeds.editorWebBuilders() : ...editorBuilders()`). 저장=`Document.toDelta().toJson()`(JSON Delta) / 로드=`Document.fromJson`.
  - `markdown_quill`(`/tarekkma/markdown_quill`): **Delta ↔ 마크다운 변환**. → 에디터는 서식(WYSIWYG)이되 **저장은 마크다운으로 변환**해 **기존 `bodyMd` 계약·`markdown_widget` 렌더를 그대로 유지**. 로드맵 §1.3 "커뮤니티=마크다운 방향 확정"과 정합(에디터만 서식, 저장 포맷 불변).
  - 대안: `appflowy_editor`(블록 기반 Notion류, 강력하나 저장 포맷 자체·복잡), `fleather`(경량 Delta).
- **⚠️ 주의**: UI/UX 로드맵 §1.3은 flutter_quill/AppFlowy를 **"마크다운 방향으로 미도입 확정"** 했었다. 이 요구는 그 방향의 **재검토**다 → 다음 세션 brainstorming에서 **저장 포맷 결정**(권장: 마크다운 유지 + markdown_quill 변환 / 대안: Delta·HTML 전환은 백엔드 `bodyMd` 계약 변경 파급)이 첫 갈림길.
- **적용 형태(권장)**: `dp_design`에 `DpRichEditor` 래퍼(Layer 2) 신설 → post_create/question_create가 소비. 저장 직전 `markdown_quill`로 Delta→md 변환해 기존 create provider(`bodyMd`)에 전달.
- **시작점**: `cd apps/web && flutter pub add flutter_quill markdown_quill`(도입 시 §3 검증: Context7·CanvasKit·라이선스·리포트) → DpRichEditor → 작성 화면 적용.

---

## 작업 순서 제안
- **B·D는 프론트 비중이 크고**(B는 excerpt 필드 1개, D는 에디터), **A·C는 백엔드 계약 설계가 선행**(시계열 스키마·벌크 API). AWS 정지 상태를 감안하면 **B → D → (A·C는 백엔드 여건 확인 후)** 순이 로컬 진행에 유리.
- 각 작업은 독립적 → Phase처럼 개별 spec→plan→구현 사이클. 계약 확장(A·B·C)은 백엔드 레포(learning-content-svc·community-svc·platform) + shared 발행 + dp_core + 프론트의 **다중 레포 조율** 필요.

## 로컬 환경 메모 (다음 세션 재현)
- **AWS 정지 유지**(EC2·RDS stopped). 로컬 postgres 미기동 → 백엔드 테스트는 CI(postgres 서비스) 의존 또는 로컬 docker/postgres 기동.
- frontend 검증: 레포 루트에서 `dart pub global run melos run analyze`·`melos run test`·`melos run format`. 단일: `cd apps/<web|admin> && flutter test test/<path>`.
- **melos 게이트 습관**: `format`은 `--set-exit-if-changed`라 미포맷 시 FAILED — 매 커밋 전 `melos run format` 확인(이번 세션 Phase 2·3·4·5 모두 format 후속 정리 발생).
- **Bash cwd 리셋 주의**: 도구 호출 간 cwd가 루트로 리셋될 수 있음 → `flutter test`는 `cd apps/web &&` 프리픽스, git은 `-C <repo>` 절대경로.
- **uv env shim 이슈**: `~/.local/bin/env`(uv)가 표준 env를 가려 `env NAME=VAL cmd`가 조용히 실패([[devpath-uv-env-shim-breaks-env-cmd]]). 브레인스톰 비주얼 컴패니언은 `start-server.sh` 우회(export+node 직접, run_in_background)로 기동.
- **PR 흐름**: feature 브랜치 → `develop` PR → CI(`analyze-test`) green → **사용자 승인** → merge(`--merge --delete-branch`). develop 직접 push 금지.

## 이번 세션 기술 교훈 (프론트)
- **skeletonizer 2.x**: public `Skeletonizer`를 내부 `_Skeletonizer`로 렌더 → `find.byType` 미매칭, `key`로 특정.
- **fl_chart 1.x**: 도넛 `PieChartData`/`centerSpaceRadius` API는 0.x와 동일.
- **data_table_2**: Context7 미수록(R/React만) → **pub cache 소스로 API 실측 검증**. `DataColumn2`/`DataRow2` re-export로 소비 앱이 dp_design만 import.
- **SegmentedButton 전환**: 기존 `ChoiceChip` 테스트 갱신 필요. `find.byIcon(...).at(i)`로 다중 행 MenuAnchor 특정.
- **Fake 상태주입 테스트**: Notifier 화면 테스트는 `class _Fake extends Controller { @override build()=>초기; void push(...) }` + `provider.overrideWith(()=>fake)`로 결정적 제어(mentor 자동스크롤).

## 참조
- 로드맵 메모리: [[devpath-uiux-elevation-roadmap]](Phase 0~5 완결 기록).
- 로드맵 spec: `devpath-frontend/docs/superpowers/specs/2026-07-30-web-admin-uiux-elevation-roadmap-design.md`(이월 항목 원 근거 §5).
