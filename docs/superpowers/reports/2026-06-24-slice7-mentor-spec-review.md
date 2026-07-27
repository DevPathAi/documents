# 설계서 검토 보고 — MD3 슬라이스 #7 AI 멘토 (2026-06-24)

> 한 줄 요약: 실측 정확성은 대체로 높고(주요 주장 90%+ 코드 일치) anthropic-java 스트리밍 API도 jar에 실재함이 확인됨. 다만 **프론트 SSE 에러/kill-switch 계약이 현 구현과 비정합**(현재는 throw된 stream error로만 처리, 설계서의 in-band `event:error`는 onData로 흘러 무력)이라는 **Critical** 결함이 있다. 이 1건과 Important 몇 건을 수정하면 채택 가능.

검토자: 시니어 아키텍트(코드 실측 기반). 검토 대상: `documents/docs/superpowers/specs/2026-06-24-md3-slice7-ai-mentor-design.md`. 비교 기준 = 실제 레포 코드(ai-svc·frontend·sandbox-svc·learning-svc·gateway·shared) 및 Gradle 캐시 SDK jar.

---

## Critical

### C-1. 프론트 kill-switch/error 처리는 "기존 처리와 연결"되지 않는다 — in-band `event:error`는 현재 무력화된다
[근거: `devpath-frontend/apps/web/test/features/mentor/mentor_controller_test.dart:42-54` + `devpath-frontend/packages/dp_core/lib/src/sse/sse_client.dart:40-61` + `devpath-frontend/apps/web/lib/src/features/mentor/application/mentor_controller.dart:50-75`]

설계서 §1.2 DoD(라인 39)·M-2(라인 90)·§7은 "`event:error`(KILL_SWITCH)→프론트 `isKillSwitch`(기구현)와 연결된다"고 단언한다. 그러나 실측상:

- 현재 멘토의 kill-switch 경로는 **스트림이 `ApiException`을 throw**할 때만 동작한다(컨트롤러 `onError`에서 `err is ApiException && err.isKillSwitch` 분기). 테스트가 이를 못박는다: KILL_SWITCH 케이스를 `Stream<SseEvent>.error(ApiException(code: aiKillSwitchActive))`로 모사한다(라인 42-47). 즉 **HTTP 에러 응답(비-200)**을 dio가 `ApiException`으로 정규화→stream error로 전파하는 경로다.
- 반면 `SseClient.connect()`는 일단 200 스트림이 열리면 `event:`/`data:` 라인을 파싱해 **모든 이벤트를 `SseEvent`로 onData에 yield**한다(라인 44). `event:error data:{code}` 프레임은 throw되지 않고 **토큰과 같은 경로로 `onData`에 도착**해, 현 컨트롤러 로직상 채팅 버블 텍스트로 append되어 버린다(`m[targetIndex].append(e.data)`). `isKillSwitch`는 영원히 발화하지 않는다.

설계서의 M-1은 멘토를 "동기 요청 → 그 자리에서 200 SSE 스트림"으로 규정하므로, kill-switch/quota가 **스트림 도중**에 결정되면 in-band `event:error`로 보낼 수밖에 없다(헤더 flush 후 상태코드 변경 불가). 결국 **현 프론트 계약과 정면 충돌**한다. 설계서는 M-2 라인 88에서 "references/done/error는 프론트 신규 처리"라고는 적었으나, **동시에 DoD·§7·리스크표에서 "기존 isKillSwitch와 연결"이라고 모순되게 기술**해 실제 필요한 F 빌드 작업량(이벤트 프레임→상태 매핑 신규 구축)을 과소평가한다.

권고: 빌드 F 범위에 **"`mentor_sse_source`/컨트롤러가 `event:error` 프레임을 파싱해 code별 상태(killSwitch/failed)로 매핑하는 신규 로직"**을 명시하고, DoD·§7의 "기존 처리와 연결" 문구를 "신규 매핑 추가"로 정정하라. 기존 `Stream.error` 기반 테스트는 그대로 두되 **in-band `event:error` 프레임을 받는 신규 실패 테스트**를 DoD에 추가하라. (대안: 스트림 시작 *전* kill-switch가 확정되는 경우는 200을 열기 전에 비-200으로 거부 → 이 경우만 기존 경로 재사용 가능. 두 경로를 설계서가 구분해야 한다.)

---

## Important

