# 핸드오프 — 2026-11-27 세션 마감 (운영 AWS 전체 일시 정지 · RDS 재정지 장치)

> 앞 문서: `handoff-2026-10-17-session-close.md`(GPU 자동 복구 완료 · 다음 릴리스 캠페인 준비 목록) · `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md`(다음 candidate 입력 §5).
> 이 문서가 다음 세션의 시작점이다. **다음 세션 첫 동작은 §1.**
> 정본(절차 · 리소스 · 검증) = gitops 런북 `docs/runbook-k3s-bootstrap.md` 「일시 정지 — 지우지 않고 세워 둘 때」 · 「데이터베이스를 계속 세워 두기 (keep the database stopped)」(develop `d42912a1` · `db39a0ba`).

## 0. 한 줄 요약

사용자 지시로 **운영 AWS 를 전부 세웠다**(지운 것 없음). GPU 감시를 먼저 끄고 ASG 0 → k3s 서버 정지 → RDS 정지.
RDS 는 7일 뒤 스스로 켜지므로(늘리는 설정 없음) **1시간마다 다시 끄는 장치 `devpath-rds-keep-stopped`** 를 만들고 운영 계정에서 실제로 끄는 것까지 확인했다.
★정지 직전에 `app` · `api` 가 **2026-10-25 03:53Z 부터 만료된 인증서**를 내보내고 있었다(약 33일 접속 불가) — 다시 켤 때 반드시 확인한다(§1-2).★

## 1. 다음 세션 첫 동작

### 1-0. 시작 점검 (읽기 전용) — 2026-11-26 23:24Z(11-27 08:24 KST) 실측

| 항목 | 지금 값 |
|---|---|
| k3s 서버 `i-09e252854566cc123`(t3.xlarge) | `stopped`(2026-11-26 22:26:26Z) · EIP `13.124.153.105` 붙은 채 · EBS `vol-052b2820a85fb7687` 50 GB |
| GPU | ASG `devpath-gpu-node` 최소 0 · 최대 1 · **희망 0** · 인스턴스 0 · `AZRebalance` 중지 · 마지막 인스턴스 `i-088afcdd793dc7101` `terminated`(120 GiB 루트 볼륨도 함께 지워짐) · 스팟 쿼터 `L-3819A6DF` 8 vCPU |
| RDS `devpath-pg` | `stopped`(23:05:14Z — 장치 검증 때 한 번 켰다 끔) · 다음 자동 기동 ≈ 2026-12-03 23:05Z(12-04 08:05 KST) → 장치가 다음 정각에 다시 끈다 |
| 알람 `devpath-gpu-ollama-not-ready` | `ALARM` · **동작 꺼짐**(생존 신호가 없으니 ALARM 이 맞다 — 메일은 안 간다) |
| EventBridge 규칙 | `devpath-rds-keep-stopped` **ENABLED** `rate(1 hour)` · `devpath-gpu-node-absence-watch` **DISABLED** · `devpath-instance-stopped-or-terminated` · `devpath-spot-interruption-warning` · `AutoScalingManagedRule` ENABLED |
| Lambda | `devpath-rds-keep-stopped` CodeSha256 `eLw/bG6dlxQko7nlVIIr3NgkD+AMnbZgOEQPXxHYkDo=` · `devpath-gpu-node-absence-watch` `BNjsV5IRzIofy/iHmZpvgNOAOqf8HHOq3qmkoZ/1w4k=`(그대로) |
| 알림 구독(토픽 `devpath-spot-interruption`) | `mingoo@leva.ai.kr` 1개 |
| 동결 head(롤백 창) | documents main `5d898ad7` · ai-svc main `cd756fbf` · 홈 master `d46c3f6a` · gitops main `ef5ad0bc` — 10-17 과 같다 |
| 웹 | `leva.ai.kr`(Cloudflare Pages) 200 · `app` · `api` 는 서버 정지로 응답 없음 |
| 열린 PR | 0(documents · gitops · frontend · ai-svc · shared · 홈) |

값이 다르면: RDS 가 `available` 인데 서버가 `stopped` 면 장치가 다음 정각에 끈다 — 2시간 넘게 그대로면 `/aws/lambda/devpath-rds-keep-stopped` 로그부터 본다. 서버가 `running` 이면 누군가 다시 켰다(장치는 그때 DB 를 건드리지 않는다).

### 1-1. 사용자에게 물을 것 — 없음

다시 켜는 시점 · 「스냅샷 뒤 RDS 삭제」(7일마다의 짧은 기동까지 없애는 방법, 되돌리기 어려워 하지 않았다)는 사용자가 정한다. 먼저 묻지 않는다.

### 1-2. 다음 작업

