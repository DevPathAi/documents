# AI 코드리뷰 일시 장애 복구(재시도 + DB 종료) 설계서

> 슬라이스 #6 최종 코드리뷰 **Important #1** 해소. 대상 레포: `devpath-ai-svc` 단독. 마이그레이션 변경 없음.

**Goal:** AI 코드리뷰 파이프라인에서 LLM(Ollama/Claude)의 **일시적** 장애(타임아웃·5xx·레이트리밋)가 영구 FAILED로 고착되고 Kafka 오프셋이 커밋되어 이벤트가 소실되는 갭을, **일시/영구 오류 구분 + Kafka 백오프 재시도 + 소진 시 DB 종료 + error_code 세분화**로 해소한다.

## 배경(문제)

현재 `ReviewService.reviewRun`은 모든 `RuntimeException`을 잡아 무조건 `finishFailed(reviewId, "LLM_FAILED")` 후 정상 리턴한다. 그 결과:
1. LLM의 일시적 타임아웃·5xx·429도 **영구 FAILED**가 된다.
2. `@KafkaListener`가 정상 종료해 **오프셋이 커밋**되어 이벤트가 영구 소실된다.
3. PENDING(→FAILED) 행이 이미 있어 재전달돼도 멱등 skip → **복구 경로 없음**.

`OllamaAiReviewClient`는 내부 1회 retry(ContractException 한정)뿐, `ClaudeAiReviewClient`는 retry가 전혀 없다.

## 확정 결정(brainstorming)

- **복구 깊이 = 재시도 + DB 종료**(별도 DLT 토픽 없음). DB의 `FAILED(LLM_EXHAUSTED)` 행이 dead-letter 기록 겸 배치 재처리 훅. 인프라 최소.
- **sandbox-svc 일시 다운 = 즉시 종료 유지**(터미널 FAILED, `SANDBOX_UNAVAILABLE`). 재시도는 finding 범위인 **LLM 호출 일시 오류에만** 적용. 스코프 타이트.

## 핵심 원리

멱등 skip을 **행 존재**가 아니라 **행 상태(status)** 기준으로 전환한다.
- `DONE`/`FAILED`(터미널) → skip(진짜 중복 또는 소진 후 재전달).
- `PENDING` → 재시도(일시 오류가 남긴 행을 재처리; reviewId 재사용).

일시 LLM 오류는 PENDING을 **남긴 채** 예외를 재던져 Kafka `DefaultErrorHandler`가 지수 백오프 재시도하고, 소진 시 recoverer가 `FAILED(LLM_EXHAUSTED)`로 종료한다. 영구 오류(파싱 실패·ownership·sandbox)는 즉시 `finishFailed`(정상 리턴 → 오프셋 커밋 → 재시도 없음).

## 컴포넌트 / 데이터 흐름

### ① 오류 분류(신규 예외, `ai.devpath.aigw.review` 패키지)

- `TransientReviewException extends RuntimeException` — 재시도 대상. `errorCode`(LLM_TIMEOUT/LLM_5XX/LLM_RATELIMIT) 보유.
- `PermanentReviewException extends RuntimeException` — 즉시 종료. `errorCode`(PARSE_FAILED) 보유.
- `SandboxUnavailableException`(기존) — 즉시 종료(`SANDBOX_UNAVAILABLE`).

### ② LLM 클라이언트 매핑

- **OllamaAiReviewClient**: `ResourceAccessException`(타임아웃/커넥션)→`TransientReviewException(LLM_TIMEOUT)` · `RestClientResponseException` 5xx→`TransientReviewException(LLM_5XX)` · 429→`TransientReviewException(LLM_RATELIMIT)` · JSON 파싱 실패/빈 응답→`PermanentReviewException(PARSE_FAILED)`. **내부 1회 retry 제거**(Kafka 재시도로 일원화).
- **ClaudeAiReviewClient**: `client.messages().create(...)`를 try/catch로 감싸 anthropic-java 예외를 매핑 — RateLimit(429)→`TransientReviewException(LLM_RATELIMIT)` · 5xx/서버오류/커넥션·읽기 타임아웃→`TransientReviewException(LLM_5XX 또는 LLM_TIMEOUT)` · 그 외 비-일시 오류(4xx 인증 등 + 응답 비정상)→`PermanentReviewException(PARSE_FAILED)`(설정성 4xx는 운영 배포 시 검출되는 희소 케이스라 PARSE_FAILED로 통합). **⚠️ 구현 시 anthropic-java 2.34.0의 예외 타입(`com.anthropic.errors.*`: 예 `RateLimitException`·`InternalServerException`·`AnthropicServiceException` 등)을 실측 확인 후 매핑**(추측 금지; claude-api 스킬 Java 문서·SDK 소스).

### ③ `ReviewService.reviewRun`(상태 기준 멱등 + 분류)

```java
AiCodeReview review = persistence.findOrCreatePending(sandboxSessionId, userId, contentId);
if ("DONE".equals(review.getStatus()) || "FAILED".equals(review.getStatus())) {
  return; // 터미널 → 멱등 skip
}
long reviewId = review.getId();
try {
  SandboxSessionView session = sandboxClient.getSession(sandboxSessionId);
  if (session.userId() == null || session.userId() != userId) {
    persistence.finishFailed(reviewId, "OWNERSHIP_MISMATCH");
    return;
  }
  ReviewResult result = aiReviewClient.review(new ReviewInput(
      session.language(), session.submittedCode(), session.stdout(), session.stderr(), session.exitCode()));
  persistence.finishDone(reviewId, result, aiReviewClient.providerName());
} catch (TransientReviewException e) {
  throw e; // PENDING 유지 → DefaultErrorHandler 재시도
} catch (PermanentReviewException e) {
  persistence.finishFailed(reviewId, e.errorCode());
} catch (SandboxUnavailableException e) {
  persistence.finishFailed(reviewId, "SANDBOX_UNAVAILABLE");
}
```

