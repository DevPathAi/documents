# GPU 스팟 노드 자동 복구 — 같은 이름으로 돌아오는 노드 설계 (2026-10-07)

> 대상: 운영 k3s 의 GPU 스팟 노드(`ollama-gpu`) · AWS 계정 `963773969059` `ap-northeast-2` · gitops `infra/aws/`.
> 계기: 2026-10-06 17:22Z 두 번째 스팟 회수 — 통지 메일 3통은 왔지만 새벽이라 94분 뒤에야 복구했다(`handoff-2026-10-06-session-close.md` §8-2).
> 사용자 결정(2026-10-07): 다음 작업 = 「GPU 노드 복구 자동화」 · 접근 = A(같은 노드 이름으로 복귀), 전제 실측 먼저 · 설계 요약 승인(「이대로 스펙 작성」).

## 1. 문제

GPU 노드는 스팟이고 회수된다. 2026-09-08 회수는 23일 동안 아무도 몰랐고, 2026-10-01 에 다시 띄운 노드는 **5일 만인** 2026-10-06 에 회수됐다.
회수 동안 학습경로 생성이 멈추고 세 기능(review · community-seed · retention)의 Claude 폴백이 사라진다. Claude 1차 경로와 재시도는 유지된다(ai-svc M1 수정).

복구 자체는 짧다 — 2026-10-06 실측으로 기동부터 `ollama-gpu` Ready 까지 6분. 그런데 사람이 봐야 시작된다.
통지는 세 층이 있다(경고 · 종료 · 6시간 반복). 그래도 새벽의 회수는 사람이 볼 때까지 방치된다.

수동 복구가 「인스턴스만 띄우면 끝」이 아닌 이유는 하나다. **새 노드가 새 이름으로 들어온다.**
`ollama-gpu-models` 의 PV 는 local-path 가 만든 `local` 볼륨이고 `kubernetes.io/hostname In [<옛 노드 이름>]` 으로 고정돼 있다.
그래서 죽은 노드 오브젝트 · 멈춘 파드 · PVC 를 차례로 지워야 한다(런북 「스팟 회수 후 복구」 3~5).

자동 재기동을 붙이면 감시에 구멍이 생긴다. 지금의 반복 통지(Lambda `devpath-gpu-node-absence-watch`)는 EC2 인스턴스 유무만 본다.
인스턴스는 떴는데 조인이나 모델 내려받기가 실패한 상태를 알리지 못한다.

## 2. 목표 · 성공 기준

| | 기준 |
|---|---|
| G1 | 회수 뒤 스팟 용량이 있으면 **사람 없이** `ollama-gpu` 1/1 과 모델 2종이 돌아온다. 종료로부터 10분 안 |
| G2 | 생존 신호(3.2)가 15분 넘게 끊기면 메일이 오고, 미복구 동안 6시간마다 다시 오고, 돌아오면 복구 메일이 온다 |
| G3 | 조인 토큰과 노드 비밀번호가 user-data · git · 로그 · 세션 기록에 나타나지 않는다 |
| G4 | gitops `apps/` 를 바꾸지 않는다. 클러스터에 삭제 권한을 가진 자동화를 넣지 않는다 |
| G5 | 한 동작으로 끌 수 있다(ASG 희망 대수 0) |

비목표: 온디맨드 폴백 · 회수 전 선제 교체(Capacity Rebalancing) · 모델 저장소의 노드 디스크 전환 · Slack 수신처 · 조인 토큰 자동 회전 · control-plane 이중화.

모델 저장소를 노드 디스크로 바꾸는 변경은 처음 범위에 있었으나 뺐다. 3.1 의 실측으로 복구에 필요하지 않게 됐고, `apps/` 변경이라 publisher 를 기다려야 한다.
얻는 것은 SSM 의 경로 값 하나(3.2 `model-dir`)를 없애는 것뿐이다.

## 3. 설계

### 3.1 전제 — 실측으로 확인했다

2026-10-06 21:25~21:36Z, 운영 클러스터에 임시 CPU 노드(`t3.small`, 이름 `spike-node`, 테인트로 격리)와 `ollama-gpu` 와 같은 모양의 테스트 워크로드
(Recreate · nodeSelector · 톨러레이션 · local-path PVC)를 올려 인스턴스 3대로 확인했다. 끝난 뒤 전부 지웠다.

