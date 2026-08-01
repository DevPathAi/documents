# Handoff — D(서식 에디터) 완결 · 커뮤니티 검색 1단계 Task 1~4 진행 (2026-08-01)

> 이번 세션은 ①이전 세션이 spec만 남긴 **D(서식 텍스트 에디터)를 구현·머지 완결**하고, ②사용자가 제기한 신규 요구 4건 중 **②커뮤니티 검색**에 착수해 **1단계 Task 1~4를 완료**했다. Task 5~9는 다음 세션으로 이관한다.

## 0. 한눈에

| 작업 | 상태 |
|---|---|
| **D 서식 텍스트 에디터** | ✅ **머지 완결** — frontend #97(`5b238cb`) · community-svc #31(`d8a5d38`) |
| **커뮤니티 검색 1단계** | 🟡 **Task 1~4 완료, 5~9 이관** — 두 레포 `feat/community-search` 브랜치에 push됨 |
| 신규 요구 ③신고 페이지 ④오류신고 메뉴 ①디자인 | ⬜ 미착수 (사용자 지정 순서: ②→③→④→①) |

---

## 1. D(서식 텍스트 에디터) — 완결

**PR**: frontend **#97**(merge `5b238cb`) · community-svc **#31**(merge `d8a5d38`, 백엔드 먼저 머지)
**결과**: flutter_quill 11.5.1 + markdown_quill 4.3.0. `DpRichEditor`는 `apps/web`(dp_design 아님). 저장은 `quillToMarkdown()`으로 기존 `bodyMd` 계약 불변 → 백엔드·dp_core·shared·`DpMarkdown` 무변경. web 테스트 199→253.

### spec 검토가 구현 전에 잡은 것 (5건)
착수 전 spec을 **코드·pub.dev 실측**으로 검토해 다음을 정정했다. 이 단계가 없었으면 전부 구현 중 사고로 드러났을 것:
1. 기존 테스트가 `"본문 (Markdown)"` 라벨이 아니라 **`find.byType(TextField)` 인덱스**에 의존 — 본문이 QuillEditor가 되면 3개→2개로 줄어 `.at(2)`가 범위 밖 예외
2. **flutter_quill 11은 `FlutterQuillLocalizations.delegate` 필수**인데 `app.dart`에 `localizationsDelegates` 자체가 없었음(누락 시 런타임 실패)
3. 툴바 플래그는 기본값 `true`가 다수 → 차단 항목 **전체 열거** 필요
4. 버전 호환 리스크는 실측으로 해소
5. `markdown` 직접 의존 불필요(전이로 충분)

### ★실측이 결정을 뒤집음
PROBE로 변환 출력을 찍어 **취소선이 `~~…~~`로 무손실 변환**됨을 확인 → 플랜의 잠정값(툴바 OFF)을 **ON으로 변경**.
실측표: bold `**x**` / italic `_x_` / h1 `# x` / bullet `- x` / ordered `1. x` / quote `> x` / inlineCode 백틱 / link `[t](u)`