### I-1. webmvc `SseEmitter` + 별도 스레드 LLM 스트림 — 함정이 항목만 나열되고 구체 설계가 비어 있다
[근거: 설계서 M-1(라인 78)·리스크표(라인 225) + `devpath-ai-svc/build.gradle.kts:31`(webmvc)]

스택이 webmvc(블로킹)임은 실측 확인(`spring-boot-starter-webmvc`). 설계서는 "별도 스레드에서 LLM 스트림을 받아 emitter로 흘린다 / 스레드풀·타임아웃·생명주기(complete/error/onTimeout) 명시"라고 **해야 할 일을 적었으나 그 명시 자체가 본문에 없다**. 구체 누락:
- emitter **타임아웃 기본값**(미설정 시 Spring MVC async 기본 타임아웃에 걸려 LLM 장기 스트림이 잘릴 수 있음) 미규정.
- 스트림을 흘리는 **스레드풀의 정체·크기**(전용 `TaskExecutor` vs 공용) 미규정 — 동시 멘토 세션이 스레드를 점유하는 백프레셔 모델 부재.
- `IOException`(클라이언트 조기 종료)·`AsyncRequestTimeoutException` 시 LLM 스트림 **취소/리소스 해제** 경로 미규정(누수 위험).

권고: 빌드 D 명세에 emitter 타임아웃 값·전용 executor·클라이언트 끊김 시 LLM 스트림 취소를 **구체 수치/클래스로** 박아라(추측 방지). study-documents의 Spring Boot 4 SSE 샘플을 1급 참조로 명시.

### I-2. `references` 이벤트가 frontend `SseClient`/컨트롤러에 미지원 — token-only 누적 모델과 충돌
[근거: `devpath-frontend/apps/web/lib/src/features/mentor/application/mentor_controller.dart:50-55` + `mentor_sse_source.dart:13-39`]

현 컨트롤러는 **이벤트 종류를 구분하지 않고** 모든 `SseEvent.data`를 마지막 버블에 append한다(`event` 필드를 보지 않음). 따라서 `event:references data:[{...}]` 프레임도 그대로 채팅 버블에 JSON 문자열로 들어간다. 설계서 §5(라인 170)·F 빌드는 "references 처리·패널 렌더"를 적었으나, 그 전제로 **컨트롤러가 `e.event`로 분기(token vs references vs done vs error)하도록 재작성**해야 함이 빌드 F 명세에 더 분명히 박혀야 한다(현재는 "필드 추가" 수준으로만 기술).

권고: 빌드 F에 "컨트롤러를 `e.event` 스위치 기반으로 재구성(token→append, references→state.references, done→idle+sessionId, error→code 매핑)"을 명시. 기존 token-only 누적 테스트(`mentor_controller_test.dart:17-36`)가 깨지지 않도록 회귀 포함.

### I-3. body 필드 전환(`fromStep`→`contentId`)의 잔여 시그니처 정리가 모호
[근거: `mentor_sse_source.dart:10-11,36-39`]

현 mock/실서버 호출은 `body:{'message':question,'fromStep':fromStep}`이고 `typedef MentorSseConnect`가 `{int fromStep}`을 갖는다. 설계서 §2.2·M-2·범위외(라인 47)는 "`fromStep` 시그니처 자리는 보존, 서버는 전량 재전송"이라 했다. 그러나 새 body는 `{message, contentId?}`(M-2)라서 **`fromStep`을 body에서 빼고 `contentId`를 넣는 변경**과 "시그니처 자리 보존"이 충돌 소지가 있다(typedef는 `fromStep` 유지하되 wire body에서는 제거?). 명세가 둘을 명확히 구분하지 않는다.

권고: 빌드 F에 "wire body는 `{message, contentId?}`로 교체(`fromStep`은 body에서 제거), `MentorSseConnect` typedef의 `fromStep` 파라미터는 미사용으로 보존(재개 후속 자리)"를 한 문장으로 못박아라.

### I-4. `ContentEmbeddingMatcher` track 완화(`matchAny`)의 정확도 저하가 과소 논의
[근거: `devpath-learning-svc/src/main/java/ai/devpath/learning/path/ContentEmbeddingMatcher.java:15-32`]

