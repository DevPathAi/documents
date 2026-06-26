# 빌드 E 보고서 — MD3 슬라이스 #8 커뮤니티 Q&A 프론트 실API 전환 (2026-06-26)

> 빌드 D 게이트(`/community/**`) 위로 프론트 커뮤니티를 목→실API 전환. WSL+Bash 메인 직접 진행(antml 마찰 0건).

## ① 선행 확인
- 설계서 §221(frontend: `community_source` wire 교체 + 작성 FAB·답변 스레드·채택·투표·AI 초안 뱃지·유사질문 안내 + 위젯/컨트롤러 테스트 갱신 + `melos run analyze/test/format` 녹색).
- **백엔드 실계약 직접 검증**(추측 금지): `CommunityController`(`@RequestMapping("/community")`, gateway StripPrefix 없음) + DTO 직독.
  - 목록 `GET /community/posts` → `List<PostSummaryView>` **bare 배열**(커서/페이지네이션 **없음** — Explore 요약의 `{data,nextCursor,limit}`는 오류였음, 컨트롤러 시그니처로 반증).
  - 상세 `GET /community/questions/{id}`(목 시절 프론트는 `/community/posts/{id}` — **불일치**).
  - 작성/답변/채택/투표/유사/태그 엔드포인트·필드(camelCase) 확정.

## ② 플랜 경로
- E 전용 플랜 문서는 미작성(D와 동일). 설계서 §221 + 슬라이스 #7 F(mentor) 패턴 + 검증된 실계약으로 직접 TDD.

## ③ 단계별 변경 · 테스트 결과 (TDD, 단일 커밋 `93e3d50`)
| 단계 | 내용 | 테스트 |
|---|---|---|
| 1. dp_core 모델 | 목 단일 `CommunityPost` → 실계약 5종(`CommunityPostSummary`·`CommunityQuestionDetail`·`CommunityAnswer`·`SimilarQuestion`·`CommunityTag`), freezed 재생성 | `dashboard_community_test` 6종 GREEN |
| 2. data | `community_source` 전면 교체 — 8 프로바이더(목록·상세·작성·답변·채택·투표·유사·태그), `apiClient` 경유. 목은 `MockHttpAdapter` 픽스처(REST라 어댑터로 충분) | 컨트롤러/위젯 테스트로 override 검증 |
| 3. 상태·컨트롤러 | 목록(페이지네이션 제거)·상세(채택/투표/답변 → 상세 재조회 §231, 403 → actionError) | `community_controller_test` 3·`qna_detail_controller_test` 5 GREEN |
| 4. UI | 목록(작성자 이름 미제공 → 메타·solved 뱃지)·상세(답변 스레드·🤖 AI 초안 뱃지·채택·투표·답변 입력)·작성 FAB 페이지(디바운스 유사질문) | `community_home_page_test` 5·`qna_detail_page_test` 3·`question_create_page_test` 3 GREEN |
| 5. 라우터 | `/community/new`를 `:id`보다 우선(`int.parse('new')` 회피) | home 위젯 테스트(FAB 이동) |
| 6. 목 픽스처 | `web_mock_fixtures` 실계약 갱신(bare 배열·questions/{id}·작성/답변/채택/투표/유사/태그) | 위젯 테스트 간접 |

## ④ 게이트 (전부 녹색, 로컬)
- `melos run format` ✅ (0 changed)
- `melos run analyze` ✅ (web/admin/mobile/dp_core)
- `melos run test` ✅ — **web 139 · dp_core 48**(community 신규/갱신 19 포함)

## ⑤ 생성/수정 파일 (19개, dp_core + apps/web 범위)
- dp_core: `models/community_post.dart`(+ `.freezed`·`.g`), `test/models/dashboard_community_test.dart`
- apps/web lib: `app/router.dart`, `data/web_mock_fixtures.dart`, `features/community/{data/community_source, application/community_controller, application/qna_detail_controller, state/community_state, state/qna_detail_state, presentation/community_home_page, presentation/qna_detail_page, presentation/question_create_page(신규)}`
- apps/web test: `features/community/{community_controller, community_home_page, qna_detail_controller(신규), qna_detail_page, question_create_page(신규)}_test`

## ⑥ PR · CI
- PR **#35** → `develop` (DevPathAi/devpath-frontend). 커밋 `93e3d50`.
- CI(`analyze-test`): **PASS** (2m8s, run 28230072483).

## ⑦ 막힌 점 / 트러블슈팅
- **WSL Flutter 미설치**: `~/flutter`에 stable 셸로우 클론(Flutter 3.44.4 / Dart 3.12.2, `^3.12.1` 충족). `melos bootstrap`이 `sky_engine 없음`으로 1차 실패 → `flutter doctor`로 엔진 precache 후 성공. PATH는 `~/.zshrc`·`~/.profile` 등록. (메모리 wsl-build-environment)
- **build_runner 부수효과**: 무관 모델 `.freezed/.g`가 줄바꿈만(CRLF↔LF) 변경돼 status에 떠 `git checkout --`로 되돌려 PR 정리.

## ⑧ 알려진 한계 / 후속
- **채택 OWNER 게이팅**: `QuestionDetailView`에 질문 `authorId` 없음 → 클라이언트 작성자 판별 불가. 미해결 상태 버튼 노출 + 백엔드 403 우아 처리. 상세 authorId 노출은 후속.
- **목록 페이지네이션**: 백엔드 MVP bare 배열(커서 없음) → 프론트 단일 로드. 커서 도입은 백엔드 변경과 함께 후속.
- **태그 자동완성 UI**: 데이터 프로바이더만 두고 작성 폼은 free-text(§221 미요구).

## 비고
- 잔여: (1) develop CI 머지, (2) CLAUDE.md "메인 도구 직접 호출 금지" 규칙 정리(WSL 방침과 상충 — handoff #3), (3) 통합 릴리스(community·ai-svc·gateway·frontend develop→main + image/deploy).
