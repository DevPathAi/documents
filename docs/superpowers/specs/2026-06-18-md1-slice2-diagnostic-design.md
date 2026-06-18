# 설계서 — MD1 슬라이스 #2: 진단(Diagnostic / 온보딩 적응형 진단) (2026-06-18)

> **상태**: 설계 확정(브레인스토밍 승인 2026-06-18). 다음 단계 = 빌드별 구현 플랜(writing-plans).
> **위치**: MD1 끝단간(가입(OAuth)→**진단**→경로 p50<8분, web 실API) 중 중간 단계. 선행=슬라이스 #1(OAuth/인증, 완료). 후행=슬라이스 #3(학습경로/1st Aha).
> **원칙**: 각 레포 CLAUDE.md 절대조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock.
> **근거 사양**: `17_스케줄.md §2`, `02_ERD_문서.md §3`, `04_API_명세서.md §2`, `07_요구사항_정의서.md §2.3 FR-ONB·§3.1 NFR-AHA`, `19_온보딩_와이어프레임_스펙.md §3`, `18_온보딩_마이크로카피_가이드.md §4`, `26_학습맥락_자동첨부_구현.md`.

---

## 1. 목적·완료 기준

- **목적**: 비회원/회원이 적응형 15문항 진단을 풀어 강점·약점·`diagnosed_level`(JUNIOR/MID/SENIOR)을 산출하고, 그 결과를 회원 계정에 귀속시켜 슬라이스 #3(학습경로 생성)의 입력으로 전달한다.
- **슬라이스 #2 DoD**(이 설계가 정의): web에서 (a) 비회원 진단 시작→15문항 적응형 진행→결과 직전 가입 게이트, (b) 로그인 후 결과 claim(귀속), (c) 회원 진단 시작→완료→결과 조회가 **실API로 끝단간 동작**하고, 진단 완료가 `AssessmentCompletedEvent`로 전파되어 `onboarding_status`가 IN_PROGRESS로 전이된다. 단위·통합·끝단간 테스트 녹색.
- **범위 외(명시)**: 슬라이스 #3 학습경로 생성, `onboarding_status`=DONE 전이(약속/경로까지 완료해야 DONE), admin 문항 CRUD(FR-ADM-019, 후속), 실 500문항 콘텐츠 제작(MD1 콘텐츠 트랙 별도).
- **관련 NFR**(`07 §3.1`): 진단 자체 목표 시간 p50 ≤ 5분(가입→1st Aha 8분 중).

## 2. 빌드 분해 (슬라이스 #1과 동형: shared → 서비스 → gateway → frontend)

| 빌드 | 레포 | 산출 | 비고 |
|---|---|---|---|
| **A. 스키마+이벤트** | devpath-shared | Flyway 마이그레이션 4테이블 + `AssessmentCompletedEvent` + 토픽 상수 | develop→**main 릴리스(publish)** 선행(서비스가 새 클래스 소비) |
| **B. 진단 엔진+API** | devpath-learning-svc | JPA 엔티티 · 적응형 엔진 · 회원 API · guest API(Redis) · claim · outbox→Kafka · 시드 픽스처 | 핵심 빌드 |
| **C. status 소비자** | devpath-platform-svc | `AssessmentCompletedEvent` 소비 → `onboarding_status` PENDING→IN_PROGRESS(멱등) | 슬라이스 #1 2b 소비자 패턴 재사용 |
| **D. 라우팅+프론트** | devpath-gateway · devpath-frontend | gateway `/onboarding/assessments/**`→learning 라우트 · web 진단 화면 목→실API · dp_core 모델 | ⚠️상류 계약 재검증 게이트 |

> 빌드 순서: A → B → (B 검증) → C → gateway 라우트 → frontend. C와 gateway는 B 계약 확정 후. frontend는 전 상류 확정 후.

## 3. 데이터 모델 (출처: `02_ERD_문서.md §3`, 변경 없이 채택)

### 3.1 question_bank
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | PK | |
| track | enum | BACKEND_SPRING/FRONTEND_REACT/MOBILE_FLUTTER/DEVOPS/FULLSTACK (user_profiles.target_track 재사용) |
| question_type | enum | MCQ / CODE_READING / SHORT_ANSWER |
| content | TEXT | 문항 본문(코드 포함 가능) |
| options | JSON | 선택지(MCQ/CODE_READING) |
| answer_key | JSON | 정답 |
| bloom_level | enum | REMEMBER/UNDERSTAND/APPLY/ANALYZE/EVALUATE/CREATE |
| difficulty | FLOAT | 0.0~1.0 |
| concept_tags | JSON | 개념 태그(강점·약점 집계 단위) |