| 확인한 것 | 결과 |
|---|---|
| 종료 뒤 상태 | 실제 회수와 같다 — 50초 뒤 NotReady, 5분 뒤 옛 파드 Terminating · 새 파드 Pending |
| 같은 이름, 비밀번호 없이 조인(대조군) | 거부 — `Node password rejected, duplicate hostname or contents of '/etc/rancher/node/password' may not match server node-passwd entry` |
| 같은 이름, 저장해 둔 비밀번호로 조인 | **같은 Node 오브젝트로 복귀**(UID · 생성 시각 · podCIDR 그대로, InternalIP 는 새 값으로 갱신). 멈춘 옛 파드는 스스로 사라지고 Pending 파드가 그 노드에 배치됐다 |
| PV 디렉터리가 없는 새 디스크(대조군) | `FailedMount … MountVolume.NewMounter initialization failed … path … does not exist`. 디렉터리를 만들자 40초 안에 Running |
| 축출(5분) 전에 교체 | 같은 파드가 제자리에서 재시작(`Pod sandbox changed`, restarts=1). 종료부터 파드 Running 까지 88초 |

함께 드러난 것:

- Node 오브젝트를 지우면 `<노드 이름>.node-password.k3s` 시크릿도 사라진다. 그 뒤 같은 이름으로 들어오는 노드는 새로 등록된다.
- `/etc/rancher/node/password` 는 33바이트(16바이트 hex + 개행), 권한 600.
- `get.k3s.io` 설치 스크립트는 `K3S_TOKEN_FILE` 을 받는다. 그러면 `k3s-agent.service.env` 에는 토큰이 아니라 **경로**가 들어간다.

실측하지 않은 것(전환과 훈련에서 확인한다, 6절): 부트스트랩 토큰으로의 조인(실측은 서버의 node-token 으로 했다), 비밀번호 파일을 미리 둔 첫 등록,
GPU 노드에서 device plugin 이 다시 등록되는 순서, IP 가 바뀐 노드로의 노드 간 파드 통신, ASG 와 기동 스크립트 자체.

### 3.2 구성 요소

| 요소 | 이름 | 역할 |
|---|---|---|
| SSM 파라미터 | `/devpath/gpu-node/agent-token` (SecureString) | GPU 노드 전용 k3s 부트스트랩 토큰. `k3s token create --ttl 0` 으로 만든다 — 클러스터 토큰과 따로 폐기할 수 있다 |
| | `/devpath/gpu-node/node-password` (SecureString) | 노드 비밀번호. 새로 생성한 32자 hex |
| | `/devpath/gpu-node/model-dir` (String) | `ollama-gpu-models` PV 의 디렉터리 경로. 파라미터가 없으면 건너뛴다(SSM 은 빈 값을 받지 않는다) |
| | `/devpath/gpu-node/k3s-version` (String) | agent 버전. 서버와 같아야 한다(현재 `v1.36.2+k3s1`) |
| IAM 역할 · 프로파일 | `devpath-gpu-node` | 위 파라미터 읽기 · `DevPath/GPU` 네임스페이스에 지표 쓰기뿐 |
| 기동 템플릿 | `devpath-gpu-node` | 지금 수동 기동과 같은 AMI · 타입 · 120 GiB gp3 · SG · 키 · 태그 + 프로파일 + IMDSv2 필수 + user-data |
| ASG | `devpath-gpu-node` | 최소 0 · 최대 1 · 희망 1. 스팟만. 서브넷 2a · 2c · 2d |
| 기동 스크립트 | `infra/aws/gpu-node/bootstrap.py` | 파라미터를 읽어 비밀번호 파일과 PV 디렉터리를 만들고 같은 이름으로 agent 를 설치한다 |
| 생존 신호 | `infra/aws/gpu-node/heartbeat.py` | 1분마다 ollama 와 모델 2종을 확인하고 지표를 쓴다 |
| 알람 | `devpath-gpu-ollama-not-ready` | 15분 신호 없음 → 메일, 복귀 → 메일 |
| 반복 통지 | Lambda `devpath-gpu-node-absence-watch` (기준 변경, 이름은 그대로) | 6시간마다, 신호가 15분 넘게 없으면 알린다 |

**노드 이름**은 `devpath-gpu` 로 고정한다. 라벨 `devpath.ai/gpu=true` 와 테인트 `devpath.ai/gpu=true:NoSchedule` 은 지금과 같다.

**기동 템플릿**: AMI `ami-09d3bdf0648512f52` · `g6.xlarge` · `/dev/sda1` 120 GiB gp3 · SG `sg-0ad7dfa8afe5d1eea` · 키 `devpath-k3s-key` ·
태그 `role=k3s-agent-gpu` `Name=devpath-k3s-gpu` · 메타데이터 `HttpTokens=required` `HttpPutResponseHopLimit=1`.
지금 노드는 IMDSv1 이 열려 있고 프로파일이 없다. 프로파일을 붙이면서 IMDSv2 를 필수로 바꿔, 오버레이 네트워크의 파드가 인스턴스 자격 증명을 얻지 못하게 한다.

