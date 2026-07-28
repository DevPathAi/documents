# Ollama 클러스터 배포 (Phase C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** k3s 클러스터 내에 Ollama를 배포하고 ai-svc가 이를 바라보게 해, 현재 죽어 있는 path 생성(`/ai/path/generate`)·임베딩(`/ai/embed`) 게이트웨이를 되살려 로드맵 실AI 생성과 콘텐츠 임베딩을 복구한다(Ollama 마이그레이션 1단계).

**Architecture:** gitops에 새 앱 `apps/devpath-ollama/base/`를 추가한다(ApplicationSet이 `apps/*`를 자동 발견). 구조는 기존 `devpath-redis` 앱(Deployment + PVC + Service)을 그대로 복제한다 — Ollama도 모델 캐시를 PVC에 영속한다. ai-svc deployment에 `OLLAMA_BASE_URL`을 주입해 Ollama Service를 가리키게 한다. 모델은 `qwen2.5:3b`(생성)·`nomic-embed-text`(임베딩)로 시작(t3.xlarge RAM 제약).

**Tech Stack:** Kubernetes(k3s), Kustomize, ArgoCD(ApplicationSet), Ollama, local-path PVC.

## Global Constraints

- 새 앱 위치: `devpath-gitops/apps/devpath-ollama/base/` — 파일 4개(`deployment.yaml`·`pvc.yaml`·`service.yaml`·`kustomization.yaml`). `devpath-redis/base/`가 정확한 템플릿.
- ApplicationSet(`argocd/applicationset.yaml`)이 `apps/*`를 자동 발견 → 별도 등록 불요. **단 `targetRevision: main`** — 즉 이 앱은 gitops **develop→main 릴리스 후에만** 실제 배포된다. syncPolicy=automated(prune·selfHeal), namespace=`devpath`(자동 생성).
- Ollama는 기본 `127.0.0.1:11434`에만 바인딩 → 파드 간 접근 위해 **`OLLAMA_HOST=0.0.0.0` 필수**.
- 모델은 PVC(`/root/.ollama`)에 영속. 첫 기동 시 pull 필요(이후 재시작은 캐시 재사용).
- ai-svc 코드 변경 없음 — provider 추상화(`devpath.ollama.*`)가 이미 존재. env 주입만.
- 검증 이원화: **오프라인 게이트 = `kubectl kustomize`(렌더 성공)**. **배포 게이트(EC2 재시작 필요) = ArgoCD sync·파드 Running·엔드포인트 실호출.** EC2가 정지 상태라 배포 게이트는 재가동 후 수행.
- TDD 대체: 이 작업은 선언적 매니페스트라 단위테스트가 없다. 절대조건 2("테스트 우선")는 **적용 전 렌더/검증**(`kubectl kustomize`·`kubectl apply --dry-run`)으로 적용한다(gitops CLAUDE.md 규약).
- 브랜치→develop PR. **main 직접 금지.** Conventional Commits.

---

### Task 1: Ollama gitops 앱 (Deployment + PVC + Service + Kustomization)

**Files:**
- Create: `devpath-gitops/apps/devpath-ollama/base/deployment.yaml`
- Create: `devpath-gitops/apps/devpath-ollama/base/pvc.yaml`
- Create: `devpath-gitops/apps/devpath-ollama/base/service.yaml`
- Create: `devpath-gitops/apps/devpath-ollama/base/kustomization.yaml`
- Reference(template): `devpath-gitops/apps/devpath-redis/base/*`

**Interfaces:**
- Produces: 클러스터 내 Service `ollama.devpath.svc:11434`(Task 2가 참조). 모델 `qwen2.5:3b`·`nomic-embed-text` 서빙.

- [ ] **Step 1: 앱 디렉터리 + PVC 생성**

`pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-models
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

- [ ] **Step 2: Service 생성**

`service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ollama
  labels:
    app: ollama
spec:
  selector:
    app: ollama
  ports:
    - port: 11434
      targetPort: 11434
