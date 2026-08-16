# Handoff — EC2 정지·진단시드 develop머지·Ollama 배포 계획 (2026-07-28 오후)

> 다음 세션 착수용. 이 세션은 [handoff-2026-07-28-reuse-detection-done-e2e-pending.md](handoff-2026-07-28-reuse-detection-done-e2e-pending.md)에서 이어졌고, E2E 시도 중 진단 버그를 발견해 **비용 절감(EC2 정지) + AI 아키텍처 재검토(Ollama)**로 전환했다.
>
> SSoT: 스펙 `specs/2026-07-28-ollama-primary-and-diagnostic-seed-design.md` · 플랜 `plans/2026-07-28-diagnostic-content-seed-migration.md`·`plans/2026-07-28-ollama-cluster-deploy-phase-c.md` · 런북 devpath-gitops `docs/runbook-k3s-bootstrap.md`.

## 완료 (이 세션)

1. **E2E 사전점검 → 두 발견**:
   - **id=1 상태가 직전 핸드오프와 불일치**(운영 DB 실측): `deepestdark@outlook.kr`(GitHub, ADMIN, allowlist) = **consent_status=DONE·birth_year=1982·status=BETA_PENDING·onboarding_status=PENDING**. 직전 문서의 "PENDING로 원복" 주장은 **틀림**(2026-07-27 저녁 defect③ 검증이 실제로 동의를 완료시켰고 원복 안 됨). user_consents 5행(13:10:04).
   - **진단 15문제 미출력**: 실력진단이 문항을 못 뽑고 종료.
2. **AWS EC2 정지**: `i-09e252854566cc123`(devpath-k3s, t3.xlarge) → **stopped**. 컴퓨트 ~$120/월 차단. **RDS `devpath-pg`(available)·EIP 13.124.153.105 유지.** (사용자 선택: "EC2만 즉시 정지")
3. **근본원인 확정**(코드·운영DB 실측 — 서로 독립인 2개):
   - 진단: `QuestionBankSeeder`(500)·`ContentSeeder`(150)가 **둘 다 `@Profile("dev")`** → 운영 프로파일 미실행 → `question_bank=0`·`contents=0`. `AssessmentService`는 빈 뱅크에서 문항 선택 불가. **Ollama 무관.**
   - 로드맵·임베딩: ai-svc `/ai/path/generate`·`/ai/embed`는 **Ollama 게이트웨이 전용**(Claude 변형 없음)인데 운영 ai-svc에 `OLLAMA_BASE_URL` **미설정**(파드 내 localhost:11434=없음) → 사망. `content_embeddings=0`.
   - AI provider 현황: review·mentor·community-seed·retention = **claude**(작동·유료). path/embed = **ollama(미배포·사망)**. provider 추상화(`@ConditionalOnProperty devpath.<기능>.provider` = mock|claude|ollama)는 이미 완비. **retention만 ollama 클라이언트 부재.**
