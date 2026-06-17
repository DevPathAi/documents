# 세션 핸드오프 — MD1 슬라이스 #1(OAuth/인증 게이트) 5빌드 완료 → 끝단간/슬라이스 #2 (2026-06-18)

> **상태**: MD1 슬라이스 #1의 **5개 빌드 전부 구현·develop 머지 완료**. 코드/단위·통합 레벨은 끝났고, **끝단간(staging) 실동작**과 다음 슬라이스가 남았다.
> **원칙**: 각 레포 CLAUDE.md 절대 조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR) + 서브에이전트 Scope Lock. 본 문서 상태는 2026-06-18 실측.

---

## 1. 완료 (이번 세션 — 슬라이스 #1 전 빌드 develop 머지)

설계→spec→plan→subagent-driven 실행(Task별 implementer + 리뷰어 + 컨트롤러 직접검증 + 전체 브랜치 opus 리뷰), 각 레포 빈 DB clean build·CI 녹색 후 머지.

| 빌드 | 레포 | PR(머지) | 산출 |
|---|---|---|---|
| 스키마 | devpath-shared | #7→develop, #8→main(릴리스·publish) | users 확장(github_id 이관)·user_oauth_identities·user_profiles·outbox + `UserRegisteredEvent` |
| 2a 인증척추 | devpath-platform-svc | #5 | GitHub OAuth2 로그인→사용자 upsert(+outbox 동일tx, provider 토큰 Tink 암호화)→JWT(HS256)→Redis refresh 회전→`/auth/refresh`·`/auth/logout`·`/users/me` |
| 2b 이벤트전파 | devpath-platform-svc | #6 (+shared #9 develop/#10 main) | outbox 릴레이→Kafka(send-ack 후 published) + 환영알림 Kafka 소비자(멱등 3중방어) + `notifications` 테이블 |
| gateway JWT엣지 | devpath-gateway | #5 | JWT 검증(HS256, platform과 동일 `JWT_SECRET`, iss/aud 미검증) + platform 라우팅 + CORS(allow-credentials) |
| frontend 목→실 | devpath-frontend | #15 | web OAuth 리다이렉트 로그인→`/auth/callback`→쿠키 `/auth/refresh`, AuthLoading 앱시작 세션복원, dp_core AuthInterceptor 쿠키 refresh |

