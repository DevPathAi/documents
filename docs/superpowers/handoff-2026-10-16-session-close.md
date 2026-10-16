# 핸드오프 — 2026-10-16 세션 마무리 (캠페인 운영 반영 → 리뷰 후속 → GPU 자동 복구 Part A·B)

> 앞 문서: `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md`(캠페인 상세) · `handoff-2026-10-07-session-close.md`(그 전 이관).
> 이 문서가 다음 세션의 시작점이다. **다음 세션 첫 동작은 §1.**
> 원장(git 밖, 지우지 말 것): 캠페인 = `D:/workspace/dpa/.release-artifacts/ms-20261016-leva-inspection-fixes/` ·
> 자동 복구 = `D:/workspace/dpa/.release-artifacts/gpu-auto-recovery-part-a/`(`progress.md` — Part A·B 실행 원장, 판단 줄 · `final-review.md` — 최종 리뷰 보고서).

## 0. 한 줄 요약

점검 명세(10-11)의 ④ 앱 · ⑤ 랜딩 수정이 운영에 나갔다(캠페인 `ms-20261016-leva-inspection-fixes`, 체인 `mission-on`).
GPU 스팟 노드 자동 복구는 **코드(Part A)와 AWS 준비(Part B)까지 끝났다.** 리소스는 있지만 꺼져 있다 — ASG 희망 대수 0, 알람 동작 꺼짐.
**남은 것은 Part C(전환 · 훈련)이고, GPU 기능이 약 10분씩 두 번 멈추므로 시각을 사용자에게 먼저 확인받는다.**

## 1. 다음 세션 첫 동작

### 1-0. 세션 시작 점검 (읽기 전용)

| 항목 | 지금 값(2026-10-16 실측) | 다르면 |
|---|---|---|
| GPU 노드 | `i-08bf0d3ef0f3471df`(스팟, 10-15 06:46Z 기동) · 노드 `ip-172-31-53-253` Ready · `ollama-gpu` 1/1 · 모델 `qwen2.5:7b` `qwen2.5:3b` | 목록에 없으면 회수된 것이다. **아직 자동 복구 전**이므로 런북 「스팟 회수 후 복구」의 수동 절차(기동은 사용자 확인 뒤) |
| 회수 알림 구독 | 토픽 `devpath-spot-interruption` → `mingoo@leva.ai.kr` 1개(해제 시 인증 요구 켜짐) | 0개면 재구독 |
| ASG `devpath-gpu-node` | 희망 0 · 인스턴스 0 | 희망이 0 이 아니면 누가 켰는지부터 본다(스팟 쿼터 4 vCPU — 지금 노드와 동시에 못 뜬다) |
| 알람 `devpath-gpu-ollama-not-ready` | `ALARM` · **동작 꺼짐** | `ALARM` 은 정상(신호가 아직 없다). 동작이 켜져 있으면 즉시 끈다 — 거짓 메일 |
| Lambda `devpath-gpu-node-absence-watch` | 옛 판(인스턴스 기준) · CodeSha256 `pkHhRBf8zgZTUA7Hy5/X+yJu9oYwvLWBaPEBv47Z6f4=` · env `TOPIC_ARN` `GPU_ROLE_TAG` | develop 판으로 바뀌어 있으면 6시간마다 거짓 통지가 온다 |
| 동결 head(롤백 창) | documents main `5d898ad7` · ai-svc main `cd756fbf` · 홈 master `d46c3f6a` · gitops main `ef5ad0bc` | 움직였으면 이 릴리스의 자동 롤백이 막혔다 — 사용자에게 알린다 |
| 운영 | Argo 16 앱 Synced/Healthy rev `ef5ad0bc` · `leva.ai.kr` · `app` 200 · `api` `/actuator/health` 200 | |

### 1-1. Part C — 사용자에게 시각을 먼저 묻는다

계획 = documents `docs/superpowers/plans/2026-10-07-gpu-node-auto-recovery.md` 의 **Part C(Task 8~11)**. 실행 방식은 직접 실행(executing-plans)으로 이어 간다.
원장 `gpu-auto-recovery-part-a/progress.md` 에 Task 0~7 완료 줄과 판단이 있다 — 새 원장을 만들지 말고 거기에 이어 적는다.

| Task | 내용 | 영향 |
|---|---|---|
| 8 전환 | 지금 노드 종료 → 옛 Node · 파드 · PVC 삭제(마지막) → ASG 희망 1 → `devpath-gpu` 로 조인 → 새 PV 경로를 `model-dir` 에 | **GPU 기능 약 10분 중단** |
| 9 감시 | 생존 신호 확인 → Lambda 를 새 판으로(역할 정책에 `ReadHeartbeat`, env 3개) → 알람 `OK` 확인 후 동작 켬 → 타이머를 20분 멈춰 ALARM · OK 메일 확인 | 없음 |
| 10 훈련 | ASG 인스턴스를 일부러 종료 → 사람 없이 10분 안에 모델 2종 · 같은 노드 UID 인지 잰다 | **GPU 기능 약 10분 중단** |
| 11 기록 | 런북 실측 단락 · 확정값 · 반복 통지 절 판정 문장 · 핸드오프 · 메모리 · 워크트리 정리 | 없음 |

