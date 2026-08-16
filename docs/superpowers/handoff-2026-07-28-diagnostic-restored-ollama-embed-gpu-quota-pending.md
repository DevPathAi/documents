# Handoff — 진단 복구 완료·Ollama embed 가동·path-gen은 GPU 대기 (2026-07-28 저녁)

> 이전: [handoff-2026-07-28-ec2-paused-seed-merged-ollama-planned.md](handoff-2026-07-28-ec2-paused-seed-merged-ollama-planned.md). 이 세션은 EC2 재가동→트랙1 릴리스→트랙2 Ollama 배포→E2E 시도까지 실행했고, **로드맵 path 생성이 CPU로 불가**함을 실측 확정해 GPU(Phase B)로 전환(쿼터 대기).

## 완료 (이 세션, 전부 운영 실측)

1. **EC2 재가동 + 클러스터 복구**: `i-09e252854566cc123` start→running(EIP 13.124.153.105). 재가동 직후 **백엔드 7개 CrashLoopBackOff 폭풍** 발견 → 근본원인 **liveness가 콜드스타트에 부족(~50s 예산, startupProbe 부재) × 7 JVM 동시기동 CPU 경합**. **순차 재기동**으로 12/12 Running 복구(learning 단독 부팅 24s 실측).
2. **트랙1 — 진단 시드 릴리스 (완료)**: devpath-shared **PR #51**(develop→main) 머지 → ci.yml image/deploy 잡이 migration 이미지 빌드 + gitops 태그 봇 커밋(`7f7588b`) → **Job immutable이라 `kubectl delete job`→ArgoCD 재생성**(ArgoCD가 새 rev 관측 후 삭제해야 새 이미지 채택 — 경쟁조건 주의) → Flyway "**Successfully applied 2 migrations**". 운영 RDS **question_bank=500(트랙당100)·contents=150(트랙당30)**. **게스트 진단 라이브 실증**(`POST /onboarding/assessments/guest`→`/next` 문항 반환, index 1/15).
3. **트랙2 — Ollama 배포 (embed만 가동)**: gitops **PR #50→#51**(apps/devpath-ollama: Deployment+PVC+Service, `ollama/ollama:0.32.5`, `qwen2.5:3b`·`nomic-embed-text`) + ai-svc `OLLAMA_BASE_URL`. ApplicationSet 컨트롤러 재시작으로 발견 촉진. **파드 Running·모델 2종 pull·노드 RAM 42%(증설 불요)**. **`/ai/embed` 라이브 성공(200, 2.1s)**.
4. **path-gen CPU 불가 확정 (핵심 발견)**: `/ai/path/generate` = **503 at 8.0s**(기본 PT8S). 원인=qwen2.5:3b가 로드맵 JSON을 **~3,000토큰**까지 **~4.9 t/s**로 생성 → **>600s**. **타임아웃 완화 스톱갭**(ai-svc OLLAMA_TIMEOUT·learning AI_SVC_TIMEOUT=PT600S·SSE 630s, gitops **#52→#53**) 배포·실측했으나 **600s ceiling마저 초과**(curl 570s exit28). → 완화로도 불가 확정.
5. **사용자 결정 = GPU(Phase B)** → **세션 내 불가 판명**: ①AWS **G/VT On-Demand vCPU 쿼터 = 0**(계정에 GPU 인스턴스 0대) ②현재 노드 **AZ ap-northeast-2d인데 g4dn은 2a/2b/2c만 제공**(2d 없음). 둘 다 세션 내 해결 불가.
6. **처리(사용자 선택 = 쿼터요청+로드맵보류+무비용E2E)**: **GPU 쿼터 증설요청 제출**(`request-service-quota-increase` L-DB2E81BA, desired=4vCPU, **Id `33d1b4db79d54d0a894150fba2af1f42ofhayrCs` PENDING**). **스톱갭 원복**(gitops **#54→#55**, PT8S fail-fast 복귀·런타임 env 부재 확인). **OLLAMA_BASE_URL은 embed용 유지.**

## 현재 상태

- **EC2 running(비용 발생 중)** — E2E 후 사용자가 정지 권장(`aws ec2 stop-instances --instance-ids i-09e252854566cc123 --region ap-northeast-2`). RDS·EIP 유지.
- **클러스터**: 13파드 전부 Healthy. shared/gitops 모두 develop=main 정합(이 세션 릴리스분 반영). ai-svc/learning은 PT8S 기본으로 복귀.
- **AI provider**: review·mentor·community-seed·retention=claude(유료·작동). embed=ollama(작동). **path 생성=사망(로드맵 E2E 불가, GPU 대기).**
- **SSH**: 키 `~/.ssh/devpath-k3s-key.pem`이 **CRLF라 Git Bash ssh가 거부**(`error in libcrypto`) → LF 사본 만들어 사용(`tr -d '\r'`). 관리IP SG(:22)=112.162.122.24/32.

## ⏭ 다음 세션

1. **E2E 브라우저(사용자)**: `app.leva.ai.kr` → GitHub 로그인(id=1 `deepestdark@outlook.kr`, consent DONE→로그인 후 진단부터) → 진단 완주. **로드맵 단계는 지금 503 fail-fast(GPU 후 복구).** `status=BETA_PENDING`이 `/beta-pending`으로 막는지 관찰(id=1은 ADMIN이라 BetaGate.admit()=true 예상).
2. **GPU Phase B (쿼터 승인 후)**: 쿼터 상태 확인(`aws service-quotas get-requested-service-quota-change --request-id 33d1b4db79d54d0a894150fba2af1f42ofhayrCs`). 승인 시: **AZ 이전 필요**(2d→2a/b/c) — 단일노드 재프로비저닝 or GPU 노드 추가(멀티노드 k3s). NVIDIA 드라이버+nvidia-container-toolkit+k8s device plugin → ollama deployment `nvidia.com/gpu:1` → 로드맵 ~40-60s 검증. **별도 스펙/플랜 권장.**
3. **startupProbe 하드닝(백로그·재발방지)**: 7개 백엔드 deployment에 startupProbe 추가(콜드스타트 유예) — **EC2 재가동마다 CrashLoop 폭풍 재발**하므로 우선순위 있음.
4. **content_embeddings 백필**: embed 가동되니 시드 콘텐츠(150) 임베딩 일괄 생성 배치.

## 교훈

- **CPU LLM path 생성은 타임아웃 완화로도 불가**(실측: 3000토큰·>600s). "느리지만 됨"이 아니라 "완료 안 됨" — 완화 전 실측 필수.
- **GPU는 쿼터(기본0)+AZ 이중 게이트**. 쿼터=0이면 인스턴스 0대(외부 승인 필요), g4dn AZ 편중(2d 제외). 착수 전 `service-quotas`+`describe-instance-type-offerings` 확인.
- **콜드스타트 CrashLoop은 EC2 재가동마다 재발**(liveness×무 startupProbe). 순차 재기동은 밴드에이드, startupProbe가 근본.
- **immutable Job 재적용**: ArgoCD가 새 rev를 desired로 관측한 뒤 `delete job`해야 새 이미지로 재생성(관측 전 삭제 시 옛 이미지 재생성 — 경쟁조건).
- SSH 키 CRLF → libcrypto 에러, LF 사본으로 우회.