실측: `match(track, queryEmbedding, limit)`는 `c.track = ?`가 **필수**다(WHERE 절). 설계서 M-4·빌드 C는 track 조건을 제거한 `matchAny(queryEmbedding, limit)`를 신규 노출한다 — 구현 가능성은 정당(단순히 track 술어 제거). 그러나 **track 무관 전체 PUBLISHED 검색**은 멘토 질문이 특정 트랙 맥락일 때 **타 트랙 콘텐츠가 상위로 섞일** 정확도 리스크가 있는데, 설계서는 이를 "track 무관" 한 줄로만 처리한다. contentId가 있을 때(현재 콘텐츠의 track을 알 수 있음)는 track 필터를, 없을 때만 `matchAny`를 쓰는 **2-경로**가 품질상 우월하나 미검토.

권고: M-4에 "contentId로 현재 콘텐츠 track 확보 시 track 필터 우선, 미상일 때만 matchAny" 옵션을 최소한 트레이드오프로 기록(컷해도 되지만 의식적으로). 정확도 회귀는 빌드 C 테스트의 단언 범위에 포함.

### I-5. learning 내부 콘텐츠 조회 라우트가 "(필요 시)"로 흐릿 — ai-svc가 사용자 JWT를 전달 못 하는 구조적 사실과 충돌
[근거: `devpath-learning-svc/src/main/java/ai/devpath/learning/content/ContentController.java:17-21`(`/contents/{idOrSlug}`는 `@AuthenticationPrincipal Jwt` 필수) + 설계서 §5 라인 162 "(필요 시)"]

실측: 기존 콘텐츠 조회 `GET /contents/{idOrSlug}`는 **JWT 사용자 컨텍스트 필수**(OWNER 의미 포함). M-3는 ai-svc가 내부 호출(게이트웨이 미경유, 사용자 JWT 없음)로 콘텐츠 본문을 가져온다고 했다. 그렇다면 **내부 무인증 콘텐츠 조회 경로가 필수**인데 설계서는 "(필요 시) … 검토"로 약하게 적어 빌드 C 범위에서 빠질 위험이 있다. context_snapshot에 "현재 콘텐츠" 주입은 DoD(라인 34) 필수 항목이므로 이 내부 라우트는 **선택이 아니라 필수**다.

권고: §5/빌드 C에서 "`GET /internal/contents/{id}`(JWT 불요, 본문 요약 반환) 신규는 필수"로 승격. ai-svc `SecurityConfig`가 learning 쪽이 아닌 점에 유의(노출은 learning-svc SecurityConfig 인가 정책 추가 동반).

### I-6. 멘토 인가가 ai-svc `SecurityConfig` 변경을 요구하나, 기존 `/ai/**` permitAll과의 경계가 미명시
[근거: `devpath-ai-svc/src/main/java/ai/devpath/aigw/config/SecurityConfig.java:40-45`]

실측: ai-svc는 `/actuator/health`·`/ai/**` permitAll + `anyRequest().authenticated()`. 설계서 M-9·§5는 "`/ai-mentor/**` 인가 추가"라 했고 이는 `anyRequest().authenticated()`로 이미 커버된다(별도 추가 불요일 수 있음). 그러나 멘토가 사용하는 learning 유사검색·콘텐츠 조회를 ai-svc가 호출할 때, **ai-svc→learning 내부 경로**는 learning의 `/internal/**`가 무인증인지(현 sandbox `/internal/**`는 SecurityConfig 미적용 또는 permitAll 여부) 설계서가 단언하지 않는다. sandbox `InternalSessionController`는 인증 데코레이터가 없으나 그 무인증 보장은 sandbox SecurityConfig에 달려 있다(본 검토 범위 밖이라 미확인 — 설계서도 미확인).

권고: 빌드 C/D에서 "learning `/internal/contents/**`는 무인증(내부 전용) — SecurityConfig 인가 명시"를 **추측 금지** 차원에서 박아라. ai-svc 쪽 `/ai-mentor/**`는 `anyRequest().authenticated()`로 충분함을 확인했으면 "추가 불요"로 정정(현 문구는 불필요한 변경을 암시).

### I-7. 스코프: Tier-2 단일 슬라이스에 6빌드(A~F) + 신규 LLM 스트리밍 추상화 3종은 과중 — 컷 후보 명시 필요
[근거: 설계서 §9 + 로드맵 `documents/17_스케줄.md:138-140`, 181]