### ★브라우저 스모크가 잡은 결함 4건 (전부 재현 테스트 선작성 후 수정)
1. **에디터 재생성 → IME 유실**(`52eda14`): 유사질문 카드가 `if (_similar.isNotEmpty) ...[위젯2개]`로 조건부 삽입되면 형제 인덱스가 밀려 `Key` 없는 `DpRichEditor`가 element 오매칭으로 재생성 → `"Range start N is out of text of length M"` assertion. **`const ValueKey`** 로 해결.
2. **★평문 구두점 백슬래시 오염**(`5d9fc4c`): `DeltaToMarkdown()` 기본 핸들러가 **평문까지** `.`·`#`·`(` 등을 무차별 이스케이프해 `bodyMd`를 오염(`안녕하세요.` → `안녕하세요\.`). 상세는 마크다운 렌더라 안 보이고 **피드 excerpt에 백슬래시 노출**. → 라이브러리 제공 **`escapeSpecialCharactersRelaxed`**(서식 있는 텍스트만 이스케이프)로 교체 **+ 서버 복원 병행**.
3. **리치 붙여넣기 크래시**(`5d9fc4c`): `enableExternalRichPasteDefault=true` → `<img>` HTML 붙여넣기가 image 임베드 생성 → 빌더 부재로 `UnimplementedError`, 에디터 복구 불가. → `QuillControllerConfig(clipboardConfig: QuillClipboardConfig(enableExternalRichPaste: false))` + `quillToMarkdown`을 `try` 안으로.
4. **FocusNode 매 리빌드 교체**(`5d9fc4c`): `QuillEditor.basic`이 `focusNode ?? FocusNode()`로 호출마다 새로 만드는데 `DpRichEditor`가 StatelessWidget → setState마다 IME 끊김(**1번과 같은 증상의 두 번째 경로**). → **StatefulWidget 전환**(FocusNode/ScrollController 소유·해제).

### 백엔드(community-svc #31)
`Excerpts`에 **lookbehind `(?<!\\)`** + `MD_ESCAPE` 복원. **순서가 중요**: 마커제거(이스케이프 보호)→복원→공백정리. 복원을 먼저 하면 `a\*b`→`a*b`→마커제거가 `*`를 지워 `ab`로 손상. ExcerptsTest 6/6.

### ★한글 IME 판정
최초 1회 조합이 어색하나 **제목 `TextField`(일반 위젯)에서도 동일 재현** → Flutter Web CanvasKit 공통 특성이지 flutter_quill 고유 문제가 아님 → **폴백(Fork 3) 전환 사유 아님**(폴백도 TextField 기반이라 무해결). **대조 실험이 판정을 갈랐다.**

### ★최대 교훈
**서드파티 "기본값"도 명시적 결정 대상이다.** 툴바 플래그 27개는 1:1 대조하면서 `DeltaToMarkdown()`·`QuillEditor.basic()`·`enableExternalRichPaste`의 기본값은 검토하지 않아 Important 3건이 전부 거기서 나왔다.
**테스트 코퍼스는 도메인 실제 입력을 닮아야 한다** — 기존 9개 테스트가 이스케이프 대상 문자를 한 글자도 안 써서 오염을 완전히 가렸다.

### 기타 교훈
- 스모크용 목 픽스처 임시 변경(`onboardingStatus` PENDING→DONE)이 golden_path 3건을 깨뜨림 → **테스트 실행 전 반드시 원복**
- `@experimental` API 사용 시 `experimental_member_use` 경고로 melos analyze 실패 → `// ignore_for_file` 필요

### 미수정 기존 결함(범위 밖)
목 픽스처의 **생성 응답 id와 상세 조회 id 불일치**: `POST /community/posts`는 id 30 반환인데 `GET /community/posts/30` 픽스처 없음(`/10`만). 질문도 99 vs 1. → 목 프로토에서 **작성→상세 이동이 `no mock` 404**로 끊긴다.

---

## 2. 커뮤니티 검색 1단계 — Task 1~4 완료

### 2.1 설계 결정 (사용자 선택)
- 검색 목적 = **하이브리드(키워드+의미) + 조건 필터**
- 의미검색 범위 = **모든 글로 임베딩 확대**(→ 2단계)
- 엔진 = **Elasticsearch**(Postgres pg_trgm+pgvector 대안 대신. 설계서 §8.3 방향·nori 한국어 품질 우선)
- 도입 범위 = **로컬 구현·검증 + gitops 매니페스트**, k3s 적용은 **AWS 재가동 시 이월**
- 벡터 위치 = **pgvector 유지**(ES dense_vector 미사용), 2단계에서 앱이 RRF 융합
- 색인 동기화 = **Kafka 경유**, 발행은 **기존 Outbox 패턴**
- 색인 대상 = **글만**(제목·본문·태그), 하이라이팅 포함
- UI = **커뮤니티 홈 상단 검색바** + `?q=` URL 동기

