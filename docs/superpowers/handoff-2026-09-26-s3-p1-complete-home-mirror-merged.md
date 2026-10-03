# 핸드오프 2026-09-26 — S3-P1 **완결**: 홈 미러 기준선 재기록·승인 후 develop 머지(#93) · 다음 = S3-P2 계획

> 앞 문서 `handoff-2026-09-24-s3-p1-token-contract-2-0-0.md` 의 **§3(홈 미러 차단)** 과 **§4 의 1·2번**을 이 세션이 처리했다. 이 문서가 그 부분만 대체한다 — 앞 문서의 §2.1(계약 2.0.0 내용)·§5(교훈)·§6(리뷰 결과)·§7(좌표)는 그대로 유효하다.
> 그 앞 문서(`handoff-2026-09-24-r3-released-cors-env-published.md`)의 §1·§2·§3·§5 도 여전히 유효하다.

## 1. 이 세션이 한 일 (2026-09-25 23:20Z ~ 23:50Z)

| # | 일 | 결과 |
|---|---|---|
| 1 | Docker 데몬 기동 | 앞 세션이 못 켠 것을 직접 실행(설치돼 있었음). Server 29.6.2 |
| 2 | 증거 재바인딩 | home `50aff21` — `candidate-spec.v2.json` 과 계약 테스트 2종의 SHA 핀을 미러 커밋 `44b8212` / product tree `4e4ec2bd…` 로 이동 |
| 3 | 승인 전 미리보기 렌더 | 핀 이미지에서 `--update-snapshots=all` 만 돌려 4폭 PNG 를 만들고, 구·신을 나란히 잘라 육안 비교 → 그 뒤 `git checkout` 으로 되돌림 |
| 4 | **사용자 기준선 승인** | 비교 이미지를 제시하고 확인 관문. 선택 = 「승인 — AI 명의로 기록」(9/21 재승인이 `claude-fable-5.1` 명의였던 전례와 동일) |
| 5 | 공식 updater | 핀 이미지 안에서 `npm run visual:baseline:update`, status `approved` · review id `tokens-mirror-2-0-0-20260926` · reviewer `claude-opus-5`. **PNG 해시가 미리보기와 한 바이트도 다르지 않았다(렌더 결정성 확인)** |
| 6 | 커밋 뒤 재검증 | `ef8cbc0` 커밋 → `npm test` **496/496** · `visual:contracts` valid(커밋 전 깨졌던 `visual-evidence-audit-contract` 가 녹색으로) |
| 7 | 핀 이미지 전체 증거 패스 | `visual:evidence:docker` 15/15 통과 · `visual:evidence:validate`(엄격)·`validate:diagnostic` 둘 다 valid |
| 8 | **PR #93 머지** | draft 해제 → develop **`022f7ef`**. CI 4잡 전원 녹색(test 1m16s/1m11s · visual-a11y 1m4s ×2), develop push CI 도 success |
| 9 | 정리 | 원격·로컬 브랜치 삭제, 워크트리 `home-s3p1-mirror-20260924` 제거 |

## 2. 기준선이 실제로 어떻게 바뀌었나 (승인 근거)

렌더에 영향을 준 토큰은 **반경**과 **본문 최대 폭** 둘뿐이다. 색·문구·섹션 순서·이미지는 그대로다(색 토큰은 `rail-*`→`header-*` 개명이라 값이 안 바뀜).

| 폭 | 페이지 높이 | 관찰 |
|---|---|---|
| 320 | 13328 → **13328 (동일)** | 모서리만 각져짐. 줄바꿈·버튼 크기 불변 |
| 600 / 840 | 미세 | 동일 경향 |
| 1240 | 9245 → **9205 (−40px)** | 본문 폭 1360→**1120** 으로 좁아져 좌우 여백 증가. 카드 18→8 · 버튼 12→6 · 칩 999→**4** |

`home-targets-44-{320,600,840,1240}` 4건이 모두 통과해 **랜딩 자체의 44×44 히트 타깃 규칙은 유지**된다(계약 2.0.0 의 최소 타깃 24 는 앱 쪽 규칙이고, 랜딩은 자기 규칙을 그대로 쓴다).

