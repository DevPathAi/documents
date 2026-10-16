# 다음 릴리스 캠페인 시작 체크리스트 (2026-10-03 작성)

> **소진(2026-10-16)**: 이 체크리스트의 캠페인은 `ms-20261016-leva-inspection-fixes` 로 운영에 반영됐다. 다음 캠페인 입력값은 `handoff-2026-10-16-release-campaign-ms-20261016-promoted.md` §5 를 본다.

> `ms-20261002-ai-provider-fallback-gpu7b` 운영 반영과 gitops 폴백 publisher(`a97a1754`) 뒤에 남은 「다음 캠페인이 반드시 밟아야 할」 순서와 입력값.
> 근거 기록: `handoff-2026-10-03-release-campaign-promoted.md` · `plans/2026-10-03-gitops-main-ai-fallback-probe-via-publisher.md`.
> 도구: `2026-10-03-next-campaign-prep/compute_ai_rendered_config.py`.

## 0. 왜 순서가 중요한가

Mission Spine 릴리스의 외부 증거는 보호 브랜치의 **현재 head** 에 묶인다.

- candidate spec 의 `analytics_privacy.approval_source_sha` = **candidate 를 만든 시점의 documents main SHA**. 프라이버시 워크플로가
  `GITHUB_SHA = approval_source_sha` 를 단언하므로, candidate 를 만든 뒤 documents main 을 움직이면 그 candidate 는 거부된다(2026-10-03 실측).
- 운영 반영 뒤 롤백 워크플로는 documents main·ai-svc main·홈 master·gitops main 의 head 가 봉인 당시와 같기를 요구한다.
  `ms-20261002-…` 의 롤백 레인은 gitops publisher(`a97a1754`)로 이미 닫혔다.

→ **세 레포 main 에 넣을 것은 전부 candidate 생성 전에 넣는다.**

## 1. candidate 를 만들기 전에 (순서대로)

