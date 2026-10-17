# 핸드오프 — 2026-10-17 GPU 자동 복구 Part C(전환 · 감시 · 훈련 · 기록)

> 앞 문서: `handoff-2026-10-16-session-close.md`(Part A · B 까지, 캠페인 `ms-20261016` 이관).
> 이 문서가 다음 세션의 시작점이다. **다음 세션 첫 동작은 §1.**
> 원장(git 밖, 지우지 말 것): `D:/workspace/dpa/.release-artifacts/gpu-auto-recovery-part-a/progress.md` — Part A · B · C 전부, 판단(`Ruling:`) 줄 포함.
> 실측의 정본은 위 원장이고, 정리된 타임라인은 gitops 런북 `docs/runbook-k3s-bootstrap.md` 「자동 복구」 → 「전환과 훈련(실측)」(PR #177).

## 0. 한 줄 요약

GPU 스팟 노드가 **자동 복구로 넘어갔다** — 노드 이름은 이제 `devpath-gpu` 로 고정이고, ASG(희망 1)가 띄우며, 생존 신호 · 알람 · 반복 통지가 켜져 있다.
훈련에서 사람 손 없이 같은 Node(같은 UID)로 돌아왔지만 **19분 41초**가 걸려 목표 10분(G1)을 넘겼다. 원인은 용량(스팟 쿼터 4 vCPU + ASG 재시도 간격)이었다.
**갱신(2026-10-17 05:45 KST)**: 사용자 승인으로 회수 메일 본문을 바꾸고 스팟 쿼터를 8 vCPU 로 올렸다. 재훈련은 **4분 4초 — G1 통과**(§2). 남은 질문이던 알람 지연(§1-1 의 2)과 메일 본문 형식은 10-17 사용자가 **그대로 두기로** 했다 — §1-1 은 모두 끝났다.

## 1. 다음 세션 첫 동작

### 1-0. 세션 시작 점검 (읽기 전용) — 값이 바뀌었다

| 항목 | 지금 값(2026-10-17 01:11 KST 실측, 인스턴스 · 쿼터 · 메일 본문은 05:45 KST 갱신) | 다르면 |
|---|---|---|
| GPU 노드 | 노드 `devpath-gpu` Ready(UID `d66f4aae-7d45-4a1d-aa54-d1b37de66d02`) · `ollama-gpu` 1/1 · 모델 `qwen2.5:7b` `qwen2.5:3b`. 인스턴스는 **ASG 에서 읽는다**(지금 `i-0bd740ebcc387f40a`, 2c — 재훈련 뒤) | UID 가 바뀌었으면 누가 Node 를 지웠다 — 런북 「자동 복구」 증상 표 |
| ASG `devpath-gpu-node` | 희망 1 · InService 1 | 희망 0 이면 누가 껐다(「끄는 법」). 인스턴스 0 이 오래가면 활동 기록의 `StatusMessage` |
| 알람 `devpath-gpu-ollama-not-ready` | `OK` · **동작 켜짐** | `ALARM` 이면 생존 신호가 약 25분 넘게 없다(실측 26분 8초) — 노드 · 타이머부터 |
| 생존 신호 | `DevPath/GPU` · `OllamaReady` · `Node=devpath-gpu` 가 1분마다 1 | |
| Lambda `devpath-gpu-node-absence-watch` | 새 판 · CodeSha256 `BNjsV5IRzIofy/iHmZpvgNOAOqf8HHOq3qmkoZ/1w4k=` · env 3개(`TOPIC_ARN` `GPU_ROLE_TAG` `HEARTBEAT_NODE`) · 역할 정책 문장 4개 | 옛 판(`pkHhRBf8…`)이면 누가 되돌렸다 |
| 회수 알림 구독 | `mingoo@leva.ai.kr` 1개 | 0개면 재구독 |
| 스팟 쿼터 `L-3819A6DF` | 8 vCPU(2026-10-16 20:01Z 승인) | 4 이하면 대체가 옛 인스턴스 종료를 기다린다(G1 실패 원인) |
| 회수 메일 본문(규칙 ① · ② `InputTemplate` 끝) | 「Auto recovery (since 2026-10-16) … Do NOT delete the node, pods or the PVC …」 | 「delete node -> force-delete old pod -> delete PVC」면 누가 되돌렸다 — gitops 런북 「회수 탐지」 의 새 문구로 다시 |
| 동결 head(롤백 창) | documents main `5d898ad7` · ai-svc main `cd756fbf` · 홈 master `d46c3f6a` · gitops main `ef5ad0bc` | 움직였으면 사용자에게 알린다 |
| 운영 | Argo 16 앱 Synced/Healthy rev `ef5ad0bc` · `leva.ai.kr` · `app` 200 · `api` `/actuator/health` 200 | |

### 1-1. 사용자에게 물을 것 — 모두 끝(1 · 3 은 2026-10-17 새벽 사용자 승인으로 실행, 2 는 그대로 두기로 결정)

1. **G1(10분 안 복귀)을 맞출지.** 훈련의 19분 41초는 기동 → 모델 4분 33초 + **대체 인스턴스가 못 뜬 15분**이다. 스팟 쿼터 `L-3819A6DF` 가 4 vCPU 라 g6.xlarge 가 한 대만 들어가고, 옛 인스턴스가 끝나는 데 6분 43초, 그 뒤 ASG 의 재시도 간격(1 · 2 · 4 · 8분)이 8분을 더했다.
   길: 쿼터를 8 vCPU 로 올려 달라고 AWS 에 요청(요청 자체는 비용이 없다. ASG 최대가 1 이라 평소에는 한 대이고, 옛 인스턴스가 끝나는 몇 분 동안만 두 대가 겹칠 수 있다) → 승인되면 **다시 훈련**
   (기동 → 모델 4분 33초 실측에 비추어 GPU 기능 약 5분 중단을 예상하지만 미실측, 시각 확인 뒤). 이 요청은 계정 바깥으로 나가는 일이라 사용자가 정한다.
   → **끝**: 03:05 KST 요청 → 05:01 KST 승인 → 05:29:59 KST 재훈련 t0 → 모델 t0 + 4분 4초(**G1 통과**, §2). GPU 기능 중단 약 4분 · 폴백 7분 40초.
2. **알람이 끊긴 뒤 약 26분에 울리는 것을 둘지.** 계획은 15~20분을 기대했지만 CloudWatch 기본 평가(슬라이딩 창)가 3/3 알람에 데이터 포인트 5개(25분)를 읽고 그 안의 실제 값을 먼저 쓴다(AWS 문서로 확인).
   반복 통지 Lambda 는 자기 15분 창으로 보므로 영향이 없다. 바꾸려면 주기를 줄이고 평가 기간 수를 늘린다(평가 범위가 줄어든다 — AWS re:Post 「cloudwatch-alarm-invoke-issues」).
   「wall clock」 평가 창(`EvaluationWindow`)도 있지만 이 지연에 대한 효과는 확인하지 않았다. 알람 설정 변경이라 계획 밖이다.
   → **끝(그대로 둔다)**: 2026-10-17 사용자 결정. 실제 회수는 규칙 ② 메일이 바로 오고 복구는 4분 4초(재훈련)라, 알람은 「인스턴스는 있는데 모델이 안 뜬」 경우의 뒷받침이다 — 계획보다 6~11분 늦어도 영향이 작다.
3. **회수 메일 본문이 옛 수동 절차를 지시한다**(2026-10-17 `ListTargetsByRule` 확인). 규칙 ① 메일 끝이 「delete node -> force-delete old pod -> delete PVC」이고, 규칙 ② 는 'spot reclaim recovery' 절을 가리킨다.
   전환 뒤로 이것을 따르면 PVC 가 새로 만들어져 `model-dir` 와 어긋나고, 다음 회수에서 `FailedMount` 로 자동 복구가 깨진다. 런북에는 「메일을 받아도 지우지 않는다」를 적었다.
   제안: 두 규칙 타깃의 `InputTransformer.InputTemplate` 에서 그 문장을 「Auto recovery (since 2026-10-16): the Auto Scaling group devpath-gpu-node launches a replacement that rejoins as node devpath-gpu. Do NOT delete the node, pods or the PVC. If it is not back in about 30 minutes: runbook 'auto recovery'.」로 바꾼다(`events:PutTargets`, `InputPathsMap` 그대로).
   이 세션은 바꾸지 않았다 — 7.5일 방치 때 끊겼던 바로 그 알림 경로이고, 렌더링은 실제 이벤트가 와야 확인된다. 사용자 확인 뒤 바꾸고, 바꾼 직후 `TestEventPattern` 이 아닌 실제 이벤트(다음 훈련의 종료 통지)로 본문을 확인한다.
   → **끝**: 03:07 KST 교체(링크는 develop 런북 — main 런북에는 「자동 복구」 절이 없다). 바꾸기 전에 임시 규칙 + 임시 SQS 로 렌더 확인(메일 없이), 재훈련의 실제 규칙 ② 통지를 임시 SQS 구독으로 받아 새 문구를 확인했다.

### 1-2. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| GPU 노드가 회수됐다 | **아무것도 지우지 않는다**(2026-10-17 03:07 KST 전에 받은 회수 메일의 삭제 지시도 따르지 않는다). ASG 가 대체를 띄우고 같은 이름으로 돌아온다(재훈련 실측 4분 4초 — 쿼터 8 vCPU. 실제 회수는 미실측이고, 세 AZ 모두 스팟 용량이 없으면 더 걸린다). 30분이 지나도 안 돌아오면 런북 「자동 복구」 증상 표 → 그래도 안 되면 「끄는 법」 뒤 「스팟 회수 후 복구」 |
| 다음 릴리스 캠페인 | 입력값 = `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md` §5. **candidate 직전 gitops publisher 로 #172~#179 전부를 main 에 올린다**(2026-10-17 사용자 결정, 범위 · 제외 목록은 §4) — 올린 뒤 회수 메일의 런북 링크를 main 으로. 서비스를 여러 개 함께 올리면 RDS 커넥션 여유부터 잰다 |
| 이미지 증거 만료 | 최단 2026-11-14 |

## 2. 이 세션에서 한 것

| 대상 | 작업 | 결과 |
|---|---|---|
| AWS · k3s | Task 8 전환 — 옛 수동 노드 `i-08bf0d3ef0f3471df` 종료 · 옛 Node · 파드 · PVC 삭제(마지막) · ASG 희망 1 · `model-dir` 파라미터 | 14:51 → 15:03 UTC, **GPU 기능 약 12분 중단**. 새 노드 `devpath-gpu` 기동 91초 뒤 조인, ai-svc 폴백 15:06 복귀 |
| AWS | Task 9 감시 — Lambda 새 판 · 역할 정책 `ReadHeartbeat` · env 3개 → 알람 `OK` 확인 뒤 동작 켬 → 생존 신호를 일부러 끊어 `ALARM` · 반복 통지 · `OK` 확인 | 신호가 들어온 **뒤에** 바꿨다. `ALARM` 은 정지 26분 8초 뒤, `OK` 는 재개 64초 뒤 |
| AWS · k3s | Task 10 훈련 — ASG 인스턴스를 일부러 종료, 사람 손 없음 | 같은 UID · 새 IP · 지운 것 없음 · 실패 파드 없음. **t0 + 19분 41초 → G1 실패**(§1-1). ai-svc 폴백은 16:08:39 UTC 복귀(모델 11분 25초 뒤, 래치 열림 기간) |
| gitops | 런북 기록 PR #177(`docs/gpu-auto-recovery-record` → develop) | 상태 줄 · 확정값 노드 이름 · 실측 표 · 증상 2줄 · 반복 통지 절을 새 판으로 · 구독 줄 · 「스팟 회수 후 복구」 3~5 생략 조건 |
| 메일 | 밤새 토픽 메일 7통(규칙 ② 4 · `ALARM` · 반복 통지 · `OK`) | SNS 지표로 전부 전달 · 실패 0. 사용자가 `mingoo@leva.ai.kr` 메일함에서 받은 것을 확인했다(10-17, 재훈련 2통까지 9통 — §5) |
| AWS | 회수 메일 본문 교체(규칙 ① · ② `InputTemplate` 끝, 03:07 KST) | 임시 규칙 + 임시 SQS 로 옛 · 새 본문 렌더를 먼저 확인 → `PutTargets` → `ListTargetsByRule` 로 같음 확인 → 임시 리소스 삭제 |
| AWS | 스팟 쿼터 `L-3819A6DF` 4 → 8 vCPU 요청(03:05 KST) | 케이스 `179217392700521` 05:01 KST 닫힘, 값 8 반영은 05:29 조회에서 확인 |
| AWS · k3s | 재훈련 — ASG 인스턴스 종료(t0 20:29:59Z = 05:29:59 KST, 사람 손 없음) | 대체 t0 + 7초(거절 0회) · Ready t0 + 1분 57초 · **모델 t0 + 4분 4초 → G1 통과** · 같은 UID · 테인트 축출 취소, 옛 파드 제자리 재시작 · agent 3회 재시작 · 알람 없음 · 폴백 t0 + 7분 40초 · 메일 규칙 ② 2통(새 본문, SNS 실패 0) |
| gitops | 런북 PR #178(`docs/gpu-reclaim-mail-quota` → develop) | 「회수 탐지」 새 본문 · 렌더 확인 방법 · 쿼터 줄 · 증상 · 함정 · 실측 표에 재훈련 |

## 3. 사용자 결정 (이 세션)

| 원문(선택지 라벨 포함) | 뜻 |
|---|---|
| 「오늘 작업 시작 예약 … 질의는 지금, 실제 작업은 23:50부터」 | Part C 를 2026-10-16 23:50 KST 에 시작 |
| 「오늘 밤 전부」 | Task 8~11 을 한 번에(훈련도 이어서) |
| 「자율 진행 · 복구까지」 | 단계마다 묻지 않음. 실패하면 되돌리고 수동 기동까지 미리 승인(쓸 일은 없었다) |
| 「발송 기록 + 나중에 직접 확인」 | 메일은 알람 이력 · SNS 지표로 확인, 실제 수신은 사용자 |
| 「회수 메일 본문 수정을 승인, 10분 복구 목표를 위해 스팟 쿼터를 8 vCPU로 올려」(10-17 03시) | §1-1 의 3 · 1 실행 |
| 「승인 즉시 자율 진행」 | 쿼터 승인을 확인하는 대로 재훈련, 단계마다 묻지 않음 · 실패하면 되돌림 · 수동 기동까지 미리 승인(쓸 일은 없었다) |
| 「알람 지연 26분과 메일 본문 형식을 그대로 두기」(10-17) | §1-1 의 2 와 §4 의 본문 형식 — 알람 설정 · `InputTemplate` 형식을 바꾸지 않는다 |
| 「gitops develop에 쌓인 #172~#179 전부 main」 + 「다음 캠페인 직전」(10-17) | 범위 = #172~#179(17개 파일, §4) · 시점 = 다음 candidate 직전 publisher — 지금은 롤백 레인을 연 채로 둔다 |

## 4. 남은 일

- §1-1 은 모두 끝났다(2 알람 지연은 그대로 두기로 결정, 10-17).
- 회수 메일 본문 형식: 큰따옴표로 감싸이고 줄바꿈이 `\n` 두 글자로 들어간다(템플릿이 JSON 문자열 — 옛 본문도 같다). 읽을 수는 있다. **그대로 둔다**(10-17 사용자 결정).
- publisher 로 런북이 main 에 올라가면 메일의 develop 링크를 main 으로 바꿔도 된다.
- 자동 복구 최종 리뷰의 미룬 Minor(원장 `final-review.md`): M1 「아직 아님」 종료 코드 1 이 크래시와 같다 · M4 필수 모델 목록과 ollama 매니페스트를 잇는 테스트 없음 · M5 노드 스크립트의 Python 3.10 문법을 CI 가 안 본다. (M6 「계획 Task 8」 번호 참조는 이번 런북 수정으로 없어졌다.)
- **다음 publisher — 범위 확정**(2026-10-17 사용자 결정 「#172~#179 전부 main」, 시점 「다음 캠페인 직전」): 17개 파일 — `docs/runbook-k3s-bootstrap.md`(#170 「루트 볼륨」 절도 같은 파일이라 함께 올라간다) · `README.md` · `.gitattributes` · `infra/aws/gpu-node-absence-watch/handler.py` · `infra/aws/gpu-node/` 5개 · `scripts/release/cloudflare_pages.py` · `scripts/release/seal_release_manifest.py` · `tests/release/` 6개(`test_gpu_node_*` 4 · `test_cloudflare_api.py` · `test_et13_atomic_evidence.py`).
  PR 이 아니라 publisher 다 — main 은 룰셋 `update` 로 앱 봇(`devpath-gitops-release`)만 갱신하고, #175 의 `scripts/release/` 는 `verify_main_pr_policy.py` 금지 경로다. 지금 올리면 ms-20261016 자동 롤백 레인이 다음 승격까지 닫혀서 미뤘다.
  **범위 밖**(develop 트리에만 있다 — 통째로 올리면 안 된다): `apps/*/base/kustomization.yaml` 11개(옛 이미지 선택자 — 올리면 운영이 되돌아간다) · `staging/mission-spine/` 4개 · `scripts/release/provision_mission_staging.sh`(#163 staging 인증서 10년) · `tests/release/test_mission_staging_stack.py` — 뒤의 둘은 그 캠페인에서 따로 판단.
- shared develop 이 main 보다 앞서 있다(#88~#90) — 다음 마이그레이션 캠페인에 함께.
- 사람 몫: 홈 H-5 영상 재녹화 · Slack 수신처(사용자가 미룸). 메일 9통 수신은 10-17 사용자가 확인했다(§5).

## 5. 이번 세션의 함정과 교훈

- ★**알람의 「15분」은 설정값이지 실제 지연이 아니다** — 슬라이딩 창은 평가 범위 안의 실제 값을 먼저 쓴다. 3/3 · 5분 알람은 신호가 끊긴 뒤 약 26분에 울렸다. 계획의 기대값을 실측으로 바꿨다.
- ★**용량 쿼터가 복구 시간을 정한다** — 노드 스크립트는 기동 → 모델 4분 33초로 빨랐지만, 쿼터 4 vCPU 에서는 옛 인스턴스가 끝나야 새 것이 뜨고 ASG 재시도 간격이 그 위에 쌓인다. 전환(Task 8)에서도 같은 일이 있었다(t0 → 대체 기동 7분 51초, 재시도 3회 거절).
- **IP 가 바뀐 같은 이름의 노드**는 첫 기동에 k3s-agent 가 몇 번 재시작한다(Node 의 옛 IP → network policy controller 실패). 저절로 약 65초에 안정된다 — 스펙의 「실측하지 않은 것」에 없던 새 발견이다(목록의 「IP 가 바뀐 노드로의 노드 간 통신」은 정상 — 16:08:39 `GET /api/tags` 200).
- 스펙의 「실측하지 않은 것」 중 이번에 본 것: 부트스트랩 토큰 조인 · 비밀번호 파일을 미리 둔 첫 등록 · device plugin 등록(Task 8: Ready 뒤 약 30초에 gpu=1) · 같은 Node 재등록 뒤 `UnexpectedAdmissionError` 없음(훈련) · 노드 간 통신 · ASG 와 기동 스크립트 · 같은 Node 로의 복귀 — 전부 동작했다.
- AWS MCP `run_script` 의 장기 작업은 5분 뒤 만료된다 — 긴 대기는 로컬 백그라운드 `sleep` 뒤 짧은 조회로 나눴다. `urllib.parse` 도 막힌다(정책 문서는 이미 dict 로 온다).
- 예약 실행(CronCreate)은 세션 안에서만 산다 — 세션을 켜 둔 채로 23:50 에 정확히 시작됐다.
- ★**메일 본문은 메일함 없이 확인할 수 있다**: 바꾸기 전에는 임시 규칙 + 임시 SQS 로 렌더를 보고, 실제 이벤트는 토픽에 임시 SQS 를 구독(raw)해 SNS 원문을 받는다. 같은 계정 SQS 구독은 확인 절차 없이 바로 켜진다. 끝나면 구독 해제 · 큐 삭제, 구독 수 1 로 원상.
- 쿼터 요청은 `CASE_OPENED` → `CASE_CLOSED`(약 2시간) 뒤 **값 반영까지 최대 28분**이 더 걸렸다 — 상태가 닫힌 것만 보고 승인으로 읽지 않는다. 케이스 내용은 기본 지원 플랜이라 Support API 로 못 본다.
- 쿼터 8 에서는 노드가 5분 안에 돌아와 테인트 축출이 취소되고 옛 파드가 제자리에서 다시 뜬다(1차 훈련은 새 파드가 Pending 으로 기다렸다).
- **메일함은 제목이 같은 메일을 한 대화로 묶는다** — 규칙 ① · ② 메일은 제목이 모두 「AWS Notification Message」라 한 줄(「DevPath Spot 8」)로 보였다: 10-16 14:02 · 14:03 KST(Part B 임시 인스턴스 종료) 2통 + 밤사이 6통(23:51 · 23:57 전환 · 00:37 · 00:44 훈련 · 05:30 · 05:36 재훈련). `ALARM` · 반복 통지 · `OK` 는 제목이 달라 각각 한 줄. 수는 줄이 아니라 대화 안의 메일로 센다 — 새 회수 메일도 이 대화 맨 위로 붙을 뿐이라 눈에 덜 띈다.

## 6. 환경과 자산

- **워크트리**: 캠페인용 7개(`gitops-dispatch-1016` 등, 10-16 핸드오프 §7)와 빌드용 2개는 그대로. 이번 세션의 `gitops-gpu-record` · `docs-handoff-1017` 은 머지 뒤 지운다.
- **AWS 운영 접근**: `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`. GPU 노드는 공인 IP 로 직접(기동마다 바뀐다 — ASG 인스턴스의 `PublicIpAddress`). AWS 는 MCP `run_script`.
