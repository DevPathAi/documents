# 핸드오프 — 학습경로 생성 되살리기, GPU 결정, 릴리스는 사람에 막힘

- 작성일: 2026-08-17
- 이전 핸드오프: `handoff-2026-08-14-track-release-and-prod-issues.md`
- 릴리스 상세의 권위 문서: `devpath-gitops/docs/mission-spine-release-handoff-2026-08-17.md` §11
- **다음 세션 착수점: 아래 「재개 순서」 1번부터. 그런데 1·2번은 사람이 해야 하고 코드로 풀 수 없다.**

## 한 줄 요약

08-14 핸드오프의 유일한 미해결 건이던 **학습경로 생성을 코드·설정·인프라 전 구간에서 해결**하고 PR 7건을 `develop`까지 병합했다. 그런데 **운영에는 아직 아무것도 반영되지 않았다** — 배포는 `main`을 거쳐야 하고, `main`은 Mission Spine 릴리스 통제에 막혀 있으며, 그 통제를 푸는 열쇠는 **두 번째 GitHub 계정의 수락**이라는 사람 몫이다.

---

## 1. 이번 세션에 병합한 것 (전부 `develop`, 운영 미적용)

| 레포 | PR | 머지 SHA | 내용 |
|---|---|---|---|
| learning-svc | #52 | `e9671e04` | 생성을 사용자당 단일 비동기 작업으로 분리, `GET /learning-paths/me/generation` 추가 |
| ai-svc | #36 | `a05e8707` | 프롬프트 한국어 지시 + 12주 계약(스키마·검증) |
| ai-svc | #37 | `f39c54bf` | 경로 생성 Ollama 를 임베딩과 분리 + 환경 변수 배선 |
| gitops | #64 | `b662cd27` | GPU 전용 Ollama 앱 · 노드 테인트 · device plugin · 타임아웃 |
| gitops | #63·#65 | `19e2a05e`·`cfe5e3db` | 릴리스 핸드오프 §11 이월 기록·갱신 |
| documents | #99 | `a0bc2ac0` | API 명세 §3.1·§3.2 |

**병합 직후 운영 ArgoCD 애플리케이션 13개는 전부 `Synced/Healthy` 로 변화 없음을 확인했다.** `develop` 머지는 배포가 아니다 — ArgoCD 는 `main` 을 본다.

### 무엇이 실제로 고쳐졌나

08-14 문서는 「12분을 계산하고도 SSE 가 끊겨 결과가 버려진다」고 적었는데, 코드 실측 결과 결함은 **세 겹**이었다.

- **D1 타임아웃**: learning-svc→ai-svc, ai-svc→Ollama 둘 다 기본 `PT8S`. 먼저 터지는 건 이것이다.
- **D2 결과 폐기**: ai-svc 가 Ollama 를 `stream:false` 로 부르므로 서버가 클라이언트 이탈을 감지하지 못한 채 끝까지 계산한 뒤 죽은 소켓에 쓴다. 게다가 `LearningPathController.send()` 가 SSE `IOException` 을 예외로 올려 **persist 직전(`matching`)에** 생성을 중단시켰다.
- **D3 중복 실행**: 요청마다 공용 ForkJoinPool 에 새 12분 작업.

D2·D3 는 코드로 닫혔고 D1 은 매니페스트로 준비됐다(배포 대기).

---

## 2. 지금 막혀 있는 것 — 둘 다 사람 몫

### ① 독립 reviewer (릴리스 전체의 임계 경로)

실측한 상태다.

| 확인 | 값 |
|---|---|
| 조직 멤버 | `VelkaressiaBlutkrone` **1명뿐**, 팀 0개 |
| shared `main` 보호 | 승인 1건 필수 · `require_last_push_approval=true` · `dismiss_stale_reviews=true` · `strict=true` · **`enforce_admins=true`** |
| shared #67 | `BLOCKED`/`REVIEW_REQUIRED`, `build` **pass**, head `a8ab5417` |
| 보호 환경 2곳 | reviewer = 본인 1명, **`prevent_self_review=true`** |

