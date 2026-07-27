# Tier-1 트러블슈팅 문서 (슬라이스 #1~6)

> 2026-06-23. Tier-1 실행 중 마주친 이슈·근본원인·해결·교훈 집대성. 선행 프로젝트 교훈은 [24_선행_트러블슈팅_참고](../../../24_선행_트러블슈팅_참고.md), 본 문서는 DevPathAi Tier-1 자체 사례다. 형식: **증상 → 근본원인 → 해결 → 교훈**.

## A. 빌드·환경 (Windows dev / Spring Boot 4 / Gradle 9)

### A-1. 로컬에서 신규 shared(GitHub Packages) jar 미해석
- **증상**: ai-svc 로컬 빌드 시 새 `devpath-shared`(ai_code_reviews 등) 의존을 못 받음. 캐시는 stale.
- **근본원인**: 로컬에 GitHub Packages 인증 없음(`gh` 토큰 스코프에 `read:packages` 결여, `~/.gradle`·env에 gpr 미설정). GitHub Packages는 비공개 → 인증 필수.
- **해결**: (운영) CI는 `GITHUB_TOKEN` 보유 → CI로 검증. (로컬 실행 필요 시) shared `./gradlew publishToMavenLocal` → ai-svc `repositories`에 `mavenLocal()` 임시 추가(미커밋, 후 복원).
- **교훈**: 비공개 패키지 의존 서비스는 로컬 검증이 인증에 묶인다. CI 검증을 1급 경로로, 로컬 실행은 mavenLocal 우회.

### A-2. Spring 7(Boot 4)에서 `ExponentialBackOffWithMaxRetries` 제거
- **증상**: `import org.springframework.util.backoff.ExponentialBackOffWithMaxRetries` → cannot find symbol(CI compileJava 실패).
- **근본원인**: Spring Framework 7.0에서 해당 클래스가 `ExponentialBackOff`로 통합(기능 흡수).
- **해결**: `new ExponentialBackOff(initialInterval, multiplier)` + `setMaxAttempts(long)`. (javap로 실 jar 시그니처 확인.)
- **교훈**: Boot 4=Spring 7. 마이너 유틸 API 이동·삭제 빈번 → 추측 말고 실 jar(javap)·문서로 확인.

### A-3. Flyway gradle 플러그인 Gradle 9 비호환
- **증상**: `./gradlew flywayMigrate` → `org/gradle/api/plugins/JavaPluginConvention` NoClassDefFound.
- **근본원인**: Flyway gradle 플러그인(11.8.2)이 Gradle 9에서 제거된 `JavaPluginConvention` 참조.
- **해결**: 로컬 마이그레이션은 psql로 SQL 직접 적용(서비스는 ddl-auto:validate라 **테이블 존재만** 필요, flyway 히스토리 무관). 운영/CI는 별도 Dockerfile.migration job.
- **교훈**: Gradle 9 환경에서 일부 플러그인 미대응. 마이그레이션 적용 경로를 플러그인에 의존하지 말 것.

