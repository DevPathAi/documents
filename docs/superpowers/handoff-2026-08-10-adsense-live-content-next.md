# 핸드오프 — 애드센스 심사 신청 완료, 다음은 콘텐츠 보강

- 작성일: 2026-08-10
- 다음 세션 우선순위: **① 콘텐츠 보강 → ② 원래 작업(인터뷰 이식 등)**

## 한 줄 요약

애드센스를 앱과 홈페이지 양쪽에 붙이고, 죽어 있던 `leva.ai.kr`을 Cloudflare Pages로 살린 뒤, 사업계획서와 어긋나던 브랜드·가격·처리방침을 맞춰 **심사 신청까지 마쳤다.** 전 레포 열린 PR 0건.

## 레포 최종 상태 (2026-08-10 실측)

| 레포 | develop HEAD | 열린 PR |
|---|---|---|
| devpath-home-page | `6288c50` (#17) | 0 |
| devpath-platform-svc | `ab8cd64` (#47) | 0 |
| devpath-frontend | `7c01f3e` (#114) | 0 |
| devpath-shared | `5317089` (#56) | 0 |
| devpath-learning-svc | `0e7abd6` (#46) | 0 |
| devpath-ai-svc | `47031c0` (#34) | 0 |

## 이번 세션에 한 일

### 1. 애드센스 병행 도입 — 앱 (Task 1~11 완결)

슬롯별로 `HOUSE`/`ADSENSE`/`OFF`를 admin에서 선택. `GET /ads`를 판별 유니온 봉투로 확장. 애드센스 가지엔 **자체 측정을 붙이지 않는다**(구글 정책) — 테스트가 이벤트 0건과 `VisibilityDetector` 부재를 함께 단언.

PR: shared #56 · platform-svc #45/#46/#47 · frontend #114 · home-page #10.

**⚠️ 앱의 애드센스는 코드만 `develop`에 있고 배포되지 않았다.** 이미지 빌드가 `main` push에서만 동작하는데 frontend는 main 대비 **+243커밋**이라 별도 릴리스 결정이 필요하다.

### 2. `leva.ai.kr` 라이브 (Task 1~8 완결)

홈페이지는 **한 번도 배포된 적이 없었다**(`HANDOFF.md:8` "Cloudflare Pages 미연결"). 루트 도메인에 A 레코드조차 없었다.

- Cloudflare Pages 프로젝트 `devpath-home-page` (**직접 업로드** — GitHub 연동 아님)
- **NS를 가비아 → Cloudflare로 이전** (`mallory`/`matias.ns.cloudflare.com`)
- 커스텀 도메인 `leva.ai.kr`(CNAME flattening) + `www`

### 3. 사업계획서 정합화 (PR #15·#16·#17)

브랜드 `Leva` 전면 교체(OG 이미지 재생성 포함) · 가격 무료+9,900 2단계 · **개인정보 처리방침 신설**(`/privacy`).

### 4. 애드센스 심사 신청 (사용자 수행)

신청 시점 실측: 4개 경로 200 · **Googlebot UA 200 · Mediapartners-Google UA 200**.

---

## 🔴 다음 세션 우선순위 ① — 콘텐츠 보강

### 왜 이게 먼저인가

애드센스 거절의 **최유력 사유가 「가치 있는 콘텐츠 부족」**이고, 현재 `leva.ai.kr`은 **제품 소개 1페이지 + 처리방침**이 전부다. 거절되고 나서 만들면 재신청까지 그만큼 늦어지므로, **심사 대기(수일~2·4주) 중에 미리 만들어 두는 것**이 시간을 버는 유일한 방법이다.

재신청에 횟수 제한은 없다.

### 착수 전 확인할 것

1. **심사 결과가 이미 나왔는지** — 애드센스 콘솔의 사이트 상태(`Getting ready` / `Ready` / `Needs attention`). 승인됐다면 콘텐츠 보강의 긴급도가 내려가고 광고 슬롯 배치 결정이 앞선다.
2. **거절이라면 사유 원문** — 「가치 있는 콘텐츠 부족」인지 정책 위반인지에 따라 대응이 완전히 다르다.

### 콘텐츠 보강 시 지켜야 할 것

- **정적 HTML로 만든다.** 크롤러가 읽어야 하므로 인터랙티브 JS 위젯은 콘텐츠로 계산되지 않는다. (앱이 심사 대상이 될 수 없었던 이유와 같다 — CanvasKit은 캔버스에 그린다.)
- **`build.mjs`의 `DEPLOY_ENTRIES`에 등록해야 배포된다.** 이 레포는 화이트리스트 복사 빌드라 파일만 만들면 조용히 누락된다.
- `robots.txt`가 이미 `Sitemap: https://leva.ai.kr/sitemap.xml`을 가리킨다. **콘텐츠가 여러 페이지가 되면 `sitemap.xml`을 실제로 만들 것** (지금은 의도적으로 안 만들었다).
- **심사 중이라면 `<head>` 애드센스 스크립트·`ads.txt`·퍼블리셔 ID를 건드리지 말 것.** 사이트 삭제 후 재등록도 금지(공식 문서가 지연을 경고).

---

## 다음 세션 우선순위 ② — 원래 작업

### 2-A. 인터뷰 이식 (분리해둔 2단계)

`devpath-landing-page`의 **AI 학습 진단 인터뷰**(A/B 답변 비교 + Sheets 증거 파이프라인)를 홈페이지로 옮기고 랜딩 레포를 폐기한다. 사용자가 「인터뷰 기능을 홈페이지로 이식」으로 명시 선택했다.

**심사에 기여하지 않는다**(인터랙티브 JS)는 이유로 1단계에서 분리했다. 실측된 선결조건:

| 필요 | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude 호출 (모델 2종) — **실제 토큰 비용** |
| `TURNSTILE_SECRET` + site key | 봇 차단 |
| **Cloudflare KV 네임스페이스** (`INTERVIEW_KV`) | rate limit + 예산 상한 |
| Apps Script / Sheets | 증거 수집 |

기존 랜딩은 `devpath-landing-page.pages.dev`로 **살아 있다**(GitHub 연동, 2026-06-24 마지막 배포). 이식 시 홈페이지의 기존 **리드폼과 역할이 겹치므로 교통정리 필요.**

### 2-B. 이월 과제

| 항목 | 내용 |
|---|---|
| **랜딩 프로젝트 시크릿** | `devpath-landing-page`의 `ANTHROPIC_API_KEY`·`TURNSTILE_SECRET`이 **`plain_text`** 로 저장돼 API 평문 조회가 가능하다. 과금 자격증명이라 `secret_text` 전환 권장 |
| 앱 애드센스 재마운트 | 재마운트가 새 광고 요청을 유발하지 않는다(10초 주기로도 요청 1건). 심사 전엔 무영향이나 **승인 후 재확인 필요** |
| frontend 릴리스 | main 대비 **+243커밋**. 앱 애드센스를 배포하려면 이 릴리스 결정이 선행 |
| SPF·DMARC | `leva.ai.kr` 존에 둘 다 없다 |
| `APPS_SCRIPT_URL` | 미설정 — 리드폼이 `endpoint_not_configured`로 graceful degrade 중 |
| 지식베이스 이월 | 임베딩 모델 한국어 개념질문 약점 · 삭제문서 sweep 부재 |
| ①결제 | PortOne 통합 PG mock 선구현 마스터 스펙만 있고 구현 미착수 |

---

## 운영 정보 (다음 세션이 알아야 할 것)

### Cloudflare

| 항목 | 값 |
|---|---|
| Account ID | `f74eb88cda37ff4f8e6c27aaaf91631c` |
| Zone (`leva.ai.kr`) | `22159344c213567f683ccf83c0d22780` |
| Pages 프로젝트 | `devpath-home-page` (직접 업로드, 프로덕션 브랜치 `develop`) |
| 요금제 | Free Website $0 |

**API 토큰은 이전 세션에서 발급한 것이라 폐기 요청 상태다.** 필요하면 새로 받을 것 (권한: `Pages:Edit` + `DNS:Edit` + `Zone:Edit`, Zone Resources는 **All zones**).

**재배포는 수동이다** — `develop` 머지만으로 배포되지 않는다:
```bash
cd /d/workspace/dpa/devpath-home-page
git switch develop && git pull --ff-only
npm run build
export CLOUDFLARE_API_TOKEN='<토큰>'
npx wrangler pages deploy dist --project-name devpath-home-page --branch develop
```

### AWS

**EC2 `devpath-k3s`(t3.xlarge)가 2026-08-10 03:59 UTC부터 가동 중이다.** 시간당 약 $0.2.

★**`leva.ai.kr`은 Cloudflare Pages라 AWS와 무관하다**★ — EC2를 꺼도 홈페이지·처리방침·`ads.txt`는 살아 있고 **심사에 영향이 없다.** 죽는 건 `app`·`api`·`admin`뿐이다. 앱을 쓸 일이 없으면 정지해 비용을 아낄 것(재가동 실측 약 5분 30초).

RDS `devpath-pg`는 정지해도 AWS가 7일 후 자동 재개시킨다.

### 사업자 정보 (처리방침·푸터에 게시 중)

상호 **레바** · 사업자등록번호 **796-76-00732** · 개인정보 보호책임자 **김민구** · 문의 `info@leva.ai.kr`.
**사업장 주소는 게시하지 않기로 결정했다** — 아파트 주소이고, 결제 전이라 전자상거래법상 표시 의무가 아직 없다. 결제 도입 시 재판단.

---

## ★이번 세션의 교훈 — 다음 세션이 같은 함정을 밟지 않도록★

### 검증

- ★**배포 직후 단발 측정은 믿을 수 없다.** 두 번 오판할 뻔했다. 엣지가 **경로별로 옛/새 버전을 섞어** 응답한다(`/privacy.html`은 새 버전인데 `/`는 옛 버전이라 「DevPath 10건」으로 보였다). 522도 몇 초간 뜬다. **안정될 때까지 반복 측정할 것.**
- ★**`/ads.txt`는 상태코드만 보면 안 된다.** SPA 폴백이 `index.html`을 200으로 돌려준다. **`content-type: text/plain`까지 확인.**
- ★**「고쳤다」와 「안 고친 게 남았다」는 다르다.** 「`devpath.ai` 부재」·「`DevPath` 부재」 같은 **부재 단언**이 계획에 없던 지점을 두 번 잡아냈다(JSON-LD `url`·`mailto` 2곳 / `e2e/smoke.spec.js`의 옛 제목 단언).
- ★**브랜드·도메인 교체는 레포 전체 grep이 필수.** `index.html`만 보면 테스트 파일과 주석에 남는다.
- **OG 이미지는 텍스트 검사로 안 잡힌다.** 재생성 후 **눈으로 볼 것.**

### Cloudflare

- ★**API로 존을 만들면 기존 DNS 레코드를 하나도 가져오지 않는다**(대시보드 온보딩과 다름). 그대로 NS를 바꿨다면 **Google Workspace 메일과 app·api·admin이 즉시 죽었다.** 「NS 변경 직전 1:1 대조 게이트」가 실제로 막았다.
- ★**Pages 커스텀 도메인도 API로 추가하면 DNS 레코드를 만들어 주지 않는다** — `pending`에 멈춘다. CNAME(`proxied=true`)을 직접 만들어야 한다.
- ★**`.html`을 떼는 clean URL로 308 리다이렉트한다**(`/privacy.html`→`/privacy`). canonical이 리다이렉트 URL을 가리키고 있었다.
- **`app`·`api`·`admin`은 `proxied=false` 유지** — 켜면 k3s TLS와 충돌하고 gateway SSE가 버퍼링에 걸린다.
- **Email Obfuscation이 `mailto:`를 가린다**(`/cdn-cgi/l/email-protection#hex`). 소스에서 주소가 grep 안 되는 게 정상.
- **Functions가 있으면 정적 요청까지 Function을 호출**해 Workers Free 100k/일을 소모한다 → `_routes.json`으로 `/api/*`만 한정(적용 완료).
- `wrangler pages project create`가 실패해도 **REST API 직접 호출은 성공**할 수 있다.

### DNS

- **가비아는 ALIAS/ANAME이 없다**(A/CNAME/MX/TXT/SRV/SPF만) → apex CNAME 불가 → NS 이전이 유일한 길.
- **기존 NS 유지 + CF 추가는 금지.** 위임은 집합이라 리졸버가 임의로 고른다 → 간헐 장애.
- **전파 확인은 공개 리졸버가 아니라 `.kr` 레지스트리에 직접**(`b.dns.kr`). 이 존은 기본 TTL이 86400이라 8.8.8.8은 한참 옛값을 준다.
- **공개 DNS로 존을 전수 열거할 수 없다**(AXFR 차단). "이것 말고 없다"는 증명 못 한다 → 최종 확인은 가비아 콘솔 육안 대조.

### 도구

- **nslookup 출력은 한글 로케일에서 깨진다** → DoH JSON(`dns.google/resolve`) 쓸 것.
- 스캔 PDF는 `pdftotext`로 안 읽힌다. 이 환경엔 `pdftoppm`도 없다 → 이미지로 받아 볼 것.

---

## 미해결

**사용자가 보고한 랜딩 결함 항목이 1·3·4번이라 2번이 무엇인지 확인되지 않았다.** 다음 세션에서 확인할 것.
