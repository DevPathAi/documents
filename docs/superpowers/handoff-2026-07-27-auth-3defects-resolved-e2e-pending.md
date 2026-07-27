# Handoff — 인증 결함 3겹 해소 (2026-07-27 저녁): E2E 완주만 남음

> 다음 세션 착수용. 상세 SSoT: devpath-gitops `docs/runbook-k3s-bootstrap.md`(**✅해소 섹션**·트러블슈팅 표 20행) + platform/frontend `docs/superpowers/specs/2026-07-27-*-design.md` 3건. 이 문서는 [handoff-2026-07-27-ws-d-deployed-e2e-open.md](handoff-2026-07-27-ws-d-deployed-e2e-open.md)의 🔴 OPEN을 종결하는 후속이다.

## 이 세션에서 한 것 — 구 🔴 OPEN(로그인 후 동의화면 401) 종결

증상 하나("동의 화면 진행 불가·401")에 **서로 다른 결함 3개**가 겹쳐 있었고, 전부 수정·배포·운영 실측 검증까지 마쳤다.

| # | 계층 | 결함 | 수정 | PR |
|---|------|------|------|-----|
| ① | platform | `RefreshTokenStore.rotate()` 비원자 단일-사용 회전 × 동시 refresh(콜백 이중 부트스트랩·인터셉터 재시도) → 뒤따른 요청 401 → 인터셉터 `store.clear()` 세션 파괴 | 회전 유예창 30s (`devpath.auth.refresh-rotate-grace`, 0=비활성) | platform#40 → 릴리스 #41 |
| ② | frontend 3앱 | refresh/retry를 **같은 dio로 재진입** → refresh 401 시 QueuedInterceptor 에러 큐 순환 대기(교착) → 무쿠키 부팅이 `/#/login` 미도달 무한 스피너(로그인 시도 자체 불가) | authFlow 전용 클라이언트(무-AuthInterceptor) 분리 + dp_core 회전 가드 보강 | frontend#82 → 릴리스 #83 |
| ③ | web 동의 화면 | 출생 연도 미등록 시(미입력 또는 IME 조합·전각 숫자를 `digitsOnly`가 조용히 삼킴) 제출 버튼이 **안내 없는 회색 비활성** → 사용자 갇힘 | 버튼 상시 활성 + 제출 시 검증·에러 안내·필드 포커스 + 전각 정규화 + digitsOnly 제거 | frontend#84 → 릴리스 #85 |

**운영 실측 검증(전부 통과)**: 동시 refresh 8라운드 401 제로·순차 스테일 200→200(①) / 무쿠키 부팅→`/#/login` 도달(②) / 빈 연도 제출→에러 노출·입력 후 제출→`POST /consents` 200→`/#/diagnostic` 완주(③, fa5eb91 번들). 테스트: platform 174건·frontend 415건 전부 녹색. 문서: gitops#46~#49(런북 해소 기록).

기각 가설(재조사 금지): PSL 쿠키 거부(`ai.kr` 단독 등재 → `Domain=.leva.ai.kr` 유효)·CORS·재로그인 미수행·미승인 분기(ADMIN이라 `admit()` 무조건 true).

## 현재 상태 (다음 세션 시작점)

- 인프라: 변동 없음 — 12앱 Healthy·TLS 3종·EIP 13.124.153.105. 접속 명령은 런북.
- **users**: id=1 `deepestdark@outlook.kr`(GitHub, ADMIN, allowlist 등재) / id=2 `deepestdark@gmail.com`(Google, ADMIN). 이메일이 달라 계정 분리 — 테스트 기준은 id=1.
- **id=1 상태는 깨끗하게 원복됨**: consent_status=PENDING·birth_year=NULL·user_consents 0행·refresh 토큰 전량 폐기. **새 GitHub 로그인 필요**(구 쿠키는 전부 무효).
- 루트 `leva.ai.kr`은 **A레코드 없음** — 직접 진입 실패가 정상(WS-A에서 처리). 진입은 `app.leva.ai.kr`.

## ⏭ 다음 세션 1순위 — E2E 완주

1. 사용자 최종 GitHub E2E 1회: 새 시크릿 창 → app.leva.ai.kr → (로그인 화면 정상 노출 확인) → GitHub 로그인 → 동의(연도 미입력 시 빨간 에러 안내 확인) → 진단 도달.
2. 이어서 E2E 잔여: 진단 → 로드맵 실AI 생성 → 광고 슬롯 노출·admin 광고 생성.
3. 그 다음 로드맵: WS-A 홈페이지(CF Pages·루트 A레코드) → WS-E 통합 e2e → 베타 광고 잔여 2건(admin file-picker·광고 스모크) → 47 P2 이월 → ①결제.

## 후속 백로그 (이번 해소의 파생)

1. frontend refresh **single-flight**(bootstrapSession+bootstrapFromCallback 이중 호출 정리) + 첫 로드 무토큰 선발사 요청의 콘솔 401 잔상 1건 제거.
2. 유예창 밖 재사용 감지(reuse detection — 탈취 토큰 시 세션 전량 폐기).
3. `BetaGate.admit()` ADMIN 조기 return이 status를 BETA_PENDING으로 방치하는 정합성(id=1이 그 상태).
4. Redis 영속성 검토(재시작 시 전 세션 로그아웃 — RDB save는 설정돼 있으나 볼륨 미확인).

## 진단 기법 (재사용 가치 — 상세는 런북·메모리)

- 운영 Redis에 테스트 refresh 토큰 삽입 → curl 동시성 실측(종료 시 전량 삭제·잔여물 diff 확인).
- gstack 헤드리스 브라우저에 refresh 쿠키 주입 → GitHub 로그인 없이 인증 플로우 전체 재현(Flutter CanvasKit은 `flt-semantics-placeholder` 클릭으로 시맨틱스 활성화 후 조작).
- EC2 안에서 클러스터 JWT 시크릿으로 액세스 토큰 민팅 → 서버 체인(gateway→svc) 독립 검증(시크릿 외부 반출 없음).
- Windows에서 EC2 ssh는 PowerShell(Windows OpenSSH)만 동작 — Git Bash ssh는 키 로드 실패(libcrypto).

## 교훈

- **증상 하나 ≠ 원인 하나**: 401 하나에 결함 3개가 겹침 — 하나 고칠 때마다 다음 층이 드러남. 각 층을 실측으로 확정하고 넘어갈 것.
- dio `QueuedInterceptor`의 onError 안에서 같은 dio 재호출 금지(교착) — dp_core 테스트 주석("교착 방지")이 이미 경고했으나 앱 배선이 어겼음.
- **조용한 비활성 버튼 금지** — 미충족 조건은 명시적 에러+포커스로 안내. `digitsOnly` 라이브 필터는 IME 조합·전각 입력을 조용히 삼킬 수 있어 제출 시 파싱 검증이 안전.
