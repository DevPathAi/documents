# Handoff — ②커뮤니티 검색 완결 · ③신고 기능 완결 (2026-08-02)

> 이번 세션은 사용자 신규 요구 4건 중 **②검색을 끝내고(Task 5~9) ③신고 기능을 처음부터 끝까지(Task 1~7) 완결**했다. 남은 것은 **④오류 신고 메뉴 → ①디자인**이다.

## 0. 한눈에

| 작업 | 상태 | PR |
|---|---|---|
| **②커뮤니티 검색 1단계(ES)** | ✅ **완결** | community-svc #32 · gitops #56 · frontend #98/#99 · documents #86 |
| **③커뮤니티 신고** | ✅ **완결** | shared #53 · community-svc #33 · frontend #100 · documents #87 |
| ④각 페이지 오류신고 메뉴 | ⬜ 미착수 — **별도 spec 필요** |
| ①전반 디자인/테마 | ⬜ 미착수 — **사용자 지정 착수 조건 있음**(§5) |

**오픈 PR 0건.** 5개 레포 develop 동기화 완료:
`shared=85a7243` · `community-svc=5f729e6` · `frontend=1300a1a` · `documents=0647a32` · `gitops=759259e`

---

## 1. ②커뮤니티 검색 — Task 5~9 완결

이전 세션이 Task 1~4(백엔드 색인·검색)를 끝냈고, 이번에 나머지를 마쳤다.

- **Task 5** 재색인 배치 + `POST /community/admin/reindex`
- **Task 6** gitops ES 매니페스트(적용은 AWS 재가동 시)
- **Task 7·8** dp_core 모델 → 검색 UI(검색바·결과·빈결과·에러·더보기·`?q=`)
- **Task 9** 로컬 통합 스모크 + API 명세 §8.1.1

상세는 스모크 리포트 `devpath-frontend/docs/superpowers/reports/2026-08-02-community-search-smoke.md`.

### ★이 작업이 남긴 교훈 3가지 (신고 작업에서 실제로 다시 쓰였다)

**1. 게이트웨이가 `/admin/**`를 platform-svc로 선점한다.**
재색인 API를 `POST /admin/community/reindex`로 만들었더니 **어떤 클라이언트도 호출할 수 없는 엔드포인트**였다. MockMvc·CI 모두 게이트웨이를 거치지 않아 전부 green이었고 **코드 리뷰가 아니었으면 운영 장애 대응 중에 발견**됐을 것이다. → `/community/admin/reindex`로 이전.

**2. `jwt()` 후처리기는 권한을 검증하지 못한다.**
이 레포 컨트롤러 테스트는 전부 `.with(jwt().jwt(j -> j.subject("1")))`를 쓰는데, 이는 authority를 직접 주입해 `SecurityConfig`의 `role`→`ROLE_*` 변환기를 **우회**한다. 권한 테스트는 **nimbus로 실제 HS256 서명 JWT**를 만들어야 한다.
덧붙여 **community-svc에는 그 변환기가 아예 없었다**(`role` 사용처 grep 0건). 규칙만 추가했다면 ADMIN 토큰조차 403이었을 것이다.

**3. 롤백 없는 테스트에서 건수 단언은 델타로.**
이 레포 테스트는 트랜잭션 롤백 없이 실 데이터를 적재한다. `before = count()` 스냅샷 후 `before + N`을 단언한다. "현재 총수와 대조"는 검증 대상과 오라클이 같은 술어에서 파생돼 헐거워진다.

### CI에서 GHCR 이미지를 못 쓴다 → 직접 빌드로 전환

첫 CI가 `denied`로 실패. 원인은 토큰 스코프가 아니라 **패키지가 어느 레포에도 연결되지 않은 것**(`gh api orgs/DevPathAi/packages/container/devpath-elasticsearch` → `repository` 필드 없음). **public 전환은 조직 정책에 막혔고 REST API로도 불가**(가시성 변경 API 자체가 없다). → CI step에서 `docker build`(레지스트리 권한 무관, 총 2m57s).
⚠️ `permissions: packages: read`는 **유지**해야 한다 — ES와 무관하게 devpath-shared Maven 패키지 접근에 필요하다.

---

## 2. ③커뮤니티 신고 — Task 1~7 완결

### 무엇이 되나

사용자가 **글·답변·댓글**의 `⋮` 메뉴에서 6가지 사유(스팸/욕설/광고/중복/부적절/기타)로 신고하고, 관리자가 목록에서 **[기각]/[처리완료]**로 판정한다.

