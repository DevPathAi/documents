# MD1 슬라이스 3 빌드 B — ai-svc Ollama 게이트웨이

## 요약

- 목표: `devpath-ai-svc`를 슬라이스 3 학습경로 생성을 위한 무상태 로컬 Ollama 게이트웨이로 전환한다.
- 범위: 빌드 B만 다룬다. 빌드 A shared pgvector, 빌드 C learning 경로 엔진, 빌드 D platform 상태 전이, 빌드 E gateway/frontend는 범위 밖이다.
- API 규약: `/api/v1` 접두사 없이 bare path를 유지한다.
- CI 규칙: CI에서 실제 Ollama를 호출하지 않는다. Ollama HTTP 계약 테스트는 모두 MockWebServer로 검증한다.

## 확정 결정

- 생성 모델: `OLLAMA_GEN_MODEL=qwen2.5:7b`.
- 임베딩 모델: `OLLAMA_EMBED_MODEL=nomic-embed-text`.
- 기본 URL: `OLLAMA_BASE_URL=http://localhost:11434`.
- 타임아웃: `OLLAMA_TIMEOUT=PT8S`.
- 임베딩 차원: `768`, 런타임에서 검증한다.
- Ollama `/api/chat`은 기본적으로 스트리밍 응답을 반환하므로, 구조화 JSON 생성을 위해 반드시 `stream:false`를 전송한다.

## ai-svc 변경 사항

- `devpath-ai-svc`에서 JPA/PostgreSQL 의존을 제거한다.
  - `spring-boot-starter-data-jpa`를 제거한다.
  - PostgreSQL 런타임 의존성을 제거한다.
  - datasource, JPA, Flyway 애플리케이션 설정을 제거한다.
  - `DbConnectionTest`를 제거한다.
  - CI postgres service와 DB 환경 변수를 제거한다.
- Spring `RestClient` 기반 무상태 Ollama HTTP 클라이언트를 추가한다.
- 공개 엔드포인트를 추가한다.
  - `POST /ai/embed`
    - 요청: `{ "texts": ["..."] }`
    - Ollama `POST /api/embed`에 `{ "model": "...", "input": texts }`로 위임한다.
    - 응답: `{ "embeddings": [[float]] }`
    - 반환된 모든 임베딩은 정확히 768차원이어야 한다.
  - `POST /ai/path/generate`
    - 요청: `{ "track", "diagnosedLevel", "strengthConcepts", "weaknessConcepts", "goal?" }`
    - Ollama `POST /api/chat`에 `stream:false`, JSON schema `format`, `options.temperature:0.2`를 포함해 위임한다.
    - Ollama `message.content`를 JSON으로 파싱하고 엄격한 학습경로 생성 응답으로 반환한다.

## 오류 정책

- 요청 검증 실패: `400`.
- Ollama 연결 실패, 타임아웃, 5xx: `503`.
- 잘못된 Ollama 응답, 학습경로 JSON 파싱 실패, 스키마 불일치, 임베딩 차원 불일치: `502`.
- 학습경로 생성 JSON 파싱 실패는 한 번 재시도한 뒤 `502`를 반환한다.

## 테스트 계획

- 문서에 `stream:false`, `qwen2.5:7b`, `nomic-embed-text`가 포함되어 있는지 확인한다.
- `devpath-ai-svc`에서 `./gradlew test`를 실행한다.
- `devpath-ai-svc`에서 `./gradlew build`를 실행한다.
- MockWebServer 테스트는 다음을 검증해야 한다.
  - `/api/chat` 요청 body에 `stream:false`와 `format`이 포함된다.
  - `/api/embed` 요청 body에 `input` 배열이 포함된다.
  - 임베딩 길이는 768이어야 한다.
  - 잘못된 JSON, 차원 불일치, 타임아웃/연결 실패, Ollama 5xx가 기대한 API 오류로 매핑된다.

## 로컬 수동 확인

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
cd devpath-ai-svc
./gradlew bootRun
```

이후 `http://localhost:8080` 기준으로 `/ai/embed`와 `/ai/path/generate`를 호출해 확인한다.
