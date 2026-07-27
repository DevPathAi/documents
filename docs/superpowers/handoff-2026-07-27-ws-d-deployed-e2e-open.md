# Handoff — WS-D 실배포 (2026-07-27): 인프라 100% 가동, E2E 1건 OPEN

> 다음 세션 착수용. 상세 SSoT: devpath-gitops `docs/runbook-k3s-bootstrap.md`(확정값·트러블슈팅 18건·**🔴 OPEN 섹션**) + documents `docs/superpowers/{specs,plans}/2026-07-27-ws-d-deploy-session*`.

## 완료 (이 세션)

- **선행 정리**: 광고 문서 반영(04 §11·02·17·06, documents #71)·svc-template #4·로컬 위생.
- **릴리스 컷**: 12레포 develop→main, ghcr 이미지 10종+migration. (buildx driver·lcs 플레이크 해소 포함)
- **AWS**: EC2 t3.xlarge `devpath-k3s`(i-09e252854566cc123)·EIP **13.124.153.105**·RDS `devpath-pg`(pg17+pgvector)·SG 2종·키페어(`~/.ssh/devpath-k3s-key.pem`). 비용 ~$140~150/월.
- **클러스터**: k3s+ArgoCD(**12 Application 전부 Synced·Healthy**)·SealedSecrets·Strimzi 1.1.0 KRaft Kafka·Redis·cert-manager·**TLS 3종 Ready**(api/app/admin.leva.ai.kr, 가비아 A레코드→EIP)·마이그레이션 **34개 적용 완료**.
- **시크릿**: platform-db·devpath-jwt·platform-oauth·ai-claude(SealedSecret) + ghcr-pull(수동, read:packages PAT). ai provider 4종=claude.
- **배포 후 발견·수정한 7계 결함**(전부 릴리스 완료): enableServiceLinks(REDIS_PORT 오염)·프로브 401(7 svc `/actuator/health/**`)·ai @Qualifier·flyway runAsUser·Hikari 풀 캡 5(RDS 슬롯)·OAuth redirect_uri 4단(CR 재봉인+forward-headers+PreserveHostHeader+trusted-proxies/절대값)·CORS 운영 origin.
- **E2E 도달점**: https 3종 유효 TLS·gateway health UP·GitHub OAuth authorize 정상(콜백 https://api.leva.ai.kr 일치)·로그인→`/beta-pending` 도달·users 생성(id=1 **deepestdark@outlook.kr** — gmail 아님!)·role=ADMIN 부여·beta_allowlist 승인 완료.

## 🔴 OPEN — 다음 세션 1순위

**증상**: allowlist 승인 후에도 웹 로그인 → **가입 동의 화면에서 진행 불가**, `/dashboard/me`·`/auth/refresh` 401.

**이미 검증(재조사 불필요)**: CORS credentials OK·dio withCredentials=true·RefreshCookies(Domain=.leva.ai.kr, Secure, Lax) env 반영·authorize 요청 정상.

**다음 진단 순서**(runbook OPEN 섹션에 상세): ① 승인 "후" 완전 재로그인 여부(→SuccessHandler 113행 웹 분기 도달해야 refresh 쿠키 발급) ② DevTools에서 `/auth/callback` 302의 `Set-Cookie: refresh_token` 존재 ③ `/auth/refresh` 요청에 Cookie 포함 여부(미포함=쿠키 저장/전송, 특히 `ai.kr` PSL로 인한 Domain 거부 가능성 실측 / 포함+401=platform refreshStore·Redis) ④ platform `LOGGING_LEVEL_AI_DEVPATH=DEBUG`로 분기 확정 ⑤ 동의 제출 API 경로·토큰 요건.

## 접속/조작 요약

- ssh: `ssh -i ~/.ssh/devpath-k3s-key.pem ubuntu@13.124.153.105`, `export KUBECONFIG=/etc/rancher/k3s/k3s.yaml`
- psql: EC2에서 `PGPASSWORD=$(cat ~/.secrets/rds-pw.txt) psql "host=devpath-pg.c7emuq20mhyy.ap-northeast-2.rds.amazonaws.com user=devpath dbname=devpath"`
- gitops 변경 관례: 작업 브랜치→develop PR→(백머지)→develop→main PR. ArgoCD 반영 지연 시 hard refresh annotate.

## 잔여 백로그 (OPEN 뒤)

E2E 완주(동의→진단→로드맵 실AI→광고 슬롯·admin 광고 생성) → WS-A(홈페이지 CF Pages·leva.ai.kr 리브랜드) → WS-E(통합 e2e) → 베타 광고 잔여 2건(admin file-picker·광고 스모크) → 47 P2 이월 → ①결제. 프로브 fix 7건은 인프라 정합 hotfix로 테스트 없이 CI+실검증 게이트로 들어감(원칙 편차 — 후속에서 테스트 이식 여지). 로컬 시크릿 파일(`D:\workspace\devpath-secrets.json`)은 클러스터 봉인 완료 상태이므로 **사용자가 삭제 권장**.
