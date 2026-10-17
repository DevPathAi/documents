# 핸드오프 — 2026-10-17 세션 마감 (GPU 자동 복구 완료 · 다음 작업 정리)

> 앞 문서: `handoff-2026-10-17-gpu-auto-recovery-cutover.md`(Part C 상세 — 전환 · 감시 · 훈련 · 재훈련 · 메일 · 쿼터, 시작 점검의 「다르면」 열) · `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md`(다음 candidate 입력 §5).
> 이 문서가 다음 세션의 시작점이다. **다음 세션 첫 동작은 §1.**
> 원장(git 밖, 지우지 말 것): 자동 복구 = `D:/workspace/dpa/.release-artifacts/gpu-auto-recovery-part-a/progress.md`(Part A~C · 후속 · 사용자 결정 · `Ruling:` 줄) · 캠페인 = `D:/workspace/dpa/.release-artifacts/ms-20261016-leva-inspection-fixes/`.

## 0. 한 줄 요약

GPU 스팟 노드 자동 복구가 **끝났다** — 2026-10-16 23:51 KST 전환, 스팟 쿼터 8 vCPU 뒤 재훈련 **4분 4초**로 목표 10분(G1) 통과, 회수 메일은 「지우지 말고 기다려라」를 안내한다. **사용자에게 물을 것은 없다.**
다음 큰 일은 **다음 릴리스 캠페인**이고(시점은 사용자가 정한다), 그 직전에 gitops publisher 로 #172~#179 를 main 에 올린다(§1-2).

## 1. 다음 세션 첫 동작

### 1-0. 세션 시작 점검 (읽기 전용) — 2026-10-17 09:21 KST 실측

값이 다르면 `handoff-2026-10-17-gpu-auto-recovery-cutover.md` §1-0 의 「다르면」 열을 따른다.

| 항목 | 지금 값 |
|---|---|
| GPU 노드 | `devpath-gpu` Ready · UID `d66f4aae-7d45-4a1d-aa54-d1b37de66d02` · `gpu=1` · `ollama-gpu` 1/1 · 모델 `qwen2.5:7b` `qwen2.5:3b` · 클러스터 노드 2개 |
| ASG `devpath-gpu-node` | 희망 1(최소 0 · 최대 1) · InService 1 — 인스턴스는 ASG 에서 읽는다(지금 `i-0bd740ebcc387f40a`, 2c) · `AZRebalance` 중지 |
| 알람 `devpath-gpu-ollama-not-ready` | `OK`(10-16 15:36:39Z 부터) · 동작 켜짐 |
| 생존 신호 `DevPath/GPU` `OllamaReady` | 최근 12분 12/12 |
| Lambda `devpath-gpu-node-absence-watch` | CodeSha256 `BNjsV5IRzIofy/iHmZpvgNOAOqf8HHOq3qmkoZ/1w4k=` · env `GPU_ROLE_TAG` `HEARTBEAT_NODE` `TOPIC_ARN` |
| EventBridge 규칙 | 4개 ENABLED(`AutoScalingManagedRule` · `devpath-gpu-node-absence-watch` · `devpath-instance-stopped-or-terminated` · `devpath-spot-interruption-warning`) |
| 회수 메일 본문(규칙 ① · ②) | 둘 다 「Auto recovery (since 2026-10-16) … Do NOT delete the node, pods or the PVC」 · 옛 삭제 지시 없음 |
| 회수 알림 구독 | `mingoo@leva.ai.kr` 1개 |
| 스팟 쿼터 `L-3819A6DF` | 8 vCPU |
| 동결 head(롤백 창) | documents main `5d898ad7` · ai-svc main `cd756fbf` · 홈 master `d46c3f6a` · gitops main `ef5ad0bc` |
| 운영 | Argo 16 앱 Synced/Healthy rev `ef5ad0bc` · `leva.ai.kr` · `app` 200 · `api` `/actuator/health` 200 |

### 1-1. 사용자에게 물을 것 — 없음

이 세션에 남았던 질문(G1 · 알람 지연 · 메일 본문 · 메일 형식 · gitops main 범위)은 모두 사용자가 정했다(§3).

### 1-2. 다음 작업

