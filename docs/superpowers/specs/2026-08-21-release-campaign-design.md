# 릴리스 캠페인 — 리뷰·수정 → 머지 → 배포·릴리즈 설계

**목표:** 2026-08-21 현재 열린 기능 PR 5건을 리뷰·수정해 `develop` 에 머지하고, Mission Spine
HOLD 를 사람 관문과 함께 풀어 **운영 배포·릴리스까지 완주**한다. 진행 방식은 「세션 동반 완주」
— 사람 차례가 오면 정확한 행동을 안내하고 기다렸다가, 끝나는 즉시 기계 단계를 잇는다.

**리뷰 범위(사용자 결정):** 열린 PR 5건의 변경분 + 외부 리뷰에서 확정했으나 미수정으로 남긴
결함 9건. 조직 13개 레포 전체 리뷰는 **이 캠페인의 범위가 아니다**(원하면 별도 프로젝트).

---

## 1. 측정된 전제 (2026-08-21 실측)

| # | 측정 | 결과 | 함의 |
|---|---|---|---|
| M1 | `qahnaarin` 조직 초대 | **pending**(8/17 발송, 멤버는 본계정 1명) | 릴리스 4단계 전부의 **단일 선행 조건** |
| M2 | 릴리스 PR #67·#133·#59 | 전부 OPEN/**BLOCKED** | 사람 승인 없이는 못 나간다 |
| M3 | 열린 기능 PR | community-svc #36 · shared #70 · frontend #136 · gitops #66 · documents #111 | 이 캠페인의 머지 대상 |
| M4 | shared #70 CI | **불변 게시 계약**(et9 jar 바이트가 소스에 하드코딩, 조건 없이 검증)에 걸려 **구조적으로 red** | et9 게시 **후** 버전 올림과 함께만 머지 가능 |
| M5 | community-svc #36 CI | `> Task :test` 53분 무출력 매달림 → 원인 실측 완료(§2) | Stage 0 이 머지의 선행 |
| M6 | frontend #136 · gitops #66 · documents #111 | CI **CLEAN** | 머지 준비됨 |

### 왜 사람 관문인가 (배경)

1인 조직이라 8/19에 정한 방식이 「실질 리뷰 = Codex / 형식 승인 = 부계정 `qahnaarin`」이다.
게이트 둘: **A** `main` 보호(승인 1명 + enforce_admins, **작성자 자기 승인은 GitHub 가 구조적으로
금지**) — 승인 클릭은 사람. **B** 보호 환경(prevent_self_review + reviewer 본계정 1명) —
qahnaarin 을 reviewer 로 **추가하는 것은 기계가 API 로** 하지만 조직 멤버만 추가할 수 있어
초대 수락이 선행이다. 8/20 에 관리자 우회 12곳을 **의도적으로** 닫았으므로 기술적 우회로는 없다.

---

## 2. Stage 0 — community-svc CI 교착 수정 (#36 차단 해제)

### 근본 원인 (매달린 순간의 실측)

CI·로컬 모두 `> Task :test` 에서 멈췄고, 매달린 순간의 `pg_stat_activity` 가 답을 냈다:

```
idle in transaction  ... SELECT COUNT(*) FROM pg_namespace ...
active  Lock/virtualxid  -- This migration is deliberately non-transactional: ...
```

**Flyway 자기 교착**이다 — `V202608161002` 의 `CREATE INDEX CONCURRENTLY` 가 다른 열린
트랜잭션이 끝나길 기다리는데, **Flyway 자신의 메타데이터 커넥션이 idle in transaction** 으로
앉아 있어 영원히 기다린다. 이 프로젝트가 이전에 2시간을 쓰고 "이미 마이그레이션된 DB 를 써라"
로 기록해 둔 바로 그 함정이, 개발용 shared 좌표(`0.0.1-dev.20260820`)가 ET8+ 마이그레이션을
community-svc CI(빈 DB)에 처음 실어 오면서 재발했다. 타이밍 의존이라 **flaky** 하다(빈 DB 4회
중 3회 매달림, 1회 통과).