**ASG**: 혼합 인스턴스 정책으로 온디맨드 0% · 스팟 할당 전략 `price-capacity-optimized` · 타입 `g6.xlarge` 하나.
서브넷은 `g6.xlarge` 가 제공되는 세 AZ(2a `subnet-08f3b5aa5e95e53b0` · 2c `subnet-053662e249d717940` · 2d `subnet-00bb150fb3e236ecb`).
`AZRebalance` 프로세스는 중지한다 — 재균형은 새 인스턴스를 먼저 띄우고 옛것을 내리는데, 같은 이름의 노드가 둘이 되면 안 된다.
Capacity Rebalancing 은 켜지 않는다. 스팟 쿼터(`L-3819A6DF`)가 4 vCPU 라 두 번째 `g6.xlarge` 는 어차피 뜨지 못한다.

**user-data** 는 `#cloud-config` 한 장이다. `write_files` 로 `bootstrap.py` · `heartbeat.py` · systemd 유닛 2개를 쓰고 `runcmd` 로 기동 스크립트를 한 번 돌린다.
`infra/aws/gpu-node/render_user_data.py` 가 소스 파일에서 결정적으로 만든다. 비밀은 들어가지 않는다.

**기동 스크립트**의 순서(각 단계는 다시 돌려도 같은 결과다):

1. SSM 에서 값을 읽는다(`model-dir` 는 없을 수 있다). 값은 출력하지 않는다.
2. `/etc/rancher/node/password` 와 `/etc/rancher/k3s/agent-token` 을 600 으로 쓴다.
3. `model-dir` 가 있으면 그 디렉터리를 만든다(0777 — local-path 가 만드는 것과 같다).
4. `get.k3s.io` 로 agent 를 설치한다 — `INSTALL_K3S_VERSION` · `K3S_URL=https://172.31.48.82:6443` · `K3S_TOKEN_FILE` ·
   `--node-name devpath-gpu` · 라벨 · 테인트. 내려받기가 실패하면 간격을 두고 30분까지 다시 시도한다.
5. 생존 신호 타이머를 켠다.

**생존 신호**: 노드에서 root 로 1분마다 돈다. `k3s crictl` 로 `devpath` 네임스페이스의 Ready 인 `app=ollama-gpu` 파드를 찾아 그 IP 의
`/api/tags` 를 읽고, `qwen2.5:3b` 와 `qwen2.5:7b` 가 둘 다 있으면 `DevPath/GPU` · `OllamaReady` = 1(차원 `Node=devpath-gpu`)을 쓴다.
하나라도 어긋나면 아무것도 쓰지 않는다. 2026-10-06 에 지금 노드에서 이 조회 경로가 동작하는 것을 확인했다(파드 IP `10.42.7.4`, 모델 2종).
모델 목록은 `apps/devpath-ollama-gpu` 의 postStart 와 같은 값을 스크립트에 둔다 — 모델을 바꾸면 여기도 바꾼다(런북에 적는다).

### 3.3 회수에서 복구까지

```
스팟 회수 ──▶ ASG 가 대체 인스턴스 기동(세 AZ 중 용량이 있는 곳)
          ──▶ cloud-init: 기동 스크립트 → 같은 이름 · 같은 비밀번호로 조인
          ──▶ 같은 Node 오브젝트가 Ready
               · 5분 안: 같은 파드가 제자리에서 재시작
               · 5분 뒤: 멈춘 옛 파드가 사라지고 Pending 파드가 배치
          ──▶ PV 디렉터리가 이미 있으므로 마운트 → postStart 가 모델 2종 pull
          ──▶ 생존 신호 재개
```

ai-svc 의 폴백은 그보다 늦게 돌아온다. `ProviderLatch` 가 실패가 이어지는 동안 재탐색 간격을 1분에서 30분까지 늘리기 때문이다
(2026-10-06: 파드 Ready 18:56, 래치 닫힘 19:26). 중단이 짧을수록 이 간격도 짧다. 이 설계의 범위 밖이다.

### 3.4 감시

| 층 | 언제 | 무엇을 |
|---|---|---|
| EventBridge ① · ② (그대로) | 회수 경고 · 종료 | 「회수됐다」 — 즉시, 1회 |
| 알람 `devpath-gpu-ollama-not-ready` (신규) | 신호가 15분 없음 / 복귀 | 「자동 복구가 15분 안에 끝나지 않았다」 / 「돌아왔다」 |
| Lambda 반복 통지 (기준 변경) | 6시간마다, 신호가 15분 넘게 없을 때 | 「아직 복구되지 않았다」 + 인스턴스가 있는지 없는지 |