- 설계서·5개 플랜·플랜 리뷰: documents `docs/superpowers/{specs,plans,reports}/2026-06-17-md1-slice1-*` (PR #11 develop 머지).
- SDD 진행 ledger: 각 레포 `.git/sdd/progress.md`. 다운스트림 노트: platform `.git/sdd/final-review-result.md`·`final-review-2b-result.md`, gateway/frontend `final-review-*-result.md`.

## 2. ⚠️ 슬라이스 #1 끝단간(staging) 완성 전 남은 작업

> 코드는 머지됐으나 **실 OAuth·교차출처 쿠키·실 Kafka는 런타임에서만 검증**된다. MD1 완료기준(가입→진단→경로 p50<8분 web 실동작) 중 "가입(OAuth)→/users/me" 끝단간을 닫으려면:

1. **외부 GitHub OAuth 앱 등록 (사용자 직접, 콘솔)**: client id/secret + redirect URI `{gateway}/login/oauth2/code/github`. (에이전트 대행 불가.)
2. **배포 env 주입** (비밀값 커밋 금지):
   - platform+gateway **동일** `JWT_SECRET`(≥32바이트, HS256)
   - gateway `PLATFORM_URI`(배포 `http://devpath-platform-svc:8080`), `CORS_ALLOWED_ORIGINS`(web 출처)
   - platform `COOKIE_SAME_SITE=None` + `COOKIE_SECURE=true`(교차출처 쿠키 R6/X-1), `TOKEN_ENC_KEYSET`(prod Tink keyset), `GITHUB_CLIENT_ID/SECRET`
   - Kafka 브로커 프로비저닝(`KAFKA_BOOTSTRAP`) — 2b 환영알림 소비 끝단간
   - 로컬 동시구동: gateway 8080 / platform **8081**(PLATFORM_URI 기본값)
3. **R4 — `User.email` nullable화 (별도 티켓)**: GitHub email 미반환 사용자는 현재 frontend dp_core `User.email`이 `required String`이라 `User.fromJson` 실패→미인증 폴백→**로그인 불가**. dp_core 모델 nullable화 + `dart run build_runner build` regen 필요. MD1 끝단간 충족에 직접적.
4. **수동 끝단간 검증**: gateway+platform+PG+Redis+Kafka 구동 + OAuth 앱 등록 후 `cd apps/web && flutter run -d chrome --dart-define=API_BASE_URL=<gateway> --dart-define=USE_MOCK=false` → GitHub 로그인→콜백→`/users/me`→온보딩 게이트 1회 확인. withCredentials 쿠키 왕복·SameSite=None 실확인.

## 3. 하드닝 후속 (운영 투입 전, 비차단 — 각 레포 ledger에 기록)

- platform: `/auth/refresh` CSRF/Origin 가드(csrf disable + 쿠키 기반), refresh `rotate` 원자성(Redis Lua/MULTI-EXEC, 멀티인스턴스), prod `TOKEN_ENC_KEYSET` 미설정 부팅실패 테스트, `@Transactional` 테스트 격리, profile 행 생성 테스트 단언.
- 2b: Kafka poison-message DLQ/백오프, `@KafkaListener` groupId SpEL 외부화.
- frontend: web 토큰 localStorage 영속·silent refresh(R3 후속), AuthInterceptor wired-콜백 실결선 테스트.

## 4. 다음 본작업 후보

- **(A) 슬라이스 #1 끝단간 닫기**: §2 외부 등록+env+R4+수동검증. MD1 첫 게이트 실동작 확정.
- **(B) 슬라이스 #2 — 진단(learning)**: 17_스케줄 §2. learning-svc `question_bank`+Bloom 태깅 스키마, 적응형 진단(난이도 ±), 비회원 진단 세션(Redis 30분)+결과 회원 이관(`/onboarding/assessments/claim`), 프론트 온보딩 진단 실API. → 슬라이스 #1의 `UserRegisteredEvent`/온보딩 게이트와 연결.
- 권장: (A)를 먼저(특히 R4 + OAuth 등록)로 #1을 실제로 닫은 뒤 (B) 착수.

## 5. 주의·참고

- **추측 금지·테스트 우선**: 인증/보안 직결. 토큰 서명·암호화는 well-tested 라이브러리(Spring Security·Nimbus·Tink) 유지.
- **Spring Boot 4 = Jackson 3**(`tools.jackson.databind.json.JsonMapper`, ObjectMapper 빈 미등록). 테스트 슬라이스·Flyway·Kafka autoconfigure **모듈 분리**(`spring-boot-flyway`·`spring-boot-kafka`·`org.springframework.boot.{data.jpa,jdbc,webmvc,jpa}.test.autoconfigure`). mock 빈 `@MockitoBean`. **서비스 테스트 DB 스키마**는 test 프로파일 Flyway로 shared jar `classpath:db/migration` 적용(main은 flyway 비활성), 모든 `@SpringBootTest`에 `@ActiveProfiles("test")`.
- **shared 변경→서비스 소비**: shared `publish.yml`은 **main push에서만** GitHub Packages publish. 서비스가 새 shared 클래스를 쓰려면 shared develop→main 릴리스 선행(D-6). 로컬은 캐시 purge 후 `--refresh-dependencies`.
- **브랜치 전략**: 각 레포 develop에서 분기 → develop PR. main 직접 금지(shared 릴리스 PR 제외). CI 녹색 후 merge commit.
- **서브에이전트**: 이 환경은 긴 최종 메시지를 반환하지 않음 → 리뷰/긴 산출물은 **파일로 Write**하게 지시(`[[subagent-final-message-suppressed]]`).

## 6. 관련 메모리

- [[md1-slice1-progress]] — 슬라이스 #1 전 빌드 상태·Boot 4 교훈·남은 작업(본 핸드오프의 SSoT)
- [[subagent-final-message-suppressed]] · [[no-guessing-test-first]] · [[w1-infra-postgres]] · [[image-pipeline]] · [[synapse-troubleshooting-reference]]
- 대시보드: https://devpathai.github.io/workflow-dashboard/