★**계획 문서를 그대로 따르면 틀리는 곳**(계획은 10-07 에 쓰였다 — 계획 문서 끝 「실행 기록」에도 적었다):

1. **Task 8 Step 1·2 의 옛 노드**: 계획의 `i-09f6b4f41ebd973c7` · `ip-172-31-60-217` 은 10-07 에 회수됐다. 지금은 **`i-08bf0d3ef0f3471df` · `ip-172-31-53-253`**. 실행 직전 `DescribeInstances`(태그 `role=k3s-agent-gpu`)로 다시 읽는다.
2. **Task 8 Step 5 의 기동 로그 기대값**: 최종 리뷰 수정(gitops `92bcdfc`)으로 순서와 문구가 바뀌었다. 지금 기대값은 순서대로
   `heartbeat timer enabled` → `wrote the node password and the agent token` → `no model-dir parameter: …` →
   `k3s agent v1.36.2+k3s1 installed as devpath-gpu (attempt N)` → `k3s-agent starting; the heartbeat reports once ollama-gpu serves both models`.
   실패 시 끝 줄은 `gpu-node bootstrap failed: … gave up after …` 이고, 그 위에 이유(오류 코드 · 설치 출력 끝부분, 비밀은 `<redacted>`)가 있다.
3. **Task 8 Step 4**: agent 는 이제 `systemctl start --no-block` 으로 시작한다. 조인 실패는 기동 스크립트를 멈추지 않고 `journalctl -u k3s-agent` 에 남는다 — 10분이 지나도 노드가 안 보이면 거기부터.
4. **Task 9 Step 1**: Lambda 의 현재 env 는 2개(`TOPIC_ARN` `GPU_ROLE_TAG`), 역할 정책 문장은 3개(`FindGpuInstances` `Remind` `WriteOwnLogs`) — 계획과 같다(10-16 실측). 배포할 소스는 gitops develop `54061633` 의 `infra/aws/gpu-node-absence-watch/handler.py`.
5. **Task 11 Step 2**: 계획은 `handoff-2026-10-06-session-close.md` §9 에 적으라고 하지만, 그때의 최신 핸드오프(이 문서 또는 그 뒤의 것)에 적는다.

★**순서를 지킬 것**: 알람 동작은 생존 신호가 들어오고 상태가 `OK` 가 된 **뒤에** 켠다. Lambda 도 신호가 들어온 뒤에 바꾼다. 반대로 하면 거짓 메일이 즉시 · 6시간마다 온다.
★**실측하지 않은 것**(전환과 훈련에서 처음 본다): 부트스트랩 토큰으로의 조인 · 비밀번호 파일을 미리 둔 첫 등록 · GPU 노드에서 device plugin 이 다시 등록되는 순서 ·
IP 가 바뀐 노드로의 노드 간 통신 · ASG 와 기동 스크립트 자체 · 폐기한 토큰으로 이미 조인한 agent 의 재시작.
★**되돌리는 법**: ASG 희망 0 + 알람 동작 끄기 + 반복 통지 규칙 끄기(런북 「자동 복구」 → 「끄는 법」) 뒤, 런북의 수동 절차.

### 1-2. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| Part C 전에 GPU 노드가 회수됐다 | 런북 「스팟 회수 후 복구」 수동 절차(사용자 확인 뒤 기동). 또는 사용자가 원하면 그 자리에서 Part C 의 Task 8 을 앞당긴다(옛 노드가 이미 없으니 Step 2 의 종료만 빠진다) |
| 다음 릴리스 캠페인 | 입력값 = `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md` §5. gitops develop 에 #175(Landing·seal 리뷰 후속)가 있어 **다음 publisher 에 함께 올린다**. 서비스를 여러 개 함께 올리면 RDS 커넥션 여유부터 잰다(§6) |
| 이미지 증거 만료 | 최단 2026-11-14 |

## 2. 이 세션에서 한 것

