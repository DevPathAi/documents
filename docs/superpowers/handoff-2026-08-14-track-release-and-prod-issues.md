# 핸드오프 — 트랙 확장 릴리스 완결, 운영 이슈 5건 중 4건 해결

- 작성일: 2026-08-14
- 이전 핸드오프: `handoff-2026-08-10-lead-recovery-notes-plan.md`
  (그 사이 8/13 약관·한국어 시드, 8/14 진단 트랙 배선·트랙 확장 세션은 핸드오프 없이 메모리로만 이어짐)
- **다음 세션 착수점: 학습경로 생성 방식 결정 — 유일한 미해결이고 사용자 판단이 필요하다**

## 한 줄 요약

보류돼 있던 트랙 확장(PYTHON_BACKEND)을 main 까지 릴리스하고 운영 DB 실측으로 검증했다.
직후 사용자가 보고한 운영 이슈 5건을 조사해 **4건을 해결·배포**했고, 원인은 대부분
「만들어야 할 것」이 아니라 **「릴리스가 안 나간 것」**이었다. 학습경로만 남았는데 그건 설정이 아니라
**하드웨어 제약**이라 결정이 필요하다.

---

## 1. 릴리스 6건 — 전부 운영 반영·검증 완료

| 레포 | PR | 머지 SHA | 내용 |
|---|---|---|---|
| devpath-shared | #62 | `41d6dfb` | 트랙 CHECK 8값 + PYTHON_BACKEND 시드 |
| devpath-learning-svc | #50 | `bbcaaaa` | 문항 100·콘텐츠 30·품질 게이트 6종 |
| devpath-frontend | #131 | `2400fb4` | 트랙 카탈로그 |
| devpath-gitops | #57 | `680cabd` | 멘토 Ollama 폴백 |
| devpath-gateway | #30 | `f784652` | `/support/**` 라우팅 |
| devpath-community-svc | #34 | `d2b9dc5` | 자유글·피드백 API + 신고 + 검색(ES) |

### 운영 DB 실측 (마이그레이션 전 → 후)

| 항목 | 전 | 후 |
|---|---|---|
| Flyway | `202608131001` | **`202608141002`** |
| 트랙 | 5종 | **6종** |
| 문항 | 500 | **600** (PB 100: MCQ 70/CR 30 · 난이도 10/25/30/25/10 · 한국어 100 · 서로다른선택지 100) |
| 콘텐츠 | 150 | **180** (PB 30) |
| 임베딩 | 238/150 | **268/180** (PB 30/30) |

라이브 번들에 카탈로그 6종 노출 확인. ArgoCD 13개 앱 전부 `Synced/Healthy`.

### ★마이그레이션은 gitops 커밋만으로 실행되지 않는다 (또 재현됐다)

ArgoCD 관리 Job 은 `spec.template` 이 immutable 이라 이미지 태그가 바뀌면 **sync 가 실패할 뿐**
자동 실행되지 않는다(`devpath-migration` = `OutOfSync`). gitops 에 `deploy(devpath-migration)` 커밋이
있는데 Job 이미지는 옛 SHA 그대로였다. 8/13 세션에 이미 겪은 함정이 그대로 재현됐다.

**절차**(실측 성공): 일회성 Job(`flyway-migrate-manual`, ArgoCD 라벨 없음)으로 새 이미지 실행 →
**파드의 실제 이미지 확인**(옛 이미지로 되살아나는 함정) → 관리 Job 삭제 →
`kubectl patch application devpath-migration -n argocd --type merge -p '{"operation":{...,"sync":{"revision":"HEAD"}}}'`
→ 재생성된 Job 이 `No migration necessary` 를 내면 멱등 확인.

---

## 2. 운영 이슈 — 사용자 보고 5건

### ★해결★ 자유글·피드백 작성(405) / 문의 전송(404) — 프론트는 main, 백엔드는 develop

**이번 세션 최대 발견.** 「버튼을 눌러도 아무 반응 없음」의 정체는
**UI 가 아직 존재하지 않는 API 를 부르고 있던 것**이었다.

```
POST /community/posts   → 405 Method Not Allowed
POST /support/requests  → 404 Not Found
```

- community-svc **main 에 `@PostMapping("/posts")` 가 없었다**(`@GetMapping("/posts")` 만 존재
  → 경로는 매칭되고 POST 만 없으니 정확히 405). develop 이 **29커밋** 앞서 있었다.
- gateway **main 라우트에 `/support/**` 가 없었다**. develop 이 2커밋 앞섬.
  platform-svc 의 `SupportController` 는 **이미 배포돼 있었고** 게이트웨이가 안 보내준 것뿐이다.