가장 큰 변화는 **admin 신고 화면이 껍데기에서 벗어난 것**이다 — `/admin/reports`를 호출하는데 그 백엔드가 4개 서비스 어디에도 없어(grep 0건) 목 픽스처로만 돌던 화면이었다.

### 설계 결정 (사용자 선택)

- 범위 = **신고 접수 + 관리자 판정**. 제재·콘텐츠 조치·AI 모더레이션은 후속
- 백엔드 = **community-svc**, 관리자 경로 **`/community/admin/reports`**
- 대상 = 글·답변·댓글, `targetType`+`targetId`로 일반화(접수 API는 하나)
- **1인 1회** UNIQUE + 자기 콘텐츠 신고 금지
- UI = `⋮` 메뉴 → 다이얼로그

spec/plan: `devpath-frontend/docs/superpowers/{specs,plans}/2026-08-02-community-report*`

### 계약 요점 (04_API_명세서 §8.1.2에 반영됨)

- `reportCount`는 **status 무관 총합**. 1인 1회 제약이 있어 곧 **신고자 수 = 심각도 신호**
- `targetPath`는 **서버가 조립**해 준다(프론트가 QNA/일반글 경로 규칙을 중복 구현하지 않게)
- 다형 참조라 **FK가 없다** → 대상만 사라질 수 있고 그때 `targetTitle`·`targetPath`가 null
- `REJECTED`를 `RESOLVED`와 분리 — 조치 기능을 붙일 때 이력이 쓸모를 가지려면 두 갈래가 남아야 한다

### ★shared가 임계 경로였다

community-svc에는 마이그레이션이 없고 **전부 devpath-shared 중앙 관리**다. 테이블 생성 → PR → 머지 → **수동 발행** 전에는 community-svc 테스트조차 돌지 않는다.

```bash
gh workflow run publish.yml --ref develop -R DevPathAi/devpath-shared
```

발행은 자동이 아니다(main push에만 워크플로가 돈다). 발행 후 `flyway_schema_history`에 새 버전이 `success=t`로 찍히는지 반드시 확인할 것.

### ★검색 작업 코드리뷰의 예고가 실현됐다

리뷰어가 남긴 말: *"`application-test.yml`에 `hikari.maximum-pool-size` 캡이 없다. 지금은 통과하지만 flake가 나면 첫 번째로 볼 곳이다."*

신고 테스트 4클래스가 늘자 `@SpringBootTest` 컨텍스트마다 뜨는 Hikari 풀(기본 10)이 postgres `max_connections(100)`를 넘겨 **`FATAL: sorry, too many clients already`로 전체 스위트가 무너졌다**. ai-svc 선례대로 **풀 캡 4**를 걸어 해소했다(`src/test/resources/application-test.yml`).

### 구현 중 테스트가 잡은 결함 3건

1. **`map(getter).orElseThrow()`가 작성자 null을 404로 오인** — AI 시드 답변(`authorId=null`)을 "대상 없음"으로 처리했다. `orElseThrow` 먼저 하고 getter를 부르도록 세 분기를 통일.
2. **답변 카드 레이아웃 회귀** — 아이콘 버튼(기본 48×48)이 카드를 높여 "답변 등록" 버튼이 뷰포트(600px) 밖으로 밀렸다. 버튼을 32×32 compact로 줄이고, 기존 테스트에 `ensureVisible` 추가(**위젯 하나만 늘어도 깨지는 뷰포트 의존이 원래 취약점**).
3. **admin 낱말 충돌** — 필터 라벨과 버튼에 "처리완료"가 겹쳐 같은 말이 두 뜻으로 쓰였다. 필터는 **상태**(처리됨), 버튼은 **행동**(처리완료)으로 구분.

### 검증

백엔드 **44클래스 141건**, 프론트 **web 282 · admin 47 · mobile 100 · dp_design 56 · dp_core 68** 전부 통과. 신규 43건(백엔드 27 + 프론트 16).

### 이번 범위가 남긴 한계

관리자는 **판정만 기록**하며 콘텐츠를 내릴 수단이 없다 — community-svc에 글 수정·삭제 기능 자체가 없다. 완화책으로 `targetPath`를 노출해 수동 대응 경로를 남겼다.

**근본 해결 시 권장 방향**: `status`를 비-PUBLISHED로 바꾸는 방식. `PostIndexer`가 비-PUBLISHED 글을 색인에서 자동 제거하므로 **숨김과 검색 정합성이 함께 해결**된다. 단, 숨김 경로에서 색인 이벤트 발행을 추가해야 한다(현재 발행 지점은 생성 2곳뿐).

