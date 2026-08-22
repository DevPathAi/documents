# 핸드오프 2026-08-22 밤 — 문항 품질 완결 + 봉인 복원 완결 (다음: governance 설계 충돌 조정)

> 선행 핸드오프: `handoff-2026-08-22-et10-release-complete-manual-gitops.md` (같은 날 오전, et10 릴리스 완주).
> 이 문서는 그 이후 오후~밤 세션의 이관이다. 메모리 상세: `devpath-question-bank-et11-seed-correction` · `devpath-sandbox-runner-and-seal-smoke`.

## 1. 다음 착수점 (우선순위 순)

1. ★★**governance 룰셋 설계 충돌 조정 (et11 차단급, 미해결 유일 항목)**★★
   - shared `scripts/release/migration_release_gate.py` 의 `_validate_governance_ruleset` 은
     governance 룰셋 규칙으로 **pull_request(allowed_merge_methods=["squash"]·
     dismiss_stale·thread resolution·count1·last_push) + required_status_checks(미션 체크 2종·strict)** 를 요구.
   - gitops `scripts/release/verify_gitops_write_authority.py` 는 **update 제한 규칙 단일**을 요구
     (현재 라이브 룰셋 = 이 형상, 21194270).
   - 같은 이름(`mission-spine-main-governance`) 하나의 룰셋로 **양립 불가**. 둘 다 라이브
     미실행이라 숨어 있던 레포 간 계약 충돌. **단일 설계로 통일**(어느 쪽 의미론을 채택할지
     설계 판단 필요 — shared 안은 사람 PR 경로 보존+App bypass, gitops 안은 App 전용 갱신)
     후 반대쪽 검증기·룰셋·테스트를 맞춘다.
   - shared 게이트는 **bypass_actors 가시 요구도 공유**(같은 잠재 결함) — gitops 에서 적용한
     「관측 가능 계약」(보이면 정확 일치/숨겨지면 caller-relative `current_user_can_bypass`)으로
     동일 교정 필요. classic 봉인형(checks null)과 shared 게이트의 classic 기대도 대조할 것.
2. [사람] `qahnaarin` 초대 수락 — **8/24 만료 임박**. 이제 남은 인간 단계는 이것뿐.
3. et11 릴리스 시: promote 첫 실가동(App 이 봉인 main 에 실쓰기) · sandbox 하드닝 상태에서
   실행 API 스모크 · et11 에는 문항 교정 마이그레이션 V202608221001 이 실린다.

## 2. 이 세션에서 완결된 것 (전부 실측 검증)