★1차 진단(비데몬 스레드)은 반증됐다 — 데몬 수정이 들어간 상태에서도 매달렸다. 교착은 다른
테스트 클래스의 **컨텍스트 기동 단계**에서 나므로 `@Timeout` 도 걸리지 않았다.★

### 수정 (조직 관례 그대로)

- `application-test.yml` 에 `spring.flyway.postgresql.transactional-lock: false`
  (속성명은 Boot 4 jar 의 configuration-metadata 에서 실측). shared 마이그레이션 테스트와
  gitops 마이그레이션 Job 이 이미 같은 값을 쓴다 — 오늘 shared 전체 스위트가 빈 DB 에서 같은
  마이그레이션을 두 번 무사히 완주한 것이 효과의 증거다.
- CI 워크플로에 `timeout-minutes: 15` — 다음에 무엇이 매달리든 53분 침묵 대신 실패로.
- 데몬 스레드·`@Timeout(120)` 은 경화 가치로 유지하되 커밋 메시지에 **원인 수정이 아니었음**을 명시.

### 검증

flaky(기저율 3/4)이므로 1회 통과는 증거가 아니다 → **빈 DB 연속 4회** from-scratch
`./gradlew cleanTest build` 완주(★`cleanTest` 필수 — env 는 태스크 입력이 아니라 두 번째부터
`:test` 가 UP-TO-DATE 로 건너뛴다★) → 푸시 → PR #36 CI green.

---

## 3. Stage A — 리뷰·수정 (확정 결함 9건 + Codex 재리뷰 1회)

**shared #70 브랜치에 3건** (전부 "레포에 이미 있는 관행을 내 테스트만 안 따른 것"):
1. `convalidated`·`pg_get_constraintdef` 단언 — 현재 ★`V202608201002` 를 통째로 비워도 전
   스위트 green★
2. 채워진 스키마 업그레이드 테스트(`SandboxDurableTerminalStateMigrationTest` 패턴 —
   `createPriorSchemaWithExistingRows` + baseline/target)
3. 리비전 테이블 테스트에 대조군(유효 삽입 성공 + SQLSTATE `23514` 확인)

주의: shared #70 의 CI 는 이 수정 뒤에도 **불변 계약 때문에 red 로 남는 것이 정상**이다(M4).
로컬 전체 스위트로 검증한다.

**frontend #136 브랜치에 6건**:
4. 인라인 에디터 컨트롤러 미동기화 — web 답변·web 댓글·mobile 답변 3곳, `_editing` 이 아닐 때
   위젯 갱신에서 `_ctrl.text` 동기화
5. 관리자 내리기 성공 후 목록 갱신(재요청 404 방지)
6. 빈 본문 인라인 저장이 조용히 막히는 것 → `내용을 입력해 주세요` 표면화
7. `community_source_edit_delete_test` 가 요청 본문을 검증하게(어댑터에서 `RequestOptions.data` 캡처)
8. `edit_delete_golden_path_test` 를 실제 위젯 구동으로(현재 ★`pumpWidget` 0건★)
9. mobile `deleteAnswer` 재조회 단언(조회 횟수 + 결과 반영)

**그 위에 Codex 재리뷰 1회**: 수정 반영된 최종 diff 를 인라인으로 실어 레포별 직렬 실행
(`-c 'mcp_servers={}'` · 응답 추출 `awk '/^codex$/{f=1;next} f'` — 검증된 레시피).
지적은 **파일 대조로 확정 후** 수용/기각. 새 critical/major 만 이 캠페인에서 수정, minor 는
기록 후 백로그.

---

## 4. Stage B — 머지 (각 건 CI green 확인 후, merge commit)

순서: **documents #111 → (Stage 0 후) community-svc #36 → (Stage A 후) frontend #136 →
gitops #66**. 각 머지는 사용자 승인 하에 진행한다.