알람: `Sum` · 주기 300초 · 평가 3 · 임계 `< 1` · 누락 데이터는 위반으로 본다. 알람과 OK 양쪽 동작을 기존 토픽 `devpath-spot-interruption` 으로 보낸다. 메일 본문은 CloudWatch 기본 형식이고, 할 일은 알람 설명에 적는다.
토픽 정책에 CloudWatch 의 게시를 허용하는 문장을 더한다(알람 ARN 조건).

Lambda 는 인스턴스 유무 대신 지난 15분의 `OllamaReady` 합을 본다. 본문에 「인스턴스 없음(용량 부족일 수 있다)」과 「인스턴스는 있는데 서비스가 안 떴다」를 구분해 적는다.
실행 역할에 `cloudwatch:GetMetricStatistics` 를 더한다.

자동 복구가 15분 안에 끝나면 알람은 울리지 않는다. 그때 오는 메일은 ① · ② 뿐이다.

### 3.5 보안

- user-data 에는 비밀이 없다. 토큰과 비밀번호는 SSM SecureString 에만 있고, 노드에서는 root 600 파일이다(지금도 토큰은 `k3s-agent.service.env` 에 600 으로 있다).
- 인스턴스 역할이 할 수 있는 일은 그 네 파라미터 읽기와 지표 한 종류 쓰기다. IMDSv2 필수 · 홉 1 로 파드에서는 그 자격 증명에 닿지 못한다.
- 토큰은 GPU 노드 전용 부트스트랩 토큰이다. 새면 `k3s token delete` 로 그것만 폐기한다.
- 전환 때 토큰을 control-plane 에서 SSM 으로 옮기는 경로: control-plane 이 임시 비공개 S3 객체에 presigned URL 로 직접 올리고, AWS 쪽에서 읽어 파라미터에 넣은 뒤 객체와 버킷을 지운다.
  값이 세션 기록을 지나가지 않는다. 노드 비밀번호는 AWS 쪽에서 생성해 바로 파라미터에 넣는다.
- SG 는 바꾸지 않는다.

### 3.6 잔여 위험 (수용)

| 위험 | 일어나는 일 | 대응 |
|---|---|---|
| 세 AZ 모두 스팟 용량 없음 | ASG 가 계속 시도, 서비스는 멈춘 채 | 알람(15분) + 6시간 반복 통지. 온디맨드 전환은 사람이 정한다 |
| 부팅 때 `get.k3s.io` · Docker Hub · ollama 저장소 장애 | 조인 또는 모델 pull 지연 | 기동 스크립트가 30분까지 재시도. 그래도 안 되면 알람. 지금 수동 절차도 같은 의존이 있다 |
| `model-dir` 가 실제 PV 와 어긋남(PVC 를 다시 만든 경우) | `FailedMount` 로 파드 정지 | 알람 → 런북: 파라미터 갱신 뒤 노드에서 디렉터리 생성 |
| GPU 파드가 device plugin 등록보다 먼저 재시작 | 파드가 한 번 실패한 뒤 다시 만들어질 수 있다 | 훈련에서 관찰하고 결과를 런북에 적는다 |
| 서버 k3s 를 올렸는데 `k3s-version` 을 안 바꿈 | 버전이 다른 agent 가 조인 | 런북의 업그레이드 절차에 한 줄 추가 |
| 누가 Node 오브젝트를 지움 | 비밀번호 시크릿도 사라져 다음 조인이 새 등록이 된다 | 전환의 첫 조인이 바로 이 경우라 거기서 확인한다. PV 고정은 이름이 같아 그대로 맞는다 |
| 조인 토큰이 만료 없이 남는다 | 새면 임의 노드가 agent 로 조인 가능 | 전용 토큰이라 따로 폐기. 자동 회전은 비목표 |
| 자동 재기동이 확인 없이 요금을 쓴다 | 스팟 1대 상한 | 사용자 수용(2026-10-07). 끄려면 희망 대수 0 |

## 4. 설정

| 항목 | 값 |
|---|---|
| 노드 이름 | `devpath-gpu` |
| 파라미터 접두 | `/devpath/gpu-node/` |
| 지표 | 네임스페이스 `DevPath/GPU` · 이름 `OllamaReady` · 차원 `Node=devpath-gpu` · 1분마다 |
| 알람 | 300초 × 3 · `Sum < 1` · 누락 = 위반 |
| 반복 통지 | `rate(6 hours)`(그대로) · 15분 창 |
| 기동 스크립트 재시도 | 30분 |
| 추가 비용 | 지표 1 · 알람 1 · PutMetricData 월 약 4.4만 건 — 공개 요금으로 월 $1 미만(전환 뒤 청구서로 확인) |