둘 다 릴리스로 해결(PR #30 · #34). **다음 세션에서 사용자 육안 확인이 필요하다.**

### ★해결★ AI 멘토가 Ollama 로 응답하지 않음

두 겹이었다. ①Anthropic **크레딧 소진**(운영 로그 400 `credit balance is too low` 실측)
②`MENTOR_PROVIDER=claude` 인데 `MENTOR_FALLBACK` 이 비어 **체인이 claude 단독**.
`OllamaMentorClient`·`FallbackMentorClient` 는 **코드에 이미 있었다** — 설정만 없었다.

★**함정을 아슬아슬하게 피했다**★ — `MENTOR_OLLAMA_MODEL` 코드 기본값이 `qwen2.5:7b` 인데
클러스터 설치 모델은 **`qwen2.5:3b`·`nomic-embed-text` 뿐**(`ollama list` 실측).
폴백만 켰다면 **없는 모델을 찾다가 똑같이 실패**했을 것이다. 세 변수를 함께 넣어야 한다.

파드 env 반영까지 확인. **실동작은 인증 게이트라 미검증 — 사용자 확인 필요.**
CPU 에서 3b 추론이라 `MENTOR_TIMEOUT`(기본 60초)에 걸릴 가능성이 남아 있다.

### ⚠미해결⚠ 학습경로 생성 — **다음 세션 착수점**

진단 15문항은 정상 완료된다(`assessments` COMPLETED · items 15 · results 1).
그런데 `learning_paths` = **0**.

★**서버 ERROR 가 세 서비스 모두 0건이라 한참 헤맸는데, 실패한 게 아니라 처리 중이었다.**★
Ollama 로그에서 진행 중인 추론을 실시간으로 잡았다:

```
slot print_timing: n_decoded = 2754, tg = 4.20 t/s
```

**4.2 토큰/초 × ~3000토큰 ≈ 12분.** 그동안 Ollama 가 노드 CPU **1974m(≈2코어)** 를 점유해
서비스 전체가 느려진다.

**결정적 후속 관측**: 추론이 끝난 뒤(부하 1974m→1m) 다시 재도 `learning_paths` 여전히 **0**
(마일스톤 0·태스크 0). **12분을 다 계산하고도 결과가 버려진다** — SSE
(`POST /learning-paths/me/generate`)가 이미 끊긴 뒤라 저장에 도달하지 못한다.

경로: 화면 → learning-svc `LearningPathGenerationService` → ai-svc `/ai/path/generate`(**Ollama**).

**선택지 (사용자 결정 필요)**
1. **Anthropic 크레딧 충전** — 가장 빠르고 품질도 좋다. 다만 멘토·리뷰·시드까지 같은 키를 쓴다.
2. **모델·프롬프트 축소** — 무료지만 경로 품질이 떨어지고, 3b 로 계약(마일스톤·주간 태스크 3개
   구조)을 만족하는 JSON 이 안 나올 위험이 있다. `validate()` 가 엄격해 `PathContractException` 이 잦을 수 있다.
3. **GPU 증설** — 근본 해결이지만 쿼터 증설 요청이 PENDING 상태로 이월돼 있다.

어느 쪽이든 **SSE 타임아웃과 결과 폐기 문제는 따로 손봐야 한다** — 생성이 빨라져도
「완료했는데 저장 안 됨」 구조는 그대로다. 비동기(작업 큐 + 폴링/알림)로 바꾸는 설계가 정공법이다.

### 미구현 (버그 아님) — 글 수정·삭제

community-svc 에 `@PutMapping`·`@PatchMapping`·`@DeleteMapping` **0건**, 프론트에도 호출 없음.
develop 에도 없다. **신규 개발 건**이다.

---

## 3. 다음 세션 할 일 (우선순위)

1. **학습경로 생성 방식 결정 + 구현** (위 선택지)
2. **사용자 육안 확인** — 자유글·피드백 작성 / 문의 전송 / AI 멘토 응답
3. **leva.ai.kr SEO** — `templates/note.html` 에 CTA 블록 → title·description 에 「레바」 →
   폴백 문구 정정 → GSC 등록(사용자 몫). 상세는 트랙 확장 메모리의 SEO 절.
4. **남은 두 트랙** `NODE_TYPESCRIPT` · `DATA_AI` — CHECK 는 이미 8값으로 열려 있다.
   착수 전 `generateContentsLocal` 이 30개를 한 번에 내는지 **먼저 끝까지 돌려볼 것**(1차 때 미검증).
5. **글 수정·삭제** 신규 개발

---

## 4. 함정 — 다음 세션이 반드시 알아야 할 것

### ★인증 게이트가 상태코드를 가린다★

`/community/posts` 를 인증 없이 POST 하면 **401** 이 나온다. 나는 이걸 「라우팅 정상」으로 판정했는데
**틀렸다** — 인증 필터가 라우팅보다 먼저 걸려 **405 를 401 로 덮는다.** 405 는 **인증된 실제 요청**
(브라우저 콘솔)에서만 드러났다. 같은 함정을 두 번 더 밟을 뻔했다:

- 배포 검증을 「404→401 로 바뀌면 성공」으로 설계했는데 **배포 전에도 이미 401** — 대조군을 먼저 재서 살았다
- 클러스터 내부 직접 호출도 서비스 자체 인증에 막혀 **미구현 DELETE 까지 401** — 판별력 0

**정답은 배포물을 직접 보는 것**: gateway 는 파드의 `/app/app.jar` 안 `application.yml` 에서 `support` 확인,
community-svc 는 **옛 버전에 없던 클래스**(`PostSearchService.class`·`ReportController.class`) 존재로 확정
(대조군 `CommunityController.class` 도 함께 잡아 측정이 작동함을 증명).

### ★Flutter 번들에서 한글 grep 은 무효★

Dart 가 한글을 `\uXXXX` 이스케이프로 저장한다. `모바일 (Flutter)` 같은 **대조군도 0건**이 나온다.
ASCII 키(`MOBILE_FLUTTER`=1 대조 → `PYTHON_BACKEND`=1)로 판별할 것.
문맥 추출도 줄 경계 때문에 `grep -o ".\{150\}KEY.\{200\}"` 가 대조군까지 0 → **바이트 오프셋 + `dd`** 로 전환.

### ★서버 ERROR 0건이 「정상」이 아니라 「아직 처리 중」일 수 있다★

로그가 조용하면 **부하(`kubectl top`)와 백엔드 프로세스 상태**를 보라. 이번엔 그게 결정타였다.

### 운영 k3s 접근 (기존 메모리의 「접근 불가」는 틀렸다)

```bash
tr -d '\r' < ~/.ssh/devpath-k3s-key.pem > "$SCRATCH/k3s-key"   # ★CRLF 라 그대로 쓰면 libcrypto 오류
chmod 600 "$SCRATCH/k3s-key"
ssh -i "$SCRATCH/k3s-key" ubuntu@13.124.153.105 'sudo kubectl get nodes'
```

로컬 `~/.kube/devpath-k3s.yaml` 은 **인증서에 EIP 가 없어 TLS 실패** — SSH 경유가 정답.
운영 DB 조회는 `platform-db` 시크릿으로 일회성 psql 파드를 띄운다. `db-url` 은 jdbc 형식이라
`sed 's#^jdbc:postgresql://#postgresql://#'` 변환 필요. 파드는 **매니페스트 파일로** 만들 것 —
`kubectl run --overrides='{...}'` 는 셸 이스케이프에 깨져 `Invalid JSON Patch` 가 난다.
**끝나면 `pg-probe` 파드·configmap 을 지운다.**

### gitops 는 develop 경유가 오히려 위험하다

CI 가 main 에 배포 커밋을 직접 푸시해 **develop 이 27커밋 뒤처져 있다.** 게다가 develop 에
**적용 보류된 Elasticsearch 매니페스트**(`apps/devpath-elasticsearch/`)가 대기 중인데,
ApplicationSet 이 `apps/*` 를 자동 발견하고 `syncPolicy: automated` 라
**develop→main 머지가 ES 를 즉시 자동 배포시킨다.** 이번엔 main 기반 hotfix 브랜치로 우회했다.

### community-svc 는 ES 없이도 뜬다 (실증됨)

`PostIndexBootstrap` 이 `try/catch` 로 삼키고, `CommunityService` 에 ES 참조 0건,
색인은 Outbox→Kafka 컨슈머(비동기), readiness 그룹에 ES health 미포함.
이번 릴리스에서 **restarts=0 으로 정상 기동**해 판단이 실증됐다. 검색만 비활성으로 남는다.

---

## 5. 참고

- 메모리: `devpath-prod-issues-2026-08-14` · `devpath-prod-k3s-access` ·
  `devpath-track-expansion-python-backend`
- 트랙 확장 레저: `devpath-learning-svc/.superpowers/sdd/2026-08-14-track-expansion-python-backend/progress.md`
