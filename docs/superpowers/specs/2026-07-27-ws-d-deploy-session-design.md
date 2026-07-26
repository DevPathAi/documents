# WS-D 실배포 세션 설계 — 선행 정리 + 릴리스 컷 + AWS k3s 플랜 실행

- 날짜: 2026-07-27
- 상태: 브레인스토밍 승인됨
- 레포: 크로스레포 오케스트레이션 (documents·devpath-shared·백엔드 svc 8·devpath-frontend·devpath-gitops·devpath-svc-template)
- 관련: [44_MVP_잔여_로드맵](../../../44_MVP_잔여_로드맵.md) · [46_전체_정합성_점검_3차](../../../46_전체_정합성_점검_3차.md) · [47_품질_리팩토링_실행계획서](../../../47_품질_리팩토링_실행계획서.md) · devpath-gitops `docs/superpowers/specs/2026-07-05-aws-k3s-deployment-design.md`(인프라 SSoT) · 동 `plans/2026-07-05-aws-k3s-deployment.md`(실행 플랜 SSoT)

## 배경 / 목표

WS-B(데모 웹 이미지)·WS-C(베타 게이팅)가 완결되어 다음 착수 지점은 **WS-D 인프라 브링업**(2026-07-18 사용자 확정)이다. 이번 세션은 (1) 짧은 선행 정리, (2) develop→main 릴리스 컷, (3) 기존 AWS k3s 플랜(Task 1~9) 실행을 직렬로 수행한다.

**WS-D 인프라 설계 자체는 이 문서가 재정의하지 않는다** — gitops의 2026-07-05 spec/plan이 SSoT이고, 이 문서는 그 위의 세션 오케스트레이션 계층(실측 반영·확정값 주입·실행 어댑테이션)만 다룬다.

## 실측 요약 (2026-07-27, 전 레포 fetch 후)