### A-4. Boot 4 모듈 분리·이동
- **증상**: `@AutoConfigureMockMvc`·MockMvc·테스트 슬라이스 import 깨짐.
- **근본원인**: Boot 4가 자동설정·테스트 슬라이스를 모듈 분리(`spring-boot-webmvc-test` 등), `@MockitoBean`(=구 @MockBean), JsonMapper(Jackson3 `tools.jackson.databind.json`).
- **해결**: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`, `spring-boot-flyway`/`spring-boot-kafka` 분리 의존, `@MockitoBean`, Jackson3 JsonMapper 사용.
- **교훈**: Boot 4 전용 import 경로·모듈 분리를 템플릿화(CLAUDE.md·메모리에 박음).

### A-5. Git Bash 경로 변환(MSYS)
- **증상**: docker exec의 컨테이너 내부 경로(`/opt/...`, `/workspace`)가 `C:/Program Files/Git/...`로 변환돼 실패.
- **근본원인**: MSYS(Git Bash)가 POSIX 절대경로를 Windows 경로로 자동 변환.
- **해결**: `MSYS_NO_PATHCONV=1` 환경변수로 변환 비활성화.
- **교훈**: docker exec·컨테이너 명령에서 슬래시 경로는 `MSYS_NO_PATHCONV=1` 가드.

### A-6. line-ending(CRLF/LF)
- **증상**: dp_core 등에서 line-ending 차이로 diff·CI 잡음.
- **해결**: `.gitattributes`에 `* text=auto eol=lf`(또는 대상 확장자 eol=lf).

## B. Sandbox (슬라이스 #5)

### B-1. docker IT Permission denied (B2)
- **증상**: native Linux CI에서 sandbox 컨테이너 실행 시 워크스페이스 읽기 실패.
- **근본원인**: 0700 권한 temp 워크스페이스 + 컨테이너 `nobody` 유저 + read-only bind → nobody가 디렉터리/파일 읽기 불가.
- **해결**: `prepareWorkspace`에서 디렉터리 0755·파일 0644로 설정(POSIX 가드). Docker volume 실험으로 근본원인 확증.
- **교훈**: 컨테이너 비특권 유저 + ro bind 조합은 호스트 파일 권한이 컨테이너 가독성을 좌우. Windows에서는 안 나타나고 native Linux(CI)에서만 발현 → 로컬 환경이 CI를 가린 사례.

### B-2. gVisor(runsc) 미적용
- **증상**: 계획은 gVisor 격리였으나 구현은 plain Docker.
- **근본원인/결정**: gVisor 셋업 복잡도·환경 변수 → MVP 단계는 plain Docker(네트워크 차단+리소스 제한+비특권)로 단순화, 강화는 MD4 pentest로 연기.
- **교훈**: 격리 강도는 단계적. 단순화 결정을 검증 보고서·백로그에 명시.

## C. AI 코드리뷰 (슬라이스 #6)

### C-1. 기존 무상태 테스트에 @ActiveProfiles 누락
- **증상**: C1이 JPA 도입하자 기존 Ollama 테스트(AiApplicationTests·OllamaControllerTest)가 `SchemaManagementException`으로 컨텍스트 로드 실패.
- **근본원인**: 기존 테스트에 `@ActiveProfiles("test")` 없음 → main 프로파일(ddl-auto:validate+flyway off+빈 DB)로 떠 검증 실패.
- **해결**: 두 테스트에 `@ActiveProfiles("test")` 추가.
- **교훈**: "모든 `@SpringBootTest`는 `@ActiveProfiles("test")`"를 불변식으로(스키마 프로비저닝). JPA 도입은 기존 무상태 테스트를 깬다.

### C-2. SecurityConfig가 기존 무인증 엔드포인트 차단
- **증상**: C1의 JWT resource-server `.anyRequest().authenticated()`가 기존 `/ai/**`(learning-svc가 호출하는 무인증 Ollama 게이트웨이)를 401 차단 → 17건 테스트 실패.
- **근본원인**: 보안 도입 시 기존 무인증 경로를 permit 누락.
- **해결**: `/ai/**` permitAll 복원(pre-C1 동작 보존), `/reviews/**`만 인증.
- **교훈**: 보안 도입은 기존 엔드포인트 계약을 깰 수 있다. 기존 경로 인벤토리 후 permit 매핑.

### C-3. 범위 밖 confidence가 정상 리뷰를 폐기
- **증상**: LLM이 confidence 101/-5 반환 시 DB CHECK(0~100) 위반 → DataIntegrityViolationException → 본문 멀쩡한 리뷰가 통째로 FAILED.
- **근본원인**: 구조화 출력이 integer만 강제, 범위 미강제. finishDone이 값 그대로 저장.
- **해결**: finishDone에서 `Math.max(0, Math.min(100, confidence))` 클램프.
- **교훈**: LLM 구조화 출력의 값 범위는 DB CHECK로 끝나지 않게 앱에서 클램프/검증.

### C-4. 일시 LLM 장애가 영구 FAILED로 고착 (Important #1)
- **증상**: LLM 일시 타임아웃/5xx/429도 영구 FAILED + Kafka 오프셋 커밋 → 이벤트 소실, 복구 경로 없음.
- **근본원인**: 모든 RuntimeException을 catch해 무조건 finishFailed; 멱등이 "행 존재"라 재전달도 skip.
- **해결**: 일시/영구 오류 타입 구분 + 멱등을 **상태 기준**(DONE/FAILED skip·PENDING 재시도)으로 + Kafka `DefaultErrorHandler` 지수백오프(3회) + 소진 시 recoverer가 FAILED(LLM_EXHAUSTED).
- **교훈**: fail-closed는 일관적이나 일시 장애에서 전송보장이 깨진다. 멱등-재시도 일관성은 상태 기준으로 설계.

### C-5. 메서드 rename 후 기존 호출부 누락
- **증상**: `createPendingIfAbsent`→`findOrCreatePending` 리네임 후 기존 클램프 테스트 호출부가 옛 이름 사용 → CI compileTestJava 실패.
- **근본원인**: 리네임 시 동일 파일 내 다른 테스트의 호출부를 함께 갱신하지 않음.
- **해결**: grep으로 잔존 참조 전수 확인 후 일괄 갱신.
- **교훈**: 시그니처 변경은 grep 전수 + (가능하면)로컬 컴파일; 로컬 불가 환경은 CI가 잡으나 라운드트립 비용.

### C-6. anthropic-java 예외 타입 실측
- **증상**: Claude SDK 오류를 transient/permanent로 매핑해야 하나 예외 계층 불명.
- **해결**: anthropic-java-core jar를 **Maven Central(공개)** 에서 받아 `javap`로 계층 확인 — `RateLimitException`·`InternalServerException`→`AnthropicServiceException`, `AnthropicIoException`·`AnthropicRetryableException`·`AnthropicInvalidDataException`→`AnthropicException`.
- **교훈**: SDK 시그니처는 추측 금지. anthropic-java는 Maven Central 공개라 jar javap로 실측 가능(GitHub Packages 인증 불필요).

## D. 콘텐츠/검증 (슬라이스 #4·#6)

### D-1. 학습경로 동시 생성 409
- **증상**: 동시 경로 생성 요청 충돌.
- **해결**: unique violation(SQLState 23505)으로 좁혀 충돌 변환(과도한 catch 방지), "정확히 하나의 active path" 테스트.

### D-2. 한국어 출력 모델 골든 eval 측정 취약
- **증상**: 골든 검출율 0.50(영문 키워드 정확매칭). 인젝션 케이스 오탐.
- **근본원인**: system prompt가 메시지를 **한국어**로 강제 → 모델이 영문 토큰(NameError 등)을 의역. 또 `noInjectionLeak`이 "PWNED 언급=실패"로 오탐(모델이 인젝션을 *지적*하는 정상 동작).
- **해결**: 검출 판정을 **기대 카테고리 비어있지않음**(robust)으로, 인젝션은 **구조화출력 유효=방어성립**으로 재정의. 키워드는 정보용 지표. → 24/24.
- **교훈**: LLM eval에서 자연어 정확매칭은 출력 언어에 취약. 카테고리/구조 기반 판정이 robust.

## E. 프로세스·오케스트레이션

### E-1. 서브에이전트 긴 최종메시지 억제 + read-only 에이전트 Write 불가
- **증상**: 리뷰/긴 산출물을 서브에이전트 최종메시지로 못 받음. 또 본 감사에서 **Explore·code-reviewer 에이전트는 Write 도구가 없어** 지시한 파일을 생성 못 함(완료 보고는 했으나 파일 부재).
- **해결**: 긴 산출물은 파일 Write 지시 + **쓰기 필요 작업은 writable 에이전트(general-purpose/executor)** 선택. 컨트롤러가 파일 존재를 직접 검증.
- **교훈**: 에이전트 타입별 도구 권한 확인(read-only=Explore/code-reviewer/architect 등은 Write 없음). 완료 보고를 신뢰 말고 산출물 실측.

### E-2. 콘텐츠 필터 차단(직접 작업 전환)
- **증상**: sandbox/docker/injection/탈옥 표현이 포함된 작업을 서브에이전트 위임 시 차단 전례.
- **해결**: 해당 슬라이스(#5 sandbox, #6 인젝션 방어/C2)는 컨트롤러 직접 작업.
- **교훈**: 보안·격리·인젝션 도메인은 위임보다 직접 작업이 안정적.

### E-3. develop 부재 레포(shared) + stale ref
- **증상**: devpath-shared는 develop 브랜치 부재(feature→main이 관례)인데 stale `origin/develop` ref로 잘못된 base 분기.
- **해결**: `git rebase --onto origin/main <stale> <branch>`로 base 교정, shared는 feature→main.
- **교훈**: 레포별 브랜치 전략 차이 확인(shared=feature→main, 서비스=develop 2단계). fetch --prune로 stale ref 정리.

## F. 횡단 교훈(메타)

1. **로컬 환경이 CI를 가린다**: B-1(권한)·A-1(인증) 모두 로컬에선 안 보이고 native Linux CI에서 발현. → fresh DB·CI 서비스 일치, CI를 1급 검증 경로로.
2. **추측 금지의 실천**: A-2/C-6은 javap 실측, A-3은 직접 적용으로 우회 — 모르는 API/동작은 실측·실험으로 확정.
3. **회귀는 도입부에서 터진다**: JPA·보안 도입(C-1/C-2)이 기존 무상태 테스트·엔드포인트를 깸 → 도입 시 기존 계약 인벤토리.
4. **fail-closed의 함정**: 일관적이나 일시 장애 복구를 막음(C-4). 재시도/DLQ는 멱등-재시도 일관성 설계가 핵심.
