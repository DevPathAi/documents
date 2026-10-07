# 핸드오프 — 2026-10-07 세션 마무리 (스팟 회수 복구 → 반복 통지 → 자동 복구 설계 · 계획)

> 앞 문서: `handoff-2026-10-06-session-close.md` — §7(10-06 저녁 후속) · §8(10-07 새벽: 결정 5건 · 두 번째 회수 복구)에 이 세션 앞부분의 상세가 있다.
> 이 문서가 다음 세션의 시작점이다. **다음 세션 첫 동작은 §1.**
> 원장(git 밖, 지우지 말 것) = `D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget/` — 이 세션에 `propagation-probe/` 를 더했다.

## 0. 한 줄 요약

운영과 동결 브랜치는 그대로다. 세션 중 GPU 스팟 노드가 회수돼 다시 띄웠고(지금 정상) 미복구 반복 통지를 붙였다.
이어서 「회수돼도 사람 없이 돌아오는」 자동 복구를 설계했다 — 스펙은 승인 · 머지됐고,
**구현 계획은 사용자 검토와 실행 방식 선택을 기다린다(documents PR #219). 구현은 시작하지 않았다.**

## 1. 다음 세션 첫 동작

### 1-0. 세션 시작 점검 (읽기 전용)

1. GPU 노드 — `DescribeInstances` 에 태그 `role=k3s-agent-gpu` 인 인스턴스가 `running` 인가(지금 `i-09f6b4f41ebd973c7`, 스팟 요청 `sir-xta7jjwp`),
   노드 `ip-172-31-60-217` Ready, `ollama-gpu` 1/1, 모델 2종. **목록에 안 보이면 회수된 것이다**(종료된 인스턴스는 약 1시간 뒤 사라진다).
   회수되면 경고 · 종료 메일에 더해 6시간마다 「GPU spot node is still missing」 메일이 온다.
2. 동결 head 4개가 §3 표와 같은가.
3. 운영: Argo 16 앱 Synced/Healthy · ai-svc `sha256:c3c29ade…`.

### 1-1. 사용자에게 먼저 물을 것

자동 복구 구현 계획(documents PR #219)에 대한 답을 받지 못한 채 세션을 닫았다. 마지막 질문은 둘이었다.

1. 계획이 원하는 내용을 담고 있는가 — 승인하면 PR #219 를 머지한다.
2. 실행 방식 — **직접 실행**(이 세션이 Task 를 순서대로 구현하고 끝에 새 리뷰어 하나가 브랜치 전체를 본다, 권장) 또는
   **서브에이전트 실행**(Task 마다 새 서브에이전트 + 새 리뷰어).

승인되면 계획의 Task 0 부터 한다. Part C(Task 8 전환 · Task 10 훈련)는 각각 GPU 기능이 약 10분 멈추므로 **시작 전에 시각을 따로 확인**받는다.
승인 전에는 gitops 코드도 AWS 리소스도 만들지 않는다 — 지금 자동 복구용 리소스는 하나도 없다(파라미터 · 기동 템플릿 · ASG · 알람 0개, 02:04Z 실측).

### 1-2. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| GPU 노드가 또 회수됐다(자동 복구를 구현하기 전) | gitops `docs/runbook-k3s-bootstrap.md` 「스팟 회수 후 복구」의 수동 절차. 루트 120 GiB + 태그 `role=k3s-agent-gpu` 로 띄운다. 기동은 비용이 드니 **사용자 확인 뒤**. 기동부터 검증 끝까지 약 7분(앞 문서 §8-2) |
| 2026-10-19 15:13 이후(Codex 한도 해제) | gitops #169(landing 마커 재시도) · #171(진단 출력)의 독립 리뷰 → 지적 처리 → publisher 준비 → **사용자 확인** → 실행. 사용자 결정: 다음 candidate 직전에 둘을 한 번에 |
| 다음 캠페인 | **보류**(사용자 결정) — 올릴 제품 변경이 생길 때 시작한다. 입력값은 앞 문서 §4 · §7-2 |
| 2026-10-15 07:12Z 가 지났다 | platform-svc 이미지 증거 만료(10-21 에 5개, 10-23 에 gateway). 캠페인을 그 뒤에 돌릴 때만 재빌드한다 |
| Slack 수신처 | **뒤로 미룸**(사용자 결정). 다시 할 때의 순서는 앞 문서 §8-4 |

## 2. 이 세션에서 한 것

| 레포 | PR | 내용 | 머지 |
|---|---|---|---|
| gitops | #171 | 원인 미확정인 일시적 게이트 실패 둘(seal 의 producer 런 선택 · landing 프로브 재시도)에 진단 출력만 추가 | develop `6c6cf436` |
| gitops | #172 | 미복구 반복 통지 Lambda 의 소스 · 테스트, 런북(회수 · 복구 실측, 120 GiB 실측, 규칙 ③, 태그 명시) | develop `a5221faf` |
| gitops | #168 | **닫음**(머지 안 함) — 범위가 이미 main 에 있는 것을 blob 으로 대조하고 근거를 댓글로 남겼다 | — |
| documents | #215 · #216 · #217 | 앞 문서의 §7 · §8, Slack 승인 절차 | develop |
| documents | #218 | 자동 복구 스펙 `specs/2026-10-07-gpu-node-auto-recovery-design.md` | develop `ac7f1ae4` |
| documents | #219 | 자동 복구 구현 계획 `plans/2026-10-07-gpu-node-auto-recovery.md` | **열림 — 검토 대기** |

PR 을 거치지 않은 것:

- **GPU 스팟 노드 교체** — 2026-10-06 17:22Z 회수(`instance-terminated-no-capacity`) → 사용자 확인(「스팟으로 지금 기동」) 뒤 18:50Z 기동 → 런북 복구 3~5단계 → 18:56Z `ollama-gpu` 복귀 → 19:26Z 폴백 복귀. 중단 약 94분.
- **AWS 리소스 4개**(전부 이름 `devpath-gpu-node-absence-watch`) — EventBridge 규칙(`rate(6 hours)`) · Lambda · IAM 역할 · 로그 그룹.
- **gitops 본 클론의 로컬 git 설정** — `.git/config` 의 `[user]`(릴리스 봇 이름)를 지웠다. 기본 작성자가 `Qahnaarin` 이 됐다.
- **실측 2건**(흔적은 지웠다) — Cloudflare Pages 전파 시간(preview 배포 4개는 남아 있다) · 같은 노드 이름으로의 복귀(임시 인스턴스 3대 · 테스트 네임스페이스).

## 3. 현재 상태 (2026-10-07 02:04Z 실측)

| 항목 | 값 |
|---|---|
| 운영 | Argo 16 앱 Synced/Healthy rev `9ab0dd79` · ai-svc `c3c29ade` 1/1 · `leva.ai.kr` · `app` · `api` 200 |
| 노드 | `ip-172-31-48-82`(control-plane) Ready · `ip-172-31-60-217`(GPU 스팟, 루트 120 GiB) Ready · `ollama-gpu` 1/1 · 모델 `qwen2.5:3b` `qwen2.5:7b` |
| EC2 | `i-09e252854566cc123`(control-plane) · `i-09f6b4f41ebd973c7`(GPU, `g6.xlarge` 스팟, 2026-10-06 18:50Z 기동) |
| 회수 감시 | 규칙 ① `devpath-spot-interruption-warning` · ② `devpath-instance-stopped-or-terminated` · ③ `devpath-gpu-node-absence-watch`(6시간마다, 18:46Z · 00:46Z 에 돌았다) |
| 열린 PR | documents #219 하나 |

| 브랜치 | head | 비고 |
|---|---|---|
| gitops **main** | `9ab0dd79` | **동결**(롤백 창) |
| 홈 **master** | `abdf57a7` | **동결** |
| documents **main** | `f52b4a9a` | **동결** |
| ai-svc **main** | `c5614621` | **동결** |
| gitops develop | `a5221faf` | #169 · #170 · #171 · #172 가 main 보다 앞서 있다 |
| 홈 develop | `7779e0a3` | #100 이 master 보다 앞서 있다 |
| documents develop | 이 문서의 PR 머지 커밋 | |

동결은 다음 캠페인 candidate 직전까지다. develop 머지는 괜찮다.

## 4. 이 세션의 사용자 결정

| 시각(KST) | 원문 | 뜻 |
|---|---|---|
| 10-06 저녁 | 「사용자가 직접 선택/작업해야 하는 부분은 내일 오전까지 연기 / 그외 작업들은 … 지속적으로 작업 진행」 | 결정이 필요한 것은 모아 두고 나머지를 진행 |
| 10-07 새벽 | 「1~5 전부 권장대로 진행」 | publisher 는 리뷰 뒤 다음 candidate 직전에 #169 · #171 한 번에 · 다음 캠페인 보류 · gitops 로컬 봇 이름 제거 · 미복구 반복 통지 구축 · PR #168 닫기 |
| 10-07 새벽 | 「스팟으로 지금 기동」 | 회수된 GPU 노드를 스팟으로 다시 띄운다 |
| 10-07 아침 | 「슬랙은 잠시 뒤로 미루고 다른 작업 우선」 | Slack 수신처 보류 |
| 10-07 아침 | 「GPU 노드 복구 자동화」 | 다음 작업 선택 |
| 10-07 아침 | 「A + 실측부터」 → 「이대로 스펙 작성」 → 「승인」 | 접근 A(같은 노드 이름으로 복귀) · 설계 · 스펙 승인 |
| 10-07 오전 | (답 없음 — 세션 이관 지시) | **계획 검토와 실행 방식은 정해지지 않았다** |

## 5. 자동 복구 — 어디까지 왔나

| 단계 | 상태 |
|---|---|
| 전제 실측 | 끝 — 2026-10-06 21:25~21:36Z, 임시 노드 `spike-node` |
| 스펙 | 승인 · 머지 — `docs/superpowers/specs/2026-10-07-gpu-node-auto-recovery-design.md` |
| 구현 계획 | 작성 · PR #219 — **검토 대기** — `docs/superpowers/plans/2026-10-07-gpu-node-auto-recovery.md`(브랜치 `docs/plan-gpu-node-auto-recovery`) |
| 구현 | 시작 전 |

**무엇을 만드나**: ASG(스팟 1대, 2a · 2c · 2d)가 대체 인스턴스를 띄우고, 기동 스크립트가 SSM 에서 조인 토큰과 노드 비밀번호를 읽어
**같은 노드 이름(`devpath-gpu`)** 으로 조인한다. 클러스터는 같은 Node 가 돌아온 것으로 보므로 노드 · 파드 · PVC 를 지우지 않는다.
노드가 1분마다 보내는 생존 신호(CloudWatch 지표)를 알람(15분)과 반복 통지 Lambda(6시간)가 본다. gitops `apps/` 를 바꾸지 않아 publisher 와 무관하다.

**실측으로 확인한 것**(스펙 3.1):

- 같은 이름 · 비밀번호 없음 → 거부(`Node password rejected, duplicate hostname …`).
- 같은 이름 · 저장해 둔 `/etc/rancher/node/password` → 같은 Node 오브젝트(UID · podCIDR 그대로)로 복귀, 멈춘 파드는 스스로 사라진다.
- local-path 의 PV 는 `local` 타입이라 새 디스크에 디렉터리를 미리 만들어야 한다(없으면 `FailedMount … path does not exist`).
- 축출(5분) 전에 교체하면 같은 파드가 제자리에서 재시작한다 — 종료부터 Running 까지 88초.

**계획의 구성**: Part A gitops 코드(Task 0~5, 테스트 44개를 먼저 쓴다) → Part B AWS 준비(Task 6~7, 서비스 영향 없음) →
Part C 전환 · 알람 확인 · 훈련 · 기록(Task 8~11). 계획이 스펙에 더한 것은 하나다 — 기동 스크립트가 `model-dir` 를 볼륨 저장소 루트 밖이면 거부한다(그 디렉터리를 0777 로 만들기 때문).

**아직 실측하지 않은 것**(전환과 훈련에서 본다): 부트스트랩 토큰으로의 조인 · 비밀번호 파일을 미리 둔 첫 등록 · GPU 노드에서 device plugin 이 다시 등록되는 순서 ·
IP 가 바뀐 노드로의 노드 간 통신 · ASG 와 기동 스크립트 자체.

## 6. 이번 세션의 함정과 교훈

앞 문서 §8-6 에 더해:

- ★**「새 노드만 띄우면 Pending」의 뿌리는 저장소가 아니라 이름이다.** PV 가 노드 이름에 고정돼 있어서, 같은 이름과 같은 노드 비밀번호로 들어오면 아무것도 지울 필요가 없다.★
- ★**Node 오브젝트를 지우면 `<이름>.node-password.k3s` 시크릿도 함께 사라진다.** 그 뒤 같은 이름으로 들어오는 노드는 새로 등록된다.★
- ★**ai-svc 의 폴백은 파드가 Ready 가 된 뒤에도 최대 30분 늦게 돌아온다.** `ProviderLatch` 가 실패가 이어지는 동안 재탐색 간격을 1분에서 30분까지 늘린다. 그동안 Claude 1차 경로와 재시도는 정상이다.★
- ★**홈 dist 는 커밋이 바뀌면 반드시 바뀐다**(모든 HTML 에 `appVersion` = 커밋 SHA). 「테스트 파일만 바뀌어 그대로일 수 있다」는 추정은 틀렸다.★
- 메일은 왔지만 새벽이라 아무도 읽지 않았다. 탐지가 있어도 사람이 볼 때까지는 방치된다 — 그래서 자동 복구다.
- AWS MCP `call_boto3` 는 바이트 인자를 넘기지 못한다(Lambda zip 은 임시 S3 버킷으로). 반대로 `s3:GetObject` 의 본문은 텍스트면 문자열로 읽힌다 — 비밀을 세션에 싣지 않고 옮기는 경로가 된다.
- EventBridge `rate()` 규칙은 만든 직후 한 번 돈다.
- gitops 에서 봇 이름이어야 하는 커밋은 이제 `-c user.name=… -c user.email=…` 를 직접 줘야 한다. `git cherry-pick -q` 는 없는 옵션이다.
- `.worktrees/_tools/` 에 재귀 grep 을 걸면 Flutter SDK 를 통째로 훑어 2분 타임아웃이 난다.
- 세션의 Slack 커넥터로는 채널이 조회되지 않았다(`general` 포함 5건 모두 0건).

## 7. 환경과 자산

- **워크트리**(`D:/workspace/dpa/.worktrees/`): 캠페인의 8개(`gitops-dispatch-1003` · `gitops-candidate-1003` · `gitops-main-1003` · `shared-dispatch-1003` · `fe-dispatch-1003` · `fe-main-1003` · `docs-dispatch-1003` · `home-master-1002`)는 그대로다.
  이 세션의 작업용은 모두 지웠다. 계획 PR 의 브랜치 `docs/plan-gpu-node-auto-recovery` 는 원격에 있다 — 고칠 일이 있으면 거기서 워크트리를 다시 만든다.
- **도구**: 고정 kustomize v5.4.3 = `D:/workspace/dpa/.worktrees/_tools/kustomize-v5.4.3/kustomize.exe` · 핀 Flutter = `…/_tools/flutter-3.44.1/bin`.
- **원장에 더한 것**: `propagation-probe/`(Pages 전파 시간 실측의 스크립트 · 로그 · README). documents 사본에도 있다.
- **남아 있는 외부 흔적**: Cloudflare Pages 의 preview 배포 4개(브랜치 `probe-prop-1006`, 운영과 무관).
- **이 세션이 건드리지 않은 것**: 각 레포 본 클론의 작업 브랜치(gitops `fix/bypass-observable-contract` · documents `docs/handoff-seal-restore` · 홈 `feat/seo-note-cta` 등)는 세션 시작 때 그대로다.
- **운영 접근**: `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`. GPU 노드는 공인 IP 로 직접(지금 `3.37.16.73`, 기동마다 바뀐다). AWS 는 MCP `run_script`.
