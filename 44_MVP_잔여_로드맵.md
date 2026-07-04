# 44. MVP 잔여 로드맵 (설정 → 마이페이지 → Google OAuth → 결제)

> **목적**: [27_MVP_설계서](./27_MVP_설계서.md) 코어 흐름 완성 이후 **남은 MVP 필수 항목**을 실행 순서로 배치한다. 각 기능은 이 로드맵 하위에서 개별 spec→plan 사이클로 구현한다(A→C→B 로드맵과 동일 운영 방식).
>
> **작성일**: 2026-07-04 · **근거**: 코드 실측(2026-07-04) + [27_MVP_설계서](./27_MVP_설계서.md) §1-2·§3-1
>
> **주의(정합성 규칙)**: 상태 표기는 2026-07-04 코드 실측 기준. 착수 전 각 레포 `origin/develop` 실측으로 재확인한다(문서가 코드보다 뒤처질 수 있음).

## 현재 상태 요약 (실측 2026-07-04)

**완성된 MVP 코어**: 15문항 적응형 진단(learning `/onboarding/assessments/**`), AI 로드맵 생성(learning `/learning-paths/me/generate`→ai `/ai/path/generate`), AI 멘토(ai `/ai-mentor/**`), 학습맥락 자동첨부 LCS(lcs-svc), Q&A 게시판(community-svc), GitHub OAuth 로그인(platform), 랜딩 페이지(devpath-landing-page 별도 레포). 부가로 평판·배지·sandbox·참여촉진(리텐션)도 구현 완료.

**남은 MVP 필수 항목 4개** — 실행 순서 **④ → ② → ③ → ①**:

| 순 | 항목 | 화면/기능 근거 | 상태 | 규모 |
|:--:|------|------|:--:|:--:|
| ④ | 설정 / 개인정보 동의 | §3-1 화면 10 | ❌ 전용 화면 없음 | 소~중 |
| ② | 마이페이지 | §3-1 화면 9 | ❌ `features/mypage` 없음 | 중 |
| ③ | Google OAuth | §1-2 · §3-1 화면 2 | ⚠️ GitHub만(google 미등록) | 소 |
| ① | 결제(토스페이먼츠) | §1-2 · §3-1 화면 9 | ❌ 전무 | 대 |

## 실행 순서 근거 (④→②→③→①)

- **④ 설정/동의 먼저**: 법적 필수(약관·개인정보 동의·14세 차단)라 우선순위 높고, 독립적이며 규모가 작아 빠르게 완결. 다른 항목에 의존하지 않는다.
- **② 마이페이지 다음**: 사용자 자기정보 허브. **결제 UI(구독 정보·결제 관리)가 안착할 뼈대**이므로 결제보다 먼저 골격을 세운다. 백엔드는 대부분 기존 조회 API 조합이라 신규 도메인 최소.
- **③ Google OAuth**: 로그인 다양화. platform OAuth 설정 확장이라 독립·소규모. 결제 전 아무 때나 가능하나, 마이페이지·설정이 로그인 이후 화면이라 그 뒤에 배치.
- **① 결제 마지막**: 최대·최고 복잡. 마이페이지 뼈대 위에 구독 섹션을 얹고, 유료/무료 게이팅을 전 기능에 반영. **외부 의존(토스페이먼츠 상점 계약·키, 사업자 등록)에 게이팅**되므로 나머지가 안정된 뒤 착수하는 것이 리스크상 유리.

## 항목별 범위 스케치

> 각 항목의 상세 설계·구현은 별도 spec→plan에서 확정. 여기서는 경계·의존·산출물만.

### ④ 설정 / 개인정보 동의 화면
- **frontend**(`apps/web/lib/src/features/settings` 신규): 약관·개인정보 처리방침 동의(법적 필수, [33_개인정보_처리방침](./33_개인정보_처리방침.md)·[34_동의화면_마이크로카피](./34_동의화면_마이크로카피.md) 반영), 알림 설정(이메일/푸시 on/off), 14세 미만 차단 고지, 로그아웃·계정.
- **backend**: 동의 이력 저장(platform `user_consents` 신규 or 기존 user_profiles 확장) + 기존 `user_notification_prefs`(notification-svc) 연결. ERD([02_ERD](./02_ERD_문서.md)) 갱신.
- **의존**: 없음(로그인만 전제). 산출물: 설정 화면 + 동의 기록 API.