| 레포 · 대상 | PR · 작업 | 내용 | 결과 |
|---|---|---|---|
| AWS SNS | 구독 보강 | 회수 알림 구독의 해제에 인증 요구(`ConfirmationWasAuthenticated=true`) | 메일 링크 한 번으로는 못 푼다 |
| 11개 레포 | 캠페인 `ms-20261016-leva-inspection-fixes` | 점검 ④ 앱 · ⑤ 랜딩 · 서비스 8곳 README · documents 공개 저장소 정리 · gitops #169·#171 publisher(Codex 대신 내부 리뷰) | 운영 반영 — 상세는 캠페인 핸드오프(#229) |
| gitops | #175 → develop `a58c39ba` | 내부 리뷰 후속: 같은 dist 마커 판정에 값 형식 검사 · 진단에 release id · 경과 시간 · seal 실패 메시지에 걸러진 런 상태 · 테스트 빈틈 | 390 tests OK · main 은 다음 publisher |
| documents | #219 → develop `34e81202` | 자동 복구 구현 계획 머지(사용자 「진행하기」 = 승인 · 직접 실행) | |
| gitops | #174 → develop `4929bd11` | 자동 복구 Part A: `infra/aws/gpu-node/`(bootstrap · heartbeat · 유닛 · user-data 렌더러) · Lambda 새 기준 · 런북 절. 최종 리뷰 Important 3 + 재등급 2 수정 | GPU 테스트 50 · CI 434 |
| AWS | Part B(사용자 「AWS 준비(Part B)를 지금 시작」) | 파라미터 3 · 역할/프로파일 · 기동 템플릿 · ASG(희망 0) · 토픽 정책 · 알람(동작 꺼짐) — §3 | 서비스 영향 없음 |
| gitops | #176 → develop `54061633` | 런북 상태 줄 「준비 완료 · 전환 전」 | |

## 3. 자동 복구 — 지금 있는 것 (Part B 결과)

| 리소스 | 값 |
|---|---|
| SSM | `/devpath/gpu-node/k3s-version`(String `v1.36.2+k3s1`) · `node-password`(SecureString, 스크립트 안에서 생성) · `agent-token`(SecureString). `model-dir` 은 **전환 때** 만든다 |
| 조인 토큰 | control-plane `k3s token list` 의 id `pc8qap`, 설명 `devpath-gpu-node`, TTL `<forever>`. 값은 presigned PUT → 임시 비공개 S3 → SSM 으로만 지났다(버킷 삭제됨) |
| IAM | 역할 · 프로파일 `devpath-gpu-node` — 인라인 `gpu-node` 하나(`ssm:GetParameter` on `parameter/devpath/gpu-node/*` · `cloudwatch:PutMetricData` 조건 `DevPath/GPU`). 임시 인스턴스로 9가지 실측(대조군 3개 거부 · IMDSv1 401 · KMS 추가 불필요) |
| 기동 템플릿 | `devpath-gpu-node` = `lt-0f28ff0caa50e2ba6` **v1** — DLAMI `ami-09d3bdf0648512f52` · `g6.xlarge` · 120 GiB gp3 · IMDSv2 필수 홉 1 · 태그 `role=k3s-agent-gpu` `Name=devpath-k3s-gpu` · user-data sha256 `d6f500be31b1e41ae37e9333098cf1496c5733b9d603cb4b608b27a59188cb89`(develop `4929bd11` 렌더, 되읽기 일치) · 스팟 DryRun 성공 |
| ASG | `devpath-gpu-node` — 최소 0 · 최대 1 · **희망 0** · 2a/2c/2d · 스팟만 `price-capacity-optimized` · EC2 상태 검사 300초 · `AZRebalance` 중지 · CapacityRebalance 끔 · LT `$Latest` |
| SNS 토픽 정책 | `AllowAccountOwner` · `AllowEventBridgePublish`(그대로) + `AllowCloudWatchAlarmPublish`(이 알람만) |
| 알람 | `devpath-gpu-ollama-not-ready` — `Sum` 300초 × 3 · `< 1` · 누락 = 위반 · **동작 꺼짐**. 지금 `ALARM`(신호 없음) — 메일은 나가지 않았다(이력에 게시 0) |
| DLAMI 실측 | 지금 GPU 노드(같은 AMI): aws-cli v2 `/usr/local/bin/aws` · k3s `/usr/local/bin/k3s` · python3 3.10.12 — 생존 신호 유닛의 PATH 와 맞다 |

## 4. 이 세션의 사용자 결정

| 원문 | 뜻 |
|---|---|
| (SNS 확인 링크 붙여 넣기) | 구독 해제에 인증 요구 켜기 |
| 「코덱스 리뷰는 제외하거나 내부 리뷰로 대체하고 진행」 | #169·#171 독립 리뷰를 새 컨텍스트 리뷰어로 · publisher → 캠페인 |
| 「승인 완료 진행」 · 「셋다 승인」 · 「진행」 | ET13 기준선 · NVDA · 프라이버시 · AI 평가 직접 승인 · 운영 변경 진행 |
| 「진행하기」 | 남은 일 진행 — gitops 리뷰 후속 · 자동 복구 계획 승인(직접 실행) · Part A |
| 「AWS 준비(Part B)를 지금 시작」 | Part B 실행 |
| 「문서정리 - 핸드오프 - Part C(전환·훈련) 다음세션 이관」 | 이 문서 · Part C 는 다음 세션(시각 확인부터) |

