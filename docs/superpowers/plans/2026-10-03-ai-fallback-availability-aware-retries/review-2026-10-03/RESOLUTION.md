# 최종 브랜치 리뷰 처리 결과 (2026-10-03)

- 대상: `devpath-ai-svc` `feat/ai-fallback-availability-aware-retries` `c26bb6d..509bd60`(계획 Task 1~13, 13커밋)
- 리뷰: 새 컨텍스트 리뷰어 1회(읽기 전용). 전문 = [REPORT.md](REPORT.md) — 리뷰어의 최종 응답이 한 단어(「Done.」)로 와서
  대화 기록에서 가장 긴 텍스트 블록을 그대로 회수했다.
- 판정: Critical 0 · Important 3 · Minor 7 · 「With fixes」

## 재등급과 처리

등급은 리뷰어의 표시가 아니라 「이대로 나가면 사람이 무엇을 겪는가」로 다시 매겼다.

| 지적 | 재등급 | 처리 |
|---|---|---|
| I-1 전부 차단 시 강제로 부른 1순위의 실패가 이미 열린 래치에 다시 기록돼 사다리가 요청마다 자란다(5→10→…60분) — Ollama 가 돌아온 뒤에도 회복된 Claude 를 최대 1시간 건너뛴다 | Important | **수정** `cf8d0e2` — `ProviderAttemptPlan.Attempt` 에 `forced`(전부 차단 분기에서만), 세 래퍼는 forced 시도의 실패를 기록하지 않는다(성공은 기록). 세 래퍼 `aFailedForcedAttemptDoesNotGrowThePrimarysBackoff` RED(5분 1초 뒤에도 열림) → GREEN. 스펙 §3.1-3 에 반영 |
| I-2 GPU 가 죽어 있는 동안 Ollama 래치 기한이 끝날 때마다 다음 생존 탐색(≤ 30초)까지 죽은 Ollama 가 쓸 수 있어 보인다 | 판단(수용) | **코드 무변경, 스펙 §3.3 잔여 위험 3 으로 기록.** 「기한 만료 = 다음 탐색 전까지 닫힘」은 모든 provider 래치의 기존 계약이고, 리뷰어가 제안한 해법(생존 탐색이 열린 래치도 계속 다시 연다)은 승인된 §3.1-5(닫힌 대상만 핑)를 바꾼다. Claude 일시 실패가 그 창과 겹쳐야 생기는, 잔여 위험 1 과 같은 종류다 |
| I-3 생존·복구 탐색과 outbox relay(2초)가 Boot 기본 스케줄러 스레드 1개를 나눠 쓴다 — 응답 없는 Ollama 탐색 중(최대 3×(3초+5초)=24초) outbox 발행이 멈춘다 | Important(낮음) | **수정** `eb8d6e7` — `spring.task.scheduling.pool.size: 3`. `SchedulingPoolTest`(실제 application.yml → Boot 자동 구성) RED `expected 3 but was 1` → GREEN |

수정 뒤 전체 스위트(로컬 Postgres): tests=421 failures=0 errors=0 skipped=1 (Task 13 의 414 + 신규 7).

## 보류한 Minor (후속 후보)

- M-1 `provider=claude, fallback=ollama` 인데 `ANTHROPIC_API_KEY` 가 없으면 체인은 Ollama 하나로 줄지만 탐색 빈은 생겨 30초마다 `/api/tags` 를 부른다(아무도 읽지 않는 래치). 해는 없다.
- M-2 모델 이름 정확 일치 vs Ollama 의 암묵 `:latest` — 태그 없이 `*_OLLAMA_MODEL=qwen2.5` 로 두면 탐색이 계속 「없음」이라 폴백이 꺼진 채로 남는다(안전한 쪽). 현재 값은 모두 태그가 있다.
- M-3 「is not loaded」 문구 — `/api/tags` 는 내려받은 모델 목록이지 메모리에 올라간 모델(`/api/ps`)이 아니다.
- M-4 404→TRANSIENT 가 provider 가 아니라 `RestClientResponseException` 타입에 걸려 있다 — RestClient 를 쓰는 다른 provider 가 생기면 그 404 도 가용성 실패가 된다.
- M-5 체인 길이 1 인 Ollama 1순위(개발) 구성도 연결 타임아웃 3초를 받는다 — §3.1-6 의 의도지만 §4 의 「동작 변화 0」은 약간 과장.
- M-6 운영 문서에 `PROVIDER_LIVENESS_INTERVAL` · `*_OLLAMA_CONNECT_TIMEOUT` 이 없다(PR 본문에 적었다).
- M-7 워크트리의 추적 안 된 `.omc/` — 커밋에 넣지 않았다(명시 경로로만 `git add`).

## 리뷰어가 판단에서 뺀 것 (요지)

SDK `maxRetries=2` 의 비멱등 POST 재시도(폴백 이전 상태와 같음) · SpEL 조건식에 따옴표가 든 값 · 단일 인스턴스 래치 ·
`LLM_ALL_PROVIDERS_BLOCKED` 제거의 외부 영향(community-svc 는 `error_code` 를 저장만 하고 분기하지 않음 — 리뷰어 확인) 등.
전문은 REPORT.md 「Declined to judge」.
