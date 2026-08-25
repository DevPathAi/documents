# 핸드오프 2026-08-25 — prod14 재개점 + staging release-host 포트 교정

> 선행 문서: `handoff-2026-08-23-et11-governance-and-shared-publish.md`.
> 이 문서는 Mission Spine release `prod10`~`prod13` 실패 원인 교정과
> `prod14` 준비 상태를 다음 세션으로 넘긴다.

## 1. 다음 세션의 정확한 착수 순서

1. **진행 중인 Android 서명 빌드 상태를 새로 조회한다.**
   - 저장소: `DevPathAi/devpath-frontend`
   - run: `32847249140`
   - 2026-08-25 21:23 KST 스냅샷에서 job `97799718249`의
     `Build production Android release without mock transport` 단계가 진행 중이었다.
   - 승인 환경 `mission-spine-mobile-signing-android`는 승인 직후 원래의
     `prevent_self_review=true` 상태로 복원되었다. 실행을 취소하거나 재실행하지 말고,
     먼저 현재 결론과 아티팩트를 조회한다.

   ```powershell
   gh run view 32847249140 --repo DevPathAi/devpath-frontend `
     --json status,conclusion,headSha,jobs,url
   gh api repos/DevPathAi/devpath-frontend/actions/runs/32847249140/artifacts
   ```

2. **라이브 staging release-host Ingress를 GitOps main과 일치시킨다.**
   - 실패 원인은 이미 코드와 테스트로 확정했다. 라이브
     `mission-spine-release-hosts` Ingress의 세 backend가 Service port `80`을
     가리켰지만 `devpath-platform-svc`가 선언한 port는 `8080`이다.
   - GitOps `main` `81c8414d859639d912518bab366ce7e2f23bd4c9`에는 세 backend를
     모두 `8080`으로 고친 manifest와 회귀 계약 테스트가 병합돼 있다.
   - `mission-spine-validate.yml`의 첫 candidate journey는 새 manifest를 적용하기 전에
     현재 라이브 staging을 호출한다. 따라서 새 candidate를 검증하기 전에 라이브
     Ingress를 현재 main 형상으로 정합화해야 한다.
   - 적용 전 `uid`, `resourceVersion`, 세 host, service name, port를 읽고 모두 예상값인지
     확인한다. 예상과 다르면 임의 패치하지 말고 원인을 다시 조사한다. 적용 후 세 backend
     port가 전부 `8080`인지 재조회하고, 클러스터 Secret 값은 출력하지 않은 채 두 release
     prerequisite 경로가 더 이상 `404`가 아닌지 확인한다.
   - 접속 정보: `ubuntu@13.124.153.105`, 키
     `$env:USERPROFILE\.ssh\devpath-k3s-key.pem`, namespace `devpath-staging`.

3. **`prod14` ET13 승인 자료와 Android 산출물을 고정한다.**
   - ET13 baseline approval run `32847246637`: `success`.
   - source SHA: `5a7d58530f7c50db56a3d8d97dcd51b74cb12713`.
   - artifact ID: `9562822009`.
   - artifact name:
     `ms-20260825-prod14-frontend-visual-approved-baseline-run-32847246637-attempt-1`.
   - artifact digest:
     `sha256:c9bd7b2a6d89b611f9dad92b295abe56309b5cb340ddc78f298853bb87c573ac`.
   - `baseline-approval.v1.json` raw SHA-256:
     `6347849cf1a24c4105a5bdc2438e88a5b7f464fb29a6d4029e6e817f4b6147cd`.
   - `review-candidate.v1.json` raw SHA-256:
     `258877ee5d93b2e71ae4d32c7649f2b00fc6189171406a3c732c94ccac217a49`.
   - 로컬 다운로드 사본:
     `D:\workspace\dpa\.tmp\prod14-baseline-handoff`.

4. **현재 GitOps main의 직접 자식으로 `ms-20260825-prod14` candidate를 만든다.**
   - 기준 GitOps main:
     `81c8414d859639d912518bab366ce7e2f23bd4c9`.
   - 이 핸드오프 문서가 `documents/main`에 병합된 뒤 main SHA가 바뀐다.
     candidate의 `analytics_privacy.approval_source_sha`와 privacy producer 입력에는
     아래 명령으로 재조회한 **새 documents main SHA**를 사용한다.

   ```powershell
   git -C D:\workspace\dpa\documents fetch origin main
   git -C D:\workspace\dpa\documents rev-parse origin/main
   ```

5. **다섯 evidence producer를 fresh run으로 완주한다.**
   - Home archive
   - analytics privacy approval
   - AI prompt/model evidence
   - ET13 visual + accessibility provenance
   - manual NVDA + TalkBack evidence
   - 이전 release의 artifact를 재사용하지 않는다. 같은 release 안에서도 실패한 producer를
     재실행했다면 final candidate에는 성공한 fresh run과 artifact만 넣는다.

6. **staging seal → production OFF/ON → landing 순서로 승격한다.**
   - `mission-spine-validate.yml`을 GitOps main에서 `prod14`로 dispatch한다.
   - `mission-spine-staging`을 candidate journey 전에 한 번, seal 대기 시 한 번 승인한다.
   - staging 성공 뒤 transient CoreDNS 우회를 live identity까지 재검증하고 제거한다.
   - `mission-spine-promote.yml` production OFF 성공 후 새 main에서 production ON을 실행하고,
     다시 staging을 승인한다.
   - 900초 canary 후 `mission-spine-landing-last.yml`과
     `mission-spine-production-landing` 승인을 끝낸다.

7. **release가 끝난 뒤 디자인 재구성 계획으로 이동한다.**
   - 대상: `app.leva.ai.kr`, `leva.ai.kr`.
   - 요구사항: 기존 디자인을 완전히 뒤집고, 관리자/실무 도구처럼 보이는 화면이 아닌
     순수 제품 디자인 언어로 새 구조와 시각 체계를 설계한다.
   - 실제 라이브와 소스 구조를 먼저 확인한 뒤 `design-consultation` 절차로 정보 구조,
     미학 방향, 타이포그래피, 색, 모션, 반응형, 핵심 화면별 구현 계획을 만든다.

## 2. 이번 세션에서 병합한 수정

### Home release-context parser

- Home `master`: `916a557bdbff13265f24c14705fdd2c6819654ba`.
- PR: develop `#43`, master `#44`.
- 현재 candidate schema의 release context를 읽도록 parser와 테스트를 교정했다.
- release path 분류는 렌더링을 발생시키지 않는 경로로 유지했다.
- Home canonical archive digest는 변경되지 않았다:
  `f27b3aa39c10c4d475770d5abc4610c2dfef1076a43a1b60d30f2d2a13e5fbdc`.

