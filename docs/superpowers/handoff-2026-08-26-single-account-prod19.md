# 핸드오프 2026-08-26 — 단일계정 prod19 릴리스

> 이 문서는 `handoff-2026-08-25-prod14-staging-port-fixed.md` 이후의 권위 있는
> 재개 문서다. 릴리스 완료 시 최종 SHA·run·artifact·검증 결과를 이 문서에 고정한다.

## 1. 계정·초대 불변조건

- 인간 GitHub 작업 계정은
  `VelkaressiaBlutkrone <77432570+VelkaressiaBlutkrone@users.noreply.github.com>`
  하나뿐이다.
- `qahnaarin` 조직 초대와 저장소 초대는 2026-08-23 취소됐다. 2026-08-26
  재조회에서도 pending 초대·조직 멤버십·PR reviewer 요청이 모두 0건이다.
- `qahnaarin`을 다시 초대하거나 reviewer로 추가하거나 수락을 기다리는 작업은
  금지한다. 2026-08-17~22 문서의 반대 지시는 역사 기록이며 이 문서가 대체한다.
- 수동 커밋, push, PR 생성과 merge는 위 단일 계정으로 수행한다. GitHub Actions가
  sealed manifest를 커밋할 때 사용하는 `devpath-release-bot`은 자동화 신원이며
  별도 인간 계정·초대 대상이 아니다.
- Home·Frontend·Platform·Learning·Documents의 인간 승격 보호 브랜치는 필수 CI,
  conversation resolution, admin enforcement, force-push/delete 금지를 유지한다.
  존재하지 않는 두 번째 사람을 요구하던 `required_approving_review_count=1`과
  `require_last_push_approval=true`만 단일계정 계약에 맞게 제거한다.
- GitOps `main`은 예외적으로 release App만 bypass하는 기존 봉인 정책을 유지한다.
  사람 PR의 승인 1명 설정은 수동 승격 경로가 아니라 App 외 쓰기를 거부하는 방어선이며,
  candidate/seal/promotion은 `devpath-gitops-release` 자동화 신원으로만 진행한다. 이 App은
  인간 계정·조직 초대·reviewer가 아니다.
- 보호 환경은 reviewer를 `VelkaressiaBlutkrone` 하나로 유지한다. 자동 승인 절차는
  `approve_pending_deployment.py`가 `prevent_self_review`를 최소 시간 동안 변경하고
  승인 직후 원래 값으로 복원한 뒤 GET으로 정확히 검증한 경우에만 유효하다.

## 2. 2026-08-26 실측 근거

- Home `master`, Frontend `main`, Platform `main`, Learning `main`, Documents `main`의
  PR 승인 수는 0이고 last-push 별도 승인 요구는 꺼져 있다.
- Home, Frontend, AI, Documents, GitOps의 확인 대상 보호 환경 reviewer는
  `VelkaressiaBlutkrone` 하나이며 `prevent_self_review=true`로 복원돼 있다.
- staging live runtime은 candidate API route port `8080`, CORS origin
  `https://app.leva.ai.kr,https://leva.ai.kr`, gateway
  `DedupeResponseHeader` 설정을 모두 갖고 있다.
- GitOps `main`은 `81c8414d859639d912518bab366ce7e2f23bd4c9`로 유지한다.
  staging manifest 수정은 main 정책이 금지하는 Argo-managed 경로이므로 develop에
  병합하고 live staging에 동일 형상을 적용했다. candidate는 current main의 정확한
  단일 자식으로 만든다.

## 3. 현재 릴리스 상태

- release ID: `ms-20260826-prod19`.
- Home protected source: `ee1f0428f4fb51b82756d20ae8de89f61cb84d24`.
- Home rendered product source:
  `546c62fbf2afbb1c97df3e23041bcd670cb81226`.
- Home canonical dist SHA-256:
  `5c03200958eb634a09e8fd124c2963b0fd7c68c85c2340b2bd34a59ece49706e`.
- Home Pages candidate deployment:
  `a8cd0b9e-2970-4b47-b1ac-05a29adbe210`.
- Platform source: `5f737991a6fd5de4cb2dc98c68f488db747ee32e`.
- Platform image digest:
  `sha256:a03b370bf48a6a25885835962c515e5991f9c18b1a919765b264df5310d7285f`.
- Learning source: `939291f9ec2c4f3de1fa1bafab09dbd517a48682`.
- Learning image digest:
  `sha256:7849563b6c6daf8031369c8eda5bf04505878ca9d50fbadcdce94e869493a553`.
- Frontend protected source·image digests, Android signing artifact, ET13 baseline,
  candidate/seal/promotion run은 진행 중이며 완료 후 아래에 고정한다.

## 4. 남은 순서

1. Frontend release PR CI를 통과시키고 reviewer 없이 단일 계정으로 `main`에 merge한다.
2. exact Frontend `main`에서 admin·mission-off·mission-on 이미지를 발행한다.
3. exact Frontend `main`에서 ET13 raw evidence → baseline approval과 signed Android
   build를 fresh run으로 생성한다.
4. 위 불변 좌표를 넣은 GitOps candidate-only commit을 current main의 단일 자식으로
   push하고 candidate artifact를 발행한다.
5. Home → Privacy → AI → Manual AT → ET13 순서로 fresh evidence producer를
   dispatch하고 필요한 보호 환경을 같은 단일 계정 절차로 승인한다.
6. staging seal → production OFF/ON → 900초 canary → landing-last를 실행한다.
7. release manifest, production identity, Cloudflare landing, 초대 0건, reviewer 요청
   0건을 재검증하고 이 문서의 진행 중 항목을 최종 좌표로 교체한다.

## 5. 실패 시 복구 좌표

- production prior web image:
  `sha256:6484ed322027ae23e0b722705347b52b2e882e8133af7df91c421e246de542c7`.
- prior Home production deployment:
  `f4f82fbc-e6d9-46f3-867f-a227a752c875`.
- prior web identity: `ready=false`, `release_id=unreleased`, candidate hash와 image
  hash는 각각 64자리 0 값이다.
- 실패 시 새 좌표를 추측하지 말고 sealed rollback workflow 또는 위 exact prior
  좌표를 사용하는 검증된 복구 절차로 되돌린다.
