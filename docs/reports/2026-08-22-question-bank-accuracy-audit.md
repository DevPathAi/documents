# 진단 문항 800개 사실 정확성 검수 보고서 (2026-08-22)

## 요약

운영 `question_bank` 800문항(8트랙 × 100) 전수를 3단계로 검수했다:
①1차 검수(25건 × 32배치, 병렬 에이전트) → ②적대적 재검증(반박 우선, 17배치) →
③컨트롤러 직접 판정(표본 12건 전유형 + WRONG_KEY 54건 전수).

**확정 결함 237/800 (29.6%)** — 이 중 **키 오답 54건은 운영 DB 에 즉시 교정 적용**
(조건부 UPDATE 54/54 적중으로 기존 키 값까지 검증). **나머지 183건도 같은 날 재작성해
운영 적용 완료**(아래 「재작성 183건」 절).

## 결함 분포

| 유형 | 건수 | 처리 |
|---|---:|---|
| WRONG_KEY (키 오답) | 54 | ✅ 운영 교정 완료 (`2026-08-22-question-bank-key-fixes.sql`) |
| MULTIPLE_CORRECT (복수 정답) | 98 | ✅ 재작성·운영 적용 완료 (`2026-08-22-question-bank-rewrites.sql`) |
| FACTUALLY_WRONG (전제/서술 오류) | 59 | ✅ 재작성·운영 적용 완료 (同) |
| AMBIGUOUS (정답 확정 불가) | 26 | ✅ 재작성·운영 적용 완료 (同) |

| 트랙 | 확정 결함 | 비고 |
|---|---:|---|
| NODE_TYPESCRIPT | 47 | 신규 트랙(08-19 생성) |
| FRONTEND_REACT | 39 | |
| DEVOPS | 38 | |
| DATA_AI | 35 | 신규 트랙(08-19 생성) |
| BACKEND_SPRING | 29 | |
| MOBILE_FLUTTER | 25 | |
| FULLSTACK | 21 | |
| **PYTHON_BACKEND** | **3** | ★08-14 검수 루프(게이트 6종+인간 확인)를 거친 유일한 트랙★ |

★핵심 관찰★: 검수 루프를 거친 PYTHON_BACKEND(3건)와 미검수 트랙(21~47건)의 결함율 차이가
7~15배다. **구조·분포 게이트만으로는 사실 정확성이 확보되지 않는다** — 08-14 의
「글로 쓴 의도는 게이트가 강제하지 못한다」의 데이터 재확인.

## 검증 방법론 특기

- 2차(적대 검증) 유지율이 97%로 나와 고무도장을 의심했으나, 컨트롤러 표본 12건 직접
  재검(전 유형 층화)에서 12/12 실결함으로 확인 — **유지율이 높았던 것은 1차 플래그
  품질 때문**이었다. 의심 → 직접 측정으로 판별한 것이 유효했다.
- WRONG_KEY 54건은 채점에 직접 영향을 주므로 컨트롤러가 **전수 직접 판정** 후에만
  적용했다(전량 수용, 이 중 8건은 키 교정으로 개선되나 근본적으론 재작성 대상:
  id 509·917·981·573·1260·878·899·623).

## 대표 결함 예 (54건 상세는 JSON 참조)

- id 1156 (NODE): 이벤트 루프 출력 순서 문제의 키가 「타이머가 마이크로태스크보다 먼저」라는
  불가능한 순서(C→B)를 정답으로 지정
- id 703 (FLUTTER): 레이아웃 원칙 "Constraints go down, sizes go up" 을 정반대로 키 지정
- id 913 (FULLSTACK): 정규화를 선호할 상황을 묻고 비정규화 선호 조건을 키 지정
- id 1205 (DATA_AI): numpy axis 0 을 「열 방향」으로 키 지정
- id 585 (SPRING): 코드에 없는 @Transactional 을 전제로 「정상 동작」을 키 지정

## 재작성 183건 (2026-08-22 완료)

WRONG_KEY 를 제외한 확정 결함 183건(MULTIPLE_CORRECT 98 · FACTUALLY_WRONG 59 ·
AMBIGUOUS 26)을 전량 재작성해 운영 DB 에 적용했다.

- **파이프라인**: 재작성 에이전트 13배치 → 프로그램 게이트(스키마·4보기·정답 인덱스·
  보기 중복·최장보기=정답 45.9% < 60%) → **적대 검증 에이전트 13배치**(단일 정답·
  사실성·결함 해소·자립성, 반박 우선) → 컨트롤러 표본 12건 층화 직접 판정(12/12 수용).
