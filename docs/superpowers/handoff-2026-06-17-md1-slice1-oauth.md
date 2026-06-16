# 세션 핸드오프 — MD1 슬라이스 #1 OAuth/인증 착수 (2026-06-17)

> **목적**: 일정 재정렬·대시보드·SSoT 이관이 끝났다. 다음 본작업은 **MD1 슬라이스 #1 — OAuth/인증(게이트)** 의 실연동이다. 이 슬라이스는 모든 인증 데이터 호출의 선행 게이트이므로 MD1의 첫 착수 지점이다. 본 문서로 다음 세션에 이관한다.
> **원칙**: 각 레포 CLAUDE.md 절대 조건(추측 금지·테스트 우선·문제 시 코드 분석) + 브랜치 전략(main 보호·develop 경유 2단계 PR). 본 문서의 "현재 상태"는 2026-06-17 실측.

---

## 1. 직전까지 완료 (이번 세션, 참고)

- **대시보드 일정 재정렬**: 주차(W1~W24)/마일스톤(M1~M6) → 단계(DONE·MD1~MD4) + 수직 슬라이스 #1~12. PR #5 머지.
- **SSoT 이관**: 9개 서비스 레포 `docs/project-management/workflow/WORKFLOW_<track>_*.md`가 진척 원본(SSoT). 대시보드는 `DOCS_DIR=<repo>/docs/project-management npm run sync -- <repo-id>`로 수집. 10개 PR 머지.
- **배포**: workflow-dashboard develop→main(PR #7) → GitHub Pages 배포 성공 → https://devpathai.github.io/workflow-dashboard/
- **레포 상태**: 9개 서비스 레포 모두 `develop` 정리 완료, W1 인프라 baseline(PG·shared 의존·CI) 완료. 각 repo 진척 md에 MD1 #1 항목이 `- [ ]`(계획)로 존재.
- 설계/계획 산출물: `workflow-dashboard/docs/superpowers/{specs,plans}/2026-06-1{6,7}-*`.

## 2. 다음 본작업: 슬라이스 #1 — OAuth/인증 (게이트)

> 출처: `documents/17_스케줄.md` §2 MD1 (L81~), §4 의존성(#1이 모든 후속 슬라이스 선행), §5 외부 의존성 타임라인. 목표(MD1 완료기준): 가입(OAuth)→진단→경로 p50 < 8분, web 끝단간 실동작 — 그 **첫 단추가 #1**.

**참여 레포 & 역할:**
| 레포 | 역할 | 슬라이스 #1 태스크(17 §2 본문) |
|---|---|---|
| devpath-platform-svc | 인증 코어 | Spring Security 7 + OAuth2 Client(**GitHub → Google → 카카오 순**), JWT + Refresh Cookie, `UserRegisteredEvent` Outbox |
| devpath-shared | 스키마 | `users`·`user_oauth_identities`·`user_profiles` Flyway 마이그레이션 (W1 users 골격 확장) |
| devpath-gateway | 엣지 | OAuth2 엣지 + JWT 검증 라우팅 |
| devpath-frontend | 프론트 실연동 | web `AuthController` 목→실API 전환 + 통합테스트 |
| (횡단) | 외부 | 카카오/Google OAuth 앱 심사 신청, Anthropic 프로덕션 한도 신청 |

## 3. ⚠️ 선행 블로커 — 외부 신청 (리드타임, 즉시 착수)

> 17_스케줄 §5. **코딩 전에 큐에 넣어야 게이트가 안 막힌다.** 사용자가 콘솔에서 진행(에이전트 대행 불가).

| 의존성 | 소요 | 비고 |
|---|---|---|
| GitHub OAuth | 즉시 | 가장 먼저 연동 — #1 최초 provider |
| 카카오 OAuth 심사 | 3~7일 | 비즈앱 전환 시 +2주(이메일 등 동의항목) |
| Google OAuth 동의 화면 | 2~6주 | 100명 이하 **테스트 모드 우선**(비민감 scope `openid email profile`) |
| Anthropic 프로덕션 한도 | 1~2주 | #3 학습경로 전 필요. 한도 전 개발 키로 진행 |

- 키·시크릿·redirect URI는 **절대 커밋 금지**(각 repo CLAUDE.md). redirect URI/scope/동의항목 정확값은 스펙 단계에서 확정.

## 4. 근거 문서 (documents 레포)

- **17_스케줄.md** §2(MD1 상세)·§4(빌드 순서)·§5(외부 의존성)·§8(리스크: Spring Boot 4 GA 미출시 시 **3.4.x 폴백 — ADR 001**)
- **02_ERD_문서.md** — users/user_oauth_identities/user_profiles 컬럼·관계 (shared Flyway 근거)
- **03_프로젝트_아키텍처_정의서.md** — gateway↔platform 경계, 이벤트(Outbox) 흐름
- **04_API_명세서.md** — auth 엔드포인트(로그인 콜백·토큰 갱신·로그아웃) 계약
- **07_요구사항_정의서.md** — FR 인증 요구사항
- **11_테스트_전략서.md** — 통합테스트·골든 스모크 기준
- W1 선행자산: shared 중앙 Flyway(공통 규약 `set_updated_at`·users 골격·법적 분리보관 `dormant_user_archives` 정보통신망법 §29) — **확장만** 하면 됨.

## 5. 권장 시작 흐름

슬라이스 #1은 **4개 repo 횡단 + 목→실 전환**이라 통합 리스크가 크다. 다음 순서 권장:

1. **외부 신청 먼저**(§3) — 리드타임 흡수.
2. **brainstorming**(선결 결정) → spec → plan(TDD) → 각 repo develop PR. (대시보드 작업과 동일 워크플로.)
3. **프론트 계약 사전검증**: P4~P5 교훈 — 플랜 API 가정을 `dp_core`/`dp_design` 실제 시그니처로 먼저 검증한 뒤 구현.

**선결 결정 후보(브레인스토밍에서):**
- D-1: OAuth provider 1차 범위 — GitHub만 먼저 끝단간(권장, 심사 무관) vs GitHub+Google 동시.
- D-2: 토큰 전략 세부 — JWT(access) + Refresh Cookie(HttpOnly/Secure/SameSite) 구체 + 회전 정책.
- D-3: gateway ↔ platform 토큰 검증 분담 — 엣지에서 JWT 검증 vs platform 위임.
- D-4: shared 스키마 마이그레이션 번호·컬럼 확정(02_ERD 대조), users 골격 확장 범위.
- D-5: `UserRegisteredEvent` Outbox 소비처(진단 #2 세션 이관 연계) 범위 — #1에 어디까지.

## 6. 빌드 후 다음 슬라이스

#1 게이트 완료 → #2 진단(learning) → #3 학습경로 1st Aha(ai+learning, Claude SSE). MD1 완료기준 = OAuth→진단→경로 p50 < 8분 web 실동작(staging).

## 7. 주의

- **추측 금지·테스트 우선**: 인증은 보안 직결 — 시크릿 관리·토큰 검증은 well-tested 라이브러리(Spring Security) 사용, 자체 구현 지양.
- **브랜치 전략**: 각 repo develop에서 분기 → develop PR. main 직접 금지. 9개 레포 모두 develop 존재.
- **서브에이전트 Scope Lock**: 위임 시 단일 Task 경계 못박고 컨트롤러 직접 검증.
- 동일 스택 선행 프로젝트 교훈은 `documents/24`(Synapse 트러블슈팅) 참고.

## 8. 관련

- 메모리: 대시보드 재정렬·SSoT(`dashboard-schedule-realign-pending`), W1 인프라(`w1-infra-postgres`), 이미지 파이프라인(`image-pipeline`), 절대 원칙(`no-guessing-test-first`), Synapse 참고(`synapse-troubleshooting-reference`).
- 대시보드(진척 현황): https://devpathai.github.io/workflow-dashboard/
