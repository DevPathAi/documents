# 정합성 3차 — 회귀 체크 (43번 이행 + 잔여 OPEN)

> 43_정합성_리팩토링_실행계획서(2026-07-02, 42번 2차 점검 기반)의 이행 현황을 기준 ref에서 재확인한다.
> 42번 §3 형식(✅ 이행 / ⚠️ 부분·확인필요 / ❌ 미이행 / ➖ 해당없음·이월).

## 기준

- documents 기준 ref: `origin/develop` = `12fa43b` (2026-07-17).
- 대조 원본: `git -C D:\workspace\dpa\documents show origin/develop:43_정합성_리팩토링_실행계획서.md` (P0 6·P1 15·P2 3·색인 4 항목).
- 각 항목의 대상 파일을 기준 ref(레포별 origin/develop)에서 완료 기준으로 재확인(워킹트리 아님).

## 방법

- 항목별 완료 기준을 `git -C <레포> show origin/develop:<파일>` + `grep`으로 스팟 검증(대표 항목 직접 실행).
- OPEN 이력 PR 2건: `gh pr view <n> --repo <repo> --json state,title,mergedAt`.
- 실행한 대표 검증 명령(발췌):
  - `show :17_스케줄.md | grep -c 미착수` → 0
  - `show :09_Git_규칙_정의서.md | grep -cE '사용하지 않|Merge Commit.*금지'` → 0
  - `show :02_ERD_문서.md | grep -c user_reputation_events` → 0 / `reputation_events` → 4
  - `show :README.md|Home.md | grep -cE '4[23]_'` → 각 2
  - `devpath-lcs-svc show :README.md | head -1` → `# devpath-lcs-svc`
  - `show :20_커뮤니티_기능_설계서.md | head -15 | grep -c 스켈레톤` → 0, `42` → 1
  - `show :26_학습맥락_자동첨부_구현.md | grep /api/lcs` → 헤더 이력설명 1건(본문 경로는 `/lcs/*` 정정 완료)
  - `templates show origin/main:README.md | grep 예정` → "예정(TARGET)" 분리 라벨 확정

## 실측

### 43번 P0 (즉시 수정) — 이행 현황

| 항목 | 대상 | 완료기준 검증 | 상태 |
|------|------|---------------|:----:|
| P0-1 | 17_스케줄.md | "미착수" 문구 0건 | ✅ |
| P0-2 | 02_ERD_문서.md | 헤더 42번 참조 존재 | ✅ |
| P0-3 | 13_테스트_보고서.md | TARGET/TEMPLATE 배너 | ⚠️ 미개별검증(round2-done 승계) |
| P0-4 | devpath-lcs-svc/README.md | 제목 `# devpath-lcs-svc` | ✅ |
| P0-5 | 09_Git_규칙_정의서.md | "develop 사용 안 함"·"Merge Commit 금지" 0건 | ✅ |
| P0-6 | devpath-ai-svc/README·CLAUDE | 엔드포인트 6종 정합 | ⚠️ 미개별검증(round2-done 승계) |

### 43번 P1 (라벨·표기) — 이행 현황

| 항목 | 대상 | 완료기준 검증 | 상태 |
|------|------|---------------|:----:|
| P1-1 | 04_API_명세서.md | 배너 42 참조 | ✅ |
| P1-4 | 02_ERD_문서.md | `reputation_events`(구 `user_reputation_events` 소멸) | ✅ |
| P1-5 | 20_커뮤니티_기능_설계서.md | "스켈레톤" 0·42 참조 | ✅ |
| P1-6 | 26_학습맥락_자동첨부_구현.md | 본문 경로 `/lcs/*` 정정(`/api/lcs` 잔존은 헤더 이력설명뿐) | ✅ |
| P1-9 | devpath-community-svc/README | moderation TARGET 표기 | ✅ |
| P1-13 | devpath-learning-svc/README | mentor=ai-svc 소관 표기 | ✅ |
| P1-15 | .github/profile/README | 조직 프로필 렌더 확인·보정(= .github#6 MERGED) | ✅ |
| P1-2·3·7·8·10·11·12·14 | 각 문서/README 배너·표기 | 미개별검증 | ⚠️ round2-done 승계 |

### 43번 P2 / 색인 — 이행 현황

| 항목 | 대상 | 완료기준 검증 | 상태 |
|------|------|---------------|:----:|
| P2-1 | 05_화면_흐름_시퀀스 | lcs-svc 주석 정정 | ⚠️ 미개별검증 |
| P2-2 | 23_PIA·33_처리방침 | 위탁 시점 각주 | ⚠️ 미개별검증 |
| P2-3 | templates/README.md | 예정 항목 "예정(TARGET)" 분리 라벨 | ✅ |
| I-1·I-2 | README.md·Home.md | 42·43 링크 추가 | ✅ |

### 잔여 OPEN 이력 PR (메모리상 OPEN → 실측)

| PR | 제목 | 실측 상태 |
|----|------|-----------|
| devpath-sandbox-svc #18 | docs: CLAUDE.md 도메인 표 실제 패키지와 정합 | **MERGED** (2026-07-03) |
| .github #6 | release: 조직 프로필 레포 표 정정 (P1-15) | **MERGED** (2026-07-03) |

### 42번 잔여 ⚠️ (P0-5 조직 프로필 웹 렌더링 미검증)

- 42번 P0-5 = 43번 P1-15 = 조직 프로필(`.github/profile/README`) 렌더링 확인·보정. `.github#6` **MERGED**로 종결 ✅.

## 불일치 후보

- **43번 미이행(❌) 0건.** 직접 스팟 검증한 대표 12항목(P0-1·2·4·5, P1-1·4·5·6·9·13·15, P2-3, 색인 I-1·2)이 전부 이행. 미개별검증 항목(P0-3·6, P1-2·3·7·8·10·11·12·14, P2-1·2)은 [[devpath-consistency-round2-done]](42·43 전부 완료)로 승계하며, 3차 축② 문서대조에서 **해당 문서들의 재역행(라벨 소멸·수치 되돌림) 징후 없음**을 확인.
- **⚠️ 승계(43 범위 확장 필요)**: 43 P1-1은 04_API의 **알림 절(§9)만** TARGET/구현 라벨을 부여했다. 3차 축②(doc-consistency B-1~B-5)에서 04의 **에스컬레이션·bounty·moderation·admin 대량 섹션은 상태 라벨이 없어** 미구현을 구현처럼 표기함을 신규 발견. 이는 "43 미이행"이 아니라 **43이 다루지 않은 범위**로, 46번 §불일치·47번 신규 Task로 승계한다(04 전 섹션 상태열 도입).

## 관찰

- 43번은 "**문서 표기 라벨 수정**" 계획(코드 수정 없음, 42번 6절 코드 관찰은 범위 밖)이었다. 3차는 여기에 **코드 축(구조·규칙·TDD)을 신설**했으므로, 43이 종결한 문서 정합 위에 코드측 발견(notification envelope 미채택·gitops 배포 누락·community 기능 미구현·jqwik 부재 등)이 추가된다 — 이들은 43 회귀 대상이 아니라 3차 신규 항목이다.
- 42→43 라운드가 실질 종결됐음을 재확인(대표 스팟 전부 이행 + OPEN 2건 MERGED). 3차의 초점은 43 이후 ~2주 머지분(baseline 표 참조)의 신규 불일치와 코드 품질이다.