- 마지막 작업일 7/22: 정합성 3차 11 PR → 로컬 QA 3버그 픽스 → 베타 광고 전체(shared #47·platform #35/#36·gateway #25·frontend #76/#77) 전부 develop 머지. org 열린 PR = svc-template #4 단 1건(build SUCCESS·MERGEABLE).
- **베타 광고가 문서 미반영**: 04_API·02_ERD에 `/ads`·광고·`ad_` 0건 — 정합성 3차 문서 수정(7/22 01시 머지) 직후 광고 코드(09~13시)가 머지되어 baseline이 다시 어긋남.
- **배포는 main 기준**: 전 svc·frontend CI 이미지 빌드가 `if: main` 한정, ArgoCD ApplicationSet revision=main. 현재 develop→main 갭: frontend 103·platform 89·notification 36·learning 30·shared 22·gitops 9 커밋 등 → **릴리스 컷 필수**.
- **admin 이미지 공백**: gitops `apps/devpath-admin`은 `ghcr.io/devpathai/devpath-admin:main` 참조하나 frontend에 `apps/admin/Dockerfile`·CI 잡이 없어 이미지 발행 경로 부재(방치 시 ImagePullBackOff).
- **shared publish 잔여는 해소됨**: 7/22 publish.yml 3회 success(svc는 `0.0.1-SNAPSHOT` 참조라 재빌드 시 수신).
- **마이그레이션 자산 실체**: shared CI가 `Dockerfile.migration`(flyway 11-alpine + `db/migration` SQL 내장)으로 `ghcr.io/devpathai/devpath-migration:{sha,main}` 발행 + gitops `_migration` kustomize 태그 봇 커밋. 단 `_migration/base/job.yaml`의 URL이 클러스터 내 `postgres:5432` 하드코딩(RDS 미대응), 자격 주입 미구현.
- Flyway 마이그레이션 34파일(V202607221001~1003 광고 3테이블이 마지막). platform ads API 11 엔드포인트, gateway `/ads/**` 라우트 반영 확인.
- svc CI deploy 잡은 main push 시 GitHub App 토큰으로 gitops 기본 브랜치에 kustomize SHA 태그를 **봇 커밋** — 릴리스 컷만 하면 이미지→gitops 반영 자동.
- 로컬 위생: shared·gateway·lcs·learning·notification HEAD가 머지 완료된 피처 브랜치에 방치(전부 ahead=0, 미푸시 커밋 없음). documents 미커밋 3건(`.tier1-baseline.md`, 6/24 office-hours 랜딩 검증 spec/plan). `.github` CLAUDE.md 미커밋 수정(6/25 antml 버그 대응 "도구 호출 전면 금지" 초안) 존재.

## 결정 사항 (사용자 확정, 2026-07-27)

1. 범위 = **선행 정리 → WS-D 착수** (직렬 풀패스).
2. AWS 사전조건 **전부 준비됨**: 자격증명 사용 가능 · 비용 승인(~$130~180/월) · leva.ai.kr DNS 제어 · OAuth 콘솔 접근.
3. AWS 실행 주체 = **Claude가 aws CLI로 직접 실행하되, 비용 발생·비가역 명령은 실행 직전 건별 확인**.
4. `.github` CLAUDE.md 미커밋 수정 = **폐기**(checkout 원복).
5. admin 이미지 공백 = **이번에 추가**(web 패턴 미러링) 후 릴리스 컷에 포함.

## 섹션 1 — 선행 정리

- **1a. 베타 광고 문서 반영** (documents `docs/beta-ads-docs` 브랜치 → develop PR):
  - 04_API: 공개 `GET /ads`(슬롯 서빙·204) · `POST /ads/{id}/events`(IMPRESSION/CLICK·202·404), admin `GET|POST /admin/ads` · `PUT|DELETE /admin/ads/{id}` · `POST /admin/ads/{id}/image` · `GET|PUT /admin/ads/settings` · `GET /admin/ads/{id}/stats` — 구현됨 상태로 기재, gateway 라우팅 표에 `/ads/**` 추가, 총계 재실측 갱신.
  - 02_ERD: advertisement·ad_settings·ad_daily_stats 3테이블 + 마이그레이션 수 31→34.
  - 17_스케줄: 엔드포인트 총계·platform 수치 재실측 갱신.
  - 06_화면: admin 광고 관리 화면·web 광고 슬롯 위젯 반영(47 P2의 "06 화면 신규 반영"과 병합 처리).
  - 수치·경로는 작성 시점에 코드 재실측(추측 금지).
- **1b. documents 미커밋 3건 보존**: `.tier1-baseline.md` + 6/24 office-hours 랜딩 검증 spec/plan 2건을 `docs:` 커밋으로 보존(WS-A 자산).
- **1c. svc-template PR #4 머지** (build SUCCESS 확인됨).
- **1d. 로컬 위생**: 5개 레포 develop 체크아웃+pull, learning `.jqwik-database` 삭제. `.omc/` untracked·home-page `.gitignore` 수정은 범위 외(보류).
- **1f. `.github` CLAUDE.md 수정 폐기**: `git checkout -- CLAUDE.md` + develop pull(behind 4 해소).

## 섹션 2 — 릴리스 컷 (develop→main)

순서(충돌·의존 최소화):

1. **shared** — main push로 라이브러리 publish 자동 발행 + devpath-migration 이미지 발행·`_migration` 태그 봇 커밋.
2. **gitops** — develop분(notification 매니페스트 등 9커밋)을 svc 봇 커밋이 쌓이기 전에 main 반영.
3. **admin 이미지 경로 추가** (frontend develop PR): web 패턴 미러링 `apps/admin/Dockerfile`(+nginx.conf·.dockerignore 필요분) + ci.yml `admin-image`/`admin-deploy` 잡(`ghcr.io/devpathai/devpath-admin`, gitops `apps/devpath-admin` 태그 커밋). API URL 각인은 web과 동일 variable 사용.
4. **frontend 릴리스 전 선행**: repo variable `WEB_API_BASE_URL=https://api.leva.ai.kr` 설정(이미지 각인 값).
5. **백엔드 svc 8**(platform·ai·community·gateway·learning·sandbox·notification·lcs) + **frontend** — 병렬 develop→main PR, CI 녹색 확인 후 merge commit 머지.
6. **documents** — 1a 광고 문서 PR 머지 후 develop→main.

검증: PR별 CI 녹색 → ghcr `:sha`/`:main` 태그 존재 → gitops main 봇 커밋 확인. main·develop 직접 push 금지(전부 PR 경유), 머지는 merge commit.

## 섹션 3 — WS-D 실행 어댑테이션 (gitops 플랜 Task 1~9 = SSoT)

**확정값**: 리전 ap-northeast-2 · EC2 t3.xlarge(Ubuntu 22.04, EBS 50GB) · RDS PostgreSQL 17 db.t4g.micro(pgvector) · Elastic IP · 도메인 `api/app/admin.leva.ai.kr` → EIP · ClusterIssuer email = deepestdark@gmail.com.

**조정 1 — DB 마이그레이션 경로**: `_migration` Job을 정식 경로로 사용. gitops 변경으로 job.yaml URL을 RDS 엔드포인트로, 자격을 SealedSecret(`platform-db` 계열) 참조로 수정. K8s Job immutable → 태그 교체 시 ArgoCD sync 실패 가능 → `Replace=true` sync 옵션(또는 Job 삭제 후 재sync) 절차를 runbook에 명시. 백업 경로 = EC2에서 flyway 컨테이너 1회 실행.

**조정 2 — Strimzi 버전 리스크**: 플랜의 Kafka CR은 ZooKeeper 기반. 최신 Strimzi는 KRaft 전용화 추세라 거부될 수 있음 → 설치 시점 버전 실측 후 필요 시 KRaft(KafkaNodePool)로 전환(사전 확정하지 않음).

**조정 3 — WS-D 중 gitops 변경 흐름**: Task 4(시크릿)·6(redis)·7(env)·8(ingress) 변경을 **묶음 단위로 "작업 브랜치→develop PR→develop→main 릴리스 PR" 반복**(3~4회, main 직접 push 금지 준수). 봇 커밋(이미지 태그)은 main 직행이므로 gitops 릴리스 PR에서 kustomization 태그 충돌 시 main 쪽(최신 SHA) 우선 해소.

**부수**: OAuth 콜백 `https://api.leva.ai.kr/login/oauth2/code/{github|google}` — 정확한 값을 준비해 사용자가 GitHub·Google 콘솔에 등록. 스모크용 사용자 이메일을 admin 베타 허용리스트에 등록 후 로그인 게이트 통과 검증.

## 섹션 4 — 검증 · 에러 대응 · 산출물

- **검증**: 기존 플랜 Task별 게이트(kubectl/argocd/aws) + 릴리스 컷 검증 + 최종 E2E(https 유효 TLS → OAuth 로그인 → 베타 게이트 → 진단→로드맵 생성 핵심 플로우).
- **에러 대응**: CI red → 해당 레포만 수정 후 재시도(녹색 전 머지 금지). AWS 단계 실패 → `Name=devpath-*` 태그 기준 정리 명령을 runbook에 준비(비용 누수 방지), 중단 시 생성 리소스 목록·비용 즉시 보고.
- **산출물**: ① 이 설계 문서 ② 실행 플랜(`docs/superpowers/plans/2026-07-27-ws-d-deploy-session.md`, 인프라 단계는 gitops 플랜 참조 실행) ③ gitops `docs/runbook-k3s-bootstrap.md`(기존 플랜 Task 9 산출물) ④ 세션 종료 보고(생성 AWS 리소스·월 비용·접속 URL·잔여 작업) + 메모리 갱신.

## 범위 밖

- WS-A(홈페이지 CF Pages 연결·leva.ai.kr 리브랜드)·WS-E(통합 e2e) — WS-D 완료 후.
- ① 결제 구현(P1~P3, PortOne) — 외부 게이팅 별도.
- 베타 광고 잔여 2건(admin 웹 이미지 file-picker·광고 로컬 실API 스모크).
- 47 P2 이월(M-4·10·13·14·17·21·22·28·29·30·S-3·S-4) 중 06 화면 반영 외 항목.
- `.omc/` gitignore 위생·home-page `.gitignore` 수정·frontend `origin/feat/p7-landing-jaspr` 원격 브랜치 정리.
- 관측성 스택(Prometheus/Grafana)·실운영 HA — gitops spec 범위 밖 유지.

## 리스크

- **R1 Strimzi ZooKeeper 비호환**(조정 2) — 실측 후 KRaft 전환으로 흡수.
- **R2 Job immutable sync 실패**(조정 1) — Replace 절차로 흡수.
- **R3 대량 릴리스 컷의 CI 동시 실행** — GitHub Actions 동시성 한도로 대기 발생 가능(기능 리스크 아님, 시간 리스크).
- **R4 실 비용 발생** — 건별 확인 게이트 + 중단 시 정리 runbook으로 통제.
- **R5 admin 이미지 신규 경로 초회 검증** — web과 달리 로컬 docker build 검증을 develop PR 단계에서 수행해 흡수.
