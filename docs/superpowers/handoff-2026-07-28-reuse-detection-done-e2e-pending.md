# Handoff — Refresh 재사용 감지 완료 (2026-07-28): develop 머지, E2E 완주 잔여

> 다음 세션 착수용. 이 문서는 [handoff-2026-07-27-auth-3defects-resolved-e2e-pending.md](handoff-2026-07-27-auth-3defects-resolved-e2e-pending.md)의 **후속 백로그 #2(재사용 감지)를 종결**한다. 인프라·E2E 착수점은 직전 핸드오프 그대로다.
>
> SSoT: platform `docs/superpowers/specs/2026-07-28-refresh-reuse-detection-design.md` · `plans/2026-07-28-refresh-reuse-detection.md`. 운영 상세: devpath-gitops `docs/runbook-k3s-bootstrap.md`.

## 완료 (이 세션 = 2026-07-28)

**platform #42 — refresh 토큰 재사용 감지(reuse detection)**: 어제 도입한 회전 유예창(grace 30s)의 **보안 짝**. develop 머지(`15b55e1`, 12:36). 이번 세션은 **platform 한 레포만** 변경했다(다른 13개 레포 2026-07-28 커밋 0건).

- **문제**: grace는 유예창 내 짧은 재사용을 의도적으로 허용하나, 유예창 **밖**에서 회전된(소비된) 토큰이 재제시되는 것 = 탈취 대표 신호를 감지 못 했다. 유예창 경과 시 `refresh:<hash>` 키가 소멸 → `GET` null → **401만 반환**(정상 만료 ↔ 탈취 재사용 구분 불가).
- **해결 (Approach A — 단일 키 진화)**: 회전 토큰의 **묘비(tombstone)** TTL을 grace(30s) → `refreshTtl`(14d)로 늘려 트립와이어화. 저장값 `grace:<userId>:<rotatedAtEpochMillis>`. 유예/재사용 판정을 TTL 소멸이 아니라 **저장된 `rotatedAt`과 현재 시각 차**로 한다:
  - `now − t0 ≤ grace` → 정상 동시-refresh (마커 불변·연장 금지, 새 토큰 발급)
  - `now − t0 > grace` → **재사용 감지** → `revokeAll(userId)` 전 세션 폐기 + `WARN` 로그 → `empty`(401)
- **킬스위치**: `devpath.auth.refresh-reuse-detection` (boolean, **기본 true**). env `DEVPATH_AUTH_REFRESH_REUSE_DETECTION`. `false`면 스테일 토큰은 여전히 401로 거부하되 **`revokeAll`은 안 함**(공격적 부분만 롤백, 사용자 체감은 today와 동일). gitops 변경 불요(코드 기본값 사용 — grace와 동일 방식).
- **계약 불변**: `AuthController` 시그니처·컨트롤러 로직·`Optional<Rotated>` 반환 전부 무변경. 재사용이든 만료든 `empty`→401. **서버 수정만으로 완결(클라이언트 배포 불요)**. `parseUserId`는 3-파트 값(`grace:<id>:<millis>`)을 파싱하도록 보강(기존 2-파트 가정의 `NumberFormatException` 방지).
- **변경 파일**: `RefreshTokenStore.java`(+56/−10) · `AuthProperties.java`(flag +3) · `RefreshTokenStoreTest.java`(신규 4 + 기존 6 계약 회귀 유지).
- 두 스위치는 독립: `refresh-rotate-grace`(Duration/30s, 묘비 존재 여부) · `refresh-reuse-detection`(boolean/true, 유예창 밖 재사용 시 `revokeAll` 실행 여부).
- → **후속 백로그 ② 종결.**

## 현재 상태 (다음 세션 시작점)

- **인프라**: 변동 없음 — 12앱 Healthy·TLS 3종·EIP **13.124.153.105**. 접속/조작 명령은 런북(직전 핸드오프 그대로, 이 세션에서 인프라 미변경).
- ⚠️ **릴리스 갭 (develop 있음 · main 미릴리스 → 운영 k3s 미반영)**:
  - `platform` #42 (reuse detection) — 2026-07-28
  - `shared` #49 (ci-migration-path: gitops `apps/devpath-migration` 경로 개명 반영) — 2026-07-27
  - → **운영 클러스터엔 reuse detection이 아직 없다.** 코드는 develop, 배포는 미반영.