### 3.2 assessments
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | PK | |
| user_id | FK nullable | guest는 null, claim 시 결합 |
| track | enum | |
| status | enum | IN_PROGRESS / COMPLETED / ABANDONED |
| current_difficulty | FLOAT | 0.0~1.0, 적응형 상태 |
| bloom_distribution | JSON | 출제된 Bloom 분포 |
| started_at / completed_at | timestamp | |

### 3.3 assessment_items
id(PK) · assessment_id(FK) · question_bank_id(FK) · order_num · presented_at · answered_at · answer(JSON, skip 시 null) · is_correct · time_spent_sec · (추가) `skipped` boolean.

### 3.4 assessment_results
assessment_id(FK, PK) · diagnosed_level(JUNIOR/MID/SENIOR) · concept_scores(JSON) · strength_concepts(JSON) · weakness_concepts(JSON) · confidence_weight(FLOAT).

> 시드 픽스처: track×bloom_level×difficulty를 커버하는 소량(수십개) 문항을 Flyway 데이터 마이그레이션 또는 테스트 픽스처로 제공. 실 500문항은 별도 콘텐츠 작업.

## 4. 적응형 진단 엔진 (확정값)

- **시작 난이도**: 0.3 (마이크로카피 "쉬운 문제로 시작" 정합).
- **난이도 전이**: 정답 **+0.1**, 오답 **−0.05**(ERD §3), `current_difficulty`를 [0.0, 1.0]로 clamp.
- **종료**: **고정 15문항**(FR-ONB-004). 15문항 출제·응답 후 COMPLETED.
- **다음 문항 선택**: 해당 track · 미출제 · `difficulty`가 `current_difficulty`에 최근접 · Bloom 분포 목표를 충족하는 후보 중 선택. 동률 시 안정적 정렬(id 등)로 결정적 선택(테스트 재현성).
- **"잘 모르겠어요"(skip)**: `answer:null, skipped:true` 기록. **난이도 무변동**(오답 아님), 점수 집계에서 제외(감점 없음, `18 §4.5` 정합).
- **결과 산출**:
  - concept_scores: concept_tag별 정답률(skip 제외).
  - strength/weakness: concept_scores 상·하위 추출.
  - **능력 추정치 θ** = 정답(non-skip) 문항들의 difficulty 평균(정답 0개면 θ=0) → **diagnosed_level**: θ < 0.4 → JUNIOR, 0.4 ≤ θ ≤ 0.7 → MID, θ > 0.7 → SENIOR. (정밀 보정식은 플랜에서 확정 가능하나 기본 지표는 이 정의로 고정.)
  - confidence_weight: 응답 수·skip 비율 기반 신뢰도(0~1).
- **Bloom 분포 보정**: 출제가 특정 Bloom에 쏠리지 않도록 6단계 목표 비중을 두고 다음 문항 선택에 반영(`assessments.bloom_distribution` 갱신).

> 엔진은 순수 도메인 로직으로 분리(저장소·전송과 무관)하여 단위 테스트로 난이도 전이·종료·레벨매핑·skip·결정적 선택을 검증한다.

## 5. API (출처: `04_API_명세서.md §2`)

베이스 prefix는 기존 명세(`/api/v1`)와 정합하되, 본 설계는 경로를 `04 §2` 표기대로 기술한다. 게이트웨이가 외부 노출.

| Method | Endpoint | 설명 | 권한 | 소유 |
|---|---|---|---|---|
| POST | `/onboarding/assessments` | 회원 진단 세션 시작(track) | AUTHENTICATED | learning |
| GET | `/onboarding/assessments/{id}/next` | 다음 문항(적응형) | OWNER | learning |
| POST | `/onboarding/assessments/{id}/answer` | 답안 제출(answer/skip) | OWNER | learning |
| POST | `/onboarding/assessments/{id}/complete` | 종료→결과 산출→`AssessmentCompletedEvent`(outbox) | OWNER | learning |
| GET | `/onboarding/assessments/{id}/result` | 결과(강점·약점·diagnosed_level) | OWNER | learning |
| POST | `/onboarding/assessments/guest` | 비회원 진단 시작(Redis 세션) | PUBLIC | learning |
| GET | `/onboarding/assessments/guest/{gid}/next` | 비회원 다음 문항 | PUBLIC | learning |
| POST | `/onboarding/assessments/guest/{gid}/answer` | 비회원 답안 제출 | PUBLIC | learning |
| POST | `/onboarding/assessments/guest/{gid}/complete` | 비회원 종료(결과 Redis 보관, 공개 직전 가입 게이트) | PUBLIC | learning |
| POST | `/onboarding/assessments/claim` | guest_assessment_id로 결과 회원 귀속 | AUTHENTICATED | learning |