4. **Ollama 설계 스펙**(documents #77): 트랙1 시드 복구 + 트랙2 Ollama **C(배포)→측정→A(전환)**. 정직한 제약 명시(CPU path-gen이 SLO p95<8s 위반, RAM, 베타 규모 비용 역전).
5. **플랜 2개**(documents #78·#79): 트랙1 시드 마이그레이션 / 트랙2 Ollama Phase C 배포.
6. **트랙1 구현 완료·develop 머지**(devpath-shared **#50**, subagent-driven):
   - `V202607281001__seed_question_bank.sql`(500)·`V202607281002__seed_contents.sql`(150) — 멱등 DO 가드(빈 테이블만), content_embeddings 제외.
   - **독립 검증**(컨트롤러 직접): FlywayMigrationTest **31/31 green**(강제 재실행), psql `qb=500·contents=150·embeddings=0`, full `build`·CI green.

## 현재 상태 (다음 세션 시작점)

- **인프라**: EC2 **정지** — 재가동 필요. 정지 전 12앱 Healthy·TLS 3종·마이그레이션 34 적용. RDS·EIP는 유지 중.
- **코드/develop**: 트랙1 시드 마이그레이션 = devpath-shared **develop 있음·main 미릴리스** → 운영 미반영. 트랙2 매니페스트 = **미작성**(플랜만). (참고: platform reuse detection #42·shared #49도 develop·main 미릴리스 상태 잔존.)
- **users**: id=1 위 실측 상태(consent 이미 DONE → 로그인 시 동의 화면 건너뜀). id=2 `deepestdark@gmail.com`(Google, ADMIN).
- **로컬**: `devpath-local-postgres-1` docker 컨테이너가 트랙1 테스트 후 떠 있음(정리: `docker compose -f devpath-shared/docker-compose.yml down -v`).

## ⏭ 다음 세션 1순위 — EC2 재가동 → 릴리스 → 배포

1. **EC2 start**: `aws ec2 start-instances --instance-ids i-09e252854566cc123 --region ap-northeast-2` → EIP 재연결·k3s·ArgoCD 복원 대기. (RDS는 7일 자동재시작 이슈 없었는지 확인 — available 유지였음.)
2. **트랙1 릴리스**: devpath-shared develop→main → `apps/devpath-migration` 잡 재실행 → 운영 DB `question_bank>=500`·`contents>=150` 실측(psql). → 진단 복구 확인.
3. **트랙2 실행**(플랜 `2026-07-28-ollama-cluster-deploy-phase-c.md`): `apps/devpath-ollama`(redis 패턴 Deployment+PVC+Service, `qwen2.5:3b`·`nomic-embed-text`) + ai-svc `OLLAMA_BASE_URL` → develop→main → ArgoCD sync → 모델 pull·path/embed 실호출·노드 RAM 실측.
4. **E2E 완주**: 진단(시드됨) → 로드맵 실AI(Ollama) → 광고. id=1은 consent DONE이라 로그인→진단부터. **`status=BETA_PENDING`이 웹 `/beta-pending`으로 막는지 관찰**(백로그 ③).

## 후속 백로그

- Phase A(채팅 provider `claude→ollama` 전환) — Claude 실비용 측정 후 별도 플랜. retention은 ollama 클라이언트 신규 필요.
- `content_embeddings` 백필 배치(시드 콘텐츠 임베딩, Ollama embed 경유).
- `BetaGate.admit()` ADMIN 조기 return이 status를 BETA_PENDING 방치(id=1). / frontend single-flight / Redis 영속성.
- ai-svc 모델 ID 최신화(`claude-sonnet-4-6`·`claude-haiku-4-5`).
- CPU Ollama path-gen SLO(p95<8s) 완화 문서화 or Phase B(GPU) 여지.

## 교훈

- **증상 하나(진단 종료)에 독립 원인 2개**(시드 미적재 vs Ollama 미배포)가 겹쳐 보였음 — 각각 코드·DB 실측으로 분리 확정. 첫 가설("C가 진단을 고친다")을 실측으로 정정.
- **전제를 코드로 검증**: "AI가 클라우드 API에만 의존"은 활성 설정 얘기였고, 코드엔 Ollama 대안이 이미 있으며 path/embed는 오히려 Ollama-미배포로 죽어 있었다.
- **자체 호스팅 LLM 경제성**: 베타(2명) 규모에선 GPU가 Claude API의 20~100배 → 비용 역전. C(복구)만 하고 A(전환)는 데이터 기반 후속.
- **서브에이전트 완료보고 불신·컨트롤러 재검증**: Windows 서브에이전트가 반환값을 안 줬으나(43 tool_uses), 커밋·파일·테스트를 직접 재실행(31/31 강제)해 확정.
- 문서(핸드오프)의 DB-상태 주장은 라이브보다 뒤처질 수 있다 — 착수 전 psql 실측.