새 기준선 해시: 320 `6baab73d…` · 600 `16173039…` · 840 `6088f95d…` · 1240 `3094f4f0…`.

## 3. 지금 상태 (2026-09-25 23:50Z 실측)

| 영역 | 상태 |
|---|---|
| 운영(app·leva.ai.kr) | **변동 없음.** S3 는 전부 `develop` 이하 |
| gitops `main` | `5427fe1e` 그대로 — 다음 candidate 의 `gitops.base_sha` |
| frontend `develop` | `17ce8a2`(S3-P1) |
| home `develop` | **`022f7ef`**(토큰 미러 2.0.0 + 승인된 기준선). `master` 는 `ffaf4b33` 그대로 |
| 홈 prior 배포 | `6f7a7e2b-522f-4bf1-b134-2dd2b345f83c`(다음 gitops landing-last 의 기대값) |
| 열린 PR | home 0 · frontend 0 · documents 이 문서뿐 |

## 4. 다음 착수점

1. **S3-P2 계획 작성** — `DpWebShell`(헤더·푸터·햄버거·계정 메뉴) 신설 → web `AppShellView` 교체. `DpAppShell`·`DpNavRail` 은 admin 이 쓰므로 남긴다. 핸드오프 2026-09-19 의 L3(`_AccountMenu` MenuAnchor focus a11y)를 여기서 흡수한다. `headerHeight` 56 은 이미 토큰에 있다.
   - P2 에서 반드시 같이 처리할 Minor(9/24 리뷰): `dp_chrome_bar` 의 오버플로 예산이 아직 48px 기준이라 액션이 필요보다 일찍 메뉴로 접힌다 · `dp_chrome_bar_account_gap_test` 와 `dp_nav_rail.dart:99-106` 주석이 48/44px 산술로 세상을 설명한다 · 테마는 타깃 **크기**만 보장하고 **간격은 보장하지 않는다**(간격은 셸이 준다, `dp_chrome_bar` 가 첫 대상).
2. **S3-P3/P4/P5 계획** — P5 재기록 목록에 `test/golden/goldens/`(`--exclude-tags golden` 때문에 아무도 안 보는 채로 낡음)를 포함할 것.
3. **다음 릴리스 캠페인** — gitops `base_sha` `5427fe1e` · 홈 prior 배포 위 id · ai-svc 이미지 증거 만기 **10/08**. preflight 보강(#168)이 TLS·게이트·Argo refresh 를 자동으로 본다. **S3 는 P5 까지 끝난 뒤에 릴리스에 태운다**(스펙 §9). 홈 미러는 이제 develop 에 있으므로 다음 `develop→master` 릴리스에 자동으로 실린다 — 랜딩 시각이 바뀌는 릴리스라는 점을 릴리스 노트에 적을 것.

## 5. 이 세션의 교훈

1. **「Docker 가 없다」가 아니라 「Docker 를 안 켰다」였다.** 앞 세션이 차단으로 기록한 것이 실제로는 설치된 앱을 실행하지 않은 상태였다. 실측 없이 차단으로 적으면 다음 세션이 그 문장을 그대로 믿는다([[devpath-handoffs-lag-verify-first]]).
2. **승인 관문은 산출물을 먼저 만들고 나서 묻는다.** updater 는 approved 메타데이터 없이는 PNG 도 안 남기므로, `--update-snapshots=all` 만 따로 돌려 미리보기를 만들고 `git checkout` 으로 되돌린 뒤 승인을 받았다. 렌더가 결정적이라 승인 후 정식 실행에서 해시가 같았다.
3. **`git worktree remove` 가 Permission denied 여도 등록은 지워진다.** 디렉터리만 남으므로 `rm -rf` + `git worktree prune` 으로 마무리한다.
4. **Windows Git Bash 에서 `tasklist` 는 `MSYS_NO_PATHCONV=1` 없이는 `/FO` 를 경로로 바꿔 먹는다**(출력도 cp949 라 `iconv` 필요).
5. `cmd.exe /c start "" "<exe>"` 는 이 환경에서 GUI 앱을 못 띄웠다 — `nohup "<exe>" &` 가 동작했다.
