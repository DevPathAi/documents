# 핸드오프 — 정리·게이트 차단·트랙 노출·스펙/계획, 그리고 백엔드 Task 1~5

- 작성일: 2026-08-20
- 이전 핸드오프: `handoff-2026-08-20-cleanup-and-backlog-triage.md`(같은 날, 앞 절반)
- **다음 세션 착수점: §7 「재개 순서」. 코드 작업은 Task 6 부터고, 인프라 레시피가 §6 에 있다.**

## 1. 한 줄 요약

작업트리 정리로 시작해 **릴리스 통제의 실재하는 구멍을 닫았고**(보호 환경 13곳 중 12곳),
2트랙을 이용자에게 노출했으며, 글 수정·삭제를 **스펙 → 계획 → 구현 Task 5/12** 까지 진행했다.
그 과정에서 **내가 쓴 계획의 결함 다섯 개를 실행 중에 잡았다.**

## 2. 완료된 것

| 산출물 | 위치 | 상태 |
|---|---|---|
| 작업트리 81 → 17 | 전 레포 | 완료. 브랜치·커밋 손실 0 |
| 「미푸시 11건」 오판 정정 | documents #104 | 완료. 11건 전부 열린 PR 에 있었다 |
| shared 게이트 2커밋 분리 | 로컬 `fix/migration-gate-split` | **푸시 안 함**. `041a2c3`·`0ec0c2f` |
| 관리자 우회 차단 | 보호 환경 12곳 | 완료. 열림 1곳(rollback, 의도적) |
| `track_catalog` 2트랙 | frontend #135 `d793598` | develop 머지 |
| 수정·삭제 스펙 | documents #107 | develop 머지 |
| 백엔드 계획(12태스크 72스텝) | documents #108·#109 | develop 머지 |
| **백엔드 Task 1~5** | **로컬 브랜치 2개, 미푸시** | **아래 §3** |

## 3. 진행 중 — 백엔드 Task 1~5 (미푸시)

**`devpath-shared` 브랜치 `feat/community-content-soft-delete`** — `origin/develop` 대비 1커밋

```
1a4ad9a feat(db): 커뮤니티 콘텐츠 소프트 삭제 상태와 수정 이력 테이블을 더한다
```

**`devpath-community-svc` 브랜치 `feat/content-edit-delete`** — `origin/develop` 대비 4커밋

```
89e1fc3 feat(content): 수정 이력 기록기를 더한다
d7a8156 fix(content): 비공개 콘텐츠의 읽기·신고 우회 경로를 막는다
5499adc feat(content): 답변·댓글에 상태를 싣고 상태 어휘를 한 곳에 모은다
1941ff8 build: shared 좌표를 프로퍼티로 빼고 개발용 좌표를 가리킨다
```

★**둘 다 원격에 없다**★(`git ls-remote --heads` 0건). shared `develop` 은 릴리스 PR #67 의 head 라
PR 시점을 정한 뒤에 연다.

**남은 태스크**: 6 글·질문 수정 · 7 글·질문 삭제 · 8 답변 · 9 댓글 ·
**10 평판 순합 회수(핵심 회귀 가드)** · 11 관리자 삭제 · 12 리비전 조회·활동 목록.

## 4. ★Task 4 가 실재하는 결함 셋을 잡았다★

계획이 "구현 전에 반드시 red" 라고 예고한 테스트가 실제로 재현했고, 하나는 예측보다 나빴다.

| 경로 | 기대 | 실제 |
|---|---|---|
| 삭제된 글 ID 직접 조회 | 404 | **200** |
| 삭제된 글의 댓글 목록 | 404 | **200** |
| 삭제된 콘텐츠 신고 | 404 | **201 Created** |

세 번째는 "404 가 안 난다" 가 아니라 **잘못된 데이터가 생성된다**는 뜻이다. 목록 쿼리 3종은
`status='PUBLISHED'` 를 걸었는데 상세·신고만 걸지 않았다. 삭제 API 를 붙이기 **전에** 닫는
순서로 계획한 것이 맞았다.