- 적대 검증이 잡은 실결함 1건(id 1299: import 누락으로 실행 불가 코드 — 원본부터
  있던 결함을 재작성이 방치)은 교정 후 재판정.
- **적용**: 조건부 UPDATE(`id + 기존 content 의 md5` 일치 시에만) **183/183 적중**,
  적용 후 재덤프 전수 대조 **mismatch 0** (content·options·answer_key 모두 일치).
- 원칙: 주제·태그·난이도·유형 보존 최소 수정, 정답이 최장 보기가 되는 편향 회피
  (08-14 「정답=최장보기 73%」 사고 재발 방지).

## 시드 원본 교정 (2026-08-22 완료)

1. **shared**: `V202608221001__correct_question_bank_accuracy.sql` (PR #73 develop 머지,
   et11 릴리스에 탑재). 6트랙 155건을 md5(content) 매칭으로 교정 + 0단계 CRLF→LF
   정규화. 버전 0.0.1-et11.20260822 로 올리고 불변 게시 스펙 재산정
   (jar 1_229_362/4ea08b9f…). 검증 의미론 = 「옛 3중(content md5·options·answer_key)
   잔존 시 실패」 — md2 시드 계열 개발 DB 의 변형 행 때문에 존재 검증은 부당 실패.
2. **learning-svc**: `db/seed/question_bank_md2_seed.sql` 전체본 237건 교정
   (PR #56 develop 머지). NODE_TYPESCRIPT·DATA_AI 2트랙의 시드 정본.

★교훈: shared `.gitattributes` 의 `/src/main/resources/** text eol=crlf` 는 CI(리눅스)
체크아웃도 CRLF 로 물질화한다 — 여러 줄 문자열 리터럴을 담는 마이그레이션은
per-file `eol=lf` 핀 필수(선례 V202608161009·1011). 그리고 스테이지드 마이그레이션
테스트의 부분 스키마 때문에 데이터 마이그레이션은 `to_regclass` 가드 필수.★

## 생성 게이트 사실 검증 축 (2026-08-22 완료)

learning-svc PR #57 로 구현·머지. 요지:

- **검증 장부** `question_verifications.jsonl` — 문항별 fingerprint(track·content·
  options·정답의 sha256) + PASS 판정 + 검증 축(FACT/SINGLE_KEY/SELF_CONTAINED) +
  리뷰어. 채점 필드가 바뀌면 fingerprint 가 어긋나 **리뷰 루프 없는 추가·수정이
  구조적으로 불가**(`stampQuestionVerifications` 로만 갱신, git diff 로 감사).
- **CI 강제** `ApprovedQuestionsGateTest` — ①전 게이트+사실 검증 ②커밋된 시드 SQL
  4곳 == 승인 JSONL 결정적 재생성본. 종전에는 validateQuestions 가 수동 태스크뿐이라
  「CI validates committed JSONL」이 선언만 있었다.
- **승인 JSONL 에 검수 교정 237건 반영** 후 정식 경로로 시드 재생성 — 시드 직접
  교정(#56)이 남겼던 「재생성 시 교정 되돌아감」 회귀 경로를 닫음.
- 리뷰 프롬프트를 적대(반박 우선) 프레임으로 강화(복수 정답 논증·코드 실행 검증·자립성).
- **게이트 실효 실증**: 도입 즉시 duplicate-option-set 게이트가 재작성 1건(id 811)과
  기존 823의 보기 집합 충돌을 적발 → Summary→Untyped 교정(운영 UPDATE 1건 적중,
  shared V202608221001 도 동기 갱신 = shared PR #74).

## 잔여 작업

1. 전체 결함 목록: `2026-08-22-question-bank-defects.json` (237건, id·트랙·유형·근거)

## 자료

- 결함 전량: `docs/reports/2026-08-22-question-bank-defects.json`
- 적용된 키 교정 SQL: `docs/reports/2026-08-22-question-bank-key-fixes.sql`
  (조건부 UPDATE — 재실행 시 이미 교정된 행은 건드리지 않음)
- 적용된 재작성 SQL: `docs/reports/2026-08-22-question-bank-rewrites.sql`
  (183건, `id + 기존 content md5` 조건부 — 재실행 시 이미 재작성된 행은 건드리지 않음)