## 5. 테스트 (TDD — 실패 테스트 먼저)

단위 테스트는 gitops `tests/release/` 에 둔다(CI 가 그 폴더만 훑는다). 외부 명령은 주입한 실행기로 대신한다.

- `bootstrap.py`: 비밀번호 파일과 토큰 파일이 agent 설치 **전에** 600 으로 쓰인다 · `model-dir` 파라미터가 없으면 디렉터리를 만들지 않고 계속한다 ·
  설치 명령에 노드 이름 · 라벨 · 테인트 · 버전 · `K3S_TOKEN_FILE` 이 들어가고 토큰 값은 들어가지 않는다 · 어떤 출력에도 비밀 값이 없다 ·
  설치 실패는 재시도하고 한도를 넘으면 실패로 끝난다 · 두 번 돌려도 결과가 같다.
- `heartbeat.py`: 모델 2종이 있으면 지표를 쓴다 · Ready 파드 없음 / HTTP 실패 / 모델 하나 없음이면 쓰지 않는다 · 지표 쓰기 실패가 조용히 삼켜지지 않는다.
- `render_user_data.py`: 같은 입력이면 같은 바이트 · 소스 파일 내용이 그대로 들어간다 · 16KB 한도 안 · 비밀처럼 보이는 문자열이 없다.
- Lambda: 지난 15분 합이 0 이거나 데이터가 없으면 알린다 · 신호가 있으면 조용하다 · 본문이 인스턴스 유무를 구분한다.

운영 실측은 6절의 전환과 훈련이다.

## 6. 전환과 배포

gitops 는 develop 까지만 간다(`infra/aws/` · `tests/release/` · 런북). `apps/` 와 `scripts/release/` 를 건드리지 않으므로 publisher 와 무관하다.

**준비(서비스 영향 없음)** — 파라미터 4개 · 역할과 프로파일 · 기동 템플릿 · ASG(희망 0) · 알람(동작 꺼 둠).
임시 소형 인스턴스에 프로파일을 붙여 SecureString 이 실제로 읽히는지 먼저 확인한다.

**전환(GPU 기능 약 10분 중단, 시각은 사용자 확인)** — 스팟 쿼터 때문에 옛 노드를 먼저 내린다.

1. 지금 인스턴스 종료 → 옛 Node 삭제 → 옛 파드 강제 삭제 → PVC 삭제(이 절차를 쓰는 마지막이다).
2. ASG 희망 1 → 노드가 `devpath-gpu` 로 조인 → 파드 배치 → local-path 가 새 PV 를 `devpath-gpu` 에 만든다.
3. 새 PV 의 경로를 `model-dir` 에 적는다.
4. 생존 신호가 들어오는 것을 확인한 뒤 Lambda 를 새 기준으로 바꾸고 알람 동작을 켠다. 순서가 바뀌면 거짓 알람이 난다.

**훈련(GPU 기능 약 10분 중단, 전환과 같은 시간대)** — ASG 인스턴스를 일부러 종료하고 다음을 잰다.

- 종료 → 대체 기동 → Node Ready(UID 가 같은가) → 파드 Running → 모델 2종 → 생존 신호 재개까지의 시각. G1 의 10분과 비교한다.
- `ollama-gpu` 접근 로그에 ai-svc 파드의 `GET /api/tags` 200 이 다시 찍히는가(IP 가 바뀐 노드로의 노드 간 통신).
- GPU 파드가 실패 없이 뜨는가, 실패한 파드가 남는가.

**알람 확인(서비스 영향 없음)** — 노드에서 생존 신호 타이머만 20분 멈춘다. 알람 메일과 Lambda 수동 호출의 통지를 확인하고, 타이머를 켜서 복구 메일을 확인한다.

**되돌리기** — ASG 희망 0 으로 자동화를 끈다. 수동으로 띄울 때는 런북의 절차에 「같은 이름 · 비밀번호 파일」 두 줄을 더한 것을 쓴다.

## 7. 문서

- gitops 런북: 「자동 복구」 절 신설(구성 · 끄는 법 · 훈련 · 파라미터 갱신 · 증상별 대응) · 「스팟 회수 후 복구」는 자동화가 꺼졌거나 실패했을 때의 절차로 고친다 · 전환과 훈련의 실측 기록.
- documents 핸드오프와 메모리: 점검 대상(노드 이름 · 인스턴스 식별 방법)과 감시 층의 변화.
