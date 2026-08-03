# Handoff — ①전반 디자인 1단계(토큰) 완료, 2단계(레이아웃) 착수 대기 (2026-08-03)

> 이 세션은 **④ 오류 신고·문의 구현**(별도 핸드오프 참고) 이후 **①전반 디자인**으로 넘어가
> **1단계(토큰 계층)를 완결**하고, 사용자가 실측으로 찾아낸 진단 버그까지 고쳤다.
> **다음 세션은 2단계(레이아웃)부터 시작한다.**

## 0. 한눈에

| 작업 | 상태 | PR |
|---|---|---|
| ④ 오류 신고·문의 | ✅ 완결 | shared#54 · platform#44 · gateway#29 · frontend#102 · documents#90·#89 |
| ①디자인 1단계 — 토큰 | ✅ 완결 | **frontend#103**(스펙·계획) · **frontend#104**(구현 14커밋) |
| 진단 완주 불가 버그 | ✅ 해결 | **frontend#105** |
| ①디자인 2단계 — 레이아웃 | ⬜ **다음 세션 시작점** | — |

12개 레포 **오픈 PR 0건**. 전 레포 `develop` 체크아웃 상태.

## 1. 1단계에서 결정·구현된 것

**팔레트 = T2 잉크·앰버**(라이트 기본). 따뜻한 무채색 그라운드 + 앰버 하나. 앰버는 "성취"(진행률·스트릭·1차 행동) 전담.

프리뷰 **14안 × 4구간 × 라이트/다크 = 112건**을 만들어 비교한 뒤 사용자가 3안(T2·L1·T5)으로 좁히고, 전체 화면 목업으로 T2를 최종 선택했다.

- 탈락 **L1 크림·코럴**: 개성은 가장 강하나 Monaco·실행로그·코드렌더러가 **항상 다크**라 크림 배경과 큰 대비 → 화면이 두 세계로 쪼개진다.
- 탈락 **T5 카본·블루**: 대비·접근성은 최고지만 인디고→블루는 계열 이동이라 "개성 없음" 지적에 소극적.

**토큰 15개 → 32개.** 면 3단계(`bg`/`surface`/`surfaceMuted`) · 텍스트 3단계(+`textFaint`) · 사이드바 전용 6 · 차트 5 · 태그 2 · `accentSoft`/`accentLine`.

**기존 토큰명은 하나도 바꾸지 않았다** — `dpColors` 소비처가 47개 파일이라 개명하면 diff가 리뷰 불가능해진다. `primary`가 앰버를 가리키는 어색함은 **2단계에서 개명**한다.

라이트 기준값: `bg #FAF9F7` · `surface #FFFFFF` · `surfaceMuted #F2F0EC` · `railBg #1A1815` · `primary #B45309` · `primaryText #92400E`.

## 2. ★실측이 다섯 번 방향을 바꿨다★

계획서에 적힌 것을 그대로 믿지 말고 **돌려보라**는 교훈이 이 세션에서 반복 확인됐다.

1. **`ColorScheme.fromSeed` 시드가 인디고로 남아 있었다**(`dp_theme.dart:15`). `DpColors`만 바꾸면 Material 파생색(`secondary`·`surfaceContainer`·스톡 위젯 배경)이 옛 팔레트로 남아 **교체가 절반만 된다.** 계획이 놓쳤고 실행 중 발견했다.
   → **팔레트를 바꿀 때는 `DpColors`와 `seedColor`를 함께 본다.**
2. **`warning` 토큰 제거 제안을 철회했다.** 9회·10개 파일에서 쓰여 부적절. 의미별 3분할로 해결: 서비스 상태(점검·한도·오프라인·부분실패) → `textSecondary` 중립 / 구분용 → `chart4` / 진짜 경고 1곳(`review_panel:80`, 백엔드 severity 계약값)만 `warning`.
3. **약점 태그를 "구분용"으로 분류한 컨트롤러 지시가 오류였다**(최종 리뷰가 차단). 약점은 강점의 대립항이라 **의미가 있는 색**인데 `chart4`로 보내 강점 `#15803D`과 약점 `#0F766E`이 둘 다 어두운 청록이 됐다. 색맹 사용자에게 구별 불가 → DESIGN.md "색만으로 의미 전달 금지" 위반. → "강점"·"보강할 점" **소제목 병행 + 약점 중립화**.
4. **`chart2`가 자기 면 위에서 1.47:1이었다.** 대비 테스트가 차트 토큰을 **한 건도** 검사하지 않아 "34건 미달 0"에 차트가 빠져 있었다. → 값 재조정(3.23:1) + **차트 5색 대비 테스트 신설**.
5. **목 모드 진단은 원래부터 완주 불가였다**(사용자 실측). §4 참고.