**2단계 분해**: 1단계=ES 키워드 검색 전체(인프라·색인·API·프론트 UI) / 2단계=임베딩 전체 확대 + RRF 하이브리드 융합(별도 spec)

### 2.2 문서
- spec: `devpath-frontend/docs/superpowers/specs/2026-08-01-community-search-design.md`
- plan: `devpath-frontend/docs/superpowers/plans/2026-08-01-community-search.md` (9 Task)
- 둘 다 `feat/community-search` 브랜치, 최신 커밋 `c4550ec`

### 2.3 ★실측 확정값 — 다음 세션은 이 값을 전제로 진행할 것
| 항목 | 확정값 |
|---|---|
| ES 클라이언트 | `spring-boot-starter-data-elasticsearch`(Boot 4.0.7) → 저수준 **`co.elastic.clients:elasticsearch-java:9.2.8`**. `ElasticsearchClient` 빈 자동 주입 |
| ES 서버 | **9.2.8** + `analysis-nori` |
| GHCR 이미지 | **`ghcr.io/devpathai/devpath-elasticsearch:9.2.8`**(digest `sha256:41f34a7d…`) — 이번 세션에 발행 완료 |
| 설정 프로퍼티 | **`spring.elasticsearch.uris`** |
| 인덱스명 | 운영 `community_posts` / 테스트 `community_posts_it`(`application-test.yml`로 격리) |
| 분석기 | `nori_analyzer`(`{"type":"nori"}`), `Analyzer.Builder.nori(...)` |
| Kafka 토픽 | `community.post.changed`, payload `{"postId":N,"deleted":bool}` |

> **spec/plan 초안의 "ES 8.x"는 오류였다.** Spring Boot 4 세대는 Elastic 9.x를 가져온다(`./gradlew dependencies` 실측). 문서는 정정 완료(`c4550ec`).

### 2.4 완료 Task (community-svc `feat/community-search`, push됨)

```
a8abf3b  fix(search): 자유글·피드백 글도 색인 이벤트를 발행하도록 보완
ff5a777  feat(search): 글 변경 시 Outbox 이벤트 발행 + 색인 컨슈머
2881225  fix(search): board=ALL 무필터·size 상한 클램프(100)·page/size 검증(400)
3fd8a8d  feat(search): 검색 서비스 + GET /community/search
b39dbcf  test(search): PostIndexer 리뷰 지적 보완
71398ee  feat(search): PostIndexer — ES 색인 upsert/delete(멱등)
31493a7  ci(search): 테스트 서비스에 Elasticsearch(nori) 추가
e76c389  test(search): Task 1 리뷰 지적 보완
589affa  feat(search): ES 기반 구축
```

- **Task 1** ES 기반: nori 이미지·클라이언트 의존·`PostIndexBootstrap`(멱등, **ES 다운 시 앱 기동 비차단**)·CI services 연동
- **Task 2** `PostIndexer`: ES upsert/delete(멱등). **Kafka·Outbox 비의존**(CI에 Kafka가 없어 이 분리가 검증의 전제)
- **Task 3** 검색: `PostSearchService` + `GET /community/search`. **ES에서 id·highlight·total만 받고 표시 데이터는 DB에서 조립**(stale 방지), `summariesByIds`가 관련도 순서 보존, `status=PUBLISHED` 항상 강제, ES 장애 시 5xx
- **Task 4** 색인 동기화: `PostIndexEventPublisher`(공용) → `QuestionService.create`(QNA)·`PostService.createPost`(FREE/FEEDBACK) 양쪽 발행 + `PostIndexConsumer`(얇은 Kafka 어댑터)

**테스트**: ES 실컨테이너 대상 통합 테스트 40여 개. 전부 컨트롤러가 `--rerun-tasks`로 캐시 없이 직접 실행 검증.

