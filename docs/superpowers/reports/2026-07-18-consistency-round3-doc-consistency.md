# 정합성 3차 — 축② 문서↔코드 대조

## 기준

- **목적**: 축② 문서↔코드 대조. 코드측 근거는 동일 세션의 **코드 실측 인벤토리**를 SSoT로 삼고, documents 문서(origin/develop)를 각 실측과 대조해 불일치를 판정한다.
- **참조 인벤토리(코드측 근거)**:
  - `docs/superpowers/reports/2026-07-18-consistency-round3-api-surface.md` — API 표면 실측 **70개**(svc별 표), Flyway 31(shared 중앙집중), 이벤트/토픽, shared 컨트랙트, frontend 라우트
  - `docs/superpowers/reports/2026-07-18-consistency-round3-structure.md` — gateway 라우트 표, gitops 배포 앱(notification-svc 부재), platform `/admin`·`/consents`·`/beta` gateway predicate 미매칭
  - `docs/superpowers/reports/2026-07-18-consistency-round3-code-rules.md` — notification 에러 envelope 미사용, community/lcs `.omc` 추적
- **기준 ref**: 문서 = `git -C D:\workspace\dpa\documents show origin/develop:<파일>`(워킹트리 아님). 코드 레포 = 각 레포 `origin/develop`(읽기 전용). 고정 SHA 대응은 인벤토리 문서와 동일(platform=4c1ca4f, learning=0461c4f, community=043b830, sandbox=a6d802e, ai=69d5e0f, lcs=bd64ada, notification=0afddfd, gateway=c8a1282, frontend=e6be351, shared=ff7f5a6, svc-template=b6c33ee, gitops=ece471d).
- **확정 코드 사실(활용)**: 실측 API 70개(42번 문서 기준 52개, +18: beta 게이팅·consent·avatar/profile·re-engagement·guest assessment). community-svc src/main에 에스컬레이션/현상금/모더레이션 grep 0 = 미구현(재검증 완료, 아래 (b) 참조).

## 방법

**읽은 documents 문서(10)**: `02_ERD_문서.md`, `04_API_명세서.md`, `06_화면_기능_정의서.md`, `17_스케줄.md`, `20_커뮤니티_기능_설계서.md`, `26_학습맥락_자동첨부_구현.md`, `27_MVP_설계서.md`, `44_MVP_잔여_로드맵.md`, `Home.md`, `README.md`.

**읽은 코드 레포 README·CLAUDE.md(12)**: platform/learning/community/sandbox/ai/lcs/notification-svc, gateway, shared, frontend, svc-template, gitops 각 `README.md`(12/12 존재) + `CLAUDE.md`(12/12 존재, 목록만 확인, 내용 대조는 README 중심).

**실행 명령(읽기 전용, 절대경로)**:
- 문서: `git -C 'D:\workspace\dpa\documents' show origin/develop:<파일>` (10개)
- 레포 README: `git -C 'D:\workspace\dpa\<repo>' show origin/develop:README.md` (12개, 전부 exit 0 = 존재)
- 커뮤니티 미구현 교차확정: `git -C 'D:\workspace\dpa\devpath-community-svc' grep -lniE 'escalat|bounty|moderation|sanction' origin/develop -- 'src/main/*.java'` → `reputation/RepPoints.java`만 매치(레벨 상수, 로직 아님); `grep -niE 'bounty'` → exit 1(0건); 컨트롤러 실측 3개(Badge/Activity/Community)
- gitops 배포 교차확정: `git -C '...gitops' ls-tree origin/develop --name-only apps/` + `show origin/develop:argocd/applicationset.yaml`
- platform 컨트롤러 교차확정: `git -C '...platform-svc' ls-tree -r --name-only origin/develop | grep Controller.java` → 8개(Auth·AdminUser·BetaStatus·Consent·Account·Avatar·Profile·User)

## 실측

### 문서별 주장 요지 (대조 결과 요약)