```

- [ ] **Step 3: 이미지 태그 확정**

`ollama/ollama`의 현재 안정 태그를 확인해 **구체 버전으로 핀**한다(`:latest` 금지 — gitops 재현성):
Run: `curl -s "https://hub.docker.com/v2/repositories/ollama/ollama/tags?page_size=5" | grep -oE '"name":"[0-9]+\.[0-9]+\.[0-9]+"' | head -5`
확정한 태그(예 `0.x.y`)를 Step 4 이미지에 사용.

- [ ] **Step 4: Deployment 생성**

`deployment.yaml` (redis 패턴 + Ollama 특화: `OLLAMA_HOST=0.0.0.0`, postStart 모델 pull, readiness). `<PINNED_TAG>`는 Step 3에서 확정한 값:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  labels:
    app: ollama
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
        - name: ollama
          image: ollama/ollama:<PINNED_TAG>
          ports:
            - containerPort: 11434
          env:
            - name: OLLAMA_HOST
              value: "0.0.0.0:11434"
          volumeMounts:
            - name: models
              mountPath: /root/.ollama
          lifecycle:
            postStart:
              exec:
                command:
                  - /bin/sh
                  - -c
                  - "(until ollama list >/dev/null 2>&1; do sleep 2; done; ollama pull qwen2.5:3b; ollama pull nomic-embed-text) &"
          readinessProbe:
            httpGet:
              path: /api/tags
              port: 11434
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 250m
              memory: 3Gi
            limits:
              memory: 5Gi
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: ollama-models
```
주의: postStart는 백그라운드(`&`)로 pull해 컨테이너 시작을 막지 않는다(pull 실패로 인한 SIGKILL 회피). 트레이드오프: pull 완료 전 짧은 시간 동안 모델 미탑재로 요청이 실패할 수 있음 — 배포 게이트(Task 3)에서 pull 완료를 확인한 뒤 e2e한다. pull이 반복 실패하면 대안으로 별도 pull `Job`으로 전환(주석으로 남길 것).

- [ ] **Step 5: Kustomization 생성**

`kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- deployment.yaml
- pvc.yaml
- service.yaml
```

- [ ] **Step 6: 렌더 검증 (오프라인 게이트)**

Run: `kubectl kustomize devpath-gitops/apps/devpath-ollama/base`
Expected: 4 리소스(Deployment·PVC·Service)가 에러 없이 렌더. YAML 문법·참조(claimName `ollama-models`, selector `app: ollama`) 일치 확인. (kubectl 미설치 시 `kustomize build ...`.)

- [ ] **Step 7: 커밋**

```bash
git -C "D:\workspace\dpa\devpath-gitops" add apps/devpath-ollama/
git -C "D:\workspace\dpa\devpath-gitops" commit -m "feat(ollama): 클러스터 내 Ollama 배포(Deployment+PVC+Service) — path/embed 게이트웨이 복구"
```

---

### Task 2: ai-svc가 Ollama를 바라보게 env 주입

**Files:**
- Modify: `devpath-gitops/apps/devpath-ai-svc/base/deployment.yaml` (env 목록에 2개 추가)

**Interfaces:**
- Consumes: Task 1의 Service `ollama.devpath.svc:11434`.
- Produces: ai-svc가 `/ai/path/generate`·`/ai/embed`에서 Ollama 실호출(코드의 `devpath.ollama.base-url`·`gen-model` 소비).

- [ ] **Step 1: env 2개 추가**

`devpath-gitops/apps/devpath-ai-svc/base/deployment.yaml`의 `env:` 목록 끝(현재 `RETENTION_PROVIDER` 다음)에 추가:
```yaml
            - name: OLLAMA_BASE_URL
              value: "http://ollama.devpath.svc:11434"
            - name: OLLAMA_GEN_MODEL
              value: "qwen2.5:3b"
```
근거: ai-svc 코드 기본값은 `OLLAMA_BASE_URL=localhost:11434`(파드 내 없음)·`OLLAMA_GEN_MODEL=qwen2.5:7b`(RAM 과대). 3b로 낮춰 t3.xlarge에 적합화. `OLLAMA_EMBED_MODEL`은 코드 기본 `nomic-embed-text` 그대로 사용(override 불요).

- [ ] **Step 2: 렌더 검증 (오프라인 게이트)**

Run: `kubectl kustomize devpath-gitops/apps/devpath-ai-svc/base`
Expected: 렌더 성공, env에 `OLLAMA_BASE_URL`·`OLLAMA_GEN_MODEL` 포함, 기존 env·secretKeyRef 무손상.

- [ ] **Step 3: 커밋**

