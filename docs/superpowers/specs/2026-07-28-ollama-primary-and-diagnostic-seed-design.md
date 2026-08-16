# Ollama 주력 전환 + 진단·콘텐츠 시드 복구 설계

- 날짜: 2026-07-28
- 상태: 사용자 승인 (구현 전 — 이 스펙 리뷰 후 플랜 작성)
- 대상 레포: `devpath-shared`(시드 마이그레이션) · `devpath-gitops`(Ollama 배포·env) · `devpath-ai-svc`(provider) · `devpath-learning-svc`(시더 프로파일·SLO)
- 배경 세션: 2026-07-28 WS-D E2E 시도 중 진단 단계 실패 발견 → AI 아키텍처(클라우드 API 의존) 재검토
- 관련: 핸드오프 [handoff-2026-07-28-reuse-detection-done-e2e-pending.md](../handoff-2026-07-28-reuse-detection-done-e2e-pending.md) · ai-svc `CLAUDE.md`("현재 dev=Ollama gateway / 운영 목표=Claude 등 provider 교체")

## 1. 배경 — E2E 퍼널이 두 지점에서 끊김 (코드·운영 DB 실측)

WS-D 실배포 후 E2E(로그인→동의→진단→로드맵→…)를 시도하니 **실력진단 15문제가 출력되지 않고 종료**. 운영 DB·코드 실측으로 **서로 독립인 두 원인**을 확정했다.

**원인 A — 진단·콘텐츠 시드 미적재 (Ollama 무관)**
- 운영 DB 실측: `question_bank=0`, `contents=0`, `content_embeddings=0`, `assessments=4`(껍데기), `assessment_items=0`.
- `QuestionBankSeeder`(500문항)·`ContentSeeder`(150콘텐츠)가 **둘 다 `@Profile("dev")`** → 운영 프로파일에서 실행 안 됨.
- `AssessmentService`는 `question_bank`에서 적응형으로 문항 선택(`selector.select(track, difficulty, excluded, questions.findByTrack(track))`) → 빈 뱅크 = 문항 0 = 진단 종료.

**원인 B — Ollama 미배포로 path 생성·임베딩 사망**
- ai-svc의 path 생성(`POST /ai/path/generate`)·임베딩(`POST /ai/embed`)은 **Ollama 게이트웨이 전용**(Claude 변형 없음).
- 운영 ai-svc에 `OLLAMA_BASE_URL` **미설정** → 파드 내 기본 `localhost:11434` = 없음 → 이 경로 전부 실패.
- 결과: 로드맵 실AI 생성 불가(`learning RestAiPathClient → ai-svc /ai/path/generate`), `content_embeddings=0`.
- 로드맵은 "완료된 진단"을 요구(`NoCompletedAssessmentException`) → **원인 A가 B보다 선행**.

**AI provider 현황 (gitops·코드 실측)**

| 기능 | 운영 provider | 작동 | 비고 |
|---|---|---|---|
| review·mentor·community-seed·retention | `claude` | ✅(유료) | provider 추상화로 `mock\|claude\|ollama` 교체 가능 |
| path 생성 · embed | Ollama 전용 | ❌ 미배포 | Claude 변형 없음 |

provider 선택 메커니즘은 이미 완비: `@ConditionalOnProperty(name="devpath.<기능>.provider")`. retention만 Ollama 클라이언트 부재.

## 2. 목표 / 비목표

**목표**
- E2E 퍼널 복구: 진단 → 로드맵 → 콘텐츠·임베딩이 실제 작동.
- AI 비용 구조를 "주 기능 Ollama, 고난도 Claude"로 이전하는 **1단계(클러스터 내 Ollama 배포)**를 놓는다.
- 모든 변경은 TDD·브랜치 플로우 준수. **운영 도달 경로(중앙 마이그레이션·gitops)**만 사용.

**비목표 (후속/별도)**
- 전용 GPU 호스팅(Phase B) — 베타 트래픽이 정당화할 때까지 보류(저volume에선 비용 역전).
- retention Ollama 클라이언트 — Phase A에서 필요 시.
- 결제·홈페이지(WS-A) 등 무관 로드맵.
- 문항·콘텐츠 품질 개선 — 기존 MD2 승인 시드 그대로 사용.

## 3. 설계

### 트랙 1 — 진단·콘텐츠 시드를 운영에 적재 (선행, Ollama 독립)

문제: 시드가 dev 전용. 운영은 **중앙 마이그레이션**(`devpath-shared/src/main/resources/db/migration`, gitops `apps/devpath-migration` 잡이 적용)으로만 스키마·데이터가 도달한다.

**접근**
- **(권장) 시드를 중앙 Flyway 마이그레이션으로 승격**: `question_bank_md2_seed.sql`(500)·`content_md2_seed.sql`(150)을 devpath-shared에 **버전 마이그레이션**(현재 최신 다음 번호)으로 추가. 멱등 보장(빈 테이블 가드 또는 `ON CONFLICT DO NOTHING`). → 운영·재현 환경 모두 자동 적재. dev 프로파일 시더는 로컬 편의로 유지(중복은 시더 count 가드로 무해).
- (대안·비권장) learning-svc 시더 `@Profile`을 운영 포함으로 조정 — 서비스 기동 시 시드하나, 시드 데이터 소유가 중앙 마이그레이션과 이원화돼 정합성 리스크.