### GitOps Home Docker evidence ownership

- GitOps develop PR `#117`, merge
  `4e131c2a98204c3f4ce6d93c3ada7661ab69b7f8`.
- GitOps main PR `#116`, merge
  `53ef6aaee137af7dd2270d264fcccce23ff07cf5`.
- Docker evidence가 만든 root-owned `home/test-results` 때문에 Playwright가
  `EACCES`로 실패했다. symlink/special file을 거부한 뒤 해당 디렉터리 소유권을
  runner로 돌리는 fail-closed 검증을 추가했다.
- release test: `265 passed, 3 skipped`.

### GitOps release-host Service port

- GitOps develop PR `#118`, merge
  `bf2a5b65fd178d394ae31b0eab1e4b928c083e25`.
- GitOps main PR `#119`, merge
  `81c8414d859639d912518bab366ce7e2f23bd4c9`.
- 라이브 클러스터에서 control token을 출력하지 않고 두 prerequisite URL의
  `HTTP 404`를 재현했고, Service 선언 port `8080`과 Ingress backend port `80`의
  불일치를 확인했다.
- 세 release helper host backend를 모두 `8080`으로 교정하고 계약 테스트를 추가했다.
- release test: `265 passed, 3 skipped`.

## 3. release lineage와 폐기 사유

| Release | Candidate SHA-256 | 결과 | 다음 release가 필요했던 이유 |
|---|---|---|---|
| `prod10` | 선행 문서 참조 | evidence 5종 성공, staging run `32837870017` 실패 | Home parser가 현재 release context schema를 읽지 못함 |
| `prod11` | 선행 candidate | candidate run `32840493421`, artifact `9560276399`; 폐기 | ET13 provenance가 stale |
| `prod12` | `8f1883702790a1e42b7fac2ab1bb28ca3b660dd86bae5a64f4fa04b213168516` | candidate run `32842252274`, artifact `9560943026`; staging `32843335511` 실패 | Home Playwright output가 root-owned여서 `EACCES` |
| `prod13` | `5b385b7561d43cc0b647e253133e6fb18cbc2c28f73a540dedaf803ef0cab001` | candidate run `32845274064`, artifact `9562046715`; staging `32846308414` 실패 | parser와 ownership gate는 통과했지만 release-host 요청이 `404` |
| `prod14` | 미생성 | ET13 승인 성공, Android 빌드 진행 중 | ingress 교정 main의 직접 자식으로 새 불변 candidate 필요 |

`prod13` 성공 evidence producer:

- Home: run `32845336764`, artifact `9562075395`.
- Privacy: run `32845337315`, artifact `9562087204`.
- AI: 첫 run `32845337126`은 GitHub `run.status` 전파 race로 artifact 전 실패.
  fresh run `32845495129`, artifact `9562397881` 성공.
- ET13: run `32845336902`, visual artifact `9562372424`, accessibility artifact
  `9562372978` 성공.
- Manual: run `32845336894`, NVDA artifact `9562114443`, TalkBack artifact
  `9562114783` 성공.

## 4. `prod14` 고정 입력

- frontend source:
  `5a7d58530f7c50db56a3d8d97dcd51b74cb12713`.
- AI source:
  `6209cf55267635968bc8fcba01f9ec86da791a31`.
- AI image digest:
  `sha256:70278d00b3d0ea0daeb95e44853bc52a218e97fa833edfede12201ed75f73d86`.