```bash
git -C "D:\workspace\dpa\devpath-gitops" add apps/devpath-ai-svc/base/deployment.yaml
git -C "D:\workspace\dpa\devpath-gitops" commit -m "feat(ai-svc): OLLAMA_BASE_URL 주입 — 클러스터 Ollama로 path/embed 라우팅"
```

---

### Task 3: PR + 배포 검증 체크리스트 (배포 게이트, EC2 재시작 후)

- [ ] **Step 1: 푸시 + develop PR**

```bash
git -C "D:\workspace\dpa\devpath-gitops" push -u origin feat/ollama-cluster-deploy
gh pr create --base develop --repo DevPathAi/devpath-gitops \
  --title "feat(ollama): 클러스터 내 Ollama 배포 + ai-svc 라우팅 (path/embed 복구)" \
  --body "apps/devpath-ollama 신규(Deployment+PVC+Service, qwen2.5:3b·nomic-embed-text) + ai-svc OLLAMA_BASE_URL 주입. path/embed 게이트웨이 부활 → 로드맵·임베딩 복구. 배포는 develop→main 릴리스 후 ArgoCD."
```
CI(있으면) 그린 확인 후 머지.

- [ ] **Step 2: 배포 게이트 — EC2 재시작 후에만 수행 (문서화된 검증 절차)**

> 이 스텝은 **EC2 정지 중엔 불가**. 재가동 후 순서대로:
1. gitops develop→main 릴리스 PR 머지 → ArgoCD가 `devpath-ollama` Application 발견·Sync.
2. `ssh` 접속(런북) → `kubectl -n devpath get pods -l app=ollama` → `Running`·`READY 1/1` 확인.
3. 모델 pull 완료 확인: `kubectl -n devpath exec deploy/ollama -- ollama list` → `qwen2.5:3b`·`nomic-embed-text` 존재. (미완이면 pull 로그 확인, 반복 실패 시 pull Job 대안 적용.)
4. **노드 여유 실측**: `kubectl top nodes`·`kubectl top pod -n devpath` → Ollama 파드가 OOM/축출 없이 안정. 메모리 압박 시 노드 증설(t3.2xlarge, 비용 2배) 검토 — 사용자 승인 후.
5. ai-svc가 Ollama를 봄: `kubectl -n devpath exec deploy/devpath-ai-svc -- env | grep OLLAMA` 확인 → `/ai/embed`·`/ai/path/generate` 실호출(클러스터 내부 curl 또는 learning-svc 경유 로드맵 생성 e2e).
6. **E2E**: (트랙1 시드 적용 전제) 진단 완주 → 로드맵 실AI 생성 성공 확인. 임베딩 필요 시 콘텐츠 임베딩 백필(후속).
7. gitops 런북에 배포·검증 기록.

- [ ] **Step 3: 정직한 한계 기록**

- CPU 추론이라 path 생성은 수십 초 가능 → learning SLO(p95<8s) 위반. 베타 SLO 완화로 수용(설계 §3 트랙2). 8s 필수 시 Phase B(GPU).
- 이 플랜은 Phase C(배포)까지. **Phase A(채팅 기능 provider=ollama 전환)는 Claude 비용 실측 후 별도 플랜.**

---

## Self-Review

**1. Spec coverage:** 스펙 트랙2 Phase C(클러스터 내 Ollama 배포 + OLLAMA_BASE_URL + path/embed 복구) 전부 커버. Phase A는 명시적으로 별도 플랜(스펙과 일치). ✅

**2. Placeholder scan:** `<PINNED_TAG>`는 Step 3에서 실제 태그를 조회해 채우라는 구체 지시(조회 명령 제공) — 미해결 placeholder 아님. 그 외 TBD 없음. 배포 게이트 스텝은 "EC2 재시작 필요"로 명확히 조건화(공백 아님). ✅

**3. 일관성:** Service 이름/포트(`ollama.devpath.svc:11434`)가 Task1 service.yaml ↔ Task2 env ↔ 검증 스텝에서 일치. PVC claimName(`ollama-models`)이 pvc.yaml ↔ deployment volumes 일치. 모델(`qwen2.5:3b`·`nomic-embed-text`)이 postStart pull ↔ ai-svc env ↔ 검증에서 일치. ✅

**4. 리스크:** RAM(3Gi req/5Gi limit, 노드 실측 게이트)·모델 pull 실패(Job 대안)·CPU SLO(완화 명시)·targetRevision main(릴리스 후 배포) 전부 명시. ✅
