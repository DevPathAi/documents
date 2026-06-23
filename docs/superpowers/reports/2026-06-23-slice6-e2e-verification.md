# 슬라이스 #6 (AI 코드리뷰) E2E 라이브 실증 보고서

> 2026-06-23. Tier-1 데모(슬라이스 #1~6) 종결 검증의 일부. 실 서비스 프로세스 간 끝단간 동작을 로컬 스택에서 실증.

## 결론

**AI 코드리뷰 파이프라인 전 구간이 실 서비스 간에서 동작함을 라이브로 확인했다.** 실 Kafka 브로커 + 실 cross-service HTTP + 실 Postgres 영속 + gateway 라우팅 + 폴링 API(JWT) + 소유권/인증 강제까지 끝단간 검증.

## 검증 스택

- 인프라: devpath-shared `docker-compose`의 **Kafka(apache/kafka 3.9.1, 9092)** + **Postgres(pgvector pg17, 5432, `devpath` DB)**.
- 서비스(로컬 bootJar, 실 프로세스): **sandbox-svc(8085)** · **ai-svc(8084, REVIEW_PROVIDER=mock)** · **gateway(8080, AI_SVC_URI→8084)**.
- 구동 방식: 코드 실행(Docker 러너)은 Windows 변수를 피해 **sandbox_sessions 시드 + `sandbox.run.submitted` 이벤트 주입**으로 이벤트 이후 전 구간을 실 서비스로 구동. 리뷰는 Mock provider(외부 LLM 불필요).

## 끝단간 결과

| # | 구간(seam) | 방법 | 결과 |
|---|---|---|---|
| 1 | `sandbox.run.submitted` Kafka → ai-svc 컨슈머 | 실 Kafka에 이벤트 발행 | 컨슈머가 파티션 할당·소비, 리뷰 처리 |
| 2 | ai-svc → sandbox-svc `/internal/sandbox/sessions/{id}` (실 HTTP) | curl sandbox-svc:8085 | 9-필드 `SandboxSessionView` JSON 정확 반환 |
| 3 | Mock 리뷰 → `ai_code_reviews` 영속 | DB 조회 | `status=DONE, provider=MOCK, confidence=85` |
| 4 | 멱등성(상태 기준 skip) | 동일 session 이벤트 재발행 | review count **1 유지**(DONE) — 중복 없음 |
| 5 | gateway `/reviews/**` 라우팅 | curl gateway:8080 | ai-svc로 라우팅(미인증 401, JWT 200) — 404 아님 |
| 6 | GET `/reviews?sandboxSessionId=1` 폴링 200 | JWT(sub=42) 직접+gateway | **200** + `CodeReview` DTO(id·status·confidence·strengths·improvements·security) |
| 7 | 소유권 강제 | JWT(sub=99) | **403** |
| 8 | 인증 강제 | JWT 없음 | **401** |

폴링 200 응답 본문(직접 ai-svc·gateway 경유 동일):
```json
{"id":"1","status":"DONE","confidence":85,"strengths":["정상 실행되었습니다 (PYTHON)"],"improvements":[],"security":[]}
```

## 타 검증으로 커버되는 구간(본 실증 미구동)

- **샌드박스 실제 코드 실행**(Docker 러너): sandbox-svc docker IT(CI, 6/6)로 검증. 본 실증은 세션 시드로 대체.
- **프론트엔드 UI 렌더**: frontend 위젯 테스트(melos)로 검증. 본 실증은 폴링 API 200 응답(프론트가 소비하는 DTO)까지 확인.
- **실 LLM 공급자**(Ollama/Claude): 본 실증은 Mock provider. 골든 eval은 별도(Ollama 가동 시).

## 재현 메모(환경 제약)

- ai-svc는 로컬에 GitHub Packages 인증이 없어, devpath-shared를 `./gradlew publishToMavenLocal`로 ~/.m2에 설치하고 ai-svc `repositories`에 `mavenLocal()`을 **임시(미커밋)** 추가해 빌드. 검증 후 즉시 복원.
- `flywayMigrate`(gradle 플러그인)는 **Gradle 9와 비호환**(`JavaPluginConvention` 제거). 누락 마이그레이션(`V202606221001__sandbox_sessions`, `V202606231001__ai_code_reviews`)을 psql로 직접 적용(서비스는 ddl-auto:validate라 테이블 존재만 필요).
- Kafka 발행 시 Git Bash 경로 변환 회피: `MSYS_NO_PATHCONV=1`.

## 정리

검증 후 로컬 상태 복원: ai-svc `build.gradle.kts` 복원(mavenLocal 제거), 서비스 3종 종료, Kafka 컨테이너 중지. `devpath` DB의 시드/리뷰 행은 로컬 dev 데이터로 잔존(무해).