1. **다시 켤 때**(사용자 지시가 있을 때) — gitops 런북 「일시 정지」의 「다시 켤 때」 그대로:
   ① `aws events disable-rule --name devpath-rds-keep-stopped` **가장 먼저** → ② RDS start · `available` → ③ k3s 서버 start · 노드 Ready · Argo 16 앱 Synced/Healthy →
   ④ **인증서 확인**(노드에서 `echo | openssl s_client -connect 127.0.0.1:443 -servername app.leva.ai.kr | openssl x509 -noout -enddate`, `api` 도) → ⑤ ASG 희망 1 → 생존 신호 → `enable-rule devpath-gpu-node-absence-watch` → `enable-alarm-actions`.
   켠 뒤 런북 「자동 복구」 위의 일시 정지 표시 줄(#181)을 지운다.
2. **인증서 사고 원인 조사**(다시 켠 뒤 · 요청이 있으면 먼저): 정지 직전 실측 사실만 —
   서버가 내보내던 인증서 `CN=app.leva.ai.kr` · `api.leva.ai.kr`, 발급 Let's Encrypt `YR1`, **만료 2026-10-25 03:53:53Z**. Secret `devpath-web-tls` · `devpath-gateway-tls` · `devpath-admin-tls` 는 만료 **2027-02-22 01:57Z**, Certificate `devpath-web-tls` 상태 「up to date」 · `renewalTime` 2027-01-23. cert-manager 파드 3개는 Running(재시작 2회, 108일 전).
   **모르는 것**: Secret 이 언제 갱신됐는지 · 왜 10-25 전에 갱신되지 않았는지 · Traefik 이 왜 새 Secret 을 안 읽었는지. 서버 재부팅 뒤에도 옛 인증서면 `kubectl -n kube-system rollout restart deploy/traefik`(실측 전 처방).
   **감시 공백**: 33일 동안 아무도 몰랐다 — 외부에서 TLS 만료를 보는 감시가 없다. 감시를 만들지는 사용자와 정한다.
3. **다음 릴리스 캠페인**(시점은 사용자) — 준비 목록은 `handoff-2026-10-17-session-close.md` §1-2 그대로다. 바뀐 것:
   - gitops develop 에 #180(재정지 장치: `docs/runbook-k3s-bootstrap.md` · `infra/aws/rds-keep-stopped/handler.py` · `tests/release/test_rds_keep_stopped.py`) · #181(런북 3줄)이 더 쌓였다. 10-17 에 정한 publisher 범위는 #172~#179 다 — **#180 · #181 을 함께 올릴지는 그 캠페인에서 사용자에게 묻는다.**
   - `handoff-2026-10-16-…-promoted.md` §5 의 「이미지 증거 최단 만료 2026-11-14」가 **이미 지났다** — 캠페인을 정할 때 증거 만료부터 다시 본다.
   - 서버를 세워 둔 상태에서는 운영 반영 단계(승격 · 검증)를 돌릴 수 없다 — 캠페인은 다시 켠 뒤다.
4. 요청이 있으면(10-17 에서 이월): 자동 복구 최종 리뷰의 미룬 Minor M1 · M4 · M5 · AI 멘토 승인 메일(운영 발송기가 mock) · 사람 몫(홈 H-5 영상 재녹화 · Slack 수신처).

### 1-3. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| 메일 「[DevPath/AWS] RDS devpath-pg started by itself and was stopped again」(약 7일마다) | 정상 — 장치가 일했다. 할 일 없음 |
| 12-04 09시 KST 가 지났는데 RDS 가 `available` 이고 위 메일이 없다 | `/aws/lambda/devpath-rds-keep-stopped` 로그 · `AWS/Events` `Invocations` · 규칙 상태를 본다. 손으로 끄려면 `aws rds stop-db-instance --db-instance-identifier devpath-pg` |
| 회수 메일(「AWS Notification Message」 — 규칙 ①②) | 세워 둔 동안 GPU 인스턴스가 없으므로 오지 않아야 한다. k3s 서버가 `stopped`/`terminated` 로 바뀌는 메일이면 누가 서버를 건드렸는지 본다 |

## 2. 이 세션에서 한 것 (2026-11-27 07시경 ~ 08:40경 KST — 첫 정지 명령 07:26)

| 대상 | 작업 | 기록 |
|---|---|---|
| 조사 | 문서(10-17 핸드오프 · 런북) · AWS 17개 리전(과금 리소스는 서울뿐, `synapse-*` 는 다른 프로젝트라 둠) · 클러스터(노드 2 Ready · Argo 16 Synced/Healthy · 파드 Running 47) | 이 문서 §1-0 |
| 발견 | `app` · `api` 인증서 만료(10-25~) — 원인은 §1-2 의 2 | 런북 「일시 정지」 |
| AWS | 정지: 알람 동작 끔 → 규칙 ③ 끔 → ASG 0 → k3s 서버 stop → RDS stop. 회수 메일 3통 전달 · 실패 0 | 런북 「일시 정지」 |
| AWS | 재정지 장치 구축: 역할 `devpath-rds-keep-stopped`(인라인 `keep-stopped` 문장 5개) · 로그 그룹(30일) · Lambda(python3.13 · arm64 · 256 MB · 30초) · 규칙 `rate(1 hour)`. 임시 업로드 버킷은 지웠다 | gitops #180 |
| 검증 | 단위 테스트 8(먼저 실패 확인) · 로컬 전체 442 OK(skipped 4) · CI 2/2 · 운영: 음성(DB 정지 → `stopped: false`) · 배선(규칙 생성 직후 1회 호출) · 양성(DB 를 손으로 켜 `available` → `stopped: true` → 23:05:14Z `stopped`, 메일 1통 전달 · 실패 0) | 런북 「keep the database stopped」 |
| 문서 | 런북 일시 정지 절차 · 장치 · 「자동 복구」 위 정지 표시 · 이 문서 · 10-17 핸드오프에 「대체됨」 | gitops #180 · #181 · documents(이 PR) |
| 저장소 | 이 세션 브랜치 · 워크트리 정리(§5) | — |

모든 변경은 develop 으로만 갔다. main 은 네 저장소 모두 동결 head 그대로다.

## 3. 사용자 결정 (이 세션)

| 원문 | 뜻 |
|---|---|
| 「문서 및 전체 구성 및 aws 현제 구성확인 후 전체 서버 중지 진행하기」 | 조사 뒤 운영 AWS 전체 정지(지우지 않고) |
| 「12-04에 RDS가 다시 켜지면 저절로 다시 정지시키는 작은 자동 장치(EventBridge 규칙과 Lambda)를 만들어줘」 · 「그냥 나중에 다시 킬때까지 계속 정지되어 있도록은 할수 없는가?」 | 다시 켤 때까지 DB 를 세워 둔다 — AWS 설정으로는 불가하므로 장치로(규칙이 켜져 있다 = 계속 세워 둔다) |
| 「참고로 로그인 계정이 deepestdark@gmail.com 에서 mingoo@leva.ai.kr로 바꿨음」 | Claude 로그인 계정 변경. 연결된 Gmail 커넥터는 여전히 deepestdark@gmail.com(실측) — SNS 메일은 계속 지표로 확인한다 |
| 「전체 작업 문서 정리 - 다음 작업 정리 - 핸드오프 - 커밋 - 푸쉬 - 브랜치 정리」 | 이 문서와 §5 |

## 4. 교훈

- **RDS 이벤트는 「Best effort」로 전달된다**(EventBridge 이벤트 참조). 자동 기동 이벤트 `RDS-EVENT-0154` 하나에 기대면 한 번 놓칠 때 DB 가 켜진 채 남는다 — 상태를 일정으로 보는 쪽을 택했다. `DescribeEvents` 에는 `EventID` 가 없고 메시지 문장만 있다(실측).
- **파이프의 종료 코드는 마지막 명령의 것이다.** `unittest … | tail -4` 의 `exit 0` 은 `tail` 의 것이었고 요약 줄도 잘렸다 — 전체 테스트는 파일로 받아 `EXIT=$?` 와 `Ran N tests` · `OK` 줄을 직접 확인했다.
- **AWS MCP `run_script` 는 스크립트 하나에 API 호출 100회까지다.** 17개 리전 × 10 조회가 한도를 넘어 8개 리전이 「Maximum number of tool calls (100) exceeded」로 비었다 — 리전을 나눠 다시 조회했다. 실패한 조회를 「비어 있음」으로 읽지 않는다.
- **인증서는 「Secret 이 갱신됐다」와 「서버가 새 것을 내보낸다」가 다르다.** cert-manager 상태가 정상이어도 실제로 내려오는 인증서를 `openssl s_client` 로 봐야 한다.

## 5. 환경과 자산

- **워크트리**: 10-16 캠페인용 9개는 그대로(롤백 · 재개 · 빌드) — `gitops-dispatch-1016` · `gitops-candidate-1016` · `gitops-main-1016` · `fe-dispatch-1016` · `docs-dispatch-1016` · `ai-dispatch-1016` · `shared-dispatch-1016` · `fe-main-1003` · `home-master-1002`(`D:/workspace/dpa/.worktrees/`).
- **정리**: 이 세션 브랜치 · 워크트리는 모두 머지 뒤 지웠다(gitops `feat/rds-auto-restop` · `docs/runbook-parked-status` — 로컬 · 원격 · 폴더, documents 이 PR 브랜치).
  10-17 과 같은 기준(원격 develop · main · master 에 들어간 커밋 · 변경과 미추적 파일 없음 · 마지막 커밋 48시간 초과 · 체크아웃 안 된 브랜치)으로 워크스페이스 전체를 다시 셌다 — **새 후보 0**(변경 있음 70 · 원격에서 닿지 않음 153 · 제외 목록 11). 10-17 이후 다른 작업이 없었다(10-17 이후 커밋은 gitops develop 의 이 세션 것뿐).
- **AWS 운영 접근**: AWS 는 MCP `run_script`. 서버를 다시 켜면 `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`.