### 문항 품질 캠페인 마무리
- **재작성 183건 운영 적용**: 13배치 재작성 → 프로그램 게이트(최장보기=정답 45.9%<60%) →
  적대 검증 13배치(실결함 1건 id1299 import 누락 적발·교정) → 표본 12건 직접 판정 12/12 →
  id+content md5 조건부 UPDATE **183/183 적중** → 재덤프 전수 대조 mismatch 0 (documents #116).
- **시드 원본 교정**: shared V202608221001(#73, **et11 버전 올림+동결 스펙 재산정 동반**) +
  learning-svc 시드 237건(#56) + 승인 JSONL 동기화(#57).
- **사실 검증 게이트**(lsvc #57): fingerprint 장부(`question_verifications.jsonl`) +
  `ApprovedQuestionsGateTest`(CI 강제: 전 게이트 + 시드 SQL 4곳 == 승인 JSONL 재생성본).
  도입 즉시 duplicate-option-set 게이트가 811·823 보기 집합 충돌을 적발 → 교정
  (운영 UPDATE 1 + shared #74 스펙 3차 재산정, jar 1_229_365/eaab3aa3…).

### 항구 과제 3건 (사용자 지정 순서 ③→②→①)
- ③ **web 신뢰앵커**: mission 접미 허용을 항구 설계로 비준(gitops #76) — 신뢰의 실체는
  digest, 태그는 전환 1회용 라벨. 결정 기록 `docs/mission-spine/web-trust-anchor-decision-2026-08-22.md`.
- ② **sandbox runsc 러너 + fail-closed 하드닝 운영 재적용**(gitops #77·#78 → main, ArgoCD 배포):
  `apps/devpath-sandbox-runner`(DinD + gVisor 20250820.0 sha512 핀 + mTLS 전용 2376),
  시크릿 3종(`sandbox-runner-mtls`/`-server-tls`/`-ca` — CA 개인키는 클러스터에만).
  검증: runsc 등록 → gVisor 합성 커널(4.4.0/2016) 실행 실증 → 무인증서 거부 →
  릴리스 이미지 카나리아 readiness UP(그룹에 sandboxRunner) → maxSurge:0 컷오버 →
  netpol 시행 실측(무라벨 차단). RUNBOOK 갱신 완료.
- ① **봉인 인증 스모크**: `mission-spine-auth-smoke.yml`(#79·#80) — App 자격 배선 실증.

### 봉인 복원 (2차·3차)
- **룰셋 2종 생성·활성**: integrity 21194269 · governance 21194270. 토글 리허설로 복구 가능성 실증.
- **classic 봉인형 전환**: checks null · push 제한=[App] · reviews(count1·dismiss_stale·last_push·
  PR bypass=[App]) · conversation resolution · linear.
- **검증기 잠재 결함 4건을 라이브 첫 실행이 순차 적발·교정**(#83~#86):
  ①protection GET 은 checks 비활성 시 키 생략 ②룰셋 GET 은 update parameters 를 값 무관 생략
  ③(스테이지드가 아니라) **bypass_actors 는 write 권한자에게만 반환** → 관측 가능 계약
  (사용자 결정: App 최소권한 유지) ④정확 형상은 `seal-verify` 로컬 하네스
  (validate_authority_state 실코드 + 설치만 목표 대입)로 판정.
- **풀 write-authority 검증 라이브 green**(run 32572408779) — promote 동등 전체 통과.
- **evidence-reader 스모크 전부 green**(frontend #142·#143) — 설치 축소(사람 클릭) 실효.

### 레거시 org App secret 폐기 완결
- 새 evidence-reader PEM: RSA 검증 + JWT→GET /app 소유 실증 후 ai-svc·documents 보호환경
  secret 배치, 사용 후 셰레드.
- **release-eval 이행**(ai-svc #40·#41): 자기 레포 읽기 github.token(et13 선례로 실증) ·
  팀 멤버십은 gitopsToken 으로 이동(gitops 단독 설치 토큰의 org teams/members 200 실증).
- **privacy-approval 이행**(documents #119·#120): App 토큰 사용처 전수 실측 후 최소 변경.
  ★계약 테스트가 워크플로 시크릿 이름·repositories 를 핀한다 — 이행 시 동반 갱신 필수★
- 전 레포 main 전수 grep(잔존 = 부정 단언·문서·동명 env 변수뿐) → **org secret 2종 삭제(잔여 0)**.

## 3. 새 함정 (재발 방지)

- ★**「픽스처가 통과해도 라이브 GET 서식은 별도 실측」** — GitHub 는 비활성 필드를 생략하거나
  (checks·update parameters) 권한 낮은 호출자에게 숨긴다(bypass_actors). 봉인류 검증기는
  라이브 첫 실행 전까지 신뢰하지 말 것. 판정 기법: 검증 함수를 로컬에서 실데이터로 직접 실행.
- ★**gitops main 수동 머지는 3중 해제**(governance disable + integrity disable + classic relax)
  → 머지 → 3중 재봉인. integrity 의 linear 는 bypass 없어 머지커밋을 상시 차단(실측).
- ★dind entrypoint 는 `DOCKER_TLS_CERTDIR` 가 비면 **비암호 2375 리스너를 추가 주입**(실측) —
  `dockerd` 직접 실행으로만 mTLS 단일 리스너 보장. verify-sandbox-hardening.ps1 이 단언.
- ★ArgoCD 가 main 추적 automated(prune·selfHeal) — 수동 kubectl 은 원복된다. 신규 앱 디렉터리는
  main 머지 즉시 자동 배포. 기존 앱은 `argocd.argoproj.io/refresh=normal` 로 즉시 refresh.
- ★.gitattributes `/src/main/resources/** text eol=crlf`(shared) 는 **CI 리눅스 체크아웃도 CRLF
  물질화** — 여러 줄 리터럴 마이그레이션은 per-file `eol=lf` 핀. SQL 생성기는 문장 재정형 금지
  (들여쓰기가 리터럴 오염, 실측 44건).
- ★Python `open()` 기본 유니버설 뉴라인이 「바이트 일치 실측」을 오염 — 바이트 주장은 `rb`/`newline=''`.
- 설치 편집·PEM 재발급 API 는 오너 계정으로도 403/404(실측) — 구조적 UI 전용.
  `pending_deployments` 승인은 `-F`(정수형), 게이트 잡마다 승인이 다시 뜬다.
- 로컬 devpath DB 는 학습-svc 시더가 재시드하는 공용 모래상자 — 마이그레이션 검증은 빈 DB 체인과 CI 로만.
- gh 토큰 계정은 부계정(VelkaressiaBlutkrone) — 조직 유일 멤버이자 owner.

## 4. 현재 봉인 상태 스냅샷 (2026-08-22 밤)

- gitops main: classic 봉인형 + 룰셋 2종 active. 검증: `scratchpad seal-verify` 하네스 PASS ·
  풀 스모크 green. **다음 수동 머지부터 3중 해제 절차 필요.**
- App 2종: 설치 gitops 단독(selected) · gitops-release=contents write+admin read ·
  evidence-reader=all read(actions/contents/members/metadata).
- 환경 psr 전부 true 복원 확인(gitops production-off · frontend et13-release-auth).
- org secrets: 0건.
