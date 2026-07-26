# WS-D 실배포 세션 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans(권장 — AWS 비용 건별 확인 게이트가 많아 인라인 실행 적합). 문서·frontend Task(3·4)는 superpowers:subagent-driven-development로 위임 가능(Scope Lock 문구+절대경로 강제 필수). 단계는 체크박스(`- [ ]`).

**Goal:** 선행 정리(광고 문서·위생) → 전 레포 develop→main 릴리스 컷 → AWS EC2+k3s+ArgoCD에 DevPath 베타를 실배포하고 `https://app.leva.ai.kr` E2E 스모크까지 통과시킨다.

**Architecture:** 배포 인프라 설계·절차의 SSoT는 devpath-gitops `docs/superpowers/specs/2026-07-05-aws-k3s-deployment-design.md`·`plans/2026-07-05-aws-k3s-deployment.md`(이하 "gitops 플랜")이다. 이 플랜은 그 위의 세션 오케스트레이션: 실측 확정값 주입 + 릴리스 컷 + 어댑테이션 3건(마이그레이션 Job RDS 배선·Strimzi KRaft 대응·gitops 변경 묶음 릴리스)만 추가한다. 스펙: `docs/superpowers/specs/2026-07-27-ws-d-deploy-session-design.md`.

**Tech Stack:** gh CLI · aws CLI · k3s · ArgoCD · SealedSecrets · Strimzi Kafka · cert-manager(Traefik) · RDS PostgreSQL 17(pgvector) · Flyway · Docker · Flutter Web

## Global Constraints