## 5. ★계획의 결함 다섯 개 — 전부 실행 중에 드러났다★

내가 쓴 계획인데 실행하니 다섯 군데가 틀렸다. 전부 계획 문서에 반영했다(#109).

**① 테스트 인프라를 잘못 적었다** — 「Postgres 와 Redis」라고 썼으나 실제 CI 는
**Postgres + Elasticsearch(nori)** 이고 **Redis 는 community-svc 가 쓰지도 않는다**
(`build.gradle.kts` 에 "redis는 미사용"). platform-svc 의 Redis 요구를 그대로 옮겨 적은 것이 뿌리다.

**② DB 대상을 잘못 적었다 — 이것이 2시간을 잡아먹었다** — `devpath_citest` 를 새로 만들라고
했으나 CI 는 `DB_URL` 로 **`devpath`** 를 준다. 빈 DB 에서 마이그레이션을 처음부터 돌리면
`V202608161002` 의 `CREATE INDEX CONCURRENTLY` 가 **자기 교착**에 걸린다 — Flyway 자신의 다른
세션이 `idle in transaction` 으로 열려 있어 영원히 기다린다.

★**진단이 두 번 틀렸다가 세 번째에 맞았다**★ — 처음엔 "느린가" 싶었고(실제로는 1시간 50분 정지),
다음엔 "ES 가 없어서" 라고 봤는데 ES 를 띄운 뒤에도 멈췄다. 그때 **스레드 덤프**를 떴고
(테스트 워커가 Postgres 소켓 read 에 매달림, 865초 경과에 CPU 4초 = 순수 대기)
`pg_blocking_pids` 로 blocked=CONCURRENTLY / blocking=`idle in transaction` 을 확인했다.

**③ 판별력 없는 테스트를 썼다** — 상태 CHECK 테스트가 `status` 컬럼이 **아예 없어도** 통과했다
(`assertThrows` 가 "컬럼 없음" 예외로도 만족된다). "CHECK 가 막았다" 와 "컬럼이 없다" 를 구분하지
못한다. 유효값(`HIDDEN`·`DELETED`) 삽입을 **대조군으로 앞에 세우자** red 가 2건 → 3건이 됐다.

**④ 재실행 안전하지 않은 테스트를 썼다** — 리비전 테스트가 건수를 단언하면서 남긴 행을 지우지
않아 **첫 실행만 통과**하고 두 번째부터 실패했다(930001 이 2 기대에 4). ★CI 는 매번 새 DB 라
드러나지 않고 로컬에서만 터진다★. `@BeforeEach` 격리 후 `cleanTest` 로 3회 연속 강제 실행해
확인했다(XML 갱신 시각 13초 간격, 매회 3건).

**⑤ 실행 위생을 안 적었다** — 긴 명령에 `timeout` 이 없었고 종료 코드를 파이프 뒤에서 잡았다.
★첫 실행에서 `./gradlew ... | tail` 의 `$?` 가 `tail` 것이라 **BUILD FAILED 를 EXIT=0 으로 읽을
뻔했다**★. `timeout` 을 건 뒤로는 15분에 `GRADLE_EXIT=124` 로 드러났다.

## 6. ★재개용 인프라 레시피 (검증됨)★

```bash
# Postgres
docker run -d --name devpath-pg -e POSTGRES_DB=devpath -e POSTGRES_USER=devpath \
  -e POSTGRES_PASSWORD=localdev -p 5432:5432 pgvector/pgvector:pg16

# Elasticsearch + nori — 공식 이미지엔 nori 가 없어 레포에서 빌드한다
cd /d/workspace/dpa/devpath-community-svc
docker build -t devpath-es:ci docker/elasticsearch
docker run -d --name devpath-es -p 9200:9200 \
  -e discovery.type=single-node -e xpack.security.enabled=false \
  -e ES_JAVA_OPTS="-Xms512m -Xmx512m" devpath-es:ci
until curl -sf http://localhost:9200 >/dev/null; do sleep 3; done

# shared 마이그레이션을 devpath 에 적용(이 경로는 PGSimpleDataSource 라 교착이 없다)
cd /d/workspace/dpa/devpath-shared && ./gradlew test --tests '*FlywayMigrationTest*'

# community-svc 테스트 — DB 는 devpath, 타임아웃 필수, 종료 코드는 파이프 앞에서
cd /d/workspace/dpa/devpath-community-svc
DB_URL=jdbc:postgresql://localhost:5432/devpath DB_USER=devpath DB_PASSWORD=localdev \
GITHUB_ACTOR=$(gh api user --jq .login) GITHUB_TOKEN=$(gh auth token) \
  timeout 900 ./gradlew test > /tmp/t.log 2>&1; echo "GRADLE_EXIT=$?"
```

**Redis 는 필요 없다.** `devpath-redis` 컨테이너가 떠 있어도 이 서비스는 쓰지 않는다.

**발행한 개발용 좌표**: `ai.devpath:devpath-shared:0.0.1-dev.20260820`.
`community-svc` 의 `gradle.properties` 가 이것을 가리킨다. 릴리스 후 et9 좌표로 바꾼다.

## 7. 재개 순서

1. §6 인프라 기동
2. 계획 `docs/superpowers/plans/2026-08-20-community-content-edit-delete-backend.md` **Task 6** 부터
3. Task 10 은 이 계획의 핵심 가드다 — 순진한 "이벤트별 역산" 구현이면 **투표 churn 테스트만** red 가
   된다. 이벤트가 한 겹뿐인 시나리오에서는 두 구현이 똑같이 green 이라 판별력이 거기에만 있다
4. Task 12 까지 끝나면 `superpowers:finishing-a-development-branch` 로 마무리
5. 프론트엔드(2부) 계획은 그 뒤에 쓴다 — 백엔드가 만든 실제 API 표면 위에서

## 8. 릴리스 통제 — 여전히 사람에 막혀 있고, 이제 더 단단히 막혔다

초대 `qahnaarin` 미수락 · 조직 멤버 1명 · #67·#59·#133 전부 `BLOCKED` · 게시는 SNAPSHOT 뿐 ·
GPU 노드 없음. 08-17 이후 변화 없음.

★**관리자 우회를 닫았으므로 이제 기술적 우회도 없다**★ — 보호 환경 15곳 중 12곳을 닫았고
열림 1곳은 `gitops/mission-spine-production-rollback`(비상 롤백 경로, **의도적**).
되돌리려면 `gh api -X PUT repos/DevPathAi/<repo>/environments/<env>` 바디
`{"can_admins_bypass": true}` — 한 필드만 보내도 나머지 설정은 보존된다.

## 9. 정리해 두실 것

- 컨테이너 3개 실행 중: `devpath-pg` · `devpath-es` · `devpath-redis`
  (redis 는 이 작업에 불필요 — `docker rm -f devpath-redis` 해도 된다)
- 개발용 패키지 `0.0.1-dev.20260820` 은 릴리스 후 정리 대상
- `.artifacts/unpushed-bundles-20260820/` · `.artifacts/shared-gate-split-20260820/` 은 감사 흔적
- 작업트리 17개 유지 중(Codex 재개용 5 + 고유 내용 12)

## 10. 참고

- 스펙: `docs/superpowers/specs/2026-08-20-community-content-edit-delete-design.md`
- 계획: `docs/superpowers/plans/2026-08-20-community-content-edit-delete-backend.md`
- 앞 절반 핸드오프: `handoff-2026-08-20-cleanup-and-backlog-triage.md`
- 메모리: `devpath-worktree-cleanup-and-gate-hole` · `devpath-mission-spine-release`
