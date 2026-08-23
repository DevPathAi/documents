# 핸드오프 2026-08-23 — governance 충돌 해소 + Shared ET11 게시 + AI 전담 전환

> 선행 문서: `handoff-2026-08-22-night-seal-restore-complete.md`.
> 이 문서는 그 문서 §1의 governance 차단 해소와 Shared ET11 게시 결과를 잇는다.

## 1. 다음 착수점

1. **AI 전담 승인 계약으로 전환**
   - 2026-08-23 사용자 결정으로 `qahnaarin` 초대·별도 사람 승인 경로를 작업과
     차단 조건에서 완전히 제외했다. 초대를 다시 보내거나 수락을 기다리지 않는다.
   - 현재 GitOps의 staging/OFF/ON/landing/rollback 환경은 reviewer가
     `VelkaressiaBlutkrone` 1명이고 `prevent_self_review=true`다. 또한
     `verify_current_protected_approval.py`와 `verify_release_artifacts.py`는 승인자가
     workflow actor·triggering actor와 같으면 실패한다. 따라서 현 계약을 그대로 둔 채
     문구만 AI 작업으로 바꾸면 sealed release가 실제로는 진행되지 않는다.
   - Shared의 migration-release 환경도 같은 단일 reviewer·self-review 방지 형상이다.
     Shared publish에서 검증한 일시 해제 → AI API 승인 → 즉시 복원 → GET 검증 절차를
     migration에도 동일하게 적용하되, GitOps의 명시적 신원 불일치 검증은 별도로
     테스트 우선 교정해야 한다.
   - 테스트를 먼저 추가해 사람 신원 분리 가정을 제거하고, AI가 수행한 코드 검토·CI·
     불변 artifact 검증 결과를 fail-closed 기계 증거로 인증하도록 검증기·워크플로·환경
     정책을 함께 교정한다. 단순 영구 무보호 전환은 금지한다.
   - 전환 전까지 AI가 보호 설정을 일시 조정해야 한다면 변경 전 원본 전체 스냅샷,
     최소 필드 변경, 작업 직후 원자적 복원, 라이브 GET 정확 일치를 모두 증거로 남긴다.
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

### GitHub 초대 경로 폐기

- 조직 초대 `78678364`(`qahnaarin`, `direct_member`)를 취소했다.
- `devpath-shared` 저장소 초대 `329407883`(`qahnaarin`, `write`)도 취소했다.
- 2026-08-23 10:51 KST 라이브 재조회에서 해당 조직·저장소 pending 초대는 각각
  0건이고, 조직 전체 멤버 목록에도 `qahnaarin`은 0건이다.
- 이 항목은 사람이 수행할 잔여 작업이 아니다. 이전 핸드오프·설계 문서의
  `qahnaarin` 수락 지시는 이 문서가 대체한다.

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

- **초대 제거 ≠ AI 승인 계약 전환 완료.** pending 초대는 0건이지만 GitOps 검증기와
  보호 환경에는 독립 사람 승인 가정이 아직 남아 있다. ET11 candidate/final/seal보다
  먼저 §1-1을 코드·테스트·라이브 정책까지 완료한다.
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
- `qahnaarin` 조직·Shared 저장소 pending 초대: 각각 0건. 조직 멤버 아님.
- GitOps AI 전담 승인 계약: 미교정. 현재 5개 보호 환경과 두 검증기에 사람 신원 분리
  가정이 남아 있음.
- ET11 GitOps candidate/final/seal/migration/promote: 미생성·미실행.