- 리전 **ap-northeast-2**(서울) · EC2 **t3.xlarge**(Ubuntu 22.04, EBS 50GB) · RDS **PostgreSQL 17 db.t4g.micro**(pgvector, 20GB) · Elastic IP. 예산 ~$130~180/월.
- 도메인: `api.leva.ai.kr`(gateway)·`app.leva.ai.kr`(web)·`admin.leva.ai.kr`(admin) → EIP. ClusterIssuer email = `deepestdark@gmail.com`.
- **`WEB_API_BASE_URL = https://api.leva.ai.kr`** — `/api/v1` 경로 금지(실측: gateway 라우트에 prefix 없음, web 소스는 `/ads` 등 루트 상대경로, 로컬 실API 검증값 `http://localhost:8080`).
- **main·develop 직접 push 금지**(전부 PR 경유, gitops bot 커밋만 예외). 머지는 merge commit. **CI 녹색 확인 전 머지 금지**.
- **비용 발생·비가역 AWS 명령(run-instances·allocate-address·create-db-instance 등)은 실행 직전 사용자 건별 확인**(2026-07-27 사용자 결정).
- 비밀값 평문 커밋 금지. 비밀값은 파일 경유로 다루고 명령 인라인 노출 최소화. 시크릿 파일은 사용 후 즉시 삭제.
- 클러스터 조작(kubectl·helm·kubeseal·argocd CLI)은 **EC2 위에서 ssh로 실행**(Windows 로컬 도구 의존 회피). 로컬은 aws·gh·git만.
- gitops 매니페스트 변경은 **작업 브랜치→develop PR 머지→develop→main 릴리스 PR** 묶음 반복. 릴리스 PR에서 kustomization 이미지 태그 충돌 시 main 쪽(bot 최신 SHA) 우선 해소.
- 서브에이전트 위임 시: "이 Task만 수행, 완료 후 보고·정지, 명세 밖 즉흥 구현 금지, 부족 시 NEEDS_CONTEXT" + 모든 git/파일 명령에 절대경로 또는 `git -C <절대경로>` 강제.
- 각 레포 CLAUDE.md의 검증 규칙 준수: documents=코드 실측 대조, gitops=`kubectl kustomize` 렌더 검증, frontend=`melos run analyze`·`test`.
- 커밋 메시지 = Conventional Commits + 트레일러 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`(플랜 내 `-m` 예시에 생략돼 있어도 항상 부착).

---

## File Structure

- documents(이 레포): `04_API_명세서.md`·`02_ERD_문서.md`·`17_스케줄.md`·`06_화면_기능_정의서.md` 수정 (Task 3)
- devpath-frontend: Create `apps/admin/Dockerfile`·`apps/admin/nginx.conf`, Modify `.github/workflows/ci.yml`(admin-image·admin-deploy 잡)·`apps/web/Dockerfile`(ARG 기본값 정정) (Task 4)
- devpath-gitops: Modify `apps/_migration/base/job.yaml`(RDS env 전환), Create `apps/devpath-redis/base/{deployment,service,pvc,kustomization}.yaml`·`infra/cert-manager/cluster-issuer.yaml`·`apps/{devpath-gateway,devpath-web,devpath-admin}/base/ingress.yaml`·`kafka/kafka-cluster.yaml`(EC2 적용용)·`docs/runbook-k3s-bootstrap.md`, Modify `apps/*/base/deployment.yaml`(인프라 env)·각 `kustomization.yaml`(sealedsecret·ingress 추가) (Task 11~15)
- 릴리스 컷은 파일 생성 없음(PR·머지 오케스트레이션) (Task 2·5~8)

---

## Task 1: 로컬 위생 + `.github` CLAUDE.md 수정 폐기

**Files:** 없음(로컬 git 상태만 변경, 커밋 없음)

**Interfaces:**
- Consumes: 없음
- Produces: 전 로컬 레포가 origin/develop 동기 상태(이후 Task의 브랜치 분기 기준점)

- [ ] **Step 1: 머지 완료 브랜치에 방치된 5개 레포를 develop으로 복귀+pull**

```powershell
foreach ($r in @('devpath-shared','devpath-gateway','devpath-lcs-svc','devpath-learning-svc','devpath-notification-svc')) {
  git -C "D:\workspace\dpa\$r" checkout develop
  git -C "D:\workspace\dpa\$r" pull --ff-only origin develop
}
```
Expected: 각 레포 `Switched to branch 'develop'` + `Fast-forward`(또는 Already up to date).

- [ ] **Step 2: learning 테스트 부산물 삭제**

```powershell
Remove-Item -Recurse -Force D:\workspace\dpa\devpath-learning-svc\.jqwik-database
```

- [ ] **Step 3: `.github` CLAUDE.md 로컬 수정 폐기(2026-07-27 사용자 결정) + develop 동기화**

```powershell
git -C D:\workspace\dpa\.github checkout -- CLAUDE.md
git -C D:\workspace\dpa\.github pull --ff-only origin develop
```

- [ ] **Step 4: 검증 — 5+1개 레포 전부 `HEAD=develop`·`behind=0`·dirty에 `.omc/`·`.env.local` 외 없음**

```powershell
foreach ($r in @('devpath-shared','devpath-gateway','devpath-lcs-svc','devpath-learning-svc','devpath-notification-svc','.github')) {
  $p="D:\workspace\dpa\$r"; "=== $r $(git -C $p branch --show-current) behind=$(git -C $p rev-list --count "develop..origin/develop")"; git -C $p status --porcelain
}
```
Expected: 전부 develop·behind=0. dirty는 `?? .omc/`류만.

## Task 2: svc-template PR #4 머지

**Files:** 없음

**Interfaces:**
- Consumes: 없음 (독립)
- Produces: svc-template develop에 CI registry 인증 env 반영(org 열린 PR 0건 상태)

- [ ] **Step 1: CI 상태 재확인**

```powershell
gh pr checks 4 -R DevPathAi/devpath-svc-template
```
Expected: build pass(image는 main 한정 skip). 실패 시 머지 금지, 원인 조사로 전환.

- [ ] **Step 2: merge commit으로 머지 + 검증**

```powershell
gh pr merge 4 -R DevPathAi/devpath-svc-template --merge
gh pr view 4 -R DevPathAi/devpath-svc-template --json state,mergedAt
```
Expected: `"state": "MERGED"`.

## Task 3: 베타 광고 문서 반영 (documents PR)

**Files:**
- Modify: `D:\workspace\dpa\documents\04_API_명세서.md` · `02_ERD_문서.md` · `17_스케줄.md` · `06_화면_기능_정의서.md`
- 근거(실측 대상): platform `src/main/java/ai/devpath/platform/ads/{AdController,AdminAdController}.java`+`dto/`, shared `src/main/resources/db/migration/V202607221001__advertisement.sql`·`V202607221002__ad_settings.sql`·`V202607221003__ad_daily_stats.sql`, gateway `src/main/resources/application.yml:12`

**Interfaces:**
- Consumes: 없음 (독립)
- Produces: documents develop에 광고 문서 정합 반영(Task 8 릴리스 컷의 내용물)

- [ ] **Step 1: 브랜치 분기**

```powershell
git -C D:\workspace\dpa\documents checkout develop
git -C D:\workspace\dpa\documents pull --ff-only origin develop
git -C D:\workspace\dpa\documents checkout -b docs/beta-ads-docs
```

- [ ] **Step 2: 근거 실측** — 위 Files의 근거 파일 5종을 읽고 요청/응답 DTO 필드·테이블 컬럼·제약을 확보한다(추측 금지). 아래 Step의 표 골격에 실측 필드를 채운다.

- [ ] **Step 3: 04_API — `## 11. 베타 광고 (Ads)` 섹션 신설**

`## 10. Admin` 섹션(`### 10.8` 끝) 뒤에 삽입, 기존 `## 11. Rate Limit · 사용량 한도`→`## 12.`, `## 12. 관련 문서`→`## 13.`으로 갱신. 내부 앵커 깨짐을 `Select-String -Path D:\workspace\dpa\documents\*.md -Pattern '#11-|#12-|11_Rate|관련-문서'`로 확인·동반 수정. 섹션 골격(WHAT 확정, 필드는 Step 2 실측값):

```markdown
## 11. 베타 광고 (Ads)

> 베타 무료기간 하우스/스폰서 광고. 소유=platform-svc `ads` 모듈. 슬롯 3종
> `DASHBOARD_TOP`·`COMMUNITY_FEED`·`CONTENT_PAGE`. gateway `platform-auth` 라우트(`/ads/**`) 경유.

### 11.1 서빙·이벤트 (로그인 사용자)

| 메서드 | 경로 | 설명 | 응답 |
|---|---|---|---|
| GET | `/ads?slot={슬롯}` | 슬롯별 활성 광고 1건(가중치 랜덤) | 200 광고 / 204 없음·전역off |
| POST | `/ads/{id}/events` | 노출/클릭 기록 `{"type":"IMPRESSION"\|"CLICK"}` | 202 / 404 미존재 |

### 11.2 관리 (Admin)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/ads?slot=` | 광고 목록 |
| POST | `/admin/ads` | 생성 |
| PUT | `/admin/ads/{id}` | 수정 |
| DELETE | `/admin/ads/{id}` | 삭제 |
| POST | `/admin/ads/{id}/image` | 이미지 업로드(멀티파트, S3ObjectStorage) |
| GET | `/admin/ads/settings` | 전역 설정 조회 |
| PUT | `/admin/ads/settings` | 전역 토글 |
| GET | `/admin/ads/{id}/stats` | 일별 노출/클릭 통계 |
```

또한 문서 상단·게이트웨이 라우팅 표(존재 시)에 `/ads/**`=platform 반영, 04 총계 표기를 grep으로 찾아 +11 갱신.

- [ ] **Step 4: 02_ERD — 광고 3테이블 반영**

마이그레이션 SQL 실측 기반으로 (a) mermaid ERD에 `advertisement`·`ad_settings`·`ad_daily_stats` 추가(관계: ad_daily_stats N:1 advertisement) (b) 테이블 정의 절 추가 (c) "Flyway 마이그레이션 31파일" 표기를 grep으로 찾아 **34파일**(최신 `V202607221003`)로 갱신.

- [ ] **Step 5: 17_스케줄 — 수치 갱신**

`Select-String -Path D:\workspace\dpa\documents\17_스케줄.md -Pattern '엔드포인트'`로 총계 표기를 찾아 백엔드 총계·platform 몫에 +11 반영(현행 표기 기준 재계산, 3차 M-1이 세운 산식 유지).

- [ ] **Step 6: 06_화면 — 광고 화면 반영**

(a) `## 12. 관리자 화면군` 끝(`### 12.7` 뒤)에 `### 12.8 광고 관리 (SCR-A-010)` 추가 — 전역 토글·슬롯 필터·목록·생성/수정 폼·통계 다이얼로그(frontend `apps/admin/lib/src/features/ads` 실측). (b) 화면 9(홈 대시보드)·11.1(커뮤니티 홈)·5(콘텐츠 뷰어)에 광고 슬롯 위젯(`AdSlotWidget`, 없으면 미표시) 문구 추가. (c) `## 1. 화면 인벤토리` 표에 SCR-A-010 행 추가.

- [ ] **Step 7: 정합성 검증(이 레포의 테스트)**

```powershell
Select-String -Path D:\workspace\dpa\documents\04_API_명세서.md,D:\workspace\dpa\documents\02_ERD_문서.md,D:\workspace\dpa\documents\06_화면_기능_정의서.md -Pattern 'ads|광고' | Measure-Object
```
Expected: 3문서 모두 매치 > 0. 04의 섹션 번호 연속성(`^## \d+\.` 목록)·02 mermaid 렌더(코드블록 짝) 육안 확인.

- [ ] **Step 8: 커밋 + PR + 머지**

```powershell
git -C D:\workspace\dpa\documents add 04_API_명세서.md 02_ERD_문서.md 17_스케줄.md 06_화면_기능_정의서.md
git -C D:\workspace\dpa\documents commit -m "docs: 베타 광고 API·ERD·스케줄·화면 반영 (7/22 머지분 정합)"
git -C D:\workspace\dpa\documents push -u origin docs/beta-ads-docs
gh pr create -R DevPathAi/documents --base develop --head docs/beta-ads-docs --title "docs: 베타 광고 문서 반영 (04·02·17·06)" --body "7/22 베타 광고 머지분(shared#47·platform#35/#36·gateway#25·frontend#76/#77)의 문서 역류. 스펙: docs/superpowers/specs/2026-07-27-ws-d-deploy-session-design.md 섹션1-1a"
gh pr checks <PR번호> -R DevPathAi/documents; gh pr merge <PR번호> -R DevPathAi/documents --merge
```
Expected: 머지 완료(checks 없으면 즉시 머지 가능).

## Task 4: admin 이미지 경로 추가 (frontend PR)

**Files:**
- Create: `D:\workspace\dpa\devpath-frontend\apps\admin\Dockerfile` · `apps\admin\nginx.conf`
- Modify: `.github\workflows\ci.yml`(잡 2개 추가) · `apps\web\Dockerfile:4`(ARG 기본값 정정)

**Interfaces:**
- Consumes: 없음 (독립)
- Produces: main 릴리스 시 `ghcr.io/devpathai/devpath-admin:{sha,main}` 발행 + gitops `apps/devpath-admin` 태그 bot 커밋 경로(Task 7이 트리거, gitops `devpath-admin` Deployment가 소비)

- [ ] **Step 1: 브랜치 분기**

```powershell
git -C D:\workspace\dpa\devpath-frontend checkout develop
git -C D:\workspace\dpa\devpath-frontend pull --ff-only origin develop
git -C D:\workspace\dpa\devpath-frontend checkout -b feat/admin-image
```

- [ ] **Step 2: `.dockerignore` 위치 실측**

```powershell
Get-ChildItem D:\workspace\dpa\devpath-frontend -Filter .dockerignore -Recurse -Depth 2 | Select-Object FullName
```
루트에 있으면 그대로 재사용(빌드 컨텍스트=루트 공유). `apps/web`에만 있으면 동일 내용을 루트로 승격 또는 admin용 복사 — 실측 결과에 따름.

- [ ] **Step 3: `apps/admin/nginx.conf` 생성** (web과 동일)

```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 4: `apps/admin/Dockerfile` 생성** (web 미러, 경로만 admin — 올바른 ARG 기본값)

```dockerfile
# ---- build stage: Flutter Web ----
FROM ghcr.io/cirruslabs/flutter:stable AS build

ARG API_BASE_URL=https://api.leva.ai.kr
ARG USE_MOCK=false

WORKDIR /src
# 워크스페이스 전체 복사(Dart pub workspaces 단일 해석에 전 멤버 필요)
COPY . .

# cirruslabs/flutter:stable ships Flutter 3.44.0/Dart 3.12.0; pubspec requires ^3.12.1 (로컬 dev=Flutter 3.44.1/Dart 3.12.1).
# 이미지 내 Flutter가 detached-HEAD([user-branch])이라 flutter upgrade 불가 → 3.44.1 tarball로 직접 교체.
RUN curl -fsSL https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.44.1-stable.tar.xz \
    | tar -xJ --strip-components=1 -C /sdks/flutter \
 && git config --global --add safe.directory /sdks/flutter \
 && flutter --version

# melos 부트스트랩(CI와 동일한 흐름) — pub-cache/bin을 PATH에 추가
ENV PATH="/root/.pub-cache/bin:${PATH}"
RUN dart pub global activate melos 7.0.0 \
 && melos bootstrap

# 실 API 설정을 빌드시 각인(Flutter Web은 런타임 주입 불가)
RUN cd apps/admin \
 && flutter build web --release \
      --dart-define=API_BASE_URL=${API_BASE_URL} \
      --dart-define=USE_MOCK=${USE_MOCK}

# ---- runtime stage: nginx ----
FROM nginx:alpine AS runtime
COPY --from=build /src/apps/admin/build/web /usr/share/nginx/html
COPY apps/admin/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
```

- [ ] **Step 5: `apps/web/Dockerfile:4` ARG 기본값 정정** (잘못된 `/api/v1` 제거 — 실측 근거는 Global Constraints)

```dockerfile
ARG API_BASE_URL=https://api.leva.ai.kr
```

- [ ] **Step 6: ci.yml에 admin-image·admin-deploy 잡 추가** (web 잡 미러 — `web-deploy` 잡 뒤에 추가)

```yaml
  admin-image:
    needs: analyze-test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v6
      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v7
        with:
          context: .
          file: apps/admin/Dockerfile
          push: true
          build-args: |
            API_BASE_URL=${{ vars.WEB_API_BASE_URL }}
            USE_MOCK=false
          tags: |
            ghcr.io/devpathai/devpath-admin:${{ github.sha }}
            ghcr.io/devpathai/devpath-admin:main
          cache-from: type=gha
          cache-to: type=gha,mode=max

  admin-deploy:
    needs: admin-image
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/create-github-app-token@v3
        id: app-token
        with:
          app-id: ${{ secrets.GITOPS_APP_ID }}
          private-key: ${{ secrets.GITOPS_APP_PRIVATE_KEY }}
          owner: DevPathAi
          repositories: devpath-gitops
      - uses: actions/checkout@v6
        with:
          repository: DevPathAi/devpath-gitops
          token: ${{ steps.app-token.outputs.token }}
          path: gitops
      - name: Install kustomize
        run: |
          curl -sLo kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv5.4.3/kustomize_v5.4.3_linux_amd64.tar.gz
          tar -xzf kustomize.tar.gz && sudo mv kustomize /usr/local/bin/
      - name: set image to commit SHA
        working-directory: gitops/apps/devpath-admin/base
        run: kustomize edit set image ghcr.io/devpathai/devpath-admin=ghcr.io/devpathai/devpath-admin:${{ github.sha }}
      - name: commit & push
        working-directory: gitops
        run: |
          git config user.name "devpath-gitops-bot[bot]"
          git config user.email "devpath-gitops-bot[bot]@users.noreply.github.com"
          git add -A
          git diff --cached --quiet && echo "no change" && exit 0
          git commit -m "deploy(admin): ${{ github.sha }}"
          for i in 1 2 3; do git push && break || (git pull --rebase && sleep 2); done
```

- [ ] **Step 7: 로컬 검증 — analyze·test + docker build/run (R5 게이트)**

```powershell
Set-Location D:\workspace\dpa\devpath-frontend; dart pub global run melos run analyze; dart pub global run melos run test
docker build -f apps/admin/Dockerfile -t devpath-admin:local .
docker run -d --rm -p 18081:8080 --name admin-local devpath-admin:local; Start-Sleep 3; curl.exe -sI http://localhost:18081 | Select-Object -First 1; docker stop admin-local
```
Expected: analyze·test 통과, `HTTP/1.1 200 OK`. (빌드 ~10분+ 소요 — Flutter 이미지 대형)

- [ ] **Step 8: 커밋 + PR + 머지**

```powershell
git -C D:\workspace\dpa\devpath-frontend add apps/admin/Dockerfile apps/admin/nginx.conf apps/web/Dockerfile .github/workflows/ci.yml
git -C D:\workspace\dpa\devpath-frontend commit -m "feat(admin): admin 웹 이미지 빌드·배포 경로 추가 (web 미러) + web ARG 기본값 정정"
git -C D:\workspace\dpa\devpath-frontend push -u origin feat/admin-image
gh pr create -R DevPathAi/devpath-frontend --base develop --head feat/admin-image --title "feat(admin): admin 웹 이미지 빌드·배포 경로 추가" --body "gitops devpath-admin이 참조하는 ghcr.io/devpathai/devpath-admin 발행 경로 신설(WS-D 스펙 섹션2-3). web Dockerfile ARG 기본값 /api/v1 제거(실측: gateway prefix 없음)."
gh pr checks <PR번호> -R DevPathAi/devpath-frontend --watch; gh pr merge <PR번호> -R DevPathAi/devpath-frontend --merge
```
Expected: analyze-test 녹색 후 머지(admin-image는 main 한정 skip=설계대로).

## Task 5: `WEB_API_BASE_URL` 설정 + shared 릴리스

**Files:** 없음(repo variable + PR 오케스트레이션)

**Interfaces:**
- Consumes: 없음
- Produces: frontend repo variable `WEB_API_BASE_URL`(Task 7 이미지 각인이 소비) · shared main(publish 발행 + `ghcr.io/devpathai/devpath-migration:{sha,main}` — Task 13 마이그레이션이 소비)

- [ ] **Step 1: variable 설정 + 확인**

```powershell
gh variable set WEB_API_BASE_URL -R DevPathAi/devpath-frontend --body "https://api.leva.ai.kr"
gh variable list -R DevPathAi/devpath-frontend
```
Expected: `WEB_API_BASE_URL  https://api.leva.ai.kr`.

- [ ] **Step 2: shared develop→main 릴리스 PR + CI 녹색 확인 + 머지**

```powershell
gh pr create -R DevPathAi/devpath-shared --base main --head develop --title "release: develop→main (에러 하드닝·베타게이팅·광고 스키마·migration 이미지)" --body "WS-D 실배포 릴리스 컷 1/12. 스펙: documents docs/superpowers/specs/2026-07-27-ws-d-deploy-session-design.md 섹션2"
gh pr checks <PR번호> -R DevPathAi/devpath-shared --watch
gh pr merge <PR번호> -R DevPathAi/devpath-shared --merge
```

- [ ] **Step 3: main 후속 워크플로 검증 — publish + migration 이미지 + gitops bot 커밋**

```powershell
gh run list -R DevPathAi/devpath-shared --branch main --limit 5
gh api "/orgs/DevPathAi/packages/container/devpath-migration/versions" --jq '.[0].metadata.container.tags'
git -C D:\workspace\dpa\devpath-gitops fetch origin; git -C D:\workspace\dpa\devpath-gitops log origin/main --oneline -3
```
Expected: main CI(image·deploy)·Publish 전부 success, `main` 태그 존재, gitops main에 `deploy(devpath-migration): <sha>` bot 커밋.

## Task 6: gitops 릴리스 (develop→main)

**Files:** 없음

**Interfaces:**
- Consumes: Task 5(bot 커밋이 main에 선행 — 충돌 해소 기준)
- Produces: gitops main = 최신 매니페스트(notification 포함, ArgoCD revision 기준)

- [ ] **Step 1: 릴리스 PR 생성·충돌 확인**

```powershell
gh pr create -R DevPathAi/devpath-gitops --base main --head develop --title "release: develop→main (notification 매니페스트 등)" --body "WS-D 릴리스 컷 2/12"
gh pr view <PR번호> -R DevPathAi/devpath-gitops --json mergeable
```
`CONFLICTING`이면: develop에서 `git merge origin/main`으로 병합 커밋 생성, kustomization `newTag` 충돌은 **main 쪽(bot 최신 SHA)** 채택, push 후 재확인.

- [ ] **Step 2: CI 확인 + 머지 + 검증**

```powershell
gh pr checks <PR번호> -R DevPathAi/devpath-gitops --watch; gh pr merge <PR번호> -R DevPathAi/devpath-gitops --merge
git -C D:\workspace\dpa\devpath-gitops fetch origin; git -C D:\workspace\dpa\devpath-gitops log origin/main --oneline -3
```
Expected: 머지 완료, main에 notification 매니페스트 존재(`git -C D:\workspace\dpa\devpath-gitops show origin/main:apps/devpath-notification-svc/base/kustomization.yaml`).

## Task 7: 백엔드 svc 8 + frontend 릴리스 컷

**Files:** 없음

**Interfaces:**
- Consumes: Task 4(admin 경로가 develop에 머지됨)·Task 5(variable·shared publish)
- Produces: 9개 레포 main + ghcr 이미지 10종(svc 8 + web·admin) + gitops main bot 커밋 10건(Task 10 ArgoCD가 소비)

- [ ] **Step 1: 9개 릴리스 PR 일괄 생성**

```powershell
$repos = @('devpath-platform-svc','devpath-ai-svc','devpath-community-svc','devpath-gateway','devpath-learning-svc','devpath-sandbox-svc','devpath-notification-svc','devpath-lcs-svc','devpath-frontend')
foreach ($r in $repos) { gh pr create -R "DevPathAi/$r" --base main --head develop --title "release: develop→main (WS-D 실배포 릴리스 컷)" --body "WS-D 릴리스 컷. 스펙: documents docs/superpowers/specs/2026-07-27-ws-d-deploy-session-design.md 섹션2" }
```

- [ ] **Step 2: CI 전 녹색 확인 후 순차 머지** (레포별 `gh pr checks --watch` → `gh pr merge --merge`; 실패 레포는 머지 보류·원인 수정 후 재시도)

- [ ] **Step 3: 검증 — ghcr 태그 + gitops bot 커밋**

```powershell
foreach ($p in @('devpath-platform-svc','devpath-ai-svc','devpath-community-svc','devpath-gateway','devpath-learning-svc','devpath-sandbox-svc','devpath-notification-svc','devpath-lcs-svc','devpath-web','devpath-admin')) {
  "$p → " + (gh api "/orgs/DevPathAi/packages/container/$p/versions" --jq '.[0].metadata.container.tags' 2>$null)
}
git -C D:\workspace\dpa\devpath-gitops fetch origin; git -C D:\workspace\dpa\devpath-gitops log origin/main --oneline -12
```
Expected: 10종 모두 `main` 태그 포함, gitops main에 `deploy(*): <sha>` 커밋 10건.

## Task 8: documents 릴리스 (develop→main)

**Files:** 없음

**Interfaces:**
- Consumes: Task 3(광고 문서 develop 머지)
- Produces: documents main = 문서 정합 최신

- [ ] **Step 1: PR + 머지**

```powershell
gh pr create -R DevPathAi/documents --base main --head develop --title "release: develop→main (정합성 3차+광고 문서+WS-D 스펙)" --body "WS-D 릴리스 컷 12/12"
gh pr checks <PR번호> -R DevPathAi/documents; gh pr merge <PR번호> -R DevPathAi/documents --merge
```

## Task 9: AWS 프로비저닝 + k3s (gitops 플랜 Task 1~2)

**Files:** 로컬 산출: `~\.ssh\devpath-k3s-key.pem`(키페어)·`~\.kube\devpath-k3s.yaml`(kubeconfig)·`<세션 scratchpad>\rds-master-pw.txt`(생성 후 SealedSecret 봉인 시까지만 보관, 봉인 후 삭제)

**Interfaces:**
- Consumes: AWS 자격증명(사용자 준비 완료)
- Produces: `EIP`(Task 14 DNS·kubeconfig server 주소) · `RDS_ENDPOINT`(Task 11 시크릿·Task 13 Job) · ssh 접근(`ssh -i ~\.ssh\devpath-k3s-key.pem ubuntu@<EIP>`) · k3s Ready

- [ ] **Step 1: 자격 확인·기본 VPC 조회**

```powershell
aws sts get-caller-identity; aws ec2 describe-vpcs --region ap-northeast-2 --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId'
```

- [ ] **Step 2: 보안그룹 2종 + 키페어 생성** (`devpath-k3s-sg`: 22/6443 ← 내 IP, 80/443 ← 0.0.0.0/0; `devpath-rds-sg`: 5432 ← devpath-k3s-sg; 키페어 `devpath-k3s-key` → pem 로컬 저장). 내 IP는 `(Invoke-RestMethod https://checkip.amazonaws.com).Trim()`.

- [ ] **Step 3: 🛑 비용 게이트 — EC2 t3.xlarge 생성** (gitops 플랜 Task 1 Step 1 명령에 확정값 대입: Ubuntu 22.04 AMI는 `aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id` 조회, `--block-device-mappings VolumeSize=50`, 태그 `Name=devpath-k3s`). **실행 직전 사용자 확인.**

- [ ] **Step 4: 🛑 비용 게이트 — EIP 할당·연결** (gitops 플랜 Task 1 Step 2). **실행 직전 사용자 확인.**

- [ ] **Step 5: 🛑 비용 게이트 — RDS 생성** (gitops 플랜 Task 1 Step 3 대입: `--db-instance-identifier devpath-pg --engine postgres --engine-version 17 --db-instance-class db.t4g.micro --allocated-storage 20 --master-username devpath --db-name devpath --vpc-security-group-ids <devpath-rds-sg> --backup-retention-period 7 --no-publicly-accessible`; 비밀번호는 사전 생성 파일에서 주입: `--master-user-password (Get-Content <scratchpad>\rds-master-pw.txt)`). **실행 직전 사용자 확인.** `aws rds wait db-instance-available --db-instance-identifier devpath-pg` 후 엔드포인트 기록.

- [ ] **Step 6: k3s 설치 + pgvector 확장** (EC2 ssh: gitops 플랜 Task 2 Step 1 그대로 `curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--write-kubeconfig-mode 644" sh -`; `sudo apt-get install -y postgresql-client` 후 `psql "host=<RDS_ENDPOINT> user=devpath dbname=devpath" -c 'CREATE EXTENSION IF NOT EXISTS vector;'`)

- [ ] **Step 7: kubeconfig 로컬 확보 + 검증** (gitops 플랜 Task 2 Step 2~3: server를 `https://<EIP>:6443`으로 교체해 `~\.kube\devpath-k3s.yaml` 저장 — 이후 로컬 kubectl은 사용하지 않고 EC2에서 조작하므로 백업 목적)

```powershell
ssh -i ~\.ssh\devpath-k3s-key.pem ubuntu@<EIP> "kubectl get nodes; kubectl get pods -A"
```
Expected: node Ready, traefik·coredns·metrics-server Running.

## Task 10: ArgoCD 설치 + gitops 연결 (gitops 플랜 Task 3)

**Files:** 없음(EC2 상 설치 + ArgoCD repo 자격 Secret)

**Interfaces:**
- Consumes: Task 7·6(gitops main=최신, 이미지 존재) · 🛑 사용자 게이트: **gitops read-only fine-grained PAT**(Contents:Read, devpath-gitops 한정 — ArgoCD가 private repo를 pull할 자격)
- Produces: ApplicationSet이 `apps/*` Application 생성(이후 Task의 sync 대상)

- [ ] **Step 1: ArgoCD 설치** (EC2: gitops 플랜 Task 3 Step 1 그대로)

- [ ] **Step 2: repo 자격 등록** — 사용자에게 PAT 요청(게이트) 후 EC2에서:

```bash
kubectl -n argocd create secret generic repo-devpath-gitops \
  --from-literal=type=git --from-literal=url=https://github.com/DevPathAi/devpath-gitops \
  --from-literal=username=x-access-token --from-literal=password=<PAT>
kubectl -n argocd label secret repo-devpath-gitops argocd.argoproj.io/secret-type=repository
```

- [ ] **Step 3: project·applicationset 적용 + 검증** (EC2에 gitops를 PAT로 clone 후 `kubectl apply -f argocd/project.yaml -f argocd/applicationset.yaml`; `kubectl get applications -n argocd` — 전 앱 발견. 이 시점 Degraded/Progressing 허용=플랜 명시)

## Task 11: SealedSecret + 시크릿 봉인 (gitops 플랜 Task 4) — gitops 묶음 1

**Files:**
- Create(gitops): `apps/devpath-platform-svc/base/sealedsecret-db.yaml`·`sealedsecret-oauth.yaml`, `apps/devpath-ai-svc/base/sealedsecret-claude.yaml` + 각 kustomization resources 추가

**Interfaces:**
- Consumes: Task 9(RDS_ENDPOINT·rds-master-pw) · 🛑 사용자 게이트: GitHub/Google OAuth client id·secret, `CLAUDE_API_KEY`(EC2 임시 파일로 전달, 봉인 후 삭제)
- Produces: k8s Secret `platform-db`(키 `db-url`·`db-user`·`db-password` — Task 13 Job·svc env가 소비)·`platform-oauth`(기존 deployment 참조 키 실측 준수)·`ai-claude`

- [ ] **Step 1: 컨트롤러 설치** (EC2: gitops 플랜 Task 4 Step 1 helm 명령 그대로 + `kubeseal` CLI 설치)
- [ ] **Step 2: 기존 참조 키 실측** — `git show origin/main:apps/devpath-platform-svc/base/deployment.yaml`에서 `platform-oauth` secretKeyRef 키 이름 확인, ai-svc deployment의 CLAUDE_API_KEY 참조 유무 확인(없으면 Task 13에서 env 추가).
- [ ] **Step 3: 시크릿 봉인** (EC2에서 gitops 플랜 Task 4 Step 2 패턴: db-url=`jdbc:postgresql://<RDS_ENDPOINT>:5432/devpath` — 사용자 제공 값 파일 경유, kubeseal → sealedsecret-*.yaml, 평문 파일 즉시 삭제)
- [ ] **Step 4: gitops 묶음 1 릴리스** — 브랜치 `feat/ws-d-secrets`→develop PR(렌더 검증 `kubectl kustomize apps/devpath-platform-svc/base`)→머지→develop→main 릴리스 PR→머지→ArgoCD sync→`kubectl get secret -n devpath platform-db platform-oauth` 존재 확인.

## Task 12: Strimzi Kafka + Redis (gitops 플랜 Task 5~6) — gitops 묶음 2

**Files:**
- Create(gitops): `apps/devpath-redis/base/{deployment,service,pvc,kustomization}.yaml` (redis:7-alpine·PVC `redis-data`·Service `redis:6379` — gitops 플랜 Task 6 요지 그대로) · `kafka/kafka-cluster.yaml`(EC2 직접 적용용, AppProject ns 제한 밖)

**Interfaces:**
- Consumes: Task 10(클러스터)
- Produces: `devpath-kafka-bootstrap.kafka.svc:9092` · `redis.devpath.svc`(Task 13 env가 소비)

- [ ] **Step 1: Strimzi Operator 설치 + 버전 실측** (EC2: gitops 플랜 Task 5 Step 1; `kubectl -n kafka get deploy strimzi-cluster-operator -o jsonpath='{.spec.template.spec.containers[0].image}'`로 버전 확인)
- [ ] **Step 2: Kafka CR 적용 — R1 분기**: Strimzi **0.46 미만**이면 gitops 플랜 Task 5 Step 2 yaml(ZooKeeper) 그대로. **0.46+(KRaft 전용)**이면 아래 KRaft 구성 사용:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: dual-role
  namespace: kafka
  labels: {strimzi.io/cluster: devpath}
spec:
  replicas: 1
  roles: [controller, broker]
  storage: {type: persistent-claim, size: 10Gi, deleteClaim: false}
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: devpath
  namespace: kafka
  annotations:
    strimzi.io/node-pools: enabled
    strimzi.io/kraft: enabled
spec:
  kafka:
    listeners:
      - {name: plain, port: 9092, type: internal, tls: false}
    config:
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
  entityOperator: {topicOperator: {}, userOperator: {}}
```
`kubectl -n kafka wait kafka/devpath --for=condition=Ready --timeout=300s`.
- [ ] **Step 3: Redis 매니페스트 커밋 → gitops 묶음 2 릴리스** (렌더 검증→develop PR→main 릴리스→sync→`kubectl -n devpath get pods -l app=redis` Running)

## Task 13: 마이그레이션 Job RDS 배선 + 전 svc env (gitops 플랜 Task 7 + 조정 1) — gitops 묶음 3

**Files:**
- Modify(gitops): `apps/_migration/base/job.yaml` · `apps/{platform,ai,community,gateway,learning,sandbox,notification,lcs}-svc/base/deployment.yaml`(정확 디렉토리명은 `apps/` 실측)

**Interfaces:**
- Consumes: Task 11(`platform-db`)·Task 12(kafka·redis DNS)·Task 5(migration 이미지)
- Produces: RDS 스키마 34 마이그레이션 적용 완료 · 전 svc Running(Healthy)

- [ ] **Step 1: 각 svc env 키 실측** — 각 svc `src/main/resources/application.yml`에서 `${...}` 키 수집(platform 실측 완료: `DB_URL`·`KAFKA_BOOTSTRAP`·`REDIS_HOST`·`REDIS_PORT`·`APP_WEB_URL`·`APP_ADMIN_URL`; DB user/password 키·gateway의 svc URI env(`PLATFORM_URI` 등)·JWT 시크릿 키도 이 단계에서 확정 — 누락 시 기동 실패로 검출).
- [ ] **Step 2: job.yaml RDS 전환** (flyway는 `FLYWAY_URL`·`FLYWAY_USER`·`FLYWAY_PASSWORD` env 지원 — args의 `-url=...` 제거):

```yaml
          env:
            - name: FLYWAY_URL
              valueFrom: {secretKeyRef: {name: platform-db, key: db-url}}
            - name: FLYWAY_USER
              valueFrom: {secretKeyRef: {name: platform-db, key: db-user}}
            - name: FLYWAY_PASSWORD
              valueFrom: {secretKeyRef: {name: platform-db, key: db-password}}
          args:
            - -locations=filesystem:/flyway/sql
            - migrate
```
(단, `_migration`은 devpath ns 배포 대상인지 kustomization·ApplicationSet 동작 실측 후 ns 정합 확인)
- [ ] **Step 3: 전 svc deployment env 추가** (gitops 플랜 Task 7 Step 1 블록 + Step 1 실측 키: 공통 `DB_URL`(secretKeyRef platform-db/db-url)·`DB_USER`·`DB_PASSWORD`·`KAFKA_BOOTSTRAP=devpath-kafka-bootstrap.kafka.svc:9092`·`REDIS_HOST=redis.devpath.svc`; platform 추가 `APP_WEB_URL=https://app.leva.ai.kr`·`APP_ADMIN_URL=https://admin.leva.ai.kr`; gateway 추가 `PLATFORM_URI=http://devpath-platform-svc.devpath.svc:8080` 등 — service 이름·포트는 `apps/*/base/service.yaml` 실측; ai 추가 `CLAUDE_API_KEY`(secretKeyRef ai-claude))
- [ ] **Step 4: gitops 묶음 3 릴리스 + Job 실행 검증** (렌더→develop PR→main 릴리스→sync; Job immutable 대응: `kubectl -n devpath delete job devpath-flyway-migrate --ignore-not-found` 후 sync → `kubectl -n devpath logs job/devpath-flyway-migrate` "Successfully applied 34 migrations" → 전 svc `kubectl -n devpath get pods` Running·로그에 DB/Kafka 연결 성공)

## Task 14: TLS + Ingress + DNS (gitops 플랜 Task 8) — gitops 묶음 4

**Files:**
- Create(gitops): `infra/cert-manager/cluster-issuer.yaml`(gitops 플랜 Task 8 yaml에 email 대입) · `apps/devpath-gateway/base/ingress.yaml`·`apps/devpath-web/base/ingress.yaml`·`apps/devpath-admin/base/ingress.yaml` + kustomization 등록

**Interfaces:**
- Consumes: Task 9(EIP) · 🛑 사용자 게이트: leva.ai.kr DNS A 레코드 3건 등록 확인(제공자에서 `api`·`app`·`admin` → EIP)
- Produces: `https://api|app|admin.leva.ai.kr` 유효 TLS(Task 15 스모크가 소비)