즉 **막힌 곳이 두 군데인데 원인이 하나**다. GitHub 은 자기 PR 승인을 막고, `enforce_admins=true` 라 **관리자 우회조차 불가능**하다(규칙을 *끄는* 것만 가능). 게시도 「승인 가능한 유일한 사람 = 배포를 일으킨 사람」이라 같은 벽에 막힌다.

**이번 세션에 보낸 초대(둘 다 미수락)**

- 조직 초대: `qahnaarin` (`state=pending`)
- devpath-shared 저장소 초대: `qahnaarin`, `write` 권한

`write` 를 따로 준 이유는 조직 기본 권한이 `read` 라 승인이 카운트되지 않을 수 있어서다.

> **주의**: `qahnaarin` 이 같은 사람의 부계정이면 GitHub 규칙은 충족되지만 **「독립 검토」의 실질은 없다.** 이 릴리스의 evidence 를 신뢰도로 평가할 때 이 사실을 함께 읽어야 한다.

### ② GPU 스팟 쿼터

| 쿼터 | 코드 | 값 | 상태 |
|---|---|---|---|
| **스팟** G/VT | `L-3819A6DF` | **0.0** | 요청 `78d4c546d7a549cfa6f9ca813d5f9a0ePZ3LBUo5` = `CASE_OPENED` |
| 온디맨드 G/VT | `L-DB2E81BA` | 4.0 | `CASE_CLOSED`(07-28 승인) |

온디맨드 쪽이 `CASE_CLOSED`+4.0 으로 보이므로 **이 측정법은 승인을 감지한다**(대조군 확보). 스팟은 아직 0 이라 지금 띄우면 `MaxSpotInstanceCountExceeded` 가 난다.

**다만 쿼터가 나와도 급하지 않다.** `ollama-gpu` 는 `main` 머지 전에는 배포되지 않으므로 노드를 미리 세우면 유휴 과금만 생긴다(스팟 $0.28/h ≈ 월 $206). **릴리스 직전에 세우는 것이 맞다.**

---

## 3. 재개 순서

1. **[사람] `qahnaarin` 으로 로그인해 조직 초대 + devpath-shared 저장소 초대 수락**
2. **[에이전트] 보호 환경 reviewer 에 `qahnaarin` 추가 후 재조회로 확인** — 아래 「함정」의 조용한 실패 참조
3. **[사람] `qahnaarin` 으로 shared #67 승인** (`require_last_push_approval=true` 라 푸시한 계정의 승인은 카운트되지 않는다)
4. **[에이전트] #67 을 merge commit 으로 `main` 병합**
5. **[사람] `publish.yml` 이 `mission-spine-shared-package-publish` 환경 승인 대기에 들어가면 `qahnaarin` 으로 승인**
6. **[에이전트] 게시 검증** — Maven 에서 `ai.devpath:devpath-shared:0.0.1-et9.20260816` 의 JAR/POM/module 을 재다운로드해 frozen SHA-256 과 대조
7. **[에이전트] AI + 7개 서비스 PR fresh rerun** → build GREEN 확인 후 feature→develop 병합 (8건 실패 원인이 전부 이 패키지 하나였다)
8. 이후는 릴리스 핸드오프 §5 의 8~12 단계를 따른다. **GPU 노드는 그 흐름에서 11~12단계 직전에 세운다**(런북 「GPU 노드 추가」 절, 10분).

### main 에 닿기 전 반드시 확인할 게이트 2개

gitops `develop` 이 곧 릴리스 PR #59 의 head 라 **GPU 매니페스트가 릴리스 범위에 들어와 있다**(`main...develop` 118개 파일 중 `apps/devpath-ollama-gpu/` 4개).

1. **GPU 노드가 실재해야 한다.** 없으면 `ollama-gpu` 는 `nodeSelector` 를 만족하는 노드가 없어 영구 `Pending`.
2. **`OLLAMA_PATH_*` 를 읽는 ai-svc 이미지가 배포돼야 한다.** 코드는 `develop` 에 있지만 이미지가 나가야 env 가 의미를 갖는다.

둘 중 하나라도 빠지면 학습경로 생성은 **지금보다 더 빨리** 실패한다(엔드포인트 없는 서비스 주소를 가리키므로).

---

## 4. GPU — 결정과 검증 (노드는 검증 후 종료함)