---

## 3. 다음 착수 — ④각 페이지 오류 신고 메뉴

**③과 별개 기능이다.** 대상이 콘텐츠가 아니라 "서비스 오류"이고 저장소·화면이 다르다. 따라서 **brainstorming → spec → plan → 구현** 흐름을 새로 시작해야 한다.

착수 전 확인할 것:
- 오류 제보를 어디에 저장할지(community_reports 재사용? 별도 테이블? platform-svc?)
- 진입점(모든 페이지 공통 위치? 설정 메뉴? 플로팅?)
- 수집 정보(사용자가 쓴 설명 + 자동 수집할 컨텍스트 — 현재 경로·브라우저·시각 등)
- 관리자 확인 화면 필요 여부

③에서 만든 `community_reports`를 재사용하고 싶어질 수 있으나, **대상이 콘텐츠가 아니라 스키마가 맞지 않는다**(`target_type`·`target_id`가 무의미). 설계 단계에서 판단할 것.

## 4. 로컬 환경 상태

컨테이너 3종이 **켜진 채로 남아 있다**(다음 세션에서 그대로 쓸 수 있다):

| 컨테이너 | 용도 |
|---|---|
| `dpa-test-pg` | Postgres(pgvector). 테스트 DB `devpath_citest` |
| `dpa-test-es` | Elasticsearch 9.2.8 + nori (`devpath-es:local`) |
| `dpa-test-kafka` | Kafka KRaft 단일 노드(`apache/kafka:3.9.1`) — 이번 세션에 새로 만듦 |

⚠️ **전체 스위트 실행 전 테스트 DB 재생성 권장**:
```bash
docker exec dpa-test-pg dropdb -U devpath --if-exists devpath_citest
docker exec dpa-test-pg createdb -U devpath -O devpath devpath_citest
```
(`ActivityMockMvcTest`·`VoteGateMockMvcTest`가 데이터 누적으로 flake — 기존 격리 문제다.)

⚠️ **Git Bash에서 한글 JSON을 `-d`로 넘기면 CP949로 깨진다**(`Invalid UTF-8 start byte`). UTF-8 파일 + `--data-binary @file`을 쓸 것.

## 5. ①전반 디자인/테마 — 사용자 지정 착수 조건

사용자 표현: **"대시보드 이외에는 디자인 개판, 대시보드도 좋은 디자인은 아님"**

**★착수 조건(사용자가 명시)★**
> 전체 구조에 맞는 디자인 테마를 **상세 리서치 + 100건 이상 프리뷰 + 모든 페이지 검토** 후 진행. **즉흥 개선 금지**, 대규모 사전 조사 필수.

즉 코드를 고치기 전에 조사·비교·합의 단계가 먼저다.

## 6. 이월 백로그

**검색 관련**
- **shared 에러 핸들러 하드닝** — 잘못된 요청 본문(`HttpMessageNotReadableException`)이 **400이 아니라 500**으로 나간다(스모크 실측). 500 알람이 오염된다
- 고아 문서 정리(alias 스왑 재색인) · 비동기 재색인 · 중복 실행 가드
- nori가 영숫자 토큰을 쪼갠다(`SMOKE1`→`SMOKE`+`1`) — 식별자·버전 검색 품질 불리
- CI 빌드 레이어 캐시(현재 매 실행 Elastic CDN 의존)

**신고 관련**
- 콘텐츠 조치(숨김) · 제재 · AI 모더레이션 · 이의제기 (설계서 §7 TARGET)
- 신고자에게 처리 결과 알림(notification-svc 연동)

**공통**
- **웹 UI 브라우저 E2E 미실시** — 실API로 보려면 게이트웨이 + platform-svc(로그인) + web 전체 기동이 필요하다. 검색·신고 모두 위젯 테스트로 대체했다
- **k3s 미적용** — AWS 정지. ApplicationSet `targetRevision: main`이라 develop 머지로는 배포되지 않는다. 재가동 후 `develop → main` 릴리스 시 ArgoCD가 동기화한다
- GHCR `devpath-elasticsearch:9.2.8`는 CI에서 안 쓰이지만 **k3s 배포에는 필요**하다(PAT 기반 `ghcr-pull` Secret이라 동작). ImagePullBackOff가 나면 그 권한을 먼저 볼 것