- [ ] **Step 1: cert-manager 설치 + ClusterIssuer 적용** (EC2: gitops 플랜 Task 8 Step 1, email=`deepestdark@gmail.com`; ClusterIssuer는 cluster 리소스라 EC2 직접 적용)
- [ ] **Step 2: DNS A 레코드 등록(사용자 게이트)** — `api`·`app`·`admin`.leva.ai.kr → `<EIP>`. `Resolve-DnsName api.leva.ai.kr`로 전파 확인.
- [ ] **Step 3: Ingress 3종 커밋** (backend Service 이름·포트는 `apps/*/base/service.yaml` 실측값 사용. 형태 — gateway 예):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devpath-gateway
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt
spec:
  ingressClassName: traefik
  rules:
    - host: api.leva.ai.kr
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: {service: {name: <실측 service 이름>, port: {number: <실측 포트>}}}
  tls:
    - hosts: [api.leva.ai.kr]
      secretName: devpath-gateway-tls
```
(web=`app.leva.ai.kr`/`devpath-web-tls`, admin=`admin.leva.ai.kr`/`devpath-admin-tls` 동형)
- [ ] **Step 4: gitops 묶음 4 릴리스 + 검증** (렌더→develop PR→main 릴리스→sync → `kubectl get certificate -A` 전부 Ready → `curl.exe -sI https://api.leva.ai.kr/actuator/health`·`https://app.leva.ai.kr`·`https://admin.leva.ai.kr` 200 + 유효 TLS)

