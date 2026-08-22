# 핸드오프 — 트랙 확장 완결, 생성기 결함 두 개, 릴리스는 여전히 사람에 막힘

- 작성일: 2026-08-19
- 이전 핸드오프: `handoff-2026-08-17-path-generation-and-gpu.md`
- **다음 세션 착수점: 아래 「재개 순서」 1번부터. 1번은 사람이 해야 하고 코드로 풀 수 없다.**

## 한 줄 요약

**8트랙이 모두 채워졌고 leva.ai.kr SEO 백로그도 닫혔다.** 그런데 트랙 작업의 실질은 콘텐츠 생성이 아니라
**생성기 수정**이었다 — 도구가 애초에 트랙 하나를 채울 수 없는 상태였다. 릴리스 통제는 08-17과 **한 글자도
바뀌지 않았다**(초대 미수락).

---

## 1. 이번 세션에 머지한 것

| 레포 | PR | 머지 SHA | 내용 |
|---|---|---|---|
| home-page | #39 | `cac381e` | 개발 기록 CTA + ET13 시각 증거 재바인딩 |
| learning-svc | #53 | `96d69ad` | NODE_TYPESCRIPT 트랙 + 셀 단위 하버스터 |
| learning-svc | #54 | `f6a90d5` | DATA_AI 트랙 + 생성 출력 상한 |

전부 `develop` 까지다. **운영 반영은 없다** — learning-svc 의 `deploy`·`image` 잡은 `main` 전용이고,
home-page 는 배포 워크플로 자체가 없어 `wrangler` 로 직접 올려야 라이브가 바뀐다.

### 트랙 확장 결과

승인본이 문항 600→**800**, 콘텐츠 180→**240**, 임베딩 청크 268→**331** 이 됐다.
DB CHECK 가 허용하는 **8트랙이 모두 채워졌다**(`V202608141001` 에 이미 있어 마이그레이션 불필요).

게이트는 문항·콘텐츠 모두 승인본 전체에서 `EXIT=0`, 전체 스위트 70클래스 **275건 실패 0**.

---

## 2. ★생성기가 애초에 트랙을 채울 수 없었다★

`generateQuestionsLocal` 이 트랙당 **단일 호출로 "100개를 만들라"** 고만 요구하고 있었다. 실측하면 붕괴한다.

| | NODE_TYPESCRIPT | PYTHON_BACKEND 1차 잔여물 |
|---|---|---|
| 산출 | 355줄 / **고유 content 16** | 30줄 / **고유 6**(7~30번이 같은 6개 반복) |
| 분포 | MCQ·REMEMBER·난이도 0.1-0.2 각각 100% | — |

**두 트랙에서 같은 실패가 재현된다.** 즉 08-14 메모리의 「문항 100개에 73분」은 도구가 100개를 낸 시간이
아니라 **사람이 도구 밖에서 소배치로 거둔 시간**이었다. `tools/content-gen/generated/raw/` 에 남은
`call_ollama.py`·`batch_prompts/`·`fix_length_spread_batch*.py` 가 그 흔적이다.

### 해법 — 쿼터 셀 단위 하버스트

`QuestionHarvester`·`ContentHarvester` 를 넣었다. 쿼터 셀(문항: `questionType` × `bloomLevel` × 난이도 밴드 /
콘텐츠: `level`)로 요청을 쪼개고, **게이트가 나중에 막을 조건을 받는 자리로 끌어온다**. 못 채우면 모자란 수를
보고하고 끝낸다 — 중복으로 숫자를 맞추지 않는다.

**효과가 수치로 나왔다**: DATA_AI 문항은 **첫 시도에 100/100**(12분 30초). 재시도도 프롬프트 수정도 없었다.

### 결함이 다섯 번 나왔는데 전부 같은 형태였다

생성기가 **요청 시점에 게이트 조건을 강제하지 않는 것**:

1. 문항 붕괴(고유 16/355)
2. CODE_READING 에 보기 22건·정답키 9건 누락 — 모델이 서술형으로 이해했다
3. 보기가 문자열이 아니라 **배열로 감싸짐**(`[["a"],["b"]…]`) — 개수만 세면 4개라 통과한다
4. 콘텐츠 레벨 쏠림(INTRO 6·ADVANCED 14 vs 목표 8·8)
5. `conceptTags` 비-kebab(`AbortController`·`node-worker_threads`) + **제목 중복**(슬러그만 다른 같은 주제)