**주의**: 시드 SQL의 컬럼이 중앙 스키마와 일치하는지 이식 전 검증(현 시드는 learning-svc 리소스 기준 작성). 스키마 대조 필수.

**테스트(Test-First)**: 마이그레이션 적용 후 `question_bank>=500`·`contents>=150` 검증. 진단이 문항을 반환하는 회귀(빈 뱅크→종료 재현 → 시드 → 문항 반환).

### 트랙 2 — Ollama 마이그레이션 (Phase C → 측정 → A)

**Phase C — 클러스터 내 Ollama 배포 + path/embed 부활**
- gitops `apps/devpath-ollama/base/`: `Deployment` + `Service` + `PVC`(모델 캐시).
  - 이미지 `ollama/ollama`. Service `ollama.devpath.svc:11434`.
  - 모델: `nomic-embed-text`(임베딩, ~275MB) + **`qwen2.5:3b`**(생성, ~2GB). **7B 아님** — t3.xlarge(16GB)에 기존 스택과 공존하려면 3B로 시작.
  - 모델 로드: init 단계 `ollama pull` 또는 PVC 사전적재(재시작 시 재pull 회피).
  - 리소스 request/limit 명시(모델+런타임 ~3–4GB) — 노드 여유는 **재가동 후 `kubectl top`으로 실측**.
- ai-svc `deployment.yaml` env에 `OLLAMA_BASE_URL=http://ollama.devpath.svc:11434` 추가(+ 필요 시 `OLLAMA_GEN_MODEL=qwen2.5:3b`).
- 검증: `/ai/embed`·`/ai/path/generate` 실호출 성공 → learning 로드맵 생성 e2e.

**정직한 제약 (설계에 반영)**
- CPU 추론: 임베딩(`nomic-embed`)은 짧은 forward라 빠름 → 문제없음. **path 생성(긴 출력)은 CPU 3B에서 수십 초 → learning SLO(생성 p95<8s) 위반.** 베타에선 SLO를 명시적으로 완화(예: p95<60s)하거나, 8s가 필수면 Phase B(GPU) 또는 Claude path 클라이언트 신설(현재 없음) 필요. **1차는 베타 SLO 완화로 수용.**
- RAM: 3B로도 노드 증설(t3.2xlarge — 비용 2배) 필요할 수 있음. 실측 후 결정.

**Phase A — 측정 후 선택적 provider 전환 (후속)**
- Claude 실비용(Console 사용량) 측정.
- 저품질 허용 기능부터 `provider=ollama` config flip(gitops env): community-seed → mentor 순. review는 품질상 Claude 유지 권장.
- retention은 Ollama 클라이언트 없음 → 필요 시 신설(TDD, 기존 Claude 클라이언트 대칭).
- 각 전환은 **골든 케이스 회귀 통과가 게이트**.

### 실행 전제
- 스펙·플랜·코드/매니페스트 작성은 **오프라인 가능**.
- 실제 배포·검증(마이그레이션 적용·Ollama 파드·e2e)은 **EC2 재시작 필요**(2026-07-28 비용 절감으로 EC2 정지). 재가동 시 일괄 검증.

## 4. 영향 범위 / 분해

| 레포 | 변경 |
|---|---|
| devpath-shared | 시드 마이그레이션 1~2개(question_bank·content) |
| devpath-gitops | `apps/devpath-ollama/*` 신규 + ai-svc env 1줄 + (증설 시 노드 스펙) |
| devpath-ai-svc | Phase C 코드 변경 없음 / Phase A에서 retention Ollama 클라이언트(후속) |
| devpath-learning-svc | (대안 택 시) 시더 프로파일 / SLO 문서 완화 |

## 5. 순서 / 롤아웃
1. **트랙1**: 시드 마이그레이션(devpath-shared) → 중앙 마이그레이션 잡 적용 → 진단 문항 반환 검증.
2. **트랙2 Phase C**: Ollama 배포(gitops) → `OLLAMA_BASE_URL` → path/embed·로드맵·임베딩 검증.
3. **측정**: Claude 비용·Ollama 품질/지연 실측.
4. **Phase A**: 데이터 기반 provider 선택 전환.
- 각 단계 독립 브랜치 → develop PR → (릴리스 시) develop→main. **main 직접 금지.**

## 6. 리스크
- 시드 SQL ↔ 중앙 스키마 컬럼 불일치 → 마이그레이션 실패. 완화: 적용 전 `kubectl kustomize`·dry-run·스키마 대조.
- Ollama RAM으로 노드 OOM → 파드 축출. 완화: 3B·리소스 한도·실측 후 증설.
- CPU 지연으로 로드맵 UX 저하. 완화: 베타 SLO 완화 명시 + 후속 GPU 여지.
- Phase A 품질 저하(3B/7B < Claude) → 골든 회귀 게이트로 차단.

## 7. 후속 백로그 (이 설계 밖)
- Phase B: GPU 호스팅(트래픽 정당화 시).
- retention Ollama 클라이언트.
- `content_embeddings` 백필 배치(시드 콘텐츠 임베딩 일괄 생성).
- ai-svc 모델 ID 최신화(`claude-sonnet-4-6`·`claude-haiku-4-5` → 현행).
- 핸드오프 정정: id=1 실제 상태(consent DONE·birth_year 1982, 문서는 PENDING로 오기재) — 별도 처리.
