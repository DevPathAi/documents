# Handoff — ④ 오류 신고·문의 스펙 확정 (2026-08-02, 2세션)

> 이번 세션은 **상태 검증 → ④ brainstorming → 스펙 확정·PR**까지 했다. **구현 계획(plan)은 쓰지 않았다** — 다음 세션이 `writing-plans`부터 이어받는다.

## 0. 한눈에

| 작업 | 상태 |
|---|---|
| 레포 상태 검증 | ✅ 완료 — 핸드오프와 실제 상태 불일치 0건 |
| ④ 오류 신고·문의 **스펙** | ✅ 확정 — **frontend PR #101 (OPEN, 미머지)** |
| ④ **구현 계획(plan)** | ⬜ **미착수 — 다음 세션 시작점** |
| ①전반 디자인 | ⬜ 미착수 (착수 조건 있음, §5) |

작업 순서는 사용자가 **③검증 → ④오류신고 → ①디자인**으로 지정했다.

## 1. 상태 검증 결과 (세션 시작 시점)

이전 핸드오프의 주장이 전부 실측과 일치했다.

- 컨테이너 3종 가동 중: `dpa-test-pg` · `dpa-test-es` · `dpa-test-kafka`
- 머지 상태: `frontend=1300a1a`(#100) · `community-svc=5f729e6`(#33) · `shared=85a7243`(#53) · `documents=d2593d0`(#88) · `gitops=759259e`(#56) — 전부 origin/develop과 동일
- **12개 레포 오픈 PR 0건**
- hikari 캡: `community-svc/src/test/resources/application-test.yml:10` `maximum-pool-size: 4` 반영 확인

### ⚠️ 다음 세션이 주의할 것 — 오래된 브랜치에 체크아웃된 레포 3개

| 레포 | 체크아웃된 브랜치 | 마지막 커밋 |
|---|---|---|
| `devpath-platform-svc` | `feat/refresh-reuse-detection` | 2026-07-28 |
| `devpath-gateway` | `fix/actuator-probe-permit` | 2026-07-27 |
| `devpath-ai-svc` | `feat/mentor-ollama-fallback` | 2026-07-29 |

**④ 구현은 platform-svc와 gateway를 모두 건드린다.** 작업 전 `git -C <레포> checkout develop && git pull` 을 반드시 먼저 할 것. 이 상태를 모르고 브랜치를 따면 7월 말 코드 위에서 작업하게 된다.

미커밋 변경은 전부 툴링 산출물이라 무해하다(`platform-svc/.gitignore`에 `.gstack/` 한 줄, 나머지는 `.omc/`·`.jqwik-database`).

## 2. ④ 스펙 — 무엇이 정해졌나

**문서**: `devpath-frontend/docs/superpowers/specs/2026-08-02-support-request-design.md`
**PR**: [devpath-frontend#101](https://github.com/DevPathAi/devpath-frontend/pull/101) — **OPEN, 머지하지 않았다**

### 사용자가 고른 것

| 질문 | 답 |
|---|---|
| 기능 성격 | 오류/버그 + 일반 문의 **통합 창구** |
| 소유 서비스 | **platform-svc** |
| 진입점 | 앱셸 상시 버튼 **+** 오류 화면의 `[문의하기]` (둘 다) |
| 자동 수집 범위 | **최근 API 실패까지** |
| 실패 기록 상세 | **응답 본문 일부 포함** → 마스킹이 범위에 들어옴 |
| 관리자 | 목록 + 상세 + 상태 전이 |
| 인증 | 로그인 필수 |
| 구조 | **A(클라 링버퍼) + B(정규화 자식 테이블)** 조합, C(자동 리포팅)는 후속 |

### ④가 ③ 재사용 불가인 이유 (스키마 실측)

`community_reports`의 세 요소가 전부 맞지 않는다 — `target_type CHECK IN ('POST','ANSWER','COMMENT')`, `UNIQUE(reporter_id,target_type,target_id)`(1인1회), 콘텐츠 위반용 `category` 6종. 이전 핸드오프의 예측이 스키마상 맞았다.

### 기획에 이미 있던 항목이다

④는 신규 발명이 아니라 **미구현 항목**이었다:
- `06_화면_기능_정의서:798` — 500 시 `[다시 시도] [문의하기]` + trace_id 복사
- `15_사용자_메뉴얼 §13` — "문의: 대시보드 → 지원"
- `33_개인정보_처리방침 §15-2` — "설정 > 고객지원"

처리방침 §자동수집에 "서비스 이용 기록·접속 로그·IP·디바이스 정보"가 **이미 고지돼 있어** 경로·UA 수집은 신규 고지가 필요 없다.

## 3. 조사에서 나온 사실 (계획 작성 시 그대로 쓸 것)

전부 파일을 열어 확인한 것이다. 추측 아님.

1. **`ApiClient.create`는 에러 정규화 인터셉터를 마지막에 두고 `handler.reject()`로 끝낸다**(`dp_core/lib/src/api/api_client.dart:28-39`). dio 5.9.2에서 `reject`는 `InterceptorResultType.reject`로 체인을 종료하므로(`.pub-cache/.../dio-5.9.2/lib/src/interceptor.dart:180`), **그 뒤에 등록된 인터셉터는 에러를 못 본다.**
2. 그런데 **index 0에 넣어도 안 된다** — `AuthInterceptor`가 refresh로 복구하는 일시적 401까지 기록된다. 정답은 **`Auth` 뒤 · `Normalizer` 앞**(`insert(length - 1, recorder)`). 현재 체인은 `[OnboardingGate, Auth, ErrorNormalizer]`(`apps/web/lib/src/providers/api_providers.dart`).
3. **platform-svc `SecurityConfig`에 `adminRoleConverter`(role→ROLE_*)가 이미 있다** — ③에서 community-svc에 없어 별도 작업이 필요했던 그 변환기다. `/admin/**` = `hasRole("ADMIN")`, 그 외 `authenticated()`.
4. **게이트웨이 `/admin/**`는 platform-auth 라우트가 선점**(`application.yml:12`) — ④는 소유가 platform-svc라 오히려 유리. 다만 **접수 경로 `/support/**`는 predicates에 신규 추가 필요**.
5. **platform-svc엔 마이그레이션이 없다**(`flyway.enabled: false`) — shared 중앙 관리. **③과 똑같이 shared 수동 발행이 임계 경로**다.
6. platform-svc 테스트 설정에 **hikari 캡 4가 이미 있다**(`@SpringBootTest` 31클래스) — ③에서 겪은 `too many clients` 붕괴는 여기서 재발하지 않는다.
7. `DpStateScaffold`는 주석부터 "**단일 1차 행동**"으로 못박혀 있다(`dp_state_scaffold.dart:6`) → 보조 액션은 **선택 파라미터(기본 null)로 추가**. `DpError` 호출부가 **19개 파일**이라 무회귀가 중요하다.
8. `app_shell.dart:70`의 `trailing` 슬롯은 **이미 명령 팔레트 버튼이 점유** → `Row`로 묶어야 한다. `DpAppShell` 자체는 무변경.
9. platform-svc 테스트 DB는 **`devpath`**(`application-test.yml`에 url 오버라이드 없음 → main의 기본값). community-svc는 `devpath_citest`라 **서로 다르다**.
10. `traceId`는 클라(`ApiException.traceId`)가 파싱하지만 **서버는 항상 null**을 보낸다(`ApiExceptionHandler.java:84`, 분산 트레이싱 미도입). 배관만 만들고 값은 비어 있을 것.

### 재사용할 코드 패턴 (계획에 그대로 인용할 것)

| 용도 | 파일 |
|---|---|
| nimbus 실서명 JWT 권한 테스트 | `devpath-community-svc/src/test/.../report/AdminReportControllerTest.java` |
| keyset 페이지네이션 + `{data,nextCursor,limit}` | `devpath-platform-svc/.../beta/AdminUserController.java` |
| 접수 컨트롤러(`@AuthenticationPrincipal Jwt`) | `devpath-community-svc/.../report/ReportController.java` |
| plain JPA 엔티티 스타일 | `devpath-platform-svc/.../ads/Advertisement.java` |
| admin 화면 4계층 구조 | `devpath-frontend/apps/admin/lib/src/features/reports/` |
| 제보 다이얼로그 | `devpath-frontend/apps/web/.../community/presentation/widgets/report_dialog.dart` |
| 게이트웨이 라우트 테스트 | `devpath-gateway/src/test/.../CommunityRouteTest.java` |

## 4. ★이번 세션이 남긴 교훈

### PROBE가 또 결정을 뒤집었다

마스킹 규칙 표를 셀프 리뷰로 "맞다"고 판단했는데, **실제로 12케이스를 돌려보니 깨졌다.** 초안은 JWT 규칙이 키=값 규칙보다 앞이라 `Authorization: Bearer eyJ...`가 `Authorization=[REDACTED] [TOKEN]`으로 반쪽 마스킹됐다. 순서를 뒤집고 값 패턴에 `(Bearer\s+)?`를 넣어 12/12 통과.

지난 세션(서식 에디터)의 "PROBE 실측이 취소선 결정을 뒤집음"과 **같은 종류의 사건이 스펙 단계에서 재현**됐다. 정규식·라이브러리 기본값처럼 **머릿속에서 실행되지 않는 것은 반드시 돌려볼 것.**

부수 효과: `py`로 실행해야 한다. Windows에서 `python`은 스텁이라 출력 없이 exit 49로 죽는다.

### 스펙 단계에서 잡은 두 번째 불일치

인덱스는 `(status, created_at DESC)`인데 keyset cursor는 유일 컬럼이어야 해 정렬 키(id)와 어긋나 있었다. 둘 다 id 기준으로 맞췄다(커밋 `eebe4f1`). **스키마를 쓸 때 "이 인덱스로 어떤 쿼리를 돌릴 것인가"를 같이 적지 않으면 이런 어긋남이 남는다.**

### 이전 세션 교훈이 설계 단계에서 실제로 쓰였다

③이 남긴 3가지(게이트웨이 `/admin/**` 선점 · `jwt()` 후처리기는 권한 검증 불가 · 델타 단언)를 **스펙 §4·§9에 선반영**했다. ③에서 "발견 후 수정"이었던 것이 ④에서는 "설계 시 회피"가 됐다. 핸드오프에 경위째 남기는 방식이 작동하고 있다.

## 5. 다음 세션이 할 일

### 즉시 (④ 이어받기)

1. **`writing-plans` 스킬로 구현 계획 작성** — 스펙 §10의 레포 순서를 Task로 분해.
   예상 Task 구성(스펙 작성 중 잡아둔 초안):
   `shared 마이그레이션+발행` → `platform-svc 마스커` → `platform-svc 접수 API` → `platform-svc admin API` → `gateway 라우트` → `dp_core 마스커` → `dp_core 링버퍼+인터셉터` → `dp_design 보조 액션` → `web 데이터/설정` → `web UI` → `admin 화면` → `documents §8.1.3`
2. 계획을 스펙 PR #101에 함께 담거나 별도 PR로 올린 뒤 **구현 착수**.
3. 착수 전 **platform-svc·gateway를 develop으로 체크아웃**(§1 경고).

### 그 다음 — ①전반 디자인

사용자 표현: **"대시보드 이외에는 디자인 개판, 대시보드도 좋은 디자인은 아님"**

**★착수 조건(사용자 명시, 변경 없음)★**
> 전체 구조에 맞는 디자인 테마를 **상세 리서치 + 100건 이상 프리뷰 + 모든 페이지 검토** 후 진행. **즉흥 개선 금지**, 대규모 사전 조사 필수.

## 6. 로컬 환경

컨테이너 3종이 **켜진 채로 남아 있다**(`dpa-test-pg` · `dpa-test-es` · `dpa-test-kafka`).

⚠️ 전체 스위트 실행 전 테스트 DB 재생성 권장:
```bash
docker exec dpa-test-pg dropdb -U devpath --if-exists devpath_citest
docker exec dpa-test-pg createdb -U devpath -O devpath devpath_citest
```
**platform-svc는 DB 이름이 `devpath`로 다르다**(위 명령은 community-svc용).

⚠️ Git Bash에서 한글 JSON을 `-d`로 넘기면 CP949로 깨진다 — UTF-8 파일 + `--data-binary @file`.
⚠️ Windows에서 파이썬은 `python`이 아니라 **`py`**.

## 7. 이월 백로그 (이전 핸드오프에서 변동 없음)

**검색**: shared 에러 핸들러 하드닝(`HttpMessageNotReadableException`이 400 아닌 **500**) · 고아 문서 정리 · 비동기 재색인 · nori 영숫자 토큰 분해 · CI 빌드 캐시
**신고(③)**: 콘텐츠 조치(숨김) · 제재 · AI 모더레이션 · 이의제기 · 신고자 결과 알림
**④에서 범위 밖으로 둔 것**: 자동 오류 리포팅(C안) · 사용자 답변 흐름 · 스크린샷 첨부 · 비로그인 접수
**공통**: 웹 UI 브라우저 E2E 미실시 · k3s 미적용(AWS 정지, ApplicationSet `targetRevision: main`)
