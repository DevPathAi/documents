# 핸드오프 2026-08-23 — governance 충돌 해소 + Shared ET11 게시

> 선행 문서: `handoff-2026-08-22-night-seal-restore-complete.md`.
> 이 문서는 그 문서 §1의 governance 차단 해소와 Shared ET11 게시 결과를 잇는다.

## 1. 다음 착수점

1. **[사람] `qahnaarin` 조직 초대 수락**
   - 2026-08-23 09:20 KST 라이브 API: membership `pending`, invitation id `78678364`.
   - 초대 생성: 2026-08-17 20:18:21 KST. GitHub의 7일 자동 만료 계약에 따라
     **2026-08-24 20:18:21 KST 전** 대상 계정 로그인으로 수락해야 한다.
   - 현재 CLI 계정은 `VelkaressiaBlutkrone`이므로 대신 수락할 수 없다.
2. **ET11 sealed release 입력 생성**
   - GitOps main의 `release-manifests/candidates/`와 `releases/`는 `.gitkeep`만 있고,
     원격 `release/candidate-*` 브랜치도 0개다. 따라서 아직 promote를 디스패치할
     인증된 `release_id`가 없다.
   - 새 release ID로 candidate-only child → candidate producer 및 보호 producer 전부 →
     final-only child → validate seal 순서를 먼저 완주한다.
3. **첫 실 promote와 운영 스모크**
   - seal 이후 migration release가 V202608221001을 적용하고 GitOps App이 봉인 main에
     첫 실쓰기를 수행하게 한다.
   - migration result를 인증한 뒤 promote OFF/ON을 실행하고, sandbox 하드닝 형상에서
     실제 실행 API를 스모크한다. candidate/seal 없이 수동으로 우회하지 않는다.

## 2. 완결된 것

### governance 단일 계약

- 설계 선택: GitOps 운영 봉인을 권위값으로 삼았다.
  - integrity ruleset `21194269`: deletion·non-fast-forward·linear, bypass 없음.
  - governance ruleset `21194270`: App만 bypass하는 update 제한 단일 규칙.
  - classic: status checks 비활성, App-only push 제한, review 1·dismiss stale·last-push,
    PR bypass App-only, admins/conversation, force/delete 금지.
- Shared의 상충 계약(classic 404 + PR/status ruleset)을 위 형상으로 교정했다.
- `bypass_actors`는 보이면 정확 일치, 숨겨지면 `current_user_can_bypass`가
  integrity=`never`, governance=`always`인 관측 가능 계약으로 통일했다.
- GitHub GET이 생략하는 classic `required_status_checks`와 update parameters는
  관측된 생략형 또는 정확한 가시값만 허용한다.
- Shared PR #75 → develop merge `79a2b228468ba50db25c0c6a3ffd37fdc9357241`.

검증:

- 실패 테스트를 먼저 확인한 뒤 release Python **44 passed, 1 Windows symlink skip**.
- CI 고정 pgvector digest의 빈 DB에서 Gradle **101 passed, 1 skip**.
- actionlint 1.7.7 green.
- 2026-08-23 라이브 ruleset/classic JSON을 Shared와 GitOps 두 검증기에 동시에 넣어
  App id `4679079`, rulesets `21194269/21194270` 모두 PASS.
- PR #75 CI run `32607131917` green.

### Shared ET11 main·불변 게시

- release PR #76 CI run `32607296990` green 후 main merge
  `c4d468a70e8870e8f60f25539e91599def75f0f2`.
- main 보호 완화는 review count 0·last-push false만 사용했고 즉시
  count 1·dismiss stale true·last-push true로 복원해 GET 재확인했다.
- 패키지 `0.0.1-et11.20260822` 게시 run `32607404583`, attempt 1, green.
  - GitHub package version id `65586707`.
  - frozen JAR: 1,229,365 bytes,
    `eaab3aa3ad891f7dfeafb084e63d89645978d7716eb0c90a0dda42e0c40dac2e`.
- main CI/image run `32607404566`, attempt 1, green.
  - migration image:
    `ghcr.io/devpathai/devpath-migration@sha256:f1ac7dac56643c2adf3dc62ace83628758826d3ebae710a13c788bfeb73e0fc6`.
  - evidence artifact id `9484536954`, publish mode `published`.
- publish 환경은 승인 직후 `prevent_self_review=true`, reviewer
  `VelkaressiaBlutkrone`, custom branch policy `main`으로 복원 확인했다.

## 3. 현재 경계와 함정

- **게시 완료 ≠ 운영 migration 완료.** 운영 DB의 V202608221001과 GitOps migration
  digest는 아직 이전 상태다. candidate/final/validation seal이 없으므로 migration release,
  promote, sandbox 실행 API 스모크는 아직 실행하지 않았다.
- Shared 로컬 영속 `devpath` DB는 콘텐츠 시드 0건으로 오염돼 전체 Gradle에서 3건이
  실패했다. 기존 볼륨을 건드리지 않고 CI와 같은 digest의 임시 빈 PostgreSQL에서
  재실행하자 전부 green이었다. DB migration 판정은 반드시 빈 DB 체인/CI로 한다.
- GitHub App 권한이 낮은 정상 실행에서는 `bypass_actors`가 숨겨진다. 관리자 토큰의
  라이브 PASS만으로 App 호출자 경로를 대체했다고 주장하지 말고, 기존 full auth smoke와
  hidden-shape 계약 테스트를 함께 증거로 사용한다.
- main CI에는 `docker/setup-buildx-action`의 Node 20 강제 Node 24 전환 경고 1건이
  있었지만 job 결론은 green이다. 이번 ET11 차단과는 무관한 후속 유지보수 항목이다.

## 4. 봉인 상태 스냅샷

- GitOps main: classic 봉인형 + integrity/governance ruleset active, 변경 없음.
- Shared main: `c4d468a70e8870e8f60f25539e91599def75f0f2`, CI/publish attempt 1 green.
- Shared main 보호: build strict 필수, review count 1, dismiss stale/last-push true,
  admins/conversation 적용, force/delete 금지.
- org invitation: `qahnaarin` pending.
- ET11 GitOps candidate/final/seal/migration/promote: 미생성·미실행.