### 2.5 ★리뷰가 잡은 결함 (전부 수정 완료)
| Task | 결함 | 성격 |
|---|---|---|
| 1 | ES 다운 시 앱 기동 비차단(핵심 요건)의 **자동화 테스트 부재** | 결함 주입으로 RED 실증 후 추가 |
| 2 | **`isSolved` 키 이름 회귀 방지 테스트 부재** — `getIsSolved()`→`isSolved()` 리팩터링 시 Jackson이 프로퍼티를 `solved`로 벗기고, dynamic 매핑이 strict가 아니라 **ES가 조용히 새 필드를 만들어 검색 필터가 무력화되는데 CI는 green** | RED 실증 후 추가 |
| 3 | **`board=ALL`이 `term(boardType=ALL)`로 들어가 항상 0건** — 기존 목록 API는 ALL을 무필터로 취급 | 실제 동작 버그 |
| 3 | `size` 무제한 + `toSummary` N+1 → DB 커넥션 고갈 여지 | 100 클램프 |
| 3 | `page<0`·`size<=0`이 500 → "ES 장애=5xx" 신호 오염 | 400으로 |
| 4 | **`PostService.createPost` 발행 누락** — 자유글·피드백이 검색에 전혀 안 잡힘 | **플랜의 수정 허용 파일 한정 실수**. 구현자가 Scope Lock을 지키며 정확히 보고 |

### 2.6 spec 정정 2건 (실측 기반)
1. **이벤트 발행 = 기존 Outbox 패턴** — 초안의 `AFTER_COMMIT` 직접 발행은 틀림. 트랜잭션 내 `OutboxEntry` 저장 → `OutboxRelayScheduler`(2초 주기)가 Kafka 발행. **색인 반영 최대 2초 지연**이 대가.
2. **글 수정·삭제 기능이 코드베이스에 없다**(grep 확인) — 발행 지점은 **생성 2곳뿐**. `deleted` 플래그·컨슈머 삭제 분기는 미래 대비.

### 2.7 🔴 프론트 Task로 전달된 보안 계약 (plan Task 8에 반영됨)
**ES 하이라이터는 사용자 본문의 `<`·`>`를 이스케이프하지 않는다.** 본문에 `<img src=x onerror=alert(1)>`가 있고 검색에 걸리면 그 마크업이 `highlight` 필드에 그대로 담겨 온다.
→ **HTML 해석 렌더 금지.** `<em>`만 화이트리스트 파싱해 `RichText`로 분해할 것. **XSS 문자열 렌더 테스트를 필수 케이스로** 명시했다.

---

## 3. 다음 세션 착수 (Task 5부터)

### 3.1 시작 절차
```bash
git -C D:/workspace/dpa/devpath-community-svc fetch origin
git -C D:/workspace/dpa/devpath-community-svc checkout feat/community-search   # a8abf3b
git -C D:/workspace/dpa/devpath-frontend  checkout feat/community-search       # c4550ec
```
SDD ledger: `devpath-frontend/.superpowers/sdd/2026-08-01-community-search/progress.md`
(Task별 브리프·보고서·리뷰 파일이 같은 디렉토리에 있다. **`git clean -fdx`로 날리지 말 것.**)

### 3.2 로컬 환경 재현 (필수)
```bash
# Docker Desktop 실행 후
docker run -d --name dpa-test-pg -e POSTGRES_USER=devpath -e POSTGRES_PASSWORD=localdev \
  -e POSTGRES_DB=devpath -p 5432:5432 pgvector/pgvector:pg16
docker exec dpa-test-pg createdb -U devpath -O devpath devpath_citest   # community-svc 테스트 DB

cd D:/workspace/dpa/devpath-community-svc
docker build -t devpath-es:local docker/elasticsearch
docker run -d --name dpa-test-es -p 9200:9200 -e discovery.type=single-node \
  -e xpack.security.enabled=false -e ES_JAVA_OPTS="-Xms512m -Xmx512m" devpath-es:local
curl -s http://localhost:9200/_cat/plugins    # analysis-nori 확인
```