로드맵 §138-140은 슬라이스 #7을 `ai_mentor_sessions`+context_snapshot(콘텐츠+최근5 sandbox)+SSE+참고자료+프론트 SSE 전환으로 규정 — **설계서가 스코프를 발명하지 않음은 확인**(좋음). 그러나 Tier-2는 "여유 시·지연 시 이연"(라인 181) 등급인데 6빌드 + 스트리밍 provider 3종(Claude/Ollama/Mock)은 Tier-1 슬라이스 #6과 동급 규모다. 품질·일정 리스크 관점에서 **컷 가능 항목**을 설계서가 선제 식별하지 않았다.

권고(컷 후보, 채택 시 명시):
- **참고자료(references)**: DoD 필수이나 로드맵에서도 "링크"로 가장 가볍다. **빌드 C(learning `matchAny`+`/internal/contents/similar`)와 references 이벤트를 후행 슬라이스로 분리** 가능 — 멘토 핵심(스트리밍 답변)은 references 없이 성립. MVP-of-MVP로 토큰 스트림+context_snapshot까지만 1차, references 2차.
- **Ollama 스트리밍**: dev 편의용. CI는 Mock으로 충분하므로(설계서도 CI=Mock), Ollama 스트리밍 구현을 후행으로 미루고 1차는 Claude(운영)+Mock(CI)만으로 출발 가능.
설계서 §9/리스크표에 "여유 부족 시 references·Ollama 스트리밍을 컷"을 컷라인으로 추가 권고.

---

## Minor

### M-1. anthropic-java 2.34.0 스트리밍 API는 jar에 **실재** — "미확인" 표현은 완화 가능(단, 정확 시그니처는 구현 시 확인 유지)
[근거: Gradle 캐시 `com.anthropic/anthropic-java-core/2.34.0` jar 내 `com/anthropic/services/blocking/MessageService.class`, `com/anthropic/core/http/StreamResponse.class`, `com/anthropic/models/messages/RawMessageStreamEvent.class` 존재 + `ClaudeAiReviewClient.java:46`(현재 `messages().create()` 블로킹 사용)]

설계서 M-5·리스크표는 `messages().createStreaming()`을 "또는 stream helper / 구현 시 검증"으로 적절히 헤지했다. 실측상 **블로킹 `MessageService`에 streaming 경로와 `StreamResponse<RawMessageStreamEvent>` 타입이 jar에 존재**하므로, "SDK 미확인" 수준의 불확실성은 아니다(API 존재는 확정). 다만 정확한 메서드명/델타 텍스트 추출(`RawMessageStreamEvent`의 content_block_delta → text) 형태는 구현 시 확인이 맞다.

권고: 리스크표 라인 224를 "anthropic-java 2.34.0에 blocking 스트리밍 API(`StreamResponse<RawMessageStreamEvent>`) 존재 확인됨 — 델타 텍스트 추출 형태만 구현 시 검증"으로 정밀화. 과한 불확실성 제거.

### M-2. 프론트 멘토 파일 경로가 설계서 §2.2/§11 표기와 불일치(중첩 디렉터리)
[근거: 실제 경로 `devpath-frontend/apps/web/lib/src/features/mentor/{data,application,state,presentation}/*.dart`]

설계서는 `features/mentor/`에 `mentor_sse_source.dart` 등이 평면 배치된 것처럼 적었으나(라인 60-63, 236), 실제는 `data/`·`application/`·`state/`·`presentation/` 4계층 하위에 있다. 기능 정합성에는 영향 없으나 빌드 F 작업자가 경로를 잘못 잡을 수 있다.

권고: §2.2/§11 경로를 실제 4계층으로 정정(사소).

### M-3. sandbox "최근 N" 정렬 컬럼 — 인덱스는 `started_at DESC`인데 설계서는 `created_at DESC` 메서드명 제시
[근거: `devpath-shared/.../V202606221001__sandbox_sessions.sql:26`(`idx_sandbox_user_started ON sandbox_sessions(user_id, started_at DESC)`) + 설계서 §5 라인 157(`findTop5ByUserIdOrderByCreatedAtDesc`)]

`sandbox_sessions`의 사용자별 시간 인덱스는 `started_at DESC` 기준이다. 설계서 빌드 B의 예시 메서드는 `OrderByCreatedAtDesc`라 **기존 인덱스를 못 타고**(또는 `created_at`과 `started_at` 정렬 의미가 미세하게 다름) 풀스캔 정렬이 될 수 있다. "최근 실행"의 자연 키는 `started_at`(또는 `finished_at`)일 개연성이 높다.

