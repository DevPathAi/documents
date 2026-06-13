# 09. Git 규칙 정의서

> **저장소**: `Public-Project-Area-Oragans/devpath-ai` (예시)
> **기본 브랜치**: `main`
> **개발 흐름**: GitHub Flow + Release 태그

---

## 1. 브랜치 전략

### 1.1 브랜치 종류

| 브랜치 | 용도 | 수명 |
|--------|------|------|
| `main` | 항상 배포 가능 (GitHub Flow 기본) | 영구 |
| `feature/*` | 신규 기능 | main에서 분기, 머지 후 삭제 |
| `fix/*` | 버그 수정 | main에서 분기, 머지 후 삭제 |
| `refactor/*` | 리팩터링 | 머지 후 삭제 |
| `chore/*` | 빌드/의존성 | 머지 후 삭제 |
| `docs/*` | 문서 전용 | 머지 후 삭제 |
| `hotfix/*` | 프로덕션 긴급 | main에서 분기, **main에만 머지** |
| `release/v*` | 릴리즈 안정화 (큰 릴리즈 시 선택적 사용) | 태그 후 삭제 |

> **브랜치 전략**: GitHub Flow 기반. `develop` 브랜치는 사용하지 않음. 모든 작업 브랜치는 `main`에서 분기하고 `main`으로 머지한다.

### 1.2 브랜치 명명 규칙

형식: `<타입>/<이슈번호>-<짧은-설명-kebab-case>`

```text
feature/142-github-profile-worker
feature/187-ar-scene-template-schema
fix/201-sandbox-timeout-not-killing-container
refactor/220-path-engine-prompt-builder
hotfix/301-oauth-token-leak
```

**규칙**: 이슈 번호 필수, 영문 소문자+하이픈, 60자 이내.

---

## 2. 커밋 규칙

### 2.1 Conventional Commits

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### 2.2 Type

| Type | 설명 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 동작 유지 구조 개선 |
| `perf` | 성능 개선 |
| `test` | 테스트 추가/수정 |
| `docs` | 문서 |
| `style` | 포맷 |
| `build` | 빌드/의존성 |
| `ci` | CI 파이프라인 |
| `chore` | 기타 |
| `revert` | 되돌리기 |

### 2.3 Scope (권장)

`user`, `auth`, `github`, `onboarding`, `path`, `content`, `ar`, `sandbox`, `ai-gateway`, `mentor`, `community`, `infra`, `web`, `mobile`, `admin`

### 2.4 예시

```text
feat(path): AI 개인화 학습 경로 SSE 생성 파이프라인

- Claude Sonnet 프롬프트 + pgvector 매칭
- SSE로 4단계 진행 스트리밍
- LearningPathGeneratedEvent Outbox 발행

Closes #142
```

```text
fix(sandbox): gVisor runsc가 30초 초과 컨테이너 kill 안 하는 문제

cgroup v2 timeout 대신 wait4 타임아웃 + SIGKILL로 전환.
재현 테스트 추가.

Fixes #201
```

```text
(v2.0 — 현재 비활성 예시)
feat(ar): ar_flutter_plugin 초기화 + glTF 다운로드 + 평면 탐지

- Android: ARCore 7.0+ 가드
- iOS: ARKit 13.0+ 가드
- CDN 캐시 전략 (2회차부터 로컬)

Closes #310
```

### 2.5 금지 사항
- `WIP`, `fix typo` 단독
- 여러 논리 변경 한 커밋
- 빌드 산출물 커밋

---

## 3. Pull Request 규칙

### 3.1 PR 템플릿

```markdown
## 요약
<1~3줄>

## 변경 내용
- [ ] 변경 1
- [ ] 변경 2

## 테스트 계획
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 수동 확인 (스크린샷/AR 캡처)

## 관련 이슈
Closes #142

## 리뷰 포인트
- SSE 구현 부분 / AR 권한 흐름 / Sandbox 격리 프로파일

## 체크리스트
- [ ] 설계 문서 업데이트 (wiki)
- [ ] 마이그레이션 스크립트 (Flyway)
- [ ] 모니터링 지표 추가
- [ ] Feature Flag (필요 시)
- [ ] 보안 영향 (OAuth / Sandbox / AR 권한)
```