- AI prompt hash:
  `01a585c4619527649be6294b60882cea82efa5a358c130b9894b23bbf71392e9`.
- Home source:
  `916a557bdbff13265f24c14705fdd2c6819654ba`.
- Home archive digest:
  `f27b3aa39c10c4d475770d5abc4610c2dfef1076a43a1b60d30f2d2a13e5fbdc`.
- documents privacy source: 이 문서의 main 병합 후 `origin/main`을 재조회해 확정.
- raw ET13 diagnostic run `32806685510`, artifact `9548560934`, digest
  `sha256:2dcabb3c169ab3a86077969b71cb9374556c9b64bad06c822bea709ddc1f1c36`.
- raw ET13 workflow hash:
  `362d897b8089e9480b39bc8a597e578214f1b001bb9b23eeb0161e617d1e45f0`.
- baseline approval workflow hash:
  `808e2b85e8dc5d2e5c73dd55b6f5b3f9049c0e0170dfa332b372264cbb23cf5d`.
- ET13 build marker:
  `0a1bddcf843d01ac5ab5083b94551c9dcef19770c2e3328893fee1198b7c4509`.
- signed Android workflow hash:
  `65f5725b56b3be919199b922276d4b367d87cb2d3e6f7ccf3e179de3abc7b4ca`.
- 이전 실행에서 확인한 APK hash:
  `eb817ff335b360b9e009d01e6492181848633f7a250435eb0f270bb83a6d2e2c`.
  `prod14` run의 실제 APK도 별도로 해시해 일치 여부를 확인한다.

## 5. ET13 provenance 재생성 규칙

- 검증용 `prod10` template:
  `D:\workspace\dpa\.tmp\prod10-et13-provenance\visual\artifacts\et13\provenance.v1.json`
  과 accessibility 대응 파일.
- `baseline_authentication`은 아래 순서로 구성한다.
  `release_id`, `repository`, `workflow_path`, `workflow_sha256`, `run_id`,
  `run_attempt`, `head_sha`, `artifact_id`, `artifact_name`,
  `artifact_archive_sha256`(접두사 `sha256:` 제외),
  `approval_document_sha256`, `approval_environment`, `approval_environment_id`,
  `approved_by_id`, `approved_by`, `approval_effective_at`.
- `input_provenance_sha256`를 제거한 객체를 재귀 key-sort한 compact JSON으로 SHA-256한
  뒤 필드에 넣는다.
- 파일 hash는 `JSON.stringify(obj, null, 2) + "\n"`의 SHA-256이다.
- 이 알고리즘은 `prod10`의 네 hash와 `prod11`의 의도된 실패를 재현해 검증했다.

## 6. 보호 설정과 운영 불변조건

- 보호 환경 승인 자동화는
  `scripts/release/approve_pending_deployment.py`만 사용한다. 성공 결과에
  `restored_prevent_self_review:true`가 없으면 완료로 취급하지 않는다.
- GitOps main governance ruleset:
  - ID `21194270`, name `mission-spine-main-governance`.
  - `update` rule 1개.
  - bypass actor는 Integration ID `4679079`, `devpath-gitops-release`, mode `always`.
- GitOps main review 원형:
  - `dismiss_stale_reviews=true`
  - `require_code_owner_reviews=false`
  - `require_last_push_approval=true`
  - `required_approving_review_count=1`
  - PR bypass는 `devpath-gitops-release` App만 허용.
- 이번 세션의 일시 변경 뒤 GET 검증 결과:
  `restored_main_review_policy=true`,
  `restored_main_governance_ruleset=true`.
- release 실행을 위해 보호를 영구 해제하거나 candidate/final seal을 우회하지 않는다.

## 7. staging 임시 DNS 상태

- ConfigMap: `kube-system/coredns-custom`.
- 마지막 확인 UID: `16109ac7-e3d4-4006-b44a-1f2b3c1e3cfd`.
- labels: `managed-by=codex-transient`, `purpose=staging-acme-dns-cache-bypass`.
- `resourceVersion`은 변할 수 있으므로 삭제 직전 반드시 다시 읽는다.
- staging seal이 성공하기 전에는 제거하지 않는다. 제거 시 exact live identity가 위 값과
  일치하는지 확인하고, 제거 뒤 DNS와 staging journey를 다시 검증한다.

## 8. 로컬 작업 경계

- 기존 `D:\workspace\dpa\documents` 작업트리는
  `docs/handoff-seal-restore` 브랜치이고 `AGENTS.md`, `CODEX.md`가 미추적 상태다.
  사용자 작업이므로 수정·삭제·stage하지 않는다.
- 기존 `D:\workspace\dpa\devpath-gitops` 작업트리도
  `fix/bypass-observable-contract` 브랜치와 미추적 지침 파일을 갖고 있다.
  release 재개 시 current main 기준의 별도 clean worktree를 사용한다.
- 이번 핸드오프 작업트리:
  `D:\workspace\dpa\.worktrees\documents-prod14-handoff`.