- **워크스페이스 위생 (git 실측)**: 스트랜드된 미머지 작업 없음 — 전 레포 로컬 체크아웃 브랜치가 develop에 머지 완료(0 ahead, 로컬이 feature 브랜치에 남은 건 PR 머지 후 미전환뿐). 실제 미커밋 작업 없음 — dirty는 `.gitignore`의 `.gstack/` 추가 + `.omc/` untracked(툴 노이즈)뿐.
- **users**: id=1 `deepestdark@outlook.kr`(GitHub, ADMIN, allowlist 등재) — **consent_status=PENDING · birth_year=NULL로 원복**(구 쿠키 무효, **새 GitHub 로그인 필요**) / id=2 `deepestdark@gmail.com`(Google, ADMIN). 이메일이 달라 계정 분리 — 테스트 기준은 id=1.
- 루트 `leva.ai.kr`은 A레코드 없음(WS-A 소관) — 진입은 `app.leva.ai.kr`.

## ⏭ 다음 세션 1순위 — E2E 완주

> #42는 **develop-only(운영 미반영)**이라 운영 E2E에는 영향이 없다. E2E가 여전히 1순위이고, #42 운영 반영은 아래 "릴리스 트랙"으로 분리한다.

1. **사용자 최종 GitHub E2E 1회**: 새 시크릿 창 → `app.leva.ai.kr` → (로그인 화면 정상 노출 확인) → GitHub 로그인 → 동의(연도 미입력 시 빨간 에러 안내 확인) → 진단 도달.
2. E2E 잔여: 진단 → 로드맵 실AI 생성 → 광고 슬롯 노출 · admin 광고 생성.
3. 이후 로드맵: WS-A 홈페이지(CF Pages · 루트 A레코드) → WS-E 통합 e2e → 베타 광고 잔여 2건(admin file-picker · 광고 스모크) → 47 P2 이월 → ①결제.

**릴리스 트랙 (E2E와 병렬 가능)**: `platform` #42 + `shared` #49 develop→main 릴리스 → 이미지 빌드 · ArgoCD 반영 확인 → 설계 §6.3 **운영 재검증**(런북 진단기법 재사용 — EC2에서 테스트 refresh 토큰 삽입, 유예창 **안**=200·세션 유지 / **밖**=401 + `refresh:byUser:<id>` 전멸 확인, 종료 시 잔여물 전량 삭제).

## 후속 백로그 (갱신)

- ~~② 유예창 밖 재사용 감지~~ → **✅ 완료(#42, develop)**.
- ① frontend refresh **single-flight** (`bootstrapSession` + `bootstrapFromCallback` 이중 호출 정리 + 첫 로드 무토큰 선발사 요청의 콘솔 401 잔상 1건 제거). *착지 시 #42 오탐 여지 추가 축소.*
- ③ `BetaGate.admit()` ADMIN 조기 return이 status를 `BETA_PENDING`으로 방치하는 정합성(id=1이 그 상태).
- ④ Redis 영속성 검토(재시작 시 전 세션 로그아웃 — RDB save는 설정됐으나 볼륨 미확인).
- Micrometer 카운터(`auth.refresh.reuse_detected`) · 묘비 TTL 튜닝(대규모 시 활성 세션당 키 증가).

## 검증 상태 (정직)

- #42 테스트(신규 4 + 회귀 6)는 커밋에 포함돼 있으나, **이 세션에서 `./gradlew test` 독립 실행 · 운영 재검증은 미수행**. develop 머지 시 CI 통과가 근거이며, main 릴리스 전 운영 재검증(설계 §6.3)은 남아 있다.
- 인프라 "변동 없음"은 이 세션에서 인프라를 건드리지 않았다는 뜻이며, 라이브 클러스터 헬스는 이 세션에서 재확인하지 않았다(직전 핸드오프 기준).

## 교훈

- **grace와 reuse detection은 한 쌍**: 유예창(grace)은 편의(동시 refresh 오탐·세션 파괴 방지), 재사용 감지는 보안(탈취 토큰 무효화). 한쪽만 있으면 불완전 — grace만 있으면 유예창 밖 탈취를 "정상 만료"로 흘려보낸다.
- 계약(반환 타입 · 컨트롤러 시그니처)을 고정한 채 스토어 내부 상태 모델(묘비 TTL · `rotatedAt`)만 진화시키면 클라이언트 배포 없이 보안 기능을 얹을 수 있다.
