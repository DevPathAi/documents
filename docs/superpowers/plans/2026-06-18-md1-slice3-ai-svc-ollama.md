# 슬라이스 #3 빌드 B — devpath-ai-svc Ollama 게이트웨이 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-ai-svc`를 슬라이스 #3 학습경로 생성을 위한 무상태 로컬 Ollama 게이트웨이로 완성한다. API는 `POST /ai/embed`, `POST /ai/path/generate` 두 개이며, CI는 실제 Ollama를 호출하지 않고 MockWebServer 계약 테스트로만 검증한다.

**Architecture:** ai-svc는 DB/JPA/Kafka/Redis 없이 Spring WebMVC + RestClient만 사용하는 stateless AI Gateway다. `/ai/embed`는 Ollama `/api/embed`에 `nomic-embed-text` 배치 입력을 위임하고 768차원을 fail-fast 검증한다. `/ai/path/generate`는 Ollama `/api/chat`에 `stream:false`, JSON schema `format`, `temperature:0.2`를 포함해 호출하고, `message.content` 문자열을 2단계 JSON 파싱해 strict DTO로 정규화한다. 모든 downstream learning-svc 호출은 이 gateway만 바라본다.

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · Spring Web MVC · RestClient · Jackson 3 `JsonMapper` · JUnit 5 · MockWebServer · Ollama dev runtime(`nomic-embed-text`, `qwen2.5:7b`).

## Global Constraints