## Task 15: OAuth 콜백 + 베타 허용리스트 + E2E 스모크 + runbook (gitops 플랜 Task 9)

**Files:**
- Create(gitops): `docs/runbook-k3s-bootstrap.md`(Task 9~14 실제 실행 명령·값(비밀 제외)·트러블슈팅 요약 — gitops 묶음 4에 편승 또는 별도 docs PR)

**Interfaces:**
- Consumes: Task 14(https) · 🛑 사용자 게이트: GitHub·Google OAuth 앱에 콜백 `https://api.leva.ai.kr/login/oauth2/code/github`·`.../google` 등록
- Produces: 실서비스 E2E 검증 완료(WS-D 종료 조건)

- [ ] **Step 1: OAuth 콜백 등록(사용자 게이트)** — 위 URI 2건 등록 확인.
- [ ] **Step 2: 최초 admin 부여 + 베타 허용리스트** — platform User role 저장 방식 실측(`users` 테이블) 후 EC2 psql로 사용자 계정(첫 로그인 후) role=ADMIN UPDATE → admin UI(`https://admin.leva.ai.kr`)에서 스모크용 이메일 베타 승인. (베타 게이팅 C1 동작 실측 준수 — platform `beta` 모듈)
- [ ] **Step 3: E2E 스모크** — `https://app.leva.ai.kr` → GitHub 로그인 → `/beta-pending` 게이트(미승인 시) → 승인 후 온보딩 진단 → 로드맵 생성(실 AI) → 대시보드 광고 슬롯 확인 → `kubectl -n devpath logs` 에러 없음, `argocd app list` 전부 Healthy·Synced.
- [ ] **Step 4: runbook 작성·커밋** (위 실행 기록 정리; gitops docs 변경이므로 develop PR→main 릴리스)