### ② 마이페이지 화면
- **frontend**(`features/mypage` 신규): 프로필(닉네임·이메일·역할), 진행 중 로드맵 상태, 완료 콘텐츠(X/Y), 작성 질문·답변 수, **구독 정보 섹션(placeholder — 결제 후 결선)**, 설정 진입.
- **backend**: 대부분 기존 조회 조합(dashboard `/dashboard/me`·path `/learning-paths/me`·community 내 활동). 신규 최소(활동 요약 집계가 없으면 추가).
- **의존**: ④(설정 진입 링크). 산출물: 마이페이지 화면 + 활동 요약(필요 시 API).

### ③ Google OAuth
- **backend**(platform): `spring.security.oauth2.client.registration.google` 추가(+provider 기본). `OAuth2LoginSuccessHandler`는 provider-무관(registrationId 기반)이나 google attrs(`sub`/`email`/`name`) 매핑 확인. 축 B의 `OAuthWebLoginE2ETest`를 google 케이스로 확장.
- **frontend**: 로그인 화면에 Google 버튼 + `oauth_launcher`가 `/oauth2/authorization/google`로 리다이렉트.
- **의존**: 없음(축 B OAuth 흐름 위). 외부: Google Cloud OAuth 클라이언트 등록(런북). 산출물: Google 로그인 경로 + e2e.

### ① 결제 (토스페이먼츠)
- **backend**(platform, 신규 도메인): 구독(subscription)·결제(payment) 도메인, 유저 `plan/tier` 필드, DB 스키마(subscriptions·payments·plan 이력), 토스페이먼츠 연동(빌링키 정기결제·해지·웹훅), 무료→유료 상태 전이.
- **게이팅**: AI 멘토 횟수 등 유료 기능 제한([27](./27_MVP_설계서.md) 시나리오 4). 기존 quota/killSwitch 표면(프론트 `isQuota`)과 연결.
- **frontend**(`features/billing` 신규 + 마이페이지 구독 섹션): 결제 화면(토스 결제위젯), 무료→유료 전환 모달, 구독 관리(해지)·결제 내역.
- **의존**: ②(마이페이지 구독 섹션 안착), ④(동의/약관 — 결제 약관). 외부: **토스페이먼츠 상점 계약·API 키, 사업자 등록**(런북·게이팅). 산출물: 구독/결제 백엔드 + 결제 화면 + 게이팅. **H1(지불의사) 검증의 핵심.**

## 운영 방식

1. 이 로드맵(문서 44) + [45_Tier3_확장_기능_카탈로그](./45_Tier3_확장_기능_카탈로그.md) 커밋.
2. **④부터** 순서대로: 각 기능 brainstorming→spec(해당 레포 `docs/superpowers/specs/`)→plan→subagent-driven 구현→검증→PR(develop 2단계 흐름).
3. ①(결제)는 외부 의존(토스 키·계약) 확보 시점에 착수. 미확보면 백엔드 도메인·스키마·프론트 UI까지 mock/테스트로 선구현하고 실연동만 게이팅.

## 관련 문서
- [27_MVP_설계서](./27_MVP_설계서.md) §1-2 필수 기능 · §3-1 화면 10개
- [02_ERD](./02_ERD_문서.md) · [04_API_명세서](./04_API_명세서.md) — 결제/구독·동의 스키마 갱신 대상
- [33_개인정보_처리방침](./33_개인정보_처리방침.md) · [34_동의화면_마이크로카피](./34_동의화면_마이크로카피.md) — ④ 근거
- [45_Tier3_확장_기능_카탈로그](./45_Tier3_확장_기능_카탈로그.md) — MVP 이후 확장(문서만)