| 문서 | 주장 요지 | 실측 대조 결과 |
|------|-----------|----------------|
| 02_ERD | "Flyway 구현 완료…(마이그레이션 24파일)". 커뮤니티 §8에 moderation_queue·user_sanctions·study_groups·project_showcases·community_ai_answers(escalation_status) 스키마 정의 | Flyway 실측 **31개**(shared 중앙집중) — 문서 "24파일" 과소. 커뮤니티 스키마는 shared V202606251001__community_qna.sql에 존재하나 **로직 미구현**(에스컬레이션/현상금/모더레이션) |
| 04_API | 헤더에 "구현 완료 범위는 42번 기준". 커뮤니티 8.6 모더레이션·8.2 bounty·에스컬레이션 엔드포인트를 표로 기재. §9 알림에 TARGET/구현 라벨. Admin §10 대량 엔드포인트 | 04 표의 상당수가 실측 70개에 없음(아래 (d) 대조표). 에스컬레이션·bounty·moderation·admin/community/*·admin/ai/*·admin/finops/* 등 미구현. 알림 §9는 라벨 정확 |
| 06_화면 | 화면 인벤토리에 SCR-A-COM-001(모더레이션 큐)·COM-005/006(자유·프로젝트)·COM-007(프로필) 등 MVP ✔. 헤더에 "화면 목록이 실API 구현 완료를 의미하지 않음" 명시 | 프론트 라우트 실측(web 15경로)엔 커뮤니티 홈/작성/상세만, 자유·프로젝트·프로필 라우트 없음. 헤더 면책으로 불일치 완화(관찰) |
| 17_스케줄 | §0 "백엔드 총 52 엔드포인트"(2026-07-02). §0.1 현황 스냅샷 svc별 엔드포인트 수 명기. 평판 "핵심 완료", moderation·레벨게이트·Silver/Gold "후속" | 총계 실측 **70**(52 과거치). §0.1 svc별 수치도 과거 스냅샷(예 platform 4→실측 16, notification device 2종→실측 5). 평판/moderation 상태 서술은 코드와 정합 |
| 20_커뮤니티 | 헤더 "Q&A·투표·태그·평판·배지·남용방지(10 엔드포인트) 구현, moderation·검색·북마크·팔로우·study-group·project-showcase는 TARGET". 본문 §4 에스컬레이션·§4.4 bounty·§7 모더레이션 상세 설계 | community 실측 **11개**(헤더 "10" 근사). 에스컬레이션/bounty/moderation은 **src/main grep 0 = 미구현** 교차확정. 헤더가 이들을 TARGET로 표기 → **정합**(20 설계서 자체는 오탐 아님; 04가 이를 구현처럼 표로 나열한 게 문제) |
| 26_학습맥락 | 헤더 "lcs-svc 스냅샷 draft/commit/조회·preferences 6개 엔드포인트 구현, sanitize_rules·이벤트 스트림(9 토픽)은 TARGET". 경로 `/lcs/*`로 정정됨 명시 | lcs 실측 **6개**(draft/commit/조회2/preferences GET·PUT) — **정합**. lcs README도 동일 6개. Kafka 미참여(실측)와 "이벤트 스트림 TARGET" 정합 |
| 27_MVP | 2026-04-23 초안. 헤더에 17·36번 우선 안내. 결제(토스페이먼츠) 필수 기능 서술 | 결제 미구현(실측 payment/subscription 컨트롤러 0). 44번이 "① 결제만 미착수"로 최신화 → 27 자체는 초안 면책 |
| 44_MVP잔여 | 2026-07-17 갱신: ④설정·②마이페이지·③GoogleOAuth **머지완료**, ①결제만 미착수. "토스페이먼츠" | ④consent·②avatar/profile·③google 실측 존재(platform 컨트롤러 8종) → **정합**. 단 결제 PG는 MEMORY상 "PortOne"인데 44는 "토스페이먼츠"(관찰) |
| Home / README | 문서 인덱스. 04를 "커뮤니티 엔드포인트", 26을 "LCS 구현 스펙"으로 링크. 상태 라벨 없음 | 인덱스 성격상 직접 불일치 낮음. 단 README "도메인 서비스 5개"(§관련 레포)는 실제 7 svc와 불일치(관찰) |

### 04_API 명세 vs 실측 70 대조표

**범례**: ✅ 04·실측 일치(경로/의미) · ⚠️ 경로/형태 상이하나 대응 존재 · ❌04 04에만 있고 실측 없음(미구현/미노출) · ➕실측 04에 없는 실측 엔드포인트

#### 04에 있는데 실측에 없음 (❌04 = 미구현·04 과다표기)

| 04 위치 | 04 엔드포인트 | 판정 근거(실측) |
|---------|---------------|-----------------|
| 04 §1 (인증) | `POST /users/me/restore`, `GET /users/me/github-profile`, `POST /users/me/github-profile/refresh`, `PUT /users/me` | platform 실측에 restore/github-profile 컨트롤러 없음. `PUT /users/me`도 없음(프로필 수정은 `PUT /users/me/profile`) |
| 04 §2 | `POST /onboarding/profile` | learning 실측에 onboarding/profile 없음(assessments 계열만) |
| 04 §4 (콘텐츠) | `GET /contents/{slug}/code-blocks/{blockId}`, `GET /contents/search` | learning 실측 콘텐츠=`/contents/{idOrSlug}`·`/progress`·`/me/progress`만. code-blocks/search 없음 |
| 04 §5 (Sandbox) | `POST /sandbox/sessions`, `GET /sandbox/sessions/{id}`, `GET .../stream`, `POST .../kill`, `GET /sandbox/quotas/me` | sandbox 실측=`POST /sandbox/run`(SSE) + `/internal/sandbox/sessions/**`. 04의 sessions/kill/quotas 경로군 부재 |
| 04 §6 (AI리뷰) | `GET /ai-reviews/sandbox/{id}`, `POST /ai-reviews/{id}/feedback` | ai 실측 경로는 `/reviews?sandboxSessionId=`·`/reviews/{id}`·`/reviews/{id}/feedback`. 04 `/ai-reviews/*` prefix 상이(⚠️ 아래 참조) |
| 04 §7 (멘토) | `POST /sessions/{id}/messages`(SSE), `GET /sessions`, `GET .../messages`, `POST /messages/{id}/feedback` | ai 실측 멘토=`POST /ai-mentor/sessions` 1종만. 메시지 스트리밍/목록/히스토리/피드백 미구현 |
| 04 §8.1~8.7 커뮤니티 | posts CRUD, bookmark, report, projects, follow, notifications, tags/{name}, users/{id}/reputation-events, leaderboard, peers/this-week, `bounty`, `ai-answer`, `escalate` | community 실측 11개엔 posts(GET)·questions·answers·vote·accept·tags(GET)·users/{id}/badges·me/activity만. bookmark/report/projects/follow/notifications/bounty/escalate/ai-answer 전부 미구현(**escalate·bounty grep 0 교차확정**) |
| 04 §8.6 / §10.6 모더레이션 | `/community/moderation/queue`, `/community/moderation/vote/{id}`, `/admin/community/sanctions` | community moderation grep 0 = 미구현. platform admin 실측=users·allowlist·approve만(community/sanctions 없음) |
| 04 §9 알림 | `GET /notifications/me`, `PUT /{id}/read`, `PUT /read-all` | notification 실측=devices 2종+prefs 2종+internal 1종. inbox 조회/읽음 미구현(04가 **TARGET 라벨 부여 → 정합**) |
| 04 §10 Admin 전체 | contents·dashboard·finops·ai/quality·reports·sanctions·questions·announcements·sandbox 관리(약 30+ 엔드포인트) | platform admin 실측=`GET /admin/users`·`POST /admin/users/{id}/approve`·`POST /admin/allowlist` 3종. 나머지 admin 대량 엔드포인트 전부 미구현 |

#### 04에 없는데 실측에 있음 (➕실측 = 04 미반영, 이후 머지 기능)

| svc | 실측 엔드포인트 | 성격 |
|-----|-----------------|------|
| platform | `POST /auth/oauth/token` | 04는 `/oauth2/authorization/*` 리다이렉트만 기재, 실측 토큰 교환 경로 |
| platform | `GET /beta/status`, `GET /admin/users`, `POST /admin/users/{id}/approve`, `POST /admin/allowlist` | **베타 게이팅**(C1/C2a) — 04·17 미반영 |
| platform | `POST /consents`, `GET /consents/me`, `POST /consents/{type}/revoke` | **설정/동의**(44 ④) — 04 미반영 |
| platform | `DELETE /users/me`, `POST /users/me/avatar`, `DELETE /users/me/avatar`, `GET/PUT /users/me/profile` | **마이페이지**(44 ②) avatar/profile — 04는 `PUT /users/me`로만 추상 표기 |
| learning | `POST /onboarding/assessments/guest`, `/guest/{gid}/next|answer|complete` | **게스트 진단** 4종 — 04엔 guest POST 1종만 |
| learning | `GET /internal/contents/{id}`, `POST /internal/contents/similar` | svc-to-svc 내부 — 04 미기재(정상) |
| learning | `GET /learning-paths/{id}/rationale`, `/me/this-week`, `POST /tasks/{taskId}/complete`, `/me/regenerate` | 04에 일부(this-week/rationale/regenerate) 있음(⚠️경로 `/learning-paths/*` 정합), tasks/complete는 04 미기재 |
| community | `GET /community/users/{userId}/badges`, `GET /community/me/activity`, `GET /community/questions/similar` | 배지·활동·유사질문 — 04 미반영(04는 users/{id} 프로필로만) |
| ai | `POST /ai/embed`, `POST /ai/path/generate`, `POST /ai/re-engagement` | AI Gateway 내부 + **재참여**(리텐션) — 04 미반영 |
| lcs | `/lcs/snapshots/draft|commit|{id}|by-question`, `/lcs/preferences` GET·PUT (6종) | LCS 전체 — 04 §커뮤니티에 미표기(26번 문서엔 정합) |
| notification | `POST/DELETE /notifications/devices`, `GET/PUT /notifications/prefs/me`, `GET /notifications/internal/prefs/timezones` | devices는 04 §9 구현라벨 정합. **prefs 2종+internal은 04 미반영** |

#### 경로 상이(⚠️) 요약

- AI 리뷰: 04 `/ai-reviews/*` ↔ 실측 `/reviews/*` (prefix 상이, gateway 라우트도 `/reviews/**`).
- 멘토: 04 `/ai-mentor/sessions/{id}/messages` 등 ↔ 실측 `/ai-mentor/sessions` 단일.
- 학습경로/콘텐츠: 04 `/contents/{slug}` ↔ 실측 `/contents/{idOrSlug}` (의미 정합).

## 불일치 후보

### (a) 문서가 "미구현·스켈레톤·예정"이라는데 실측에 존재 → 불일치 (과거 라운드 주종 패턴)

| # | 문서위치(파일:요지) | 코드근거(명령+출력요지) | 후보 | 수정방향 |
|---|---------------------|--------------------------|:----:|----------|
| A-1 | `17_스케줄.md` §0.1 현황표: "인증/사용자 = platform-svc 4 엔드포인트", "알림 = device 2종" (2026-07-02 스냅샷) | `platform-svc ls-tree grep Controller.java` → **8 컨트롤러/16 엔드포인트**(auth3·admin3·beta1·consents3·users me/avatar/profile6). notification 실측 **5**(devices2·prefs2·internal1) | **P1** | §0.1 표를 실측 70 기준으로 갱신(platform 16·learning 22·community 11·sandbox 3·ai 7·lcs 6·notification 5). "52 엔드포인트" 문구도 70으로 |
| A-2 | `17_스케줄.md` §0: "백엔드 총 52 엔드포인트(2026-07-02 기준)" | api-surface 실측 합계 **70**(+18: beta·consent·avatar/profile·re-engagement·guest) | **P1** | 총계 70으로 갱신 + 증가분 출처 1줄 |
| A-3 | `02_ERD_문서.md` 헤더: "마이그레이션 24파일" | `shared ls-tree -r grep db/migration \| grep -c .sql` = **31** | **P1** | "31파일"로 정정(V…beta_allowlist·consent·weekly_report 등 포함) |
| A-4 | `platform-svc/README.md` 담당 도메인표: `user`(OAuth2 GitHub)·`github` 2모듈만. "OAuth2(GitHub)" | 실측 컨트롤러 8종: beta(AdminUser·BetaStatus)·consent·avatar·profile 포함. 44번은 google OAuth·consent·마이페이지 머지완료로 기록 | **P1** | README에 beta 게이팅·consent(동의)·mypage(avatar/profile)·admin allowlist 모듈 추가, OAuth "GitHub·Google" 반영 |
| A-5 | `04_API_명세서.md` §1 로그인 응답 `plan:"FREE"` / §5.2·§11 Pro 한도 등 유료 표기 산재 | 결제·plan/tier 미구현(44번 "①결제만 미착수" 최신). platform grep에 subscription/payment 0 | **P2** | 유료/plan 표기에 "결제 미구현(44 ① 대기)" 주석. (04 헤더가 이미 42번 위임하나 표 본문은 미표시) |

### (b) 문서가 존재를 주장하는데 실측에 없음 → 불일치 (특히 20 커뮤니티 교차확정)

| # | 문서위치 | 코드근거 | 후보 | 수정방향 |
|---|----------|----------|:----:|----------|
| B-1 | `04_API_명세서.md` §"에스컬레이션(CEO 리뷰 보강 6)": `POST /community/questions/{id}/escalate` + community.ai_answer.escalated 등 이벤트 표 | `community grep -lniE 'escalat…' src/main` → **RepPoints.java(레벨 상수)만** 매치, escalate 컨트롤러/서비스 0. 컨트롤러 실측=Badge·Activity·Community 3개 | **P1** | 04에서 escalate·에스컬레이션 이벤트 표에 **TARGET(미구현)** 라벨 명시(20 설계서 헤더처럼) |
| B-2 | `04_API_명세서.md` §8.2 `POST /community/questions/{id}/bounty`, §4.4 현상금 | `community grep -niE 'bounty' src/main` → **exit 1(0건)**. ERD community_questions.bounty_amount 컬럼만 존재(스키마), 로직 없음 | **P1** | 04 bounty 행에 TARGET 라벨. 20 §4.4/9.2는 이미 Phase 2로 분류(정합) |
| B-3 | `04_API_명세서.md` §8.6·§10.6 모더레이션: `/community/moderation/queue`·`/vote/{id}`·`/admin/community/sanctions` | community moderation grep 0. community README "moderation…TARGET, 아직 미구현" 명시. platform admin 실측=users·approve·allowlist뿐 | **P1** | 04 모더레이션 표에 TARGET 라벨(20 헤더·community README와 일관되게) |
| B-4 | `04_API_명세서.md` §10 Admin 대량 엔드포인트(contents·dashboard/overview·finops·ai/quality·reports·announcements·questions·sandbox 관리 ~30+) | platform admin 실측 3종(users·approve·allowlist)만. 그 외 admin/* 컨트롤러 없음 | **P1** | 04 §10 Admin 표에 "구현=users/approve/allowlist 3종, 그 외 TARGET" 상태열 추가 |
| B-5 | `04_API_명세서.md` §5 Sandbox `sessions`·`kill`·`quotas`, §7 멘토 messages/history | sandbox 실측=`/sandbox/run`(SSE)+internal뿐. ai 멘토=`/ai-mentor/sessions` 1종 | **P1** | 04 §5/§7을 실측 계약(run SSE·mentor sessions)으로 정정 또는 TARGET 라벨 |
| B-6 | `02_ERD_문서.md` §8.7 study_groups·project_showcases, §8.4 moderation_queue·user_sanctions | 해당 로직 community src/main 미구현(스키마는 shared Flyway 존재 여부와 무관하게 서비스 로직 0) | **P2** | ERD는 목표 스키마라 유지 가능하나, 헤더에 "커뮤니티 moderation/study/project 스키마는 로직 미구현(TARGET)" 1줄 |

### (c) 42번(7-02) 이후 머지 기능의 문서 반영 여부

| # | 기능(머지) | 문서 반영 상태 | 코드근거 | 후보 | 수정방향 |
|---|-----------|----------------|----------|:----:|----------|
| C-1 | 베타 게이팅 C1/C2a/C2b | 04·17·platform README **미반영**(어디에도 beta 엔드포인트/화면 없음) | 실측 `GET /beta/status`·`/admin/allowlist`·`/admin/users/{id}/approve`; frontend web `/beta-pending` 라우트; user.beta.waitlisted/approved 이벤트 | **P1** | 04 §1/§10에 beta 게이팅 엔드포인트 신설, 06에 /beta-pending 화면, 17 §0.1 반영 |
| C-2 | 에러 envelope 표준화(5 svc) | 04 §"공통 에러 응답" envelope 예시 존재하나 "5 svc 채택/1 미채택(notification)" 서술 없음 | code-rules 실측: 사용5(platform·community·sandbox·ai·lcs)·독자1(learning)·**미사용1(notification)** | **P2** | 04 공통 에러 절에 "shared ApiExceptionHandler 채택 현황(notification 미채택=TARGET)" 주석 |
| C-3 | Tier-2 웹 실API·마이페이지 P1~P4·설정/동의·Google OAuth | 44번 2026-07-17 갱신에 **반영됨**(머지완료 표기) | 실측 consent·avatar/profile 컨트롤러, frontend `/consent`·`/mypage`·`/settings` 라우트 | — | 44 정합. 단 04/06에 mypage/settings/consent 엔드포인트·화면 미반영(A-4·C-1과 함께 처리) |
| C-4 | 결제 마스터 spec(구현 미착수) | 44번 "①결제만 미착수" 정확. 단 결제 PG명 **불일치** | 44=토스페이먼츠·17=토스페이먼츠 ↔ MEMORY/평판노트=PortOne(통합 PG mock 선구현 마스터 spec, platform #28) | **P2** | 결제 PG명 SSoT 확정(PortOne vs 토스). 44·17·27 문구 통일 |
| C-5 | 웹 이미지(WS-B) | 문서 직접 반영 대상 아님(배포 산출물) | gitops apps/devpath-web 존재 | — | 해당 없음 |

### (d) 04 엔드포인트 표 vs 실측 70 건별 (요약 — 상세는 위 "실측" 대조표)

- **04에만 있고 실측 없음(❌04)**: 인증 restore/github-profile·onboarding/profile·contents code-blocks/search·sandbox sessions/kill/quotas·mentor messages/history·커뮤니티 posts CRUD/bookmark/report/projects/follow/notifications/bounty/escalate/ai-answer·moderation·admin 대량(~30+). → 04는 **v1 목표 계약**이라 상당수가 의도된 TARGET이나 **상태 라벨 부재**가 핵심 문제(§9 알림처럼 라벨링 필요).
- **실측에 있고 04 없음(➕실측)**: beta(4)·consent(3)·avatar/profile(6 중 신규)·guest assessment(4)·ai/embed·path·re-engagement(3)·lcs(6)·notification prefs/internal(3)·community badges/activity/similar(3)·learning tasks/complete. → 42번 이후 머지분이 04에 **역류 미반영**.
- **경로 상이(⚠️)**: `/ai-reviews/*`→`/reviews/*`, 멘토 messages 계층 축약, `/contents/{slug}`→`{idOrSlug}`.

## 관찰 (판정 보류·대형)

- **O-1 (04 문서 성격 = v1 목표 계약)**: 04 헤더가 "구현 범위는 42번 기준"으로 위임하고 있어, 04의 미구현 엔드포인트를 곧바로 "허위 주장"으로 보긴 어렵다. 다만 §9 알림만 TARGET/구현 라벨을 달고 나머지(에스컬레이션·bounty·moderation·admin·sandbox sessions·mentor messages)는 라벨이 없어 **독자가 구현으로 오인**한다. → 대형 수정: 04 전 섹션에 상태열(구현/TARGET) 도입이 근본 해법(리팩토링 트랙 후보).
- **O-2 (20 커뮤니티 설계서는 오탐 아님)**: 20 헤더가 moderation·study-group·project-showcase·검색·북마크·팔로우를 명시적 TARGET로 선언하고 §4.4 bounty·수료자 라운지를 Phase 2로 분류 → **20 자체는 코드와 정합**. 문제는 **04가 20의 미래 기능을 현재 엔드포인트 표로 옮겨 적은 것**(B-1~B-3). 축② 불일치의 진원지는 20이 아니라 04.
- **O-3 (README "도메인 서비스 5개")**: documents `README.md` §관련 레포가 "API Gateway + 도메인 서비스 5개"로 기재하나 실제 백엔드 svc는 **7개**(platform·learning·community·sandbox·ai·lcs·notification). Home/README는 인덱스라 영향 낮으나 수치 정정 권장(P2).
- **O-4 (gitops README 스테일 + notification 배포 누락 교차확정)**: gitops README 구조 블록은 `apps/devpath-frontend/base`를 나열하나 실제 `apps/`엔 **devpath-admin·devpath-web**(frontend 분리)이며 **devpath-notification-svc 부재**. `applicationset.yaml`은 `apps/*` 자동 발견(revision=**main**)이므로 notification-svc는 apps/에 없어 **배포 대상에서 자동 제외** — 축① P1(실배포 시 `/notifications/**` 502) 재확인. 문서(03 §2 모듈 구성)는 notification을 정식 서비스로 명시 → 코드(gitops)↔문서 불일치. (applicationset revision=main인데 본 점검 기준은 develop인 점은 별도 관찰.)
- **O-5 (frontend 화면 vs 라우트)**: 06 화면 인벤토리는 자유게시판(COM-005)·프로젝트(COM-006)·프로필(COM-007)을 MVP ✔로 두나 frontend web 라우트 실측엔 없음(community 홈/new/:id만). 06 헤더가 "화면 목록≠실API 구현"으로 면책하여 P2 관찰. 44 로드맵상 커뮤니티 확장은 MD3 Tier-2라 시기적으로 정합.
- **O-6 (결제 PG SSoT 미확정)**: C-4 — 문서(44·17=토스페이먼츠)와 MEMORY(PortOne 마스터 spec platform #28)가 상충. 코드 실측상 결제 자체가 미구현이라 어느 쪽도 "구현으로 위배"는 아니나, 착수 전 PG SSoT를 문서에서 확정해야 함(판정 보류, 사용자 결정 필요).
- **O-7 (CLAUDE.md 12/12 존재, 내용 대조 미수행)**: 12개 레포 전부 `CLAUDE.md`·`README.md` 존재(스킵 0건). 본 축은 README 도메인표를 상태 대조의 1차 소스로 삼았고 CLAUDE.md 본문(작업규칙 중심)은 축③에서 다룸. CLAUDE.md의 기능 상태 서술 대조는 필요 시 후속.