### 3.2 PR 크기

- **권장**: 변경 라인 400 이하, 파일 10개 이하
- 초과 시 Stacked PR 권장

### 3.3 리뷰 정책

| 브랜치 | 필수 승인 | 필수 체크 |
|--------|----------|----------|
| main | 2명 | CI 통과, 커버리지 유지, SonarQube 통과 |
| release/* | 2명 + QA | 부하/보안/AR 디바이스 매트릭스 **(v2.0 — 현재 비활성)** |
| hotfix | 1명 | 핵심 회귀 테스트 |

### 3.4 머지 정책

- **Squash Merge** 기본
- 연속 커밋 서사 보존 시 **Rebase Merge**
- **Merge Commit** 금지
- 머지 후 브랜치 즉시 삭제

---

## 4. 보호 규칙

### 4.1 `main` 보호

- 직접 push 금지
- 필수 상태 체크: `build`, `test`, `lint`, `security`, `coverage`, `sonar`
- 리뷰 승인 2건
- 새 커밋 푸시 시 승인 무효화
- Signed Commits 권장
- `--force-push` 금지

### 4.2 `release/*` 보호

- main 동일 + QA 사인오프

---

## 5. 태그와 릴리즈

### 5.1 태깅

- **SemVer**: `vMAJOR.MINOR.PATCH` (예: `v1.0.0`)
- pre-release: `v1.0.0-rc.1`

### 5.2 릴리즈 노트

- GitHub Releases 자동 생성 + 수동 보완
- 섹션: 🚀 Features / 🐛 Fixes / ⚡ Performance / 🔧 Refactor / 📖 Docs / 🎨 UI / 🥽 AR / ⚠️ Migration

---

## 6. 이슈 관리

### 6.1 라벨

| 범주 | 라벨 |
|------|------|
| 유형 | `type:feature`, `type:bug`, `type:refactor`, `type:docs` |
| 우선순위 | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` |
| 모듈 | `area:ar`, `area:sandbox`, `area:path`, `area:mentor`, `area:auth` |
| 특수 | `needs-ar-device-test`, `needs-security-review`, `good-first-issue` |

---

## 7. 커밋 훅

- **husky + lint-staged** (Web)
- **ktlint / Spotless** (Java)
- **flutter analyze** (Mobile)
- **detect-secrets** — OAuth 토큰 커밋 방지
- **commitlint**

hook bypass (`--no-verify`) 엄격 제한.

---

## 8. 금지 및 주의사항

### 8.1 절대 금지

- ❌ OAuth 토큰/Claude 키/결제 키 커밋
- ❌ `main`, `release/*` 강제 푸시
- ❌ 타인 브랜치 rebase/push
- ❌ glTF 에셋 Git 저장 (CDN 사용, Git LFS조차 지양) — (v2.0 — 현재 비활성, AR 재활성화 시 적용)

### 8.2 비밀 관리

- 유출 시 즉시 revoke + `git filter-repo`로 히스토리 정리
- Slack 채널 공유

---

## 9. 예시 워크플로우

```bash
git checkout main && git pull
git checkout -b feature/310-ar-scene-template

git commit -m "feat(ar): scene_template 스키마 + admin 등록 API"
git commit -m "test(ar): interaction_schema 검증"

git fetch origin
git rebase origin/main

git push -u origin feature/310-ar-scene-template
gh pr create --fill
```

---

## 10. 관련 문서

- [12_코드_리뷰_규칙.md](./12_코드_리뷰_규칙.md)
- [14_배포_가이드.md](./14_배포_가이드.md)
- [11_테스트_전략서.md](./11_테스트_전략서.md)