사용자 결정: **g6.xlarge 스팟 + Ollama 이중화.** Ollama 는 학습경로뿐 아니라 **임베딩과 멘토 폴백**도 맡고 있어(크레딧 소진으로 `MENTOR_PROVIDER=ollama`), 통째로 GPU 노드에 올리면 스팟 회수 때 그 둘까지 멈춘다.

| | 노드 | 맡는 일 |
|---|---|---|
| `devpath-ollama`(기존) | t3.xlarge CPU | 임베딩 · 멘토 폴백 · 리뷰 · 커뮤니티 시드 |
| `devpath-ollama-gpu`(신규) | g6.xlarge GPU(스팟) | 학습경로 생성 전용 |

노드 계층은 **온디맨드로 임시 검증 후 종료**했다(스팟 쿼터 대기). 검증 결과:

- g6.xlarge = **NVIDIA L4 23GB**, 드라이버 595.91.07. `nvidia.com/gpu: 1` 이 할당 가능 자원으로 광고되는 것까지 확인.
- **테인트 격리가 실제로 필요했다.** 없으면 기존 서비스 파드가 재시작될 때 스팟 노드로 흘러가 회수 시 무관한 서비스까지 내려간다. `devpath.ai/gpu=true:NoSchedule` 적용 후 GPU 노드의 파드가 `ollama-gpu` 와 device plugin **둘뿐**임을 확인했다.
- **성능: 66 t/s(순간 97) vs 운영 CPU 4.2 t/s ≈ 16배.** 12주 한국어 경로 1건이 ai-svc 왕복 포함 **86초**.

**클러스터에 남겨둔 것**: `infra/nvidia-device-plugin/daemonset.yaml`(적용됨, GPU 노드 없으면 스케줄되지 않아 무해)과 SG 의 self-referencing 규칙 3개(`6443/tcp`·`8472/udp`·`10250/tcp`, 외부 노출 없음). 절차는 gitops `docs/runbook-k3s-bootstrap.md` 「GPU 노드 추가」 절에 실측으로 기록했다.

---

## 5. 함정 — 다음 세션이 반드시 알아야 할 것

### ★성공 응답이 적용을 뜻하지 않는다 (환경 reviewer)★

보호 환경에 `qahnaarin` 을 reviewer 로 추가하는 PUT 이 **200 을 반환했는데 실제로는 추가되지 않았다.** 초대 수락 전이라 저장소 접근 권한이 없어 GitHub 이 그 항목만 조용히 버렸다. 재조회하지 않았다면 "reviewer 2명 준비됨"으로 보고했을 것이고, 게시 워크플로는 **승인자 없이 영원히 대기**했을 것이다. **환경 설정은 PUT 후 반드시 재조회한다**(다른 통제 값 보존 여부까지).

### ★속성만 추가하면 환경 변수는 조용히 무시된다★

ai-svc 에 `devpath.ollama.path-timeout` 을 추가하고 `OLLAMA_PATH_TIMEOUT=PT300S` 를 주었는데 요청이 **정확히 8.1초에 503** 으로 끊겼다. 이 서비스의 환경 변수는 완화 바인딩이 아니라 **`application.yml` 자리표시자로 배선**되므로, 거기 등록하지 않은 속성은 env 를 아무리 넣어도 무시된다. 단위 테스트는 점 표기 속성을 직접 주입해 전부 통과했었다 — **클러스터로 실제 호출해서야 드러났다.**

추가로, yaml 기본값을 env(`${OLLAMA_BASE_URL:...}`)로 가리키면 속성 오버라이드 경로가 끊겨 기존 테스트 16건이 깨진다. **속성**(`${devpath.ollama.base-url}`)을 가리켜야 한다.

### ★`gh pr diff` 는 큰 PR 에서 조용히 0건을 낸다★

릴리스 PR #59 의 범위를 `gh pr diff 59 --name-only | grep -c ollama-gpu` 로 쟀더니 **0** 이었다. 원인은 **HTTP 406(diff 20000줄 초과)**. 「릴리스에 안 들어갔다」로 오판할 뻔했다. `git diff --name-only origin/main...origin/develop` 으로 재야 한다(118개 중 GPU 4개).

### ★목(mock)은 「내용이 못 쓸 것」을 보지 못한다★