권고: 빌드 B에서 정렬 컬럼을 `started_at DESC`(인덱스 정합)로 맞추거나, `created_at` 사용이 의도라면 그 근거를 명시. `SandboxSessionView`에 시간 필드가 없으므로(현재 id·userId·language·contentId·code·stdout·stderr·exitCode·status만, [근거: `SandboxSessionView.java:3-5`]) "최근순"은 리포지토리 정렬로만 보장되고 뷰에는 노출 안 됨 — 의도 확인 필요.

### M-4. context_snapshot/`reference_links` 데이터모델은 #6 규약과 정합 — 양호
[근거: `V202606231001__ai_code_reviews.sql:25-28`(인덱스 `(user_id, created_at DESC)`·`set_updated_at` 트리거·JSONB) 대비 설계서 §4]

`ai_mentor_sessions` §4의 `(user_id, created_at DESC)` 인덱스·`set_updated_at` 트리거·JSONB 기본값·CHECK·교차서비스 FK 금지·`references`→`reference_links` 컬럼명 회피는 모두 기존 마이그레이션 규약과 일치한다. 마이그레이션 번호 `V202606241001`은 현재 최댓값 `V202606231001` 다음으로 정확(실측). 이견 없음.

### M-5. CI Kafka 불요 주장 정합 — 양호
[근거: `build.gradle.kts:35-36,47`(spring-kafka 실재, 테스트에 spring-kafka-test) + 설계서 §0 라인 18·§8 라인 202]

ai-svc에 spring-kafka가 실재하나 그것은 코드리뷰(#6) Consumer 전용이고, 멘토는 동기 SSE라 Kafka 미사용이라는 설계서 주장은 타당. 단, ai-svc IT(`@SpringBootTest`)가 기동 시 **기존 Kafka 자동설정/Consumer 빈이 떠서** 멘토 테스트 컨텍스트에 영향이 없는지는 빌드 D에서 확인 필요(현 #6 테스트가 이미 처리했을 개연성 높음 — 본 검토 미확인).

---

## 종합 판정

**조건부 채택 가능.** 설계서의 실측 정확성은 높다 — ai-svc 스택(webmvc·anthropic-java 2.34.0·spring-kafka), 블로킹 LLM 사용처, 인젝션 델리미터 패턴, sandbox 단일 조회만·`ContentEmbeddingMatcher` track 필수·gateway 선언형 라우트(`anyExchange().authenticated()` 포함)·최신 마이그레이션 번호·데이터모델 규약이 모두 코드와 일치했고, 우려됐던 anthropic-java 스트리밍 API도 jar에 실재함을 확인했다. 설계 골격(M-1~M-9)과 스코프는 로드맵에 충실하며 발명이 없다.

그러나 **머지 전 반드시 수정해야 할 항목**이 있다:

1. **[C-1 필수]** 프론트 kill-switch/error 계약 모순 해소. DoD·§7·리스크표의 "기존 isKillSwitch와 연결" 문구를 삭제/정정하고, 빌드 F에 "**in-band `event:error` 프레임 → code별 상태 매핑 신규 구축**" + 신규 실패 테스트를 명시. (스트림 시작 전 거부는 비-200, 시작 후는 in-band — 두 경로 구분.)
2. **[I-2·I-3 필수]** 빌드 F에 "컨트롤러를 `e.event` 스위치 기반으로 재작성(token/references/done/error)" 및 "wire body `{message, contentId?}` 교체, `fromStep`은 typedef에만 보존"을 명문화.
3. **[I-5 필수]** learning **내부 무인증 콘텐츠 조회 라우트**를 "(필요 시)"에서 **빌드 C 필수**로 승격(context_snapshot 현재 콘텐츠 주입이 DoD 필수이므로).
4. **[I-1 권장]** 빌드 D에 SseEmitter 타임아웃·전용 executor·클라이언트 끊김 시 LLM 스트림 취소를 구체값으로 박기.
5. **[I-7 권장]** 컷라인(references·Ollama 스트리밍 후행 분리)을 §9에 선제 명시 — Tier-2 일정 리스크 흡수.

Minor(M-1~M-5)는 머지 차단 사유는 아니나 M-1(SDK 불확실성 정밀화)·M-2(경로)·M-3(정렬 컬럼)은 빌드 착수 전 1줄씩 정정 권장. 위 1~3을 반영하면 빌드 A(shared)부터 착수 가능하다.