★**「보기 벌 중복 21건」의 정체가 빈 보기끼리의 중복이었다**★ — 증상 이름과 원인이 달랐다.

---

## 3. ★내가 만든 결함 — 출력 상한 부재★

하버스터를 붙이며 `num_predict` 를 두지 않았다. `num_ctx` 는 16384 로 열려 있으니 **한 요청이 컨텍스트를
채울 때까지 늘어진다.** DATA_AI 콘텐츠 생성이 **70분 넘게 같은 요청**에 매달렸다.

**교착과 폭주를 가르는 법**(다음에 로그가 조용할 때 쓸 것):

| 관측 | 값 | 해석 |
|---|---|---|
| `nvidia-smi` GPU | 29~30% | 연산은 돌고 있다 |
| 서버 로그 `task N`(45초 간격) | **바뀌지 않음** | 같은 요청이 계속 뱉는 중 |
| 로그 크기 | 45초에 +1,302바이트 | 진행은 하고 있다 |

★**`prompt eval time ... tokens per second` 를 생성 속도로 읽으면 안 된다**★ — 실제 속도는
`slot print_timing ... n_gen = N, tg = X t/s` 다. 로컬 RTX 2080 Ti + `qwen2.5:14b` 는 **약 9 t/s**.

콘텐츠 `num_predict=3072` · 문항 `2048`, 콘텐츠 배치 **6→3** 으로 묶어 호출당 최악을 약 5.6분으로 한정했다.
잘린 줄은 하버스터가 파싱 실패로 버리고 재요청하므로 승인본으로 새지 않는다.

---

## 4. 외부 리뷰 위임 — 8/21까지 불가

사용자 지시로 **외부 리뷰를 Codex 에 위임**하기로 했다(1인 조직이라 부계정 승인엔 독립 검토의 실질이 없다 —
실질 리뷰=Codex, 형식 승인=별도 계정으로 분리).

**첫 시도는 전량 실패했다.** 5건을 동시에, reasoning `max` 로 돌려 **Codex 계정 한도를 소진**했다
(측정된 4건만 986K 토큰). `try again at Aug 21st, 2026 6:59 AM`. **보고서는 5건 전부 0건 산출.**

★**`grep -c "## 판정"` 이 5건 모두 1을 반환해 「산출됨」으로 보였는데, 그 1건은 내가 준 프롬프트의 출력 형식
예시가 에코된 것**★이었다. 프롬프트 길이 이후 구간만 다시 세니 전부 0이었다.

**Gemini CLI 는 대체재가 못 된다**(실측): `gemini 0.42.0` + 무료 Code Assist OAuth =
`IneligibleTierError: This client is no longer supported ... migrate to the Antigravity suite`.
`GEMINI_API_KEY` 미설정이라 우회 불가.

**재개용 자산**: worktree 5개(`/d/workspace/dpa/.worktrees/{shared,gitops,frontend,learning-svc,ai-svc}-codexreview`),
임시 base 브랜치 `codexreview-base`(learning-svc `a4da1c4` · ai-svc `47031c0`). **지시문은 세션
스크래치패드라 재작성이 필요하다.** 재개 시 **직렬로, 작은 것부터**.

---

## 5. 릴리스 통제 — 08-17에서 한 글자도 안 바뀜

2026-08-19 재측정:

| 확인 | 값 |
|---|---|
| 조직 초대 `qahnaarin` | **`pending`** |
| shared 저장소 초대 | `qahnaarin` 미수락 |
| 보호 환경 reviewer | `["VelkaressiaBlutkrone"]` — 본인 1명 |
| shared #67 | `OPEN` / `BLOCKED` / `REVIEW_REQUIRED` |
| 게시된 패키지 | `0.0.1-SNAPSHOT` 뿐 |

### 스팟 GPU 쿼터는 승인됐다

`L-3819A6DF` = **4.0**(08-17 문서는 `0.0`/`CASE_OPENED` 로 적혀 있다). 이월 블로커를 다시 잰 결과다.

### main 에 닿기 전 게이트 2개 — 둘 다 여전히 미충족

1. **GPU 노드 없음** — `ap-northeast-2` 실행 인스턴스는 `t3.xlarge / devpath-k3s` **하나뿐**.
2. **`OLLAMA_PATH*` 가 `develop` 에만 있음** — `main` 0건(대조군 `OLLAMA_BASE_URL` 은 양쪽 1건씩이라
   검색법 자체는 유효함을 먼저 확인했다).

