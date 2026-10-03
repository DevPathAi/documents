# 핸드오프 2026-09-19 — 웹 문법 재구성 설계 · 모바일 레포 분리(S2b·S2c-1) · 승격 차단 실측

> 2026-09-19 세션의 재개 문서다. 직전 문서는
> `docs/superpowers/handoff-2026-09-17-night-home-deploy-and-community-flat-pages.md`.
> 설계의 원천은 `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md`(이하 "스펙")이고,
> 이 문서는 **지금 어디까지 왔고 다음에 무엇을 하는지**만 고정한다. 세부 근거는 스펙 절 번호로 가리킨다.

## 1. 지금 상태 (전부 세션 종료 시 실측)

| 영역 | 상태 | 식별자 |
|---|---|---|
| 앱 운영(`app.leva.ai.kr`) | **변화 없음** — 200 응답, 9/16 승격분 그대로 | frontend main 은 `03e0c13` 이지만 **운영 미승격** |
| 홈 운영(`leva.ai.kr`) | 변화 없음 | `appVersion` `24c6e748` |
| frontend `main` | 릴리스 #221 머지(#215~#220) | `03e0c13` |
| frontend `develop` | + #222(승인 워크플로 개수 파생) + #223(ET13 모바일 distribution 제거) | `db955ea`, main 보다 9 커밋 앞 |
| **`DevPathAi/devpath-mobile`** | **신설**(public). 단독 해석·테스트·Android/iOS 빌드 계약 CI 녹색, main 릴리스됨 | main `6722ae4`, 로컬 `D:\workspace\dpa\devpath-mobile` |
| documents `develop` | 스펙·계획 2건·이 문서 | #135~#141 + 이 PR |
| gitops | **손대지 않음** | main `4f3ed64` |
| 웹 시안 | 20화면, 사용자 시각 승인 완료 | https://claude.ai/artifact/DWi8kMV6QcAzBEQwbrNPNd (Version 2) |
| 열린 PR / 세션 워크트리 | 0 / 0 | frontend 주 checkout(`feat/evidence-auth-smoke`)은 건드리지 않았다 |

## 2. 이번 세션이 정한 것 (사용자 결정)

| # | 결정 | 스펙 |
|---|---|---|
| D1 | Flutter 유지, 디자인만 웹 문법으로(DOM 재작성 아님 — CanvasKit 한계는 범위 밖) | §2 |
| D2 | 폰 폭은 반응형 웹 문법(햄버거 메뉴·1열, 하단 고정 요소 없음) | §2 |
| D3 | 모바일 앱은 별도 레포·작업 디렉터리 | §2·§6 |
| D4 | `dp_design` 포크 + `dp_core` 는 frontend 를 커밋 핀 git 의존성으로 | §2·§6.2 |
| D5 | 전역 내비 = 상단 헤더 + 중앙 본문 + 푸터 | §2 |
| D6 | 약 20화면 시안을 먼저 시각 확인 → **승인됨** | §5 |
| 시안 3결정 | 헤더 **어둡게**(`rail*`→`header*` 승계) · 밀도 **촘촘(컨트롤 30px, 타깃 기준을 WCAG 2.2 AA 2.5.8 24px 로)** · 게시판 이동 **헤더 드롭다운만** | §5.4 |
| 릴리스 계약 | **웹 릴리스 계약에서 모바일 제거**(모바일은 독립 서명·배포) | §6.3 |
| 묶기(B) | gitops 의 ET13 숫자 갱신을 모바일 제거와 **한 번의 gitops 변경**으로. 대가: #217·#219·#220 운영 반영 연기 | §6.4 |
| 모바일 레포 | 가져오지 않은 워크플로를 검사하던 계약 테스트 2개는 새 레포에서 제거 | §6.2 |

## 3. 하위 프로젝트 진행표

순서는 스펙 §6.5 가 교정했다: **gitops 는 frontend ET13 카탈로그의 거울**이라 frontend 가 먼저다.

