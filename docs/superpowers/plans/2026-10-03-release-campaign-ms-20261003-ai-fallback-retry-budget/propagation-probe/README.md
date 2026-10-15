# Cloudflare Pages 전파 시간 실측 (2026-10-06)

landing 게이트 수정(gitops #169)이 「같은 dist·다른 release 마커」를 최대 30초 예산 안에서 재시도한다.
그 예산이 실제 전파 시간에 충분한지 보려고 쓴 일회용 스크립트와 결과다.
**운영(production 브랜치)에는 배포하지 않았다.** preview 브랜치 `probe-prop-1006` 의 별칭에만 올렸다.

## 방법

- 홈 master(`abdf57a7`) dist 사본에 `.well-known/devpath-release/propagation-probe.json`(`{"seq":n}`)을 넣고
  `wrangler@4.146.0 pages deploy --branch probe-prop-1006` 을 4번 반복했다. 매번 같은 경로의 내용만 바뀐다
  (`Uploaded 1 files (51 already uploaded)` — 2026-10-06 운영 landing 실패 때와 같은 모양).
- wrangler 가 끝난 직후부터 75초 동안 별칭 URL 을 약 1초 간격으로 읽었다(게이트와 같은 User-Agent, 서울 → ICN PoP).
- `probe-propagation.log` 한 줄 = `<회차> <배포 종료 뒤 ms> <HTTP> <cf-ray> <본문>`.

## 결과

| 회차 | 표본 | 옛 내용 200 | 마지막 옛 응답 | 응답 순서 (S=옛 내용, N=새 내용) |
|---|---|---|---|---|
| 1 (별칭 첫 배포) | 69 | 0 | — | `NNNN…` |
| 2 | 73 | 0 | — | `NNNN…` |
| 3 | 71 | 7 | 배포 종료 14.2초 뒤 | `SSNSNSNSNSNNSNNN…` |
| 4 | 74 | 5 | 5.5초 뒤 | `SSSSNSNNN…` |

비-200 응답은 한 번도 없었다.

## 읽는 법

- 「같은 경로·다른 내용 파일은 전파 중 옛 내용을 HTTP 200 으로 준다」가 재현됐다(내용이 바뀐 배포 3번 중 2번).
  404 재시도만으로는 덮이지 않는다는 #169 의 전제와 맞는다.
- 옛 응답과 새 응답이 **섞여** 온다. 한 번 새 내용을 받았다고 전파가 끝난 것이 아니고, 한 번 옛 내용을 받았다고 실패도 아니다.
- 관측한 최장은 14.2초다. 게이트 프로브는 새 응답을 한 번만 받으면 통과하고 예산은 30초다.
- #169 이전 게이트(지금의 gitops main)는 첫 응답이 옛 내용이면 바로 실패한다 — 3·4회차가 그 경우다.

## 한계

- 내용이 바뀐 배포는 3번뿐이다.
- PoP 한 곳(ICN)에서만 쟀다. 릴리스 런너는 미국에서 본다.
- preview 별칭(`*.pages.dev`)이다. 운영은 커스텀 도메인(`leva.ai.kr`)이다.
- 운영 경로의 실제 값은 gitops #171 이 재시도 통과 때 남기는 stderr 한 줄로 모인다.

## 다시 돌리려면

- 스크립트의 `S` 는 당시 세션의 임시 폴더다. 새 폴더로 바꾸고 `$S/dist-master` 에 홈 dist 를 둔다.
  홈 빌드는 git 이력(sitemap lastmod)을 읽으므로 `git archive` 사본으로는 실패한다 — 홈 워크트리에서 `node build.mjs`.
- wrangler 는 로컬 OAuth 로그인(`~/.wrangler/config/default.toml`)을 쓴다.
- 남은 것: 브랜치 `probe-prop-1006` 의 preview 배포 4개(`8184788b`·`d7ec49c6`·`109b9958`·`bad6137f`). 운영과 무관하다.