## Task 16: 세션 종료 보고 + 메모리 갱신

**Files:** `C:\Users\deepe\.claude\projects\D--workspace-dpa\memory\`(신규 ws-d 메모리 + 관련 메모리 갱신 + MEMORY.md 색인)

- [ ] **Step 1: 종료 보고** — 생성 AWS 리소스 표(EC2·EIP·RDS·SG·키페어, 월 비용 추정), 접속 URL 3종, 릴리스된 레포·PR 목록, 잔여 작업(WS-A·WS-E·광고 잔여 2건·47 P2 등).
- [ ] **Step 2: 메모리 갱신** — `devpath-deploy-homepage-demo-roadmap`(WS-D 완료 상태)·신규 `devpath-ws-d-deploy` 파일(리소스 ID·엔드포인트·교훈)·MEMORY.md 갱신.

---

## Self-Review

**1. Spec coverage:** 섹션1(1a=T3·1b=완료됨·1c=T2·1d/1e=T1) / 섹션2(순서1=T5·2=T6·3=T4·4=T5S1·5=T7·6=T8, 검증 포함) / 섹션3(확정값=Global+T9~15, 조정1=T13·조정2=T12·조정3=T11~14 묶음 릴리스, OAuth·허용리스트=T15) / 섹션4(검증=각 Task·에러 대응=Global+게이트·산출물=스펙플랜 PR+runbook T15+보고 T16). 커버 완료. ※1b(미커밋 산출물 보존)는 플랜 작성 세션에서 이미 커밋됨 — Task 불필요.

**2. Placeholder scan:** `<EIP>`·`<RDS_ENDPOINT>`·`<PR번호>`·`<PAT>`·`<실측 service 이름>` 등은 **실행 시점 확정값·게이트 산출물**(변수 표기, gitops 플랜과 동일 관례). "실측 후 확정" 지시는 이 워크스페이스의 추측 금지 원칙에 따른 의도된 단계(T11 S2·T13 S1·T14 S3)로 placeholder가 아님. 그 외 TBD/TODO 없음.

**3. Type consistency:** Secret 이름 `platform-db`(키 db-url/db-user/db-password)·`platform-oauth`·`ai-claude`, DNS `devpath-kafka-bootstrap.kafka.svc:9092`·`redis.devpath.svc`, 이미지 `ghcr.io/devpathai/devpath-{svc|web|admin|migration}`, 태그 `Name=devpath-*` 가 T5~T15에서 일관. gitops 플랜의 동일 명칭과 정합.