### 3.3 남은 Task
- **Task 5** 재색인 배치 + `POST /admin/community/reindex`(ADMIN 권한 필수) → **백엔드 PR 생성**
- **Task 6** gitops ES 매니페스트 (**적용은 AWS 재가동 시 이월**, PR 본문에 명시)
- **Task 7** dp_core 검색 모델 + 데이터 소스 + 목 픽스처
- **Task 8** 검색바 UI + 결과/빈결과/에러 + 더보기 + `?q=` 라우팅 (**§2.7 XSS 계약 준수**)
- **Task 9** 로컬 통합 스모크 + `04_API_명세서.md` 갱신

**머지 순서: 백엔드 → 프론트**(계약 확정 먼저).

### 3.4 ⚠️ Task 5에서 처음 확인되는 것
**CI에 붙인 ES가 실제로 도는지는 PR을 만들어야 확인된다**(`on: pull_request` 트리거라 브랜치 push만으로는 안 돎). Task 5에서 PR 생성 후 **CI green을 반드시 확인**할 것. 실패하면 GHCR credentials·health-cmd·메모리 설정을 의심.

### 3.5 알려진 이슈·이월
- ⚠️ **기존 테스트 2건 flake**: `ActivityMockMvcTest`·`VoteGateMockMvcTest`는 DB 초기화 없이 전체 스위트를 반복 실행하면 데이터 누적으로 실패한다. **기존 격리 문제이지 검색 작업의 회귀가 아니다.** 전체 스위트 전 `devpath_citest` 재생성 권장. (이 레포 테스트가 트랜잭션 롤백 없이 실 데이터를 적재하는 구조 — 손대지 않았다.)
- Task 1 minor: TOCTOU(exists→create, 단일 인스턴스 전제라 무해) · shards/replicas 미지정으로 단일 노드 인덱스 yellow · Spring Data ES 리포지토리 스캔 경고 노이즈
- Task 2 minor: nori 테스트가 `useEffect가`(스크립트 경계)라 표준 애널라이저로도 통과 가능 · `authorId`·`status`·`createdAt` 미단언
- Task 3 minor: `sort` 임의값이 조용히 relevance 폴백(테스트 없음) · `Thread.sleep(10)` 약한 flake · **ES 색인 지연 중 비공개 전환 레이스**(ES엔 PUBLISHED인데 DB는 아님 — `summariesByIds`가 DB 최신 상태로 재필터링하지 않음)

---

## 4. 사용자 신규 요구 — 남은 3건

사용자 지정 순서 **②검색 → ③신고 페이지 → ④오류신고 메뉴 → ①디자인**

- ② 커뮤니티 검색 — 진행 중(위 §2)
- ③ 게시판 **문제/신고 페이지 부재**
- ④ 각 페이지 **오류 신고 메뉴 부재**
- ① **전반 디자인/테마 품질** — "대시보드 이외에는 디자인 개판, 대시보드도 좋은 디자인은 아님"
  **★사용자 지정 착수 조건: 전체 구조에 맞는 디자인 테마를 상세 리서치 + 100건 이상 프리뷰 + 모든 페이지 검토 후 진행★** (즉흥 개선 금지, 대규모 사전 조사 필수)

---

## 5. ⚠️ 미머지 핸드오프 PR 2건

`documents` 레포에 이전 핸드오프 PR이 **OPEN 상태로 남아 있다**:
- **#83** `docs/handoff-2026-07-31-contract-expansion` — UI/UX 로드맵 완결 + 계약확장 4건 이관
- **#84** `docs/handoff-2026-07-31-abc-done-d-spec` — 계약확장 A·B·C 완결·D spec 단계

이 핸드오프(#85 예정)와 함께 정리 필요. develop = `50590f8`.