이어 보면 지금 gitops #59 를 `main` 에 머지하면 ai-svc 가 **파드가 하나도 없는 서비스**
(`http://ollama-gpu.devpath.svc:11434`)로 경로 생성을 보낸다. 타임아웃이 늘어난 게 아니라 **연결이 즉시
실패**한다. **GPU 노드 기동이 #59 머지의 선행 조건**이고, 쿼터가 승인됐으니 이제 가능하다(런북 10분).

---

## 6. leva.ai.kr SEO — GSC 등록만 남고 닫힘

08-14 백로그 4단계 중 **2개가 착수 시점에 이미 사실이 아니었다.**

- ① CTA 블록 — **완료**(PR #39). `templates/note.html` 한 곳으로 10편 반영, 빌드 산출물 전수 확인.
- ② title·description 에 「레바」 — ★**하면 안 되는 일이었다**★. `996ef48 feat(brand): 브랜드를 Leva로
  전면 교체한다` 가 들어가 `head-meta.test.js` 가 `<title>Leva — …</title>` 를 문자열째 고정한다.
  게다가 「푸터에 레바가 있다」던 근거는 브랜드 표기가 아니라 **사업자명 고지**였다. 사용자 결정 = 현상 유지.
- ③ 폴백 문구 정정 — ★**이미 해결돼 있었고 내 제안보다 나은 설계였다**★. h2 는 평소 `베타 진행 상황` 이고
  **검증된 수치를 실제로 렌더할 때만** `숫자로 보는 지금` 으로 바뀐다(`traction-heading.test.js` 가 양쪽 강제).
- ④ GSC 등록 — **사용자 몫으로 남는다.**

### home-page 는 제품 파일이 동결돼 있다

`assets/`·`templates/`·`tests/`(증거 계약 파일 제외)를 건드리면 `visual-evidence-audit-contract` 가 제품 트리
해시 불일치로 막는다. 허용목록은 `scripts/visual-evidence.mjs` 의 `EVIDENCE_ONLY_PATHS`.

제품 변경 절차: ①제품 커밋 ②`e2e/visual/candidate-spec.v2.json` 의 `rendered_product_sha`·`tree_sha256`
갱신·커밋 ③고정 Docker 안에서 `scripts/update-visual-baselines.mjs` ④두 증거 테스트의 고정 SHA **전수** 치환
(`grep -rn 084ab218` — 상단 상수만 고치면 본문 `HOME_RENDERED_PRODUCT_SHA` 3곳이 남는다).

★**PNG 4장은 하나도 안 바뀌었다**★ — CTA 는 글 템플릿과 `.note__cta` 규칙만 건드려 홈 렌더에 영향이 없다.
바뀐 값은 출처 해시 둘뿐이다.

★**Windows 체크아웃의 CRLF 가 증거 해시를 CI 와 어긋나게 한다**★ — 컨테이너에 Windows 트리를 바인드
마운트하면 CRLF 기준 해시가 기록된다(`case-catalog` 디스크 `de9efef5…` vs git blob `a3c338c6…`).
해법 = 레포 로컬 `core.autocrlf=false` + `git rm --cached -r . && git reset --hard` 로 정규화 후 재렌더.
정규화하자 **로컬 실패가 5건 → 0건**이 됐다. ★그 5건을 「develop 기준선이 red」로 오독했었다 — develop 의
CI 는 줄곧 green 이다.★

---

## 7. 함정 — 다음 세션이 반드시 알아야 할 것

### ★「올바른 이유로 red」를 이름만 보고 판정하지 말 것★

트랙을 추가하고 시드 테스트 4건이 실패하는 것을 보고 「쿼터 커버리지가 걸렸다」고 보고했다. **틀렸다.**
메시지를 열어 보니 전부 `Failed to load ApplicationContext` — **Postgres 연결 실패**였다.
DB 를 띄우고 나서야 진짜 red(`expected: 210 but was: 180`)가 나왔다.

**로컬 테스트 기동**:
```bash
docker run -d --name devpath-pg -e POSTGRES_DB=devpath -e POSTGRES_USER=devpath \
  -e POSTGRES_PASSWORD=localdev -p 5432:5432 pgvector/pgvector:pg16
docker run -d --name devpath-redis -p 6379:6379 redis:7-alpine
```
둘 다 있어야 275건이 전부 통과한다(Redis 없으면 게스트 진단·보안 3건이 409/503 으로 실패).

### ★판별력 없는 green 을 세 번 잡았다★

가드를 **임시로 지워 red 가 나는지 실제로 돌려봐야** 드러났다:
1. CTA 위치 단언 — 잘 작동했다(정확히 1건만 red)
2. 문항 중복 제거 가드 — 잘 작동했다
3. **콘텐츠 레벨 가드 — 판별력이 없었다.** 가짜 클라이언트가 레벨마다 같은 slug 를 내 **중복 제거에 먼저
   걸리는 바람에** 가드 유무와 무관하게 통과했다. 호출마다 새 slug 를 주도록 고치니 `Expected size: 8 but
   was: 30` 으로 제대로 red 가 났다.

### 그 밖에

- ★**`... | codex ... | tail` 의 `$?` 는 `tail` 것이다**★ — 인자 오류로 5건이 즉시 죽었는데 `EXIT=0` 으로 보였다.
- `codex exec review --base <BRANCH>` 는 **커스텀 프롬프트와 병용 불가**. 표적 질문을 주려면 일반
  `codex exec -s read-only -` 를 쓰고 diff 범위를 프롬프트에 지시한다.
- ★**`harvest.attempts` 같은 노브는 `systemProperty` 로 넘겨야 한다**★ — `JavaExec` 은 별도 JVM 이라
  Gradle JVM 의 `-D` 를 안 물려받아 **조용히 무시**된다. 값이 도달했는지 **출력으로 보이게** 할 것.
- 단일 트랙 초안을 `validateQuestions --args=<draft>` 로 재면 **다른 트랙 부재 오류가 `EXIT=1`** 을 만든다.
  트랙 이름으로 걸러 읽을 것. (`--args` 오버라이드는 `JavaExec` 태스크에 먹힌다.)
- `python` 은 스텁이다 — `py` 를 써야 파일이 실제로 바뀐다. 판별력 실측이 한 번 무효였다.
- `gh api` 로 `origin/branch:path` 를 쓸 때 `MSYS_NO_PATHCONV=1` 을 붙인다.
- 테스트 결과 XML 에서 **`<testcase name>` 추출이 실패 내용과 어긋나는 경우가 잦다.** 스택트레이스가 정확하다.

---

## 8. 재개 순서

1. **[사람] `qahnaarin` 으로 로그인해 조직 초대 + devpath-shared 저장소 초대 수락**
2. **[에이전트] 보호 환경 reviewer 에 `qahnaarin` 추가 후 재조회로 확인**
   (PUT 이 200 을 반환하고도 조용히 버려진다 — 08-17 핸드오프 §5)
3. **[사람] `qahnaarin` 으로 shared #67 승인**
4. **[에이전트] #67 을 merge commit 으로 `main` 병합 → 게시 승인 → 게시 검증 → 서비스 8개 PR fresh rerun**
5. **[에이전트] GPU 노드 기동**(쿼터 승인됨, 런북 10분) → gitops #59 게이트 2개 충족 확인 → 릴리스
6. **[8/21 06:59 이후] Codex 외부 리뷰 재개** — 직렬로, 작은 것부터. worktree 는 남아 있고 지시문만 재작성.

## 9. 남은 백로그

- **문항 내용의 사실 정확성 검수** — 두 트랙 모두 구조·분포만 검증했다. 08-14 트랙은 별도 검수에서
  「정답이 최장 보기 73%」를 잡았다. 게이트가 그 축을 이제 직접 재긴 한다(NODE_TYPESCRIPT 39% ·
  DATA_AI 44%, 상한 60%).
- **프론트 `track_catalog.dart` 에 두 트랙 노출** — CHECK 는 값을 허용할 뿐이고 이용자에게 보이는 목록은
  프론트가 정한다.
- **글 수정·삭제** 신규 개발(community-svc 에 `@PutMapping`·`@DeleteMapping` 0건).
- **GSC 등록**(사용자 몫) · 08-14 이월 사용자 육안 확인 3건.
- learning-svc `main...develop` 이 **10 / 8 로 갈라져 있다** — 릴리스 시 확인 필요.

## 10. 참고

- 릴리스 통제: `devpath-gitops/docs/mission-spine-release-handoff-2026-08-17.md`
- GPU 노드 절차: `devpath-gitops/docs/runbook-k3s-bootstrap.md` 「GPU 노드 추가」
- 시각 증거 절차: `devpath-home-page/docs/visual-a11y-evidence.md`
- 메모리: `devpath-track-expansion-python-backend` · `devpath-external-review-via-codex` ·
  `devpath-mission-spine-release` · `devpath-path-generation-async`