| 단계 | 내용 | 상태 |
|---|---|---|
| S1 | 웹 시안 20화면 | ✅ 승인 |
| S2b | `devpath-mobile` 추출(비파괴) | ✅ 완료 — 계획 `plans/2026-09-19-s2b-devpath-mobile-repo-extraction.md` |
| S2c-1 | frontend ET13 에서 `mobile` distribution 제거 | ✅ 완료(#223) — 계획 `plans/2026-09-19-s2c1-et13-drop-mobile-distribution.md`, 산출값 스펙 §6.6 |
| **S2c-2 + S2a** | 릴리스 증거에서 서명 모바일·TalkBack 제거(frontend) ↔ gitops 미러 갱신 | ⬅️ **다음. 쌍 설계부터**(§4) |
| S2c-3 | frontend 에서 `apps/mobile`·`mobile.yml`·`tools/mobile_source_guard.dart`·workspace 항목 삭제 | 대기 |
| 재릴리스·승격 | frontend develop→main → ET13 baseline **봇 디스패치** → 사람 승인 → gitops candidate→promotion→landing-last | 대기(N01 Cloudflare 토큰도 사람 단계) |
| S3 | 웹 재구성 구현(토큰 2.0.0 → `DpWebShell` → 공용 위젯 → 화면군 3 PR → 기준선 재기록) | 대기 — 계획 미작성. S2 와 독립이라 병행 가능 |
| 모바일 후속 | 독립 서명·배포 파이프라인(시크릿 4종은 사람이 옮김) | 대기 — 모바일 레포의 별도 계획 |

## 4. 다음 세션 착수점 — S2c-2 + S2a 쌍 설계

구현 계획을 쓰기 전에 **브레인스토밍(설계 문답)** 부터 한다. 공급망 방어선 코드라 즉흥으로 고치지 않는다.

**왜 쌍인가(실측)**: frontend `mission-spine-manual-at-evidence.yml` 은 서명 APK 인증을 NVDA·TalkBack 이 공유하는
`authenticate-inputs` 잡에 두고(256–384행), `tools/mission_spine_manual_at_evidence.mjs` 가 증거 JSON 에
`signed_apk_sha256` 을 쓴다(364–431·539·590행). gitops `verify_release_artifacts.py` 가 그 필드와 서명 모바일
provenance 를 검증하고, `validate_release_manifest.py` 가 `quality_evidence_inputs.mobile_test_artifacts`
(803·1024–1065·1647–1663행)·`SIGNED_MOBILE_*`(244–266)·`manual-talkback`(59·68·79·283–297)을 요구한다.
한쪽만 바꾸면 증거 모양과 검증기가 어긋난다.

**설계에서 닫을 질문**
1. 서명 모바일을 뺀 `authenticate-inputs` 의 모양 — candidate 인증만 남기는가.
2. 수동 접근성 증거는 `manual-nvda` 단독으로 가는가(`QUALITY_EVIDENCE` 6 → 5 레이블).
3. gitops candidate spec 의 `schema_version` 을 올리는가, 필드만 빼는가(기존 sealed manifest·픽스처와의 호환).
4. gitops 의 `FRONTEND_FIXTURE_IDS`·`FRONTEND_PROJECTION_MATRIX`·`FRONTEND_CATALOG_CONTRACTS` 를 리터럴 미러로 둘지,
   frontend 카탈로그에서 파생·대조하게 바꿀지(같은 계열 결함이 이번 세션에만 다섯 번 나왔다 — §6).
5. gitops `main` 은 룰셋 2종 + classic 의 3중 잠금이다. 머지 절차의 사람 단계를 계획에 명시한다.

**S2a 가 미러할 값**은 스펙 §6.6 에 있다(13 fixture id · `projection_contract_sha256` `158fdc88…435b78` ·
`catalog_sha256` `c5acc346…b00c96` · visual 104 / a11y 26 · 표면 개수 · distribution 2개). 착수 시 frontend
`origin/develop` 에서 다시 읽어 대조한다.

**재개 명령**

```bash
export MSYS_NO_PATHCONV=1   # Git Bash 에서 origin/x:path 인자가 깨지지 않게
git -C D:/workspace/dpa/devpath-frontend fetch origin && git -C D:/workspace/dpa/devpath-frontend rev-list --left-right --count origin/main...origin/develop
git -C D:/workspace/dpa/devpath-gitops fetch origin && git -C D:/workspace/dpa/devpath-gitops log origin/main --oneline -3
git -C D:/workspace/dpa/devpath-frontend show origin/develop:evidence/et13/generated/visual-cases.v1.json | py -c "import sys,json;d=json.load(sys.stdin);print(d['projection_contract_sha256'],d['catalog_sha256'],d['case_count'],len(d['fixture_ids']))"
git -C D:/workspace/dpa/devpath-gitops grep -nE "mobile|talkback|signed" origin/main -- scripts/release | wc -l
```

## 5. 승격이 막혀 있는 이유 (2026-09-17 핸드오프의 정정)

직전 핸드오프는 "ET13 baseline 승인 + Cloudflare 토큰만 있으면 승격 가능"이라고 적었다. **사실이 아니었다.**

1. frontend `et13-baseline-approval.yml` 이 12-fixture 개수(162·96·98)를 리터럴로 고정 → 사용자가 승인한 run
   `35405819787` 이 승인 직후 실패. **#222 로 수정**(develop). 그 승인은 소모됐다 — 재릴리스 뒤 다시 눌러야 한다.
2. gitops 검증기가 12-fixture 카탈로그(목록·매트릭스·해시·개수)를 미러로 고정 → frontend 가 15(지금은 13)인 한
   승격 검증이 통과할 수 없다. **미수정 — S2a.**
3. `tools/et13_baseline_updater.dart` 가 `case_count == 96` 을 요구 → 승인이 성공했어도 baseline 반영 단계에서
   죽었을 것. **#223 으로 수정.**

## 6. 이번 세션의 교훈

- **fixture 수 리터럴 결함이 다섯 번 나왔다**: 승인 워크플로(162/96/98) · gitops 검증기 · 스키마 5종의
  `case_count`/web 개수 · baseline updater · producer 계약 테스트. N06(9/17)의 `capture.mjs`·캡처 합계까지 치면
  일곱 번이다. fixture 수를 바꾸면 **도구·스키마·테스트·`capture.mjs`·합계·`.github/workflows`·다른 레포(gitops)**
  까지 grep 하고, 가능한 곳은 생성 카탈로그에서 파생시킨다. ET13 스키마는 기계 검증되지 않는다(`$id`·선택 필드만).
- **보호 승인 워크플로는 `gh workflow run` 으로 직접 띄우지 않는다.** 이 PC 의 `gh` CLI 가 리뷰어 계정
  (`VelkaressiaBlutkrone`)이라 `prevent_self_review` 에 걸린다. `automation/dispatch-<release_id>` 브랜치의
  디스패처 워크플로(`github.token`)로 봇이 띄우고, `pending_deployments` 의 `current_user_can_approve` 가 true 인지
  확인한 뒤 링크를 건넨다. 승인 클릭은 사람의 검토 단계라 API 로 대신 누르지 않는다.
  **취소한 대기 실행은 다시 확인한다** — run `35402963889` 는 첫 취소 요청 뒤에도 `waiting` 으로 남아 있어 세션 끝에
  재취소했다.
- **투영 계약 해시의 잠금은 세 곳**이다: `tools/et13_evidence.dart` 상수 · `catalog.v1.json` · 카탈로그 계약 테스트.
- `resolution: workspace` 가 있는 패키지도 **git + `path` 커밋 핀으로 해석된다**(실증). frontend 가 public 이라
  모바일 CI 는 자격 증명 없이 `dp_core` 를 받는다.
- **S2c-3 에서 걸릴 지점**: `tools/et13_evidence.dart` 가 `pubspec.lock` 의 해시(`_workspaceLockSha`)를 고정한다.
  workspace 에서 `apps/mobile` 을 빼면 lock 이 바뀌므로 함께 갱신한다.
- `apps/admin` 이 `DpAppShell` 을 쓴다 → S3 에서 web 셸을 교체해도 레일 셸은 지우지 않는다.
- Windows 로컬 전용: frontend `packages/dp_design/test/theme/dp_code_font_test.dart` 는 CRLF 체크아웃에서 1건
  실패할 수 있다(CI 는 통과, 모바일 포크에서는 정규화로 수정). frontend 쪽은 미수정.
- 도구 함정: Explore 서브에이전트가 두 번 연속 빈 보고("Stopped.")로 끝났다 — 인벤토리는 `git grep` + `awk` 함수
  문맥 추출로 직접 했다. Bash 도구의 heredoc 안 `\`+개행은 깨진다 → 여러 줄·백슬래시 치환은 스크래치패드의 파이썬
  스크립트(치환 횟수 assert, 백슬래시는 `chr(92)`). `node --test <디렉터리>` 는 이 Node 에서 모듈 해석 오류 →
  파일을 직접 지정. worktree 안에 셸 cwd 를 둔 채 `git worktree remove` 하면 Permission denied.

## 7. 사람 단계 (도구로 도달 불가)

1. **ET13 baseline 재승인** — S2a·재릴리스 뒤 봇이 띄운 실행에서 `VelkaressiaBlutkrone` 로 Approve.
2. **gitops main 3중 잠금 해제** — S2a 머지 시.
3. **Cloudflare durable token(N01)** — landing-last 전. 절차는 frontend
   `docs/community-information-architecture/task.md` §5 N01.
4. **모바일 서명 시크릿 4종**(`ANDROID_RELEASE_KEYSTORE_BASE64`·`…_PASSWORD`·`ANDROID_RELEASE_KEY_ALIAS`·`…_KEY_PASSWORD`)
   과 환경 `mission-spine-mobile-signing-android` 를 모바일 레포로 — 독립 서명 파이프라인을 설계할 때.
5. 직전 핸드오프에서 넘어온 것: YouTube 재업로드(게시본 `MTSrOoTlZss` 44–48s 자리표시자), 로그인 캡처, AdSense 결정.

## 8. 직전 핸드오프 큐의 처리

| 항목 | 결과 |
|---|---|
| L1 frontend 릴리스 + 승격 | 릴리스는 완료(#221). 승격은 §5 의 이유로 S2a 뒤 |
| L2 게이트웨이 CORS dedupe(#44) 운영 반영 | 미착수 — 같은 gitops 승격 캠페인에 태운다 |
| L3 셸 `_AccountMenu` a11y · L4 frontend 큐 문서 | S3-P2(새 셸의 계정 메뉴)에 흡수 — 스펙 §7 |
| L5 §9.6 후속(승격 후 nginx 압축 실측) | 승격 뒤 |
| L6 P2 후속(12주 미리보기 문구 등) | 미착수 |

## 9. 작업 환경 메모

- 사용자는 작업을 맡겨 두고 같은 PC 에서 게임을 한다. 무거운 검증(웹 빌드·Playwright)은 CI 에 맡기고 로컬은
  analyze·단위 테스트까지. 도구 호출은 묶는다.
- frontend PR 은 docs 만 바꿔도 perf-gate 약 23분이 돈다 → 교차 레포 기록은 이 레포(documents)에 쓴다.
- 세션 마무리는 30분 안에 끝낸다.