1. **다음 릴리스 캠페인**(시점은 사용자). 입력값 = `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md` §5. candidate 직전에 몰아서 하는 것:
   - **gitops publisher — #172~#179 전부**(2026-10-17 사용자 결정). 17개 파일 목록과 범위 밖 목록 = `handoff-2026-10-17-gpu-auto-recovery-cutover.md` §4.
     PR 로는 못 올린다(main 룰셋 `update` 의 bypass 가 앱 `devpath-gitops-release` 하나 · `scripts/release/` 는 `verify_main_pr_policy.py` 금지). develop 트리를 통째로 올리면 `apps/*` 이미지 선택자 11개가 옛 값으로 되돌아간다.
     범위 밖 중 `scripts/release/provision_mission_staging.sh`(#163 staging 인증서 10년) · `tests/release/test_mission_staging_stack.py` 는 **그 캠페인에서 사용자에게 함께 올릴지 묻는다.**
   - publisher 뒤 회수 메일의 런북 링크를 develop → main 으로(규칙 ① · ② `InputTemplate` 한 줄, 바꾸기 전 렌더 확인 = gitops 런북 「회수 탐지」).
   - shared develop #88~#90(테스트 · 문서) 함께.
   - documents · ai-svc · 홈 main 릴리스도 candidate 생성 전에(동결 규칙 — 운영 반영 뒤엔 롤백 창이 그 head 에 달린다).
   - 서비스를 여러 개 함께 올리면 RDS 커넥션 여유부터 잰다(10-16 9개 동시 롤링이 슬롯을 소진).
   - 이미지 증거 최단 만료 2026-11-14 — 캠페인 일정을 정할 때 함께 본다.
2. 요청이 있으면: 자동 복구 최종 리뷰의 미룬 Minor — M1 「아직 아님」 종료 코드 1 이 크래시와 같다 · M4 필수 모델 목록과 ollama 매니페스트를 잇는 테스트 없음 · M5 노드 스크립트의 Python 3.10 문법을 CI 가 안 본다(원장 `final-review.md`).
3. 요청이 있으면: AI 멘토 승인 메일 — 운영 메일 발송기가 mock 이라(실제 발송 0통) 발송 인프라(SES 등 · SPF/DKIM · 시크릿 · gitops env)부터.
4. 사람 몫: 홈 H-5 영상 재녹화 · Slack 수신처(사용자가 미룸).

### 1-3. 조건이 되면 하는 일

| 조건 | 할 일 |
|---|---|
| GPU 노드가 회수됐다 | **아무것도 지우지 않고 기다린다**(재훈련 실측 4분 4초 · 실제 회수는 미실측). 메일은 「AWS Notification Message」 대화(발신 「DevPath Spot」)에 붙는다. 30분이 지나도 안 돌아오면 gitops 런북 「자동 복구」 증상 표 |
| 알람 메일(`ALARM: "devpath-gpu-ollama-not-ready"`) | 생존 신호가 약 26분 끊겼다 — 노드 · `devpath-gpu-heartbeat` 타이머 · ollama 부터. 지연은 그대로 두기로 했다(§3) |

## 2. 이 세션에서 한 것 (2026-10-16 23:50 ~ 10-17 09:30 KST)

| 대상 | 작업 | 기록 |
|---|---|---|
| AWS · k3s | Part C 전환(GPU 기능 약 12분 중단) · 감시 전환(`ALARM` 은 신호 정지 26분 8초 뒤) · 훈련 19분 41초(G1 실패, 원인 = 쿼터 4 vCPU) | gitops #177 · documents #231 |
| AWS | 회수 메일 본문 교체(렌더를 임시 규칙 + SQS 로 먼저 확인) · 스팟 쿼터 4 → 8 vCPU · 재훈련 **4분 4초(G1 통과)** | gitops #178 · documents #232 |
| 메일 | 사용자가 메일함에서 9통 수신 확인 — 규칙 ① · ② 메일은 제목이 같아 한 대화로 묶인다 | documents #233 |
| 결정 기록 | 알람 지연 · 메일 본문 형식은 그대로 | gitops #179 · documents #234 |
| 결정 기록 | gitops publisher 범위 = #172~#179, 시점 = 다음 캠페인 직전 | documents #235 |
| 문서 정리 | 이 문서 · 계획 끝 「실행 기록」 Part C · 설계 문서 상태 줄 · Part C 핸드오프에 「대체됨」 | documents(세션 마감 PR) |
| 저장소 | 이 세션 워크트리 · 브랜치 정리 + 워크스페이스의 합쳐진 로컬 워크트리 149 · 브랜치 453 정리(§5) | — |

모든 변경은 develop 으로만 갔다. main 은 네 저장소 모두 동결 head 그대로다.

## 3. 사용자 결정 (이 세션)

| 원문 | 뜻 |
|---|---|
| 「오늘 작업 시작 예약 … 질의는 지금, 실제 작업은 23:50부터」 · 「오늘 밤 전부」 · 「자율 진행 · 복구까지」 · 「발송 기록 + 나중에 직접 확인」 | Part C(Task 8~11)를 10-16 23:50 KST 부터 한 번에, 단계마다 묻지 않음 |
| 「회수 메일 본문 수정을 승인, 10분 복구 목표를 위해 스팟 쿼터를 8 vCPU로 올려」 · 「승인 즉시 자율 진행」 | 메일 본문 교체 · 쿼터 요청 · 승인 즉시 재훈련 |
| 「알람 지연 26분과 메일 본문 형식을 그대로 두기」 | 알람 설정 · `InputTemplate` 형식을 바꾸지 않는다 — 다시 묻지 않는다 |
| 「gitops develop에 쌓인 #172~#179 전부 main」 + 「다음 캠페인 직전 (Recommended)」 | 범위 = #172~#179(17개 파일) · 시점 = 다음 candidate 직전 publisher. 지금은 ms-20261016 롤백 레인을 연 채로 둔다 |
| 「전체 작업 문서 정리 - 다음 작업 정리 - 핸드오프 - 커밋 - 푸쉬 - 브랜치 정리 - 다음세션 이관」 | 이 문서와 §5 |

## 4. 이 세션 뒷부분의 교훈 (앞부분은 Part C 핸드오프 §5)

- **메일함은 같은 제목을 한 대화로 묶는다.** 사용자가 본 「7통」은 줄 수였다(지원 케이스 메일 3줄 포함, 규칙 ① · ② 메일 8통이 한 줄). 수는 SNS 분 단위 `NumberOfMessagesPublished` 와 대화 안의 메일 수로 맞춘다.
- **「gitops main 에 올린다」는 곧 publisher 다** — PR 경로가 없고, 운영 릴리스의 자동 롤백 레인을 다음 승격까지 닫는다. 범위는 `git diff origin/main origin/develop` 에서 PR 별 파일을 골라 센다. 이 세션은 처음에 「22개 파일」로 잘못 말했다가 직접 세어 17개로 바로잡았다 — 숫자는 diff 로 센 뒤에 말한다.

## 5. 환경과 자산

- **워크트리**: 10-16 캠페인용 9개는 그대로(롤백 · 재개 · 빌드) — `gitops-dispatch-1016` · `gitops-candidate-1016` · `gitops-main-1016` · `fe-dispatch-1016` · `docs-dispatch-1016` · `ai-dispatch-1016` · `shared-dispatch-1016` · `fe-main-1003` · `home-master-1002`(`D:/workspace/dpa/.worktrees/`). 이 세션의 작업 워크트리는 모두 지웠다.
- **정리 기준(2026-10-17)**: 지운 것은 「원격 develop · main · master 에 이미 들어간 커밋이고, 변경 · 미추적 파일이 없고, 마지막 커밋이 48시간보다 오래된」 워크트리와 「그런 커밋을 가리키고 어느 워크트리에도 체크아웃되지 않은」 로컬 브랜치뿐이다 — 잃는 커밋이 없다. 변경이 있거나 아직 안 합쳐진 것은 남겼다.
- **정리 결과**: 워크트리 **149개**(ai-svc 11 · frontend 40 · gateway 6 · gitops 30 · 홈 35 · lcs 1 · learning 6 · platform 9 + 등록만 남은 것 1 · sandbox 2 · shared 3 · documents 6) · 로컬 브랜치 **453개** 삭제, 실패 0. 실행 때 `git worktree remove`(강제 없음)와 도달성을 다시 확인했다. 플러그인 상태 파일만 남은 빈 폴더 3개도 지웠다.
- **남긴 것**: 워크트리 232개(메인 체크아웃 제외) = 캠페인 9 · 변경 있음 70 · 원격 develop · main · master 에서 닿지 않는 커밋 153(gitops 98 — 스쿼시 머지 · publisher · 증거 커밋일 수 있어 하나씩 판단해야 한다) · 로컬 브랜치 약 335개(통합 · 체크아웃 중 · 닿지 않는 66).
  손대지 않은 것: **원격 브랜치**(증거 · 디스패치 브랜치가 섞여 있다) · 각 저장소의 메인 체크아웃(여러 곳이 옛 작업 브랜치에 변경을 안고 있다) · `.worktrees/visibility-cleanup-state`(공개 범위 정리 증거) · `.worktrees/*-et8-flyway` 5개(2026-08-24 WSL 에서 만든 워크트리, git 등록이 끊겨 변경 여부를 git 으로 볼 수 없다 — 약 540 MB).
- **AWS 운영 접근**: `ssh -i ~/.ssh/devpath-k3s-key-lf.pem ubuntu@13.124.153.105` 후 `sudo kubectl …`. GPU 노드는 ASG 인스턴스의 공인 IP 로 직접. AWS 는 MCP `run_script`.