비동기화 후 로컬에서 **실제 Ollama** 로 돌리자 두 결함이 드러났다. ①학습경로만 **영어**로 나온다(멘토·커뮤니티 시드 프롬프트에는 `in Korean` 이 있는데 path 프롬프트에만 없었다) ②**12주를 약속하고 3주를 저장한다**(14b 가 weekNum 1·2·4 로 3개만 냈는데 계약이 통과시켰고, `setTotalWeeks(12)` 는 하드코딩이다). 둘 다 ai-svc #36 에서 닫았다.

### ★「없음」을 404 로 응답하면 테스트가 판별력을 잃는다★

매핑이 없어도 404 라서 구현 전에도 통과한다. 그래서 생성 상태 조회는 **200 + `state=NONE`** 으로 설계했다.

### 그 밖에

- **스팟 쿼터는 온디맨드 쿼터와 별개다**(`L-3819A6DF` vs `L-DB2E81BA`).
- **이월된 블로커는 이월된 채로 믿지 말 것.** 08-14 문서의 전제 3건이 모두 틀렸다(GPU 쿼터는 이미 승인·g5/g6 는 같은 AZ 가용·실패 지점은 SSE 가 아니라 PT8S). 「PENDING」은 시간이 지나면 사실이 아니게 되는 종류의 진술인데 문서는 갱신되지 않는다.
- **`gh api` 로 `/aws/...` 나 `origin/branch:path` 를 쓸 때 Git Bash 가 경로를 변환한다.** `MSYS_NO_PATHCONV=1` 을 붙인다.
- **`| tail` 로 파이프한 백그라운드 프로세스의 로그는 종료 전까지 비어 있다.** 서비스 기동 로그를 그렇게 잡으면 못 읽는다.

---

## 6. 착수 전 재확인 명령

```bash
# 초대 수락 여부
gh api orgs/DevPathAi/memberships/qahnaarin --jq .state
gh api repos/DevPathAi/devpath-shared/invitations --jq '.[].invitee.login'

# 환경 reviewer (추가 후 반드시 재조회)
gh api repos/DevPathAi/devpath-shared/environments/mission-spine-shared-package-publish \
  --jq '[.protection_rules[]|select(.type=="required_reviewers")|.reviewers[].reviewer.login]'

# shared #67
gh pr view 67 --repo DevPathAi/devpath-shared --json mergeStateStatus,reviewDecision

# 패키지 게시 여부 (게시 전에는 0.0.1-SNAPSHOT 만 보인다)
gh api orgs/DevPathAi/packages/maven/ai.devpath.devpath-shared/versions --jq '.[].name'

# 스팟 쿼터
aws service-quotas get-service-quota --service-code ec2 --quota-code L-3819A6DF --region ap-northeast-2 --query Quota.Value

# 릴리스 범위(gh pr diff 쓰지 말 것)
git -C devpath-gitops diff --name-only origin/main...origin/develop | wc -l
```

---

## 7. 남은 백로그 (이번 세션 범위 밖)

- **프론트 폴링 미구현** — 웹은 SSE 단절을 실패로 처리하고 `GET /me/generation` 을 부르지 않는다. 지금 손대면 릴리스 PR #133 의 head 가 움직인다.
- **ai-svc 재시도 정책** — `OllamaClient.generatePath` 는 계약 위반 시 1회 재시도라 최악 2배 시간.
- **한국어 준수가 100%는 아니다** — 제목 12/12 는 한국어인데 `rationale` 이 영어로 나온 실행이 있었다. L4 24GB 는 `qwen2.5:14b`(9GB)도 수용하므로 모델 상향이 선택지.
- 08-14 이월분: 사용자 육안 확인 3건(자유글·문의·멘토), leva.ai.kr SEO, 남은 두 트랙(`NODE_TYPESCRIPT`·`DATA_AI`), 글 수정·삭제 신규 개발.

## 8. 참고

- 릴리스 통제·STOP 조건: `devpath-gitops/docs/mission-spine-release-handoff-2026-08-17.md`
- GPU 노드 절차: `devpath-gitops/docs/runbook-k3s-bootstrap.md` 「GPU 노드 추가」
- 메모리: `devpath-path-generation-async` · `devpath-mission-spine-release` · `devpath-prod-k3s-access`
