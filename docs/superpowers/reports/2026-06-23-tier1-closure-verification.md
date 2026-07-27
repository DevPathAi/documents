# Tier-1 종결 검증 보고서 (계획 대비)

> 2026-06-23. Tier-2 진입 전 Tier-1(슬라이스 #1~6 = MD1+MD2 = 1st+2nd Aha) 전체 작업을 계획 문서와 대조 검증.
> 기준 문서: [17_스케줄](../../../17_스케줄.md)(현행 실행 baseline) · 슬라이스 설계서 6종(`docs/superpowers/specs/`) · [27_MVP_설계서](../../../27_MVP_설계서.md)(전략 컨텍스트).

## 0. 요약

**Tier-1 핵심 골든패스는 코드 완성·릴리스·배포·E2E 실증까지 도달했다.** 7개 레포(shared·platform-svc·learning-svc·ai-svc·sandbox-svc·gateway·frontend) 모두 슬라이스 #6까지 main 릴리스. 단 MD2 완료기준 중 **결제·베타100·일부 provider 항목은 의도적 연기 또는 미수행**이며, 일부 계획 항목은 **단순화하여 구현**(gVisor→plain Docker, Claude→Ollama dev)되었다.

| 판정 | 항목 |
|---|---|
| ✅ 달성 | 인증(GitHub)·진단·학습경로·콘텐츠·Sandbox·AI리뷰 백엔드 끝단간 실동작(E2E 실증), 아키텍처 원칙 준수 |
| 🟡 부분/단순화 | 학습경로·리뷰 provider(운영 Claude 미배선, dev=Ollama/Mock), Sandbox 격리(plain Docker), frontend 실API(mock 잔존), 골든 24/50 |
| 🔴 미수행/연기 | 결제(토스페이먼츠), 베타 100명, Google·카카오 OAuth |

## 1. 슬라이스별 계획 대비 검증

### 슬라이스 #1 — OAuth/인증 (MD1 게이트)
- **계획**: Spring Security 7 + OAuth2(GitHub→Google→카카오), JWT+Refresh Cookie, `users`·`user_oauth_identities`·`user_profiles`, gateway OAuth2 엣지, frontend AuthController 실API.
- **실측**: platform-svc `application.yml`에 **GitHub registration만 존재**(Google·카카오 없음). JWT+Refresh·스키마·gateway 엣지·`UserRegisteredEvent` Outbox 구현. 
- **판정**: 🟡 GitHub OAuth 골든패스 성립. **Google·카카오 미구현(gap)** — MVP는 "Google+GitHub"였고 스케줄은 카카오까지. 데모는 GitHub로 성립하나 사용자 커버리지 한계.

### 슬라이스 #2 — 진단
- **계획**: `question_bank`+Bloom 태깅+적응형 알고리즘, 비회원 세션(Redis 30분)→회원 이관, frontend 온보딩 실API.
- **실측**: learning-svc 진단(answer/complete/result)·claim·`AssessmentCompletedEvent`, 진단 문항 **500개**(슬라이스 #4 B1) 구축.
- **판정**: ✅ 달성. 문항 500개는 콘텐츠 일정(MD1 500개)과 정합.

### 슬라이스 #3 — 학습경로 (1st Aha)
- **계획**: ai-svc AI Gateway 경로생성(**Claude SSE** + Event), learning-svc 임베딩 768(HNSW)+milestone 매칭+`path_milestones`/`path_weekly_tasks`, frontend PathController SSE 실API. 완료기준 가입→진단→경로 p50<8분.
- **실측**: ai-svc는 **Ollama dev gateway**(`/ai/embed`·`/ai/path/generate`, nomic-embed-text 768). learning-svc 경로 영속·임베딩·milestone 구현. ai-svc의 Claude/anthropic 사용은 **리뷰 모듈에만 국한**(경로생성은 Ollama).
- **판정**: 🟡 1st Aha 골든패스 성립(실 provider=Ollama dev). 계획의 "**Claude** SSE"는 provider 추상화로 교체 가능하나 **운영 Claude 미배선**. p50<8분은 staging 미측정.

### 슬라이스 #4 — 콘텐츠 (MD2)
- **계획**: content 뷰어 API(Markdown)+진척 자동추적+다음 추천, frontend ContentPage 실API. 콘텐츠 30(MD1)~100(MD3), 실습 코드블록 50.
- **실측**: learning-svc 콘텐츠 뷰어 API+진척+`user_content_progress`, dev ContentSeeder **150편**, 동시성 409 처리(unique violation), frontend 뷰어.
- **판정**: ✅ 달성(콘텐츠 150편으로 MD2 100편 목표 초과).

### 슬라이스 #5 — Sandbox (MD2)
- **계획**: Docker 풀(Java21/Node20/Python3.12)+**gVisor(runsc)**+리소스제한(CPU/MEM/30s/네트워크차단)+`sandbox_sessions`+실행로그 SSE+`SandboxRunSubmittedEvent`, frontend RunController 실API.
- **실측**: sandbox-svc RunnerBackend+**plain Docker**(runsc/gVisor 코드 부재)+리소스제한+`sandbox_sessions`+SSE+이벤트+다언어. docker IT 6/6.
- **판정**: 🟡 실행·격리·SSE·이벤트 성립. **gVisor 미적용(plain Docker)** — 격리 강도 계획 대비 완화(워크스페이스 권한 0755/0644 수정으로 native Linux 동작). 보안 강화는 MD4 pentest 항목과 연계 권장.

### 슬라이스 #6 — AI 코드리뷰 (2nd Aha)
- **계획**: 인젝션 방어(입력필터+system prompt+탈옥방지), Claude 리뷰+골든 50+`ai_code_reviews` 비동기+👍👎, frontend ReviewPanel 실API. **+결제(토스페이먼츠 월14,900)**. 완료기준 과제→AI리뷰 실동작, 유료전환, 베타100, 2R IR.
- **실측**: 비동기 파이프라인(Kafka→멱등 ai_code_reviews→폴링/피드백)+인젝션 방어 3계층(델리미터+강건 system+구조화출력)+provider 추상화(Claude sonnet-4-6/Ollama qwen2.5-coder/Mock)+골든 eval+E2E 라이브 실증+일시장애 재시도복구. 골든 **24/50**.
- **판정**: 🟡→✅ AI리뷰 코어는 계획 이상(비동기·재시도/DLQ·E2E·인젝션 3계층). 단 **인젝션 방어는 구조화출력 중심(입력 필터/분류기는 MD4로 연기)**, **골든 24/50**, **운영 Claude 키 미배선**(dev=Mock). **결제·베타100 미수행(아래 2절)**.

## 2. MD2 완료기준 중 미수행/연기 항목

| 항목 | 상태 | 사유/메모 |
|---|---|---|
| **결제(토스페이먼츠)** | 🔴 연기 | 슬라이스 #6 brainstorming에서 **별도 spec→plan 사이클로 분해**(사용자 결정). MD2 "유료 전환 가능" 완료기준 미충족. AI리뷰와 독립이라 분리 타당하나, MVP 가설 H1(지불의사) 검증은 결제 구현 전까지 불가. |
| **베타 100명** | 🔴 미수행 | 런칭·모집 활동(코드 외 영역). H1·H2·리텐션 측정의 전제. |
| **Google·카카오 OAuth** | 🔴 미구현 | GitHub만. 사용자 커버리지·H3 외 영향은 낮으나 베타 모집 시 가입 마찰. |
| **운영 Claude 라이브** | 🟡 provider-ready | 추상화·키 주입 경로 완비, `ANTHROPIC_API_KEY` 미배선(dev=Ollama/Mock). 비용(MVP 자금 30%)·한도 신청과 연계. |
| **골든 50** | 🟡 24/50 | 하니스·실모델 검증 완료, 케이스 26개 추가 잔여. |
| **gVisor 격리** | 🟡 plain Docker | MD4 Sandbox pentest와 함께 강화 권장. |
| **frontend 완전 실API** | 🟡 부분 | 실 ApiClient(Dio) 인프라 + 일부 실연동, `web_mock_fixtures.dart` 잔존(E2E 일부 mock 렌더). |

## 3. 아키텍처·품질 원칙 준수

| 원칙(스케줄·CLAUDE.md) | 준수 | 근거 |
|---|---|---|
| MSA + 이벤트구동(Kafka Outbox) | ✅ | 7개 서비스, Transactional Outbox + @KafkaListener 멱등 |
| 교차서비스 FK 금지 | ✅ | `ai_code_reviews` 등 FK 없음, 내부 HTTP/이벤트로 연계 |
| 중앙 Flyway(shared SSoT) | ✅ | 마이그레이션 shared 소유, 서비스 ddl-auto:validate |
| Boot4 모듈 분리 | ✅ | spring-boot-flyway/kafka, webmvc.test, @MockitoBean 등 |
| develop 경유 2단계 PR·CI 녹색 게이트 | ✅ | 전 슬라이스 develop→main, CI 통과 후 머지 |
| 인젝션 방어(법적 필수) | 🟡 | 구조화출력+델리미터+강건 system 3계층. 입력 필터/분류기(MD4 모더레이션)는 후속 |
| 테스트 우선·끝단간 검증 | ✅ | TDD, E2E 라이브 실증(documents 보고서), 골든 eval |

## 4. 계획 대비 확장(계획 이상 달성)

- MVP 초안(모놀리식, AI멘토채팅+LCS+Q&A)에서 **MSA + 슬라이스 #5·#6(Sandbox+AI코드리뷰)을 2nd Aha로 재정의** — 스케줄에 반영된 의도적 진화. (MVP 초안은 Sandbox를 "베타후반 M2+ 제외"로 뒀으나 실행에서 2nd Aha 핵심으로 승격.)
- 비동기 이벤트구동 리뷰 + **일시장애 재시도/DB종료 복구**(Important #1, 계획 외 운영안정성).
- **E2E 라이브 실증**·**골든 eval 실모델 검증**(계획의 검증 강도 이상).
- 콘텐츠 150편(MD2 목표 100편 초과).

## 5. Tier-2 진입 전 권고

1. **Tier-1 데모 성립 여부**: 백엔드 골든패스는 실동작(E2E 실증). 단 **데모를 "web 끝단간 실API"로 시연하려면 frontend 실API 전환 완료 + 운영 provider(Claude/OAuth) 배선**이 필요. 현재는 "백엔드 실동작 + frontend 부분 실API/mock".
2. **MVP 가설 검증 차단요인**: H1(지불의사)=결제 미구현, H2(LCS)=LCS는 Tier-2(#9), 베타100 미수행 → **현 상태로는 가설 측정 불가**. 결제·베타는 별도 트랙으로 계획 필요.
3. **연기 항목의 명시적 백로그화**: 결제·Google/카카오 OAuth·gVisor·골든 50·골든 frontend 실API를 Tier-2/MD4 일정에 배치(이 보고서 2절 표 기준).
4. Tier-2(#7 멘토·#8 커뮤니티·#9 LCS·#10 모바일·#11 랜딩)는 슬라이스 #6까지의 패턴(수직 슬라이스+이벤트구동+develop 2단계 PR)을 승계.