> guest용 next/answer/complete는 `04 §2`에 미명시였던 공백을 본 설계에서 확정(회원과 동일 엔진, Redis 상태). 요청/응답 JSON 스키마는 플랜에서 구체화하되, 회원·비회원이 동일 DTO를 공유한다.

### 5.1 요청/응답 요지(플랜에서 확정)
- start 응답: `{ assessmentId | guestAssessmentId, firstQuestion? }`
- next 응답: `{ question: {id, type, content, options, bloomLevel, difficulty}, progress: {index, total:15} }` (answer_key 미노출)
- answer 요청: `{ questionId, answer | null, skipped, timeSpentSec }` → 응답 `{ isCorrect?(비노출 정책 검토), nextAvailable }`
- result 응답: `{ diagnosedLevel, conceptScores, strengthConcepts, weaknessConcepts, confidenceWeight }`
- claim 요청: `{ guest_assessment_id }` → 응답 이관된 assessment 요지.

## 6. 비회원 세션·claim

- `guest` 시작 → `guestAssessmentId`(UUID) 발급 + Redis 세션 키 `assessment:guest:{guestAssessmentId}` 에 진단 상태(track·current_difficulty·출제이력·응답) 직렬화.
- **TTL 30분, 매 answer마다 갱신**(FR-ONB-008 중단 복귀). 만료 시 404/재시작 유도.
- guest complete → 결과를 동일 Redis 세션에 보관(공개 직전 가입 게이트: 프론트가 결과 표시 전 로그인 요구, FR-ONB-007).
- 로그인 후 `claim {guest_assessment_id}` → Redis 세션을 DB `assessments`/`assessment_items`/`assessment_results`로 이행(`user_id` 결합, status=COMPLETED) → 이때 `AssessmentCompletedEvent`(outbox) 발행. 멱등(이미 claim된 guest_assessment_id 재요청 무해).
- 비밀·보안: guestAssessmentId는 추측 불가 UUID. guest 엔드포인트는 PUBLIC이나 세션 키 소지자만 진행 가능.

## 7. 이벤트·서비스 경계