1. **documents develop → main 릴리스** — 프라이버시 도구 수정(PR #200 `9af1090`, candidate 런 목록을 `branch=release/candidate-<id>` 로 좁힘)이
   develop 에만 있다. 넣지 않아도 다음 candidate 런 1건(목록 79→80건, 약 1,043 KB)까지는 1 MiB 상한 아래지만 그 다음 캠페인은 반드시 터진다.
   릴리스 후 **새 documents main SHA** 가 다음 candidate 의 `approval_source_sha` 가 된다.
   이 릴리스에는 공개 저장소 정리(`specs/2026-10-15-repo-visibility-cleanup-design.md`)가 함께 들어간다 —
   머지 뒤 `plans/2026-10-15-repo-visibility-cleanup/check_cleanup.py` 를 main 트리에 다시 돌린다(계획 Task 5) —
   `--base` = `1689aacb6927bf4102b7265d027f63dfdcd586c9`(비공개 사본 `leva-business-docs` README 「출처」에도 있다).
   C1~C4·C7~C9 는 PASS 필수. C5·C6 이 FAIL 이면 그 사이 develop 에 들어온 다른 PR 때문일 수 있다 — 계획 Task 5 Step 3 의 `git log` 로 무관한 PR 인지 분류하고 기록한다.
2. ai-svc main · 홈 master 에 넣을 변경이 있으면 이때 넣는다(캠페인 범위 결정과 함께).
3. gitops main 확인 — 현재 **`a97a175466962e33ca1823edbb6656091700db81`**(폴백 publisher). 그 사이 또 움직였으면 아래 값을 그 SHA 로 다시 구한다.

## 2. candidate spec 입력값 (gitops main = `a97a1754` 기준)

| 필드 | 값 | 근거 |
|---|---|---|
| `gitops.base_sha` | `a97a175466962e33ca1823edbb6656091700db81` | 현재 main. 다음 base 증명 통과(`prove_next_base.py`) |
| `gitops.base_web_digest` | `sha256:902f1ae1da304750d24225f39577ea03adf7b526d61e77d54edfbf32a45bdebf` | 운영 mission-on 웹(SSH 실측) |
| ★`ai_release_eval_config.rendered_config_sha256`★ | **`9b7d7031fafe5104ec51200e5c1b90ddd9bc38cd305683c672ee95f5238f4f4f`** | 아래 §3 — 이전 spec 값(`bfa0126d…`)을 **복사하면 안 된다** |
| `analytics_privacy.approval_source_sha` | §1-1 뒤의 documents main SHA | 0절 |

## 3. ★AI 렌더 해시는 다시 계산한다★ (리뷰 M3)

검증기 `verify_ai_rendered_config` 는 `gitops.base_sha` 의 `apps/devpath-ai-svc/base` 를 고정 kustomize v5.4.3 으로 렌더해 sha256 을 비교한다
(promote·landing·ai-release-eval 에서 fail-closed — 늦게 터지면 release id 를 버린다). 10/02 생성기는 이 값을 이전 spec 에서 복사했고,
AI base 가 바뀌지 않아서 맞았을 뿐이다. 지금은 ai-svc 이미지(`107fd20a`)와 폴백 env 9개가 바뀌었다.

```
py -B compute_ai_rendered_config.py <gitops clone> <gitops main 체크아웃> <base_sha> <kustomize v5.4.3 바이너리> [expected]
```

검증기의 `_materialize_git_tree`·`validate_ai_rendered_config_bytes` 를 **그대로 import** 하므로 CI 와 다른 것은 kustomize 의 OS 빌드뿐이다
(공식 릴리스 `kustomize_v5.4.3_windows_amd64.zip`, checksums.txt 대조 `5ce680e5…`). 실측(2026-10-03):

| base | 결과 | 의미 |
|---|---|---|
| `eb413814`(10/02 릴리스 base) | `bfa0126d…` = 10/02 spec 값 **일치** | 방법 증명 — Windows 빌드도 CI 와 바이트 동일 |
| `cea3610a`(릴리스 직후) | `7626f312…` | publish 하지 않았어도 이미 달라졌다 |
| **`a97a1754`(현재 main)** | **`9b7d7031…`**(4,431 → 5,100 bytes) | 리뷰어의 독립 계산과 일치 · 런타임 라우팅 검증 통과 |

**다음 생성기 규칙**: 이 필드를 「바뀌는 필드」로 취급해 도구로 계산하고, 생성기의 변경집합 단언에 넣는다
(AI base 가 이전 spec 의 base 와 다르면 값도 달라야 한다).

## 4. 이미지 증거 만기 (2026-10-03 preflight)

`platform-svc` **2026-10-15 07:12Z**(최단) · community·lcs·learning·notification·sandbox 10-21 · gateway 10-23 · admin·ai-svc 10-31.
다음 캠페인이 10-15 를 넘기면 platform-svc 이미지 재빌드가 필요하다(그대로 두면 preverify 에서 막힌다).

> **2026-10-16 갱신**: platform-svc 는 이미 만기가 지났다 → 재빌드 확정. 캠페인은 Codex 리뷰(10-19 15:13 이후) 뒤라
> 10-21 을 넘기면 community·lcs·learning·notification·sandbox 도, 10-23 을 넘기면 gateway 도 재빌드 대상이다. 시작 시점에 preflight 로 다시 확인한다.

## 5. 범위 후보로 함께 볼 것

- **(2026-10-16 추가) 이 캠페인을 여는 제품 변경 — 점검 명세 ④⑤**. 둘 다 develop 에만 있다(frontend 는 main 푸시에서만 배포, 홈 master 는 롤백 창 동결).
  - frontend develop: #248(`ff6b2a73` — 로그인 초대 안내·카피·og 이미지·보안 헤더·세션 힌트·브랜드 「레바」) + #249(로고 스크린리더 라벨·관리자 앱 문구 「레바」, 머지 후 SHA 확인)
  - 홈 develop: #100(validate 저니 입력 안정화) + #102(`46fc4de3` — 초대 CTA `?intent=invite`·승인 메일 약속 삭제·12주 경로 예시·HSTS·시각 기준선 재녹화)
  - shared develop: #88(README)·#89(MinIO 이미지 고정)·#90(Testcontainers 1.21.4, CI 에서 IT skip 금지) — 전부 테스트·문서라 운영 아티팩트에는 영향 없음. main 반영은 선택.

- **ai-svc M1 근본 수정** — 폴백을 켜면 Claude SDK 재시도가 2→0 이 되어, GPU 회수·7b 부재 시 폴백 이전보다 나빠진다(운영에서 지금 켜져 있다).
  재시도 예산을 실제 폴백 가용성에 연동하는 수정이 들어가려면 ai-svc 이미지 릴리스가 필요하다.
- gitops develop 의 staging 정비(staging 이미지 3개·route 8080·migration job·gateway CORS·TLS 10년 스크립트) — 폴백 publisher 범위에서 뺐다.
  `scripts/`·`staging/` 이라 main PR 정책상 publisher 경로다.
- develop 의 릴리스 관리 kustomization 4개(web·ai-svc·admin·migration)에 남은 r3 값 — develop→main 을 다시 쓸 일이 생기면 먼저 main 을 develop 으로 sync 한다.