### ④ 영속 변경(`ReviewPersistenceService`)

- `findOrCreatePending(sid, userId, contentId)` → `AiCodeReview`(기존 행 또는 신규 PENDING; 절대 empty 아님). UNIQUE 경합은 `DataIntegrityViolationException` 흡수 후 재조회. **기존 `createPendingIfAbsent`(Optional 반환) 대체.**
- `markExhausted(sid)` → 해당 세션의 PENDING 행을 `FAILED(LLM_EXHAUSTED)`로(이미 터미널이면 무변경). recoverer 전용.
- `finishDone`/`finishFailed`는 기존 유지(finishDone의 confidence [0,100] 클램프 포함).

### ⑤ Kafka 에러 핸들러(신규 `ReviewKafkaConfig`)

- `@Bean DefaultErrorHandler`: `ExponentialBackOff`(initialInterval 1s, multiplier 2.0, maxRetries 3 → 1s·2s·4s) + recoverer. Spring Boot `KafkaAutoConfiguration`이 `CommonErrorHandler` 빈을 기본 컨테이너 팩토리에 자동 주입.
- **Recoverer**(소진 시 `(ConsumerRecord, Exception)`): payload 역직렬화 → `sandboxSessionId` → `persistence.markExhausted(sid)`로 `FAILED(LLM_EXHAUSTED)`. 이후 오프셋 커밋(이벤트 종료). PENDING 고아행 방지.
- 리스너 밖으로 나가는 예외는 `TransientReviewException`뿐(영구 오류는 내부 `finishFailed` 후 정상 리턴)이므로 핸들러는 그것만 재시도. 역직렬화 실패는 기존 `ReviewConsumer`의 poison-skip(catch→warn→return) 유지.

### ⑥ error_code 집합(`ai_code_reviews.error_code` VARCHAR(32), 기존 컬럼 재사용)

`LLM_TIMEOUT` · `LLM_5XX` · `LLM_RATELIMIT` · `PARSE_FAILED` · `OWNERSHIP_MISMATCH` · `SANDBOX_UNAVAILABLE` · `LLM_EXHAUSTED`. (마이그레이션 변경 없음 — 컬럼은 자유 문자열, CHECK 없음.)

## 오류 처리 매트릭스

| 오류 | 분류 | reviewRun 동작 | 최종 상태 |
|---|---|---|---|
| LLM 타임아웃 | Transient | re-throw | 재시도→성공 시 DONE / 소진 시 FAILED(LLM_EXHAUSTED) |
| LLM 5xx | Transient | re-throw | 〃 |
| LLM 429 | Transient | re-throw | 〃 |
| LLM 응답 파싱 실패 | Permanent | finishFailed | FAILED(PARSE_FAILED) |
| ownership 불일치 | (검증) | finishFailed | FAILED(OWNERSHIP_MISMATCH) |
| sandbox 조회 실패 | 터미널 | finishFailed | FAILED(SANDBOX_UNAVAILABLE) |
| 역직렬화 실패 | poison | listener skip | (행 미생성) |

## 테스트(TDD)

- **ReviewServiceTest**:
  - `transientLlmFailureRethrowsAndKeepsPending`: aiReviewClient가 TransientReviewException → reviewRun이 재던지고 행은 PENDING 유지(FAILED 아님).
  - `permanentLlmFailureMarksParseFailed`: PermanentReviewException → FAILED(PARSE_FAILED).
  - `sandboxFailureMarksFailed`(기존): error_code 단언을 `SANDBOX_UNAVAILABLE`로 갱신.
  - `ownershipMismatchFails`(기존): 유지.
  - `duplicateEventIsIdempotent`(기존, DONE→skip): 유지.
  - `pendingRedeliveryIsRetried`(신규): PENDING 행 존재 + mock LLM 성공 → 재시도되어 DONE.
- **에러 핸들러 IT**(EmbeddedKafka): 항상 TransientReviewException 던지는 mock AiReviewClient → 이벤트 발행 → N회 재시도 후 `await` FAILED(LLM_EXHAUSTED).
- **OllamaAiReviewClientTest**: MockWebServer로 5xx→Transient(LLM_5XX) · 429→Transient(LLM_RATELIMIT) · 깨진 JSON→Permanent(PARSE_FAILED) 매핑. 기존 정상경로 유지.
- **ClaudeAiReviewClientTest**: SDK 예외→Transient/Permanent 매핑(가능한 단위 수준; 실호출 없음).

## 제약 / 비범위

- ai-svc는 로컬에 GitHub Packages 인증이 없으면 빌드 불가 → **CI(GITHUB_TOKEN)로 검증**. develop에서 fix 브랜치 분기, develop으로 PR.
- **마이그레이션 변경 없음**. 비밀값(ANTHROPIC_API_KEY) 커밋 금지.
- **비범위**: sandbox 다운 재시도(즉시 종료 유지), 별도 DLT 토픽/컨슈머, stale PENDING 청소 배치(별도 백로그), 골든50 확장.
- 멱등성 핵심 불변식: 동일 sandbox_session_id에 리뷰 1행(UNIQUE) 유지. 상태 기준 skip이 중복 생성을 막음(`duplicateEventIsIdempotent`로 회귀 방지).