## 5. 남은 일

- **Part C**(§1-1) — 시각 확인부터.
- **자동 복구 최종 리뷰의 미룬 Minor**(원장 `final-review.md`): M1 생존 신호의 「아직 아님」 종료 코드 1 이 파이썬 크래시와 같다 · M4 필수 모델 목록과 ollama 매니페스트의 pull 목록을 잇는 테스트 없음 · M5 노드 스크립트의 Python 3.10 문법을 CI 가 안 본다 · M6 런북이 「계획 Task 8」을 번호로만 가리킨다.
- **다음 publisher**: gitops develop 의 #175(리뷰 후속)를 main 으로. 다음 candidate 직전에.
- shared develop 이 main 보다 앞서 있다(#88~#90, 테스트 · 문서) — 다음 마이그레이션 캠페인에 함께.
- 사람 몫: 홈 H-5 영상 재녹화 · Slack 수신처(사용자가 미룸).
- 선택 과제: 운영 메일 발송 인프라(지금은 mock — SES · DKIM · 시크릿 · gitops) · prototype 보관/재작성 · CSP.

## 6. 이번 세션의 함정과 교훈

- ★**서비스 9개 동시 롤링 업데이트가 RDS 커넥션 슬롯을 소진했다** — 옛 · 새 파드가 동시에 커넥션 풀을 잡아 `remaining connection slots are reserved … rds_reserved`, learning-svc 새 파드 1회 재시작 → promote OFF 의 런타임 검증(`restartCount == 0`) 실패. 파드 재생성 → `promote-resume` 로 복구. 09-21 의 CPU herd 와 같은 모양, 다른 자원.
- ★**11개 레포 main 이 전부 `strict`** — 릴리스 PR 전에 main→develop sync 가 필요했다(병합 트리 = develop 트리 확인). 서비스 3곳(`reviews=1`)은 리뷰 필드만 몇 초 완화 → 복원 · 대조.
- ★**서브에이전트 보고서는 쓰기 가능한 경로로** — scratchpad 경로를 받은 리뷰어가 파일을 못 써 약 25만 토큰의 리뷰가 유실됐다. 레포 안 gitignore 작업 공간(`.superpowers/sdd/…`)이나 릴리스 원장 경로를 주고, 최종 메시지에도 전문을 요구한다.
- ★**계획의 문구는 실행 시점의 사실과 다시 맞춘다** — 런북 「2026-10-07 부터 자동 복구가 처리한다」는 리소스가 없을 때 거짓이었다. 노드 ID 도 계획 뒤에 바뀌었다(§1-1).
- k3s `install.sh` 의 `INSTALL_K3S_SKIP_START=true` 는 유닛을 enable 하되 `systemctl restart`(Type=notify · `TimeoutStartSec=0`)만 건너뛴다(원본 확인).
- AWS MCP `run_script` 는 `base64` · `hashlib` · `__name__` 을 막는다 — 큰 문자열의 전사 검증은 순수 파이썬 해시(FNV-1a)를 양쪽에서.
- Bash 도구: 인라인 파이썬의 `\n` 을 먹는다 · `$'\r'` 인용이 파싱을 깬다 · jq 의 `/` 가 MSYS 경로 변환에 깨진다 · `env NAME=VAL cmd` 는 uv shim 에서 무동작(export 를 쓴다) · 10-03 원장 `.py` 는 CRLF.
- 홈 develop push CI 의 `page.goto` 30초 타임아웃은 일시 실패였다(재실행 성공).

## 7. 환경과 자산

- **워크트리**(`D:/workspace/dpa/.worktrees/`): 캠페인용 7개를 남겼다 — `gitops-dispatch-1016` · `gitops-candidate-1016` · `gitops-main-1016` · `fe-dispatch-1016` · `docs-dispatch-1016` · `ai-dispatch-1016` · `shared-dispatch-1016`(롤백 · 재개에 쓴다). 빌드용: `fe-main-1003`(frontend `c6356e60`) · `home-master-1002`(홈 `d46c3f6a`, dist 빌드됨). 자동 복구 작업 워크트리는 지웠다.
- **AWS 운영 접근**: `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`. GPU 노드는 공인 IP 로 직접(지금 `15.165.34.108`, 기동마다 바뀐다). AWS 는 MCP `run_script`.
- **도구**: 고정 kustomize v5.4.3 · 핀 Flutter 3.44.1(`.worktrees/_tools/`) · wrangler 4.146.0(npx).