- 레포 절대조건: 추측 금지 · **테스트 우선** · 문제 시 코드 분석. (`devpath-ai-svc/CLAUDE.md`)
- 브랜치 전략: develop 분기 → develop PR, CI 녹색 후 merge commit. main 직접 금지.
- **범위:** 빌드 B만 수행한다. shared pgvector 스키마(A), learning 경로 엔진(C), platform DONE(D), gateway/frontend(E)는 범위 밖이다.
- **API prefix:** 슬라이스 #1/#2와 동일하게 `/api/v1` 없이 bare path 유지: `/ai/embed`, `/ai/path/generate`.
- **CI Ollama 실호출 금지:** CI에는 Ollama service/container를 띄우지 않는다. 외부 AI는 전부 MockWebServer로 대체한다.
- **무상태화:** `spring-boot-starter-data-jpa`, PostgreSQL runtime, datasource 설정, DB 테스트, CI postgres service를 두지 않는다.
- **모델 기본값:** `OLLAMA_GEN_MODEL=qwen2.5:7b`, `OLLAMA_EMBED_MODEL=nomic-embed-text`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_TIMEOUT=PT8S`.
- **임베딩 차원:** `nomic-embed-text` 결과는 768차원이어야 한다. 응답 개수와 각 벡터 길이를 runtime에서 검증한다.
- **오류 매핑:** 요청 검증 실패 400, Ollama 5xx/timeout/connection failure 503, 잘못된 Ollama 계약/JSON/차원 불일치 502.
- **현재 소스 상태 참고(2026-06-20 확인):** `devpath-ai-svc`에는 이미 `OllamaClient`, `OllamaController`, DTO, MockWebServer 테스트 일부가 존재한다. 이 플랜은 신규 구현뿐 아니라 기존 구현의 gap 보강과 검증을 포함한다.
- **로컬 Ollama 상태 참고(2026-06-20 확인):** `ollama` CLI는 PATH에 없고, `winget`도 없다. `choco`와 Docker는 존재한다. 따라서 Task 0에서 host 설치 또는 compose 기반 runtime을 선행한다.

---

## File Structure

- Modify: `devpath-ai-svc/build.gradle.kts` — WebMVC/validation/MockWebServer 유지, JPA/DB 의존성 없음 검증
- Modify: `devpath-ai-svc/src/main/resources/application.yml` — Ollama env 이름과 기본값 정합
- Modify: `devpath-ai-svc/src/main/java/ai/devpath/aigw/ollama/OllamaClient.java` — request body, retry, strict validation, prompt/schema 보강
- Modify: `devpath-ai-svc/src/main/java/ai/devpath/aigw/ollama/OllamaExceptionHandler.java` — 400/502/503 오류 정책 정합
- Modify: `devpath-ai-svc/src/main/java/ai/devpath/aigw/ollama/dto/*.java` — validation annotation과 response contract 정합
- Modify: `devpath-ai-svc/src/test/java/ai/devpath/aigw/ollama/OllamaControllerTest.java` — MockWebServer 계약 테스트 보강
- Modify: `devpath-ai-svc/README.md`, `devpath-ai-svc/CLAUDE.md` — `OLLAMA_GEN_MODEL` 명칭 정정, 로컬 Ollama 절차 문서화
- Optional Modify: `devpath-shared/docker-compose.yml` — `ollama` service 추가(팀이 host 설치보다 compose runtime을 선택할 때)

---

## Task 0: 로컬 Ollama 선행 게이트

**Files:**
- Optional Modify: `devpath-shared/docker-compose.yml`
- Modify: `devpath-ai-svc/README.md`

**Interfaces:**
- Produces: 개발자가 `http://localhost:11434`에서 Ollama를 사용할 수 있는 상태. CI에는 영향 없음.

- [ ] **Step 1: 설치 여부 확인**

```powershell
where.exe ollama
ollama --version
```

Expected if already installed: version output. 현재 확인 결과는 `ollama` 미설치.

- [ ] **Step 2A: host 설치 경로(choco 사용 가능 시)**

```powershell
choco install ollama -y
ollama --version
```

> Windows에서 관리자 권한/네트워크가 필요할 수 있다. 설치 후 새 shell에서 PATH를 다시 읽는다.

- [ ] **Step 2B: compose runtime 경로(Docker 사용 시)**

`devpath-shared/docker-compose.yml`에 선택적으로 추가:

```yaml
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
```

`volumes:`에 추가:

```yaml
  ollama-data:
```

실행:

```powershell
docker compose -f ..\devpath-shared\docker-compose.yml up -d ollama
```

- [ ] **Step 3: 모델 pull**

Host CLI:

```powershell
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

Compose runtime:

```powershell
docker compose -f ..\devpath-shared\docker-compose.yml exec ollama ollama pull nomic-embed-text
docker compose -f ..\devpath-shared\docker-compose.yml exec ollama ollama pull qwen2.5:7b
```

- [ ] **Step 4: 로컬 smoke**

```powershell
ollama list
```

또는 compose:

```powershell
docker compose -f ..\devpath-shared\docker-compose.yml exec ollama ollama list
```

Expected: `nomic-embed-text`, `qwen2.5:7b`가 보인다.

---

## Task 1: ai-svc 무상태 dependency/config 게이트

**Files:**
- Modify: `devpath-ai-svc/build.gradle.kts`
- Modify: `devpath-ai-svc/src/main/resources/application.yml`
- Modify: `devpath-ai-svc/.github/workflows/ci.yml`

**Interfaces:**
- Produces: DB 없이 `./gradlew build` 가능한 stateless gateway.

- [ ] **Step 1: JPA/DB 의존성 부재 확인 테스트(정적 검증)**

```powershell
rg -n "data-jpa|postgresql|datasource|flyway|services:\s*$|postgres:" devpath-ai-svc/build.gradle.kts devpath-ai-svc/src/main/resources devpath-ai-svc/.github/workflows/ci.yml
```

Expected: `spring-boot-starter-data-jpa`, `org.postgresql:postgresql`, datasource, Flyway, CI postgres service 없음.

- [ ] **Step 2: build.gradle.kts 정합**

필수 의존성:

```kotlin
implementation("org.springframework.boot:spring-boot-starter-actuator")
implementation("org.springframework.boot:spring-boot-starter-validation")
implementation("org.springframework.boot:spring-boot-starter-webmvc")
implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
```

금지 의존성:

```kotlin
implementation("org.springframework.boot:spring-boot-starter-data-jpa")
runtimeOnly("org.postgresql:postgresql")
```

- [ ] **Step 3: application.yml env 명칭 정합**

`devpath.ollama`:

```yaml
devpath:
  ollama:
    base-url: ${OLLAMA_BASE_URL:http://localhost:11434}
    gen-model: ${OLLAMA_GEN_MODEL:qwen2.5:7b}
    embed-model: ${OLLAMA_EMBED_MODEL:nomic-embed-text}
    timeout: ${OLLAMA_TIMEOUT:PT8S}
```

> README/CLAUDE에 남아 있는 `OLLAMA_CHAT_MODEL` 표기는 `OLLAMA_GEN_MODEL`로 정정한다.

- [ ] **Step 4: CI postgres service 없음 확인**

`.github/workflows/ci.yml`의 build job에는 checkout/setup-java/setup-gradle/`./gradlew build`만 있고 `services.postgres`가 없어야 한다.

---

## Task 2: `/ai/embed` 계약 완성

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/ollama/dto/EmbedRequest.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/dto/EmbedResponse.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/OllamaClient.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/OllamaController.java`
- Modify: `src/test/java/ai/devpath/aigw/ollama/OllamaControllerTest.java`

**Interfaces:**
- Consumes: `POST /ai/embed` JSON `{ "texts": ["..."] }`
- Produces: `{ "embeddings": [[double...768]] }`
- Calls: Ollama `POST /api/embed` JSON `{ "model": "<embedModel>", "input": ["..."] }`

- [ ] **Step 1: 실패 테스트 작성/보강**

MockWebServer 테스트가 다음을 단언해야 한다.

- `/api/embed` path 호출
- request body에 `"model":"nomic-embed-text"` 포함
- request body에 `"input":["hello"]` 포함
- 768차원 응답은 200
- 응답 개수 불일치 → 502
- 임베딩 차원 불일치 → 502
- Ollama 5xx → 503
- timeout/body delay → 503
- 빈 `texts`/blank text → 400

- [ ] **Step 2: 구현 정합**

`OllamaClient.embed`:

- `RestClient.post().uri("/api/embed")`
- body는 `model`, `input`
- response null, embeddings null, size mismatch는 `OllamaContractException`
- 각 embedding null 또는 size != 768은 `OllamaContractException`
- `RestClientException`은 `OllamaUnavailableException`

- [ ] **Step 3: 테스트 실행**

```powershell
cd devpath-ai-svc
.\gradlew.bat test --tests ai.devpath.aigw.ollama.OllamaControllerTest
```

Expected: PASS.

---

## Task 3: `/ai/path/generate` structured JSON 계약 완성

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/ollama/dto/PathGenerateRequest.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/dto/PathGenerateResponse.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/OllamaClient.java`
- Modify: `src/test/java/ai/devpath/aigw/ollama/OllamaControllerTest.java`

**Interfaces:**
- Consumes: `POST /ai/path/generate`

```json
{
  "track": "BACKEND_SPRING",
  "diagnosedLevel": "JUNIOR",
  "strengthConcepts": ["Java"],
  "weaknessConcepts": ["Spring MVC"],
  "goal": "취업 준비"
}
```

- Produces:

```json
{
  "rationale": "...",
  "milestones": [
    {
      "weekNum": 1,
      "title": "...",
      "goalDescription": "...",
      "targetSkills": ["..."],
      "estimatedHours": 6,
      "whyThisOrder": "...",
      "expectedOutcome": "...",
      "tasks": [
        {"orderNum": 1, "taskType": "READ", "title": "...", "required": true}
      ]
    }
  ]
}
```

- Calls: Ollama `POST /api/chat`.

- [ ] **Step 1: request body 계약 테스트**

MockWebServer recorded request body가 다음을 포함해야 한다.

- `"model":"qwen2.5:7b"`
- `"stream":false`
- `"format"` JSON schema object
- `"options":{"temperature":0.2}`
- system/user messages
- user prompt에 track, diagnosedLevel, strengths, weaknesses, goal 포함

- [ ] **Step 2: strict parsing/validation 테스트**

다음을 테스트한다.

- `message.content`가 valid JSON이면 200
- Ollama 응답 body는 JSON이고, 그 안의 `message.content` 문자열을 다시 JSON parse한다
- malformed `message.content`는 1회 retry 후 502
- 첫 응답 malformed, 두 번째 valid → 200
- empty `message.content` → retry 후 502
- missing `rationale`/empty milestones → 502
- milestone 필수 필드 누락 → 502
- task 필수 필드 누락 → 502
- task가 4개 이상이면 상위 3개로 normalize
- task가 3개 미만이면 502 또는 명시 정책 적용. 권장: 설계 R-5에 따라 3개 보장, 3개 미만은 502
- `taskType`이 `READ/PRACTICE/QUIZ` 외 값이면 502
- Ollama 5xx/timeout → 503
- blank `track` 또는 빈 concept list → 400

- [ ] **Step 3: JSON schema 보강**

`pathSchema()`는 최소 다음을 포함한다.

- root required: `rationale`, `milestones`
- milestone required: `weekNum`, `title`, `goalDescription`, `targetSkills`, `estimatedHours`, `whyThisOrder`, `expectedOutcome`, `tasks`
- task required: `orderNum`, `taskType`, `title`, `required`
- taskType enum: `READ`, `PRACTICE`, `QUIZ`
- tasks `minItems: 3`, `maxItems: 3`

- [ ] **Step 4: system prompt 문구 보정**

현재 문구 `Each milestone must include exactly practical, concise tasks.`는 숫자가 빠져 있다. 다음처럼 명확히 고친다.

```text
Each milestone must include exactly 3 practical, concise tasks.
```

- [ ] **Step 5: 테스트 실행**

```powershell
cd devpath-ai-svc
.\gradlew.bat test --tests ai.devpath.aigw.ollama.OllamaControllerTest
```

Expected: PASS.

---

## Task 4: 오류 응답 정책과 validation 하드닝

**Files:**
- Modify: `src/main/java/ai/devpath/aigw/ollama/OllamaExceptionHandler.java`
- Modify: `src/main/java/ai/devpath/aigw/ollama/dto/*.java`
- Modify: `src/test/java/ai/devpath/aigw/ollama/OllamaControllerTest.java`

**Interfaces:**
- Produces: downstream이 stage error로 매핑 가능한 안정적인 HTTP status.

- [ ] **Step 1: validation 400 테스트**

테스트 케이스:

- `/ai/embed` `{ "texts": [] }` → 400
- `/ai/embed` `{ "texts": [""] }` → 400
- `/ai/path/generate` blank `track` → 400
- `/ai/path/generate` empty `strengthConcepts` 또는 `weaknessConcepts` → 400

- [ ] **Step 2: exception handler 정합**

현재 `OllamaContractException` → 502, `OllamaUnavailableException` → 503은 유지한다. Spring validation exception은 기본 400을 사용하되, 테스트에서 status를 고정한다.

- [ ] **Step 3: 오류 body 최소 계약**

502/503은 `{ "error": "<message>" }`를 반환한다. 400은 Spring 기본 body를 허용하거나 프로젝트 표준 error body가 있으면 맞춘다.

---

## Task 5: 로컬 실 Ollama smoke(runbook 성격)

**Files:**
- Modify: `devpath-ai-svc/README.md`

**Interfaces:**
- Consumes: Task 0의 local Ollama runtime.
- Produces: 개발자가 learning-svc 없이 ai-svc 단독으로 실 모델 smoke 가능.

- [ ] **Step 1: ai-svc 실행**

```powershell
cd devpath-ai-svc
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_EMBED_MODEL="nomic-embed-text"
$env:OLLAMA_GEN_MODEL="qwen2.5:7b"
.\gradlew.bat bootRun
```

- [ ] **Step 2: embed smoke**

```powershell
Invoke-RestMethod -Method Post http://localhost:8080/ai/embed `
  -ContentType "application/json" `
  -Body '{"texts":["Spring Boot controller test"]}'
```

Expected: `embeddings[0].Count == 768`.

- [ ] **Step 3: path generate smoke**

```powershell
Invoke-RestMethod -Method Post http://localhost:8080/ai/path/generate `
  -ContentType "application/json" `
  -Body '{"track":"BACKEND_SPRING","diagnosedLevel":"JUNIOR","strengthConcepts":["Java syntax"],"weaknessConcepts":["Spring MVC"],"goal":"첫 백엔드 포트폴리오 만들기"}'
```

Expected: `rationale`, `milestones`, milestone `expectedOutcome`, task 3개.

> 이 Task는 local/manual smoke다. CI와 PR gate는 Task 6의 MockWebServer 테스트/빌드만 사용한다.

---

## Task 6: 전체 빌드 + PR 게이트

- [ ] **Step 1: 단위/계약 테스트**

```powershell
cd devpath-ai-svc
.\gradlew.bat test
```

Expected: BUILD SUCCESSFUL. 실제 Ollama 호출 없음.

- [ ] **Step 2: 전체 빌드**

```powershell
.\gradlew.bat clean build
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: 정적 범위 확인**

```powershell
rg -n "data-jpa|postgresql|datasource|flyway|OLLAMA_CHAT_MODEL|/api/v1" .
```

Expected:

- JPA/Postgres/datasource/Flyway 없음
- `OLLAMA_CHAT_MODEL` 없음(`OLLAMA_GEN_MODEL`만 사용)
- `/api/v1` 경로 없음

- [ ] **Step 4: develop PR**

```powershell
git add .
git commit -m "feat(ai): Ollama 기반 학습경로 게이트웨이 계약 완성"
git push
gh pr create --base develop --title "feat(ai): 슬라이스 #3 Ollama 게이트웨이" --body "<요약>"
```

---

## Acceptance Checklist

- [ ] `POST /ai/embed`가 Ollama `/api/embed`에 `model` + `input`으로 위임한다.
- [ ] embeddings 응답 개수와 각 vector 768차원을 검증한다.
- [ ] `POST /ai/path/generate`가 Ollama `/api/chat`에 `stream:false`, `format`, `temperature:0.2`를 보낸다.
- [ ] `message.content`를 2단계 JSON parse한다.
- [ ] path response에 `expectedOutcome`이 포함된다.
- [ ] milestone별 task는 정확히 3개 정책으로 검증/정규화된다.
- [ ] malformed JSON은 1회 retry 후 502다.
- [ ] Ollama 5xx/timeout/connection failure는 503이다.
- [ ] 요청 validation 실패는 400이다.
- [ ] CI와 `./gradlew build`는 실제 Ollama 없이 MockWebServer로 통과한다.
- [ ] ai-svc에 DB/JPA/Postgres/CI postgres service가 없다.
- [ ] README/CLAUDE의 env 변수명이 `OLLAMA_GEN_MODEL`로 정합하다.
- [ ] 로컬 Ollama 미설치 시 Task 0 절차로 설치 또는 compose runtime을 준비할 수 있다.

---

## Self-Review

- **Spec coverage:** 설계서 §2 AI 레이어, §9 빌드 B, §10 CI MockWebServer 원칙, R-1 chat non-streaming/2단계 파싱, R-5 task 3개/expectedOutcome, R-6 ai-svc 무상태화, 세부 정정 모델 기본값/768차원 fail-fast를 커버한다.
- **Current source alignment:** 현재 ai-svc에는 이미 `OllamaClient`/controller/test가 존재하므로 플랜은 구현 gap 보강 방식으로 구성했다. 특히 prompt의 "exactly 3" 누락, 3개 미만 task 검증, validation 400 테스트, README `OLLAMA_CHAT_MODEL` stale 표기를 명시 보강한다.
- **CI safety:** CI에는 Ollama service를 추가하지 않는다. 모델 pull은 local/manual Task 0/5로만 둔다.
- **Risk:** `qwen2.5:7b`는 로컬 메모리/디스크 요구가 크다. host 설치가 막히면 Docker 기반 `ollama/ollama` service로 대체한다. 모델 JSON 준수 실패는 retry 1회 + strict 502로 downstream이 SSE error stage에 매핑한다.