- **이벤트**: shared에 `AssessmentCompletedEvent`(assessmentId·userId·track·diagnosedLevel·conceptScores 요지·completedAt). Kafka 토픽 **`learning.assessment.completed`**(`26 §` 정합). learning이 `/complete`(회원) 및 `claim`(비회원→회원) 시 outbox 동일tx 적재 → 릴레이가 send-ack 후 published(슬라이스 #1 2b 패턴 재사용).
- **소비(빌드 C)**: platform이 `AssessmentCompletedEvent` 소비 → `users.onboarding_status` PENDING→IN_PROGRESS 멱등 전이(이미 IN_PROGRESS/DONE이면 무변동). 진단 결과 참조(diagnosed_level)는 슬라이스 #3 입력 위해 보관 여부 플랜에서 결정(최소: status 전이만).
- **경계 원칙**: learning은 assessment 도메인만, platform은 user 도메인만 각자 테이블 소유. 교차 갱신은 이벤트로만(직접 테이블 쓰기 금지).
- **라우팅(빌드 D)**: gateway에 `/onboarding/assessments/**` → learning-svc 라우트 신설. `/onboarding/profile`(목표·트랙·시간)은 platform 소유(슬라이스 #1 user_profiles) — 별도 라우트. guest 경로는 gateway 공개경로(JWT 불요)로 추가, 그 외 진단 경로는 JWT 엣지 검증.

## 8. 프론트(web, 빌드 D)

- 화면 흐름(`19 §3`): O01 Intro → 목표/트랙 → **O03 진단 퀴즈(15문항)** → O04 로딩 → O05 경로(#3). 슬라이스 #2는 O03 + 결과/claim까지.
- O03: 진행률 `index/15` 도트, 문항 헤더(카테고리+난이도 별 5단계), 코드블록, 4지선다 Option Card + "잘 모르겠어요"(항상 하단 고정, 감점 없음). 3문항마다 격려 토스트(`18 §4.6`).
- 비회원 진입: guest 플로우로 진행 → complete 후 **결과 직전 가입 게이트** → OAuth 로그인(슬라이스 #1) → `claim` → 결과 표시.
- 회원 진입: 바로 회원 엔드포인트.
- dp_core: `Assessment`·`Question`(answer_key 미포함)·`AssessmentResult` 모델 + 진단 API 클라이언트. 목 픽스처를 실계약과 정합(슬라이스 #1 frontend 교훈).
- 진단 중 새로고침 복귀(`18 §9.2`): guest는 Redis 30분, 회원은 DB IN_PROGRESS 세션 재개.

## 9. 테스트 전략 (테스트 우선)

- **엔진 단위**(learning): 난이도 전이(정답/오답/skip·clamp), 고정 15 종료, 다음 문항 결정적 선택, diagnosed_level 임계(0.4/0.7), concept 강·약점 집계, confidence.
- **JPA 슬라이스**: 4테이블 매핑·제약. test 프로파일 Flyway로 shared jar `classpath:db/migration` 적용(`@ActiveProfiles("test")`).
- **이벤트 IT**: EmbeddedKafka로 `/complete`·`claim` → outbox→`learning.assessment.completed` 발행, send-ack 후 published(슬라이스 #1 2b 패턴).
- **guest Redis IT**: 세션 생성·TTL·만료·중단 복귀·claim 이행 멱등.
- **소비자 IT**(platform): `AssessmentCompletedEvent` 소비 → onboarding_status 멱등 전이.
- **gateway**: `/onboarding/assessments/**` 라우팅·공개/보호 경로 분리.
- **frontend**: 진단 컨트롤러/위젯(진행·skip·격려), guest→가입 게이트→claim→결과, 목 실계약 정합.

## 10. Spring Boot 4 / 스택 주의(슬라이스 #1 교훈 승계)

- Jackson 3(`tools.jackson.databind.json.JsonMapper`, ObjectMapper 빈 미등록) — Kafka 소비/직렬화에 JsonMapper 사용.
- 테스트 슬라이스·Flyway·Kafka autoconfigure **모듈 분리**(`spring-boot-flyway`·`spring-boot-kafka`·`spring-boot.{data.jpa,webmvc,jpa}.test.autoconfigure`), mock 빈 `@MockitoBean`.
- 서비스 테스트 DB 스키마는 test 프로파일 Flyway로 shared jar 마이그레이션 적용(main flyway 비활성), 모든 `@SpringBootTest`에 `@ActiveProfiles("test")`.
- shared 변경→서비스 소비: shared develop→**main 릴리스(publish)** 선행. 로컬은 캐시 purge 후 `--refresh-dependencies`.
- 스케줄러(outbox 릴레이)는 테스트 레이스 회피 위해 `@Profile("!test")` 분리.

## 11. 미해결/플랜 확정 대상 (공백·정합성 주의)

1. next/answer/complete/result/guest 요청·응답 **JSON 스키마 정밀**(§5.1 요지 → 플랜에서 필드 확정).
2. answer 응답에 **정답 여부(is_correct) 노출 정책**(즉시 피드백 vs 결과까지 비공개) — 와이어프레임 재확인 후 결정.
3. **Bloom 분포 목표 비중** 구체값(6단계) — 플랜에서 수치화.
4. platform 소비자가 진단 결과(diagnosed_level)를 **보관할지**(슬라이스 #3 입력 경로) vs status 전이만 — 슬라이스 #3 설계와 함께 최소화.
5. 이벤트 페이로드 필드 확정 + ERD §8.9 Outbox 이벤트 표에 `learning.assessment.completed` **문서 반영**(정합성).
6. 시드 픽스처 규모·track 커버리지(끝단간 15문항 진행 가능 최소량).

## 12. 관련 문서·메모리
- 슬라이스 #1 핸드오프: `docs/superpowers/handoff-2026-06-18-md1-slice1-done.md`
- 슬라이스 #1 끝단간 런북: `docs/superpowers/runbook-2026-06-18-md1-slice1-e2e.md`
- 사양 출처: 위 헤더 "근거 사양" 참조.
