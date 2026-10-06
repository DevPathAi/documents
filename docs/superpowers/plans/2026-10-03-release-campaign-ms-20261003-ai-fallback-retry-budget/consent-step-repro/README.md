# 활성화 저니 동의 단계 — 로컬 재현 기록 (2026-10-06)

gitops validate 런 `37417289045` 의 `required-consent-claim-replay` 타임아웃(`POST /consents` 미발생)을 조사하며 쓴 일회용 스크립트다.
결론과 수정은 documents `docs/superpowers/handoff-2026-10-06-release-campaign-ms-20261003-promoted.md` 3-2 절, 홈 PR #100.

## 빌드 (약 130초)

후보와 같은 Flutter 3.44.1 을 쓴다. PATH 의 flutter 는 3.47.2 다.

```bash
export PATH="/d/workspace/dpa/.worktrees/_tools/flutter-3.44.1/bin:$PATH"
git -C /d/workspace/dpa/devpath-frontend worktree add --detach <WT> origin/main
cd <WT> && dart pub get --enforce-lockfile && dart run melos bootstrap --enforce-lockfile
cd <WT>/apps/web && flutter build web --release --no-pub --no-web-resources-cdn \
  --dart-define=USE_MOCK=true --dart-define=MISSION_SPINE_ENABLED=true \
  --dart-define=MOCK_PROFILE=consent --dart-define=HOME_BASE_URL=http://127.0.0.1:1
```

- mock 의 `GET /consents/me` 는 `birthYear: 1998`(재동의 조건)이다. 신규 사용자 조건은
  `apps/web/lib/src/data/web_mock_fixtures.dart` 의 그 값을 `null` 로 바꿔 다시 빌드한다(커밋하지 않는다).
- mock 에는 `POST /consents` 픽스처가 없다 — 제출 성공은 「새 문구가 뜸」으로, 검증 실패는 에러 문구로 판정한다.
- 서버는 frontend `tools/browser_ux/serve.mjs` 의 `serve(dist)`, 브라우저는 홈 워크트리의 `@playwright/test`(로컬 chromium). Docker 는 필요 없다.

## 스크립트

| 파일 | 용도 | 2026-10-06 결과 |
|---|---|---|
| `consent-repro.mjs <n> spec\|guarded\|stable` | 스펙 순서로 제출까지 가서 결과를 분류 | 신규 사용자 조건: `spec` 32회 중 29회 `validation-year` · `stable` 32/32 제출 · `guarded` 12회 중 9회 `toHaveValue` 실패 |
| `consent-repro2.mjs <n> spec\|prewait\|type\|stable` | 연도 입력이 프레임워크에 남는지(blur 뒤 값)만 측정 | 재동의 조건: `spec` 30회 중 17~22회 유실 · `prewait` 22회 유실 · `type` 7회 유실 · `stable` 0회 유실 |
| `consent-verify.mjs <n>` | 수정된 홈의 실제 헬퍼(`fillFlutterTextField`)와 바뀐 스펙 순서 검증 | 신규 사용자 조건 60/60 · 재동의 조건 30/30 제출 |