- ★**shared #70 은 여기서 머지하지 않는다**★ — et9 게시 전에 develop 에 넣으면 불변 검증이
  develop CI 를 깨뜨리고 #67 의 후보를 오염시킨다. C-4 에서 처리.
- **gitops #66 은 develop 머지 시 릴리스 #59 에 실린다** — 승인된 결정: **태운다**. 이 수정이
  없으면 릴리스의 `flyway validate` 가 exit 1 로 배포를 깨는 것을 실측했으므로 candidate 에
  들어가는 것이 맞다.
- documents #111(동시성 스펙·관례)과 이 스펙의 PR 도 이 단계에서 머지한다.

---

## 5. Stage C — 배포·릴리즈 (세션 동반 완주)

| # | 주체 | 행동 |
|---|---|---|
| C-1 | **[사람]** | `qahnaarin` 으로 로그인 → DevPathAi 조직 초대 수락(메일 링크 또는 github.com/DevPathAi). **유일한 단일 선행 조건** |
| C-2 | [기계] | 보호 환경 reviewer 에 qahnaarin 추가 + 재조회로 확인 |
| C-3 | **[사람]** | shared #67 승인(qahnaarin) → [기계] 머지 → main push 가 **et9 게시** → 게시물 바이트를 불변 스펙으로 검증 |
| C-4 | [기계] | 서비스 8개 PR 재실행·해제 확인 / shared #70 에 **다음 버전 + 불변 검증 처리** 커밋 → ★릴리스 계약 변경이므로 도달 시 두 안(새 버전 스펙 재산정 vs 게시된 et9 원격 검증으로 전환)을 사용자에게 묻는다★ → CI green → **[사람]** 승인 → 머지. community-svc `devpathSharedVersion` 을 dev 좌표에서 정식 좌표로 환원하는 커밋 포함 |
| C-5 | [기계] | gitops flyway target 4곳 갱신(`TARGET_FLYWAY_VERSION`·`EXPECTED_SHARED_COMMIT`·`test -f`·preflight `required_target`) — shared 머지 커밋 확정 후에만 가능 |
| C-6 | **[사람]** | GPU 노드 기동(런북 10분) + `OLLAMA_PATH*` env 의 main 반영 확인 → #59 승인 → [기계] 머지 = **운영 배포** |
| C-7 | 순서 제약 | ★frontend #133 은 learning-svc 릴리스(두 트랙 문항 시드) **뒤에만**★ — 먼저 나가면 0문항 트랙 선택 시 빠져나올 수 없는 진단 세션이 된다. #133 승인도 [사람] |
| C-8 | [기계] | 배포 검증 — 마이그레이션 Job **재생성**(Job immutable) 확인 · ★배포물 직접 확인★(401 이 404 를 가리므로 상태코드 신호 대신 jar 내용·신규 클래스 존재로) · 수정·삭제 골든패스 운영 스모크 · 검색 색인 반영 |
| C-9 | [기계] | 릴리스 핸드오프 문서 + 메모리 갱신 |

---

## 6. 성공 기준

1. 기능 PR 5건 중 **4건**(documents·community-svc·frontend·gitops)이 develop 에 머지
2. shared 경로 완결: et9 게시 → #70(버전 올림 포함) 머지 → 서비스 8개 PR 해제
3. 릴리스 3건(#67·#59·#133) main 머지 + **운영 스모크 통과**
4. 사람 클릭이 멈추면: 그 지점까지 전부 완료 + 잔여 행동만 적힌 런북을 남긴다

## 7. 범위 밖 · 수용 위험

- 조직 13개 레포 전체 코드베이스 리뷰(별도 프로젝트)
- 서비스 기동 시 Flyway 실행 경로의 교착 가능성(운영은 마이그레이션 Job 이 선행하므로 창이
  좁다) — 관찰 위험으로 기록만
- Codex 재리뷰에서 나오는 minor 지적(기록 후 백로그)