## 3. 검증 자산 (2단계에서 재사용)

- **대비 44건**(텍스트·UI 34 + 차트 10) 미달 0. 검증 스크립트: `devpath-frontend/docs/superpowers/specs/2026-08-03-token-contrast-check.py`
- **다크의 `onPrimary`는 어두운 색**(`#1A1200`) — 앰버 위 흰 텍스트는 2.2:1 미달이라 라이트와 방향이 반대. `contrast(onPrimary, primary) ≥ 4.5` 단일 식이 이 반전을 지킨다.
- `DpColors` 32필드가 생성자·`copyWith`·`lerp` **7개 지점 전부 일치**(기계 검증).
- **전 라우트 캡처 절차** — Playwright, 브라우저 1회 기동, hash 라우팅으로 16개 순회:
  ```bash
  cd apps/web && flutter build web --release
  cd build/web && py -m http.server 8099
  # capture 스크립트: BASE=http://localhost:8099, 각 라우트는 window.location.hash 로 이동
  ```

### ⚠️ 캡처의 사각지대 (이번에 실제로 당했다)

대시보드 등을 보려면 `web_mock_fixtures.dart`의 `onboardingStatus`를 `PENDING → DONE`으로 임시 변경해야 하는데, **그러면 `/diagnostic`이 리다이렉트돼 진단 화면이 검증되지 않는다.** 파일명은 `diagnostic.png`인데 내용이 학습 경로 화면이었고, 그 상태로 "16라우트 확인 완료"라고 보고했다. 사용자가 직접 앱을 띄워 버그를 찾아냈다.

**2단계에서는 온보딩 상태별로 두 번 캡처하거나, 진단은 위젯 테스트로 따로 검증할 것.** 그리고 임시 변경은 **반드시 원복**한다(이번에 한 번 잊었다).

## 4. 진단 완주 버그 (frontend#105)

**증상**: 로그인 후 실력 진단에서 문항이 안 나오고 다음으로 넘어가지 않음.

**근본 원인 2겹**:
1. 로그인 회원 경로 픽스처가 통째로 없었다(게스트 경로만 존재). `diagnostic_controller.dart:33`이 `startMember()` → `POST /onboarding/assessments`를 치는데 키가 없어 404. → #104에서 6건 추가.
2. **그래도 완주는 안 됐다.** `AssessmentApi.next`는 본문이 `null`일 때만 null을 돌려주고 `DiagnosticController._advance()`는 그때만 `complete()`로 간다. `MockHttpAdapter`는 키 하나에 고정 응답 하나라 "문항 → 문항 → 없음"을 표현할 수 없어 같은 문항이 무한 반복. **게스트 흐름도 같은 한계라 목 모드 진단은 처음부터 완주 불가였다.**

**해결**: `MockFixture` 타입은 **불변**(26개 파일이 직접 참조). `sequences`를 선택 인자로 추가.
```dart
MockHttpAdapter(fixtures, {Map<String, MockSequence>? sequences})
typedef MockSequence = List<(int status, Object? body)>;  // 본문이 nullable
```
소진되면 마지막 항목 반복 → 완료 상태 유지. `sequences` 미지정 시 기존 동작 그대로(하위 호환 테스트로 고정).

**검증**: `회원 진단이 문항 2개를 거쳐 완주한다` 위젯 테스트가 문항1 → 답변 → **문항2로 넘어감** → 답변 → **진단 화면 이탈**까지 확인한다.

## 5. 다음 세션이 할 일 — ①디자인 2단계(레이아웃)

**1단계로 해결되지 않은 것**(사용자 지적 4축 중 "위계 밋밋"·"페이지마다 따로 놈"):

| 문제 | 위치 |
|---|---|
| Bento 그리드가 L자로 깨져 좌측 하단에 큰 빈 구멍 | 대시보드 |
| 차트에 축·값 레이블·기준선 없음 → 데이터가 장식처럼 보임 | 대시보드 |
| 카드 제목이 전부 같은 크기·굵기 → 무엇이 중요한지 안 보임 | 전 화면 |
| "배지" 카드가 전체 폭인데 내용은 칩 2개 | 대시보드 |
| **카드가 하나도 없음**(평평한 나열) — 대시보드와 같은 앱으로 안 보임 | 학습 경로 |
| 목록 행에 본문 미리보기·작성자·시간 없음 | 커뮤니티 |
| 데스크톱에서 FAB(모바일 패턴) 사용 | 커뮤니티 |
| **레일 256px 중 아래 700px가 완전히 빈 공간**, 하단 아이콘 3개 정렬 없음 | 전 화면 |
| 상단바가 얇고 제목만 — 브레드크럼·컨텍스트·액션 없음 | 전 화면 |
| **로고·브랜드 마크가 어디에도 없음** | 전 화면 |

**★중요★ 32개 토큰 중 15개(`rail*` 6종·`tag*` 2종·`accentSoft`·`accentLine`·`textFaint`·`chart1/2/3/5`)가 아직 소비자 0곳이다.** `dp_app_shell.dart`는 색을 전혀 지정하지 않고 Material 기본값을 쓴다. **2단계에서 셸에 배선해야 1단계 토큰이 실제로 값을 한다.**

### 착수 자료

- **프리뷰 아티팩트 2건**(목업에 2단계 해법이 이미 그려져 있다 — 레일 섹션 구분·브랜드 로고·상단바 브레드크럼·KPI 위계·차트 축·목록 미리보기):
  - 112건 비교: `https://claude.ai/code/artifact/c671eec2-5bd0-4fd0-b50b-441b4d751651`
  - 최종 3안 전체화면: `https://claude.ai/code/artifact/ed3f5c0c-11f4-448a-86ef-a67c708d3854`
- 스펙 `devpath-frontend/docs/superpowers/specs/2026-08-03-design-token-overhaul-design.md` §10에 범위 밖 목록
- 캡처 이미지(1단계 후) — 스크래치패드에만 있으므로 필요하면 재캡처

## 6. 이월 백로그

**디자인 관련**
- `primary` → `accent` 토큰 개명(47개 파일 파급, 2단계에서 화면 작업과 함께)
- `chart4`가 차트 토큰이자 분류용 UI 톤 겸용 → 별칭 토큰(`neutralAccent` 등) 분리 권장
- `DpTypography`에 아직 미정의 스케일 존재(`labelSmall`은 #104에서 추가됨)
- `DpStateScaffold:43`이 `iconColor` 기본값을 `textSecondary`로 두므로 상태위젯 3곳의 명시 인자는 중복

**기능 결함**
- 마이페이지에 **enum 원문 노출**: 학습목표 `CAREER_CHANGE`, 목표트랙 `BACKEND_SPRING` → 사용자용 라벨 매핑 부재
- 마이페이지 활동 카드 "커뮤니티 활동을 불러오지 못했습니다"
- `MockHttpAdapter`의 일반화된 404 카피가 **픽스처 누락을 브라우저에서 눈에 안 띄게** 만든다(debug 필드·콘솔에만 남음)

**④ 후속**: 자동 오류 리포팅 · 관리자 답변 확인 흐름 · 스크린샷 첨부 · 비로그인 접수
**검색**: shared 에러 핸들러 하드닝 · 고아 문서 정리 · 비동기 재색인 · nori 영숫자 토큰 분해
**신고(③)**: 콘텐츠 조치(숨김) · 제재 · AI 모더레이션 · 이의제기 · 신고자 결과 알림
**공통**: k3s 미적용(AWS 정지, ApplicationSet `targetRevision: main`)

## 7. 로컬 환경

⚠️ **Docker Desktop이 꺼져 있으면 shared 테스트 31건이 DB 연결 거부로 실패**한다 — 마이그레이션 문제로 오진하지 말 것.
⚠️ **platform-svc 전체 스위트는 Redis가 없으면 10건 실패**(Auth·RefreshToken·OAuth 계열). `docker run -d --name dpa-test-redis -p 6379:6379 redis:7-alpine`
⚠️ Windows에서 파이썬은 `python`이 아니라 **`py`**. Git Bash에서 한글 JSON은 UTF-8 파일 + `--data-binary @file`.
⚠️ platform-svc 테스트 DB는 **`devpath`**, community-svc는 `devpath_citest`.

컨테이너: `dpa-test-pg` · `dpa-test-redis`(이번 세션에서 신규 생성) 가동 중.
