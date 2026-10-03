# S2b — `devpath-mobile` 레포 추출 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `devpath-frontend` 의 네이티브 모바일 앱을 이력과 함께 새 레포 `DevPathAi/devpath-mobile` 로 옮겨, 그 레포만으로 analyze·test·Android/iOS 빌드 계약 CI 가 녹색이 되게 한다.

**Architecture:** 새 레포는 frontend 와 같은 디렉터리 배치(`apps/mobile`, `packages/dp_design`)를 유지하는 Dart pub workspace 다 — 경로를 바꾸지 않아야 `tools/mobile_source_guard.dart` 와 `mobile.yml` 의 하드코딩 경로가 그대로 통한다. `dp_design` 은 분리 시점 복사본을 이 레포가 소유(포크)하고, `dp_core` 는 공개 레포 `DevPathAi/devpath-frontend` 를 커밋 핀 git 의존성으로 참조한다. 이 계획은 **비파괴**다: frontend 에서는 아무것도 지우지 않는다(삭제는 다음 계획 S2c 가 한다 — 스펙 §6.5 의 순서: S2b → S2c → S2a).

**Tech Stack:** Flutter 3.44.1 · Dart ^3.12.1 · pub workspaces · `git-filter-repo`(pip) · GitHub Actions · `gh` CLI

**Spec:** `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §6 (D3·D4). 스펙 §6.2-1 은 새 레포 구조를 `app/` 로 적었으나, 이 계획은 **`apps/mobile` 경로를 유지**한다(가드·워크플로 경로 재작성과 그 회귀를 피한다 — YAGNI). Task 6 에서 스펙을 이에 맞춘다.

## Global Constraints

- 기준 커밋: frontend `origin/develop` = `7634b63d6a0127eafb4d164b07d71ea1d380c40f`. `dp_core` git 핀도 이 커밋이다.
- 브랜치 전략(조직 공통): `main` 보호 · `develop` 통합 · 작업 브랜치 → `develop` PR → CI 녹색 → merge commit. `main`·`develop` 직접 push 금지. 단 **빈 레포의 최초 이력 push 는 예외**(PR 을 올릴 base 가 없다): 추출 이력을 `main` 으로 한 번 올리고 거기서 `develop` 을 만든 뒤, 모든 수정은 PR 로 한다.
- frontend 레포는 이 계획에서 **읽기 전용**이다. `D:\workspace\dpa\devpath-frontend` 주 checkout 은 건드리지 않는다(사용자 소유 상태가 있다).
- 모든 git/파일 명령은 절대경로 또는 `git -C <절대경로>` 로 실행한다. Git Bash 에서 `origin/x:path` 인자를 쓸 때는 `export MSYS_NO_PATHCONV=1`.
- 로컬에서 `flutter build apk`·iOS 빌드를 돌리지 않는다(사용자 PC 메모리 제약). 빌드 계약은 CI 로 판정한다. 로컬은 `pub get`·`analyze`·단위 테스트까지.
- 서명 릴리스 워크플로(`mission-spine-signed-mobile-build.yml`)는 **이 계획 범위 밖**이다. frontend 의 `tools/mission_spine_release_evidence.mjs`·`tools/mission_spine_protected_approval.mjs` 와 웹 릴리스 `release_id` 입력에 묶여 있어, 독립 서명 파이프라인은 모바일 레포의 후속 계획으로 새로 설계한다. 서명 시크릿 4종(`ANDROID_RELEASE_KEYSTORE_BASE64`·`ANDROID_RELEASE_KEYSTORE_PASSWORD`·`ANDROID_RELEASE_KEY_ALIAS`·`ANDROID_RELEASE_KEY_PASSWORD`)과 환경 `mission-spine-mobile-signing-android` 도 그때 옮긴다(값은 사람만 가진다).
- 커밋 메시지는 Conventional Commits, 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

---

### Task 1: `dp_core` git 의존성 해석 실증 (스파이크)

> **이미 실행됨(2026-09-19, 계획 작성 중): 결과 = yes.** 아래 절차 그대로 돌려 `pubspec.lock` 에
> `source: git` · `resolved-ref: 7634b63d6a0127eafb4d164b07d71ea1d380c40f` 가 찍히고 `dart analyze` 가
> `No issues found!` 였다. 실행자는 기준 커밋이 달라졌을 때만 다시 돌린다 — 아니면 Task 2 부터 시작한다.

`dp_core` 의 pubspec 에는 `resolution: workspace` 가 있다. Dart 문서는 워크스페이스 패키지를 워크스페이스 밖에서 의존성으로 소비하는 것을 지원한다고 하지만 git+`path` 조합에서 `resolution` 이 무시되는지는 명시하지 않는다. 레포를 만들기 전에 실측한다.

**Files:**
- Create: `%TEMP%\dp-core-git-spike\pubspec.yaml` (버리는 파일)
- Create: `%TEMP%\dp-core-git-spike\bin\spike.dart` (버리는 파일)

**Interfaces:**
- Produces: 결정 기록 한 줄 — `dp_core` 를 `git: {url, ref, path}` 로 해석할 수 있는가(yes/no). Task 3 이 이 결과를 전제로 한다.

- [ ] **Step 1: 스파이크 패키지 작성**

`%TEMP%\dp-core-git-spike\pubspec.yaml`:

```yaml
name: dp_core_git_spike
publish_to: none
environment:
  sdk: ^3.12.1
dependencies:
  dp_core:
    git:
      url: https://github.com/DevPathAi/devpath-frontend.git
      ref: 7634b63d6a0127eafb4d164b07d71ea1d380c40f
      path: packages/dp_core
```

`%TEMP%\dp-core-git-spike\bin\spike.dart`:

```dart
import 'package:dp_core/dp_core.dart';

void main() {
  // 심볼 하나를 실제로 참조해 import 가 해석되는지 본다.
  print(ApiException);
}
```

`ApiException` 은 `packages/dp_core/lib/src/error/api_exception.dart:6` 의 클래스이고 `dp_core.dart` 가
`export 'src/error/api_exception.dart';` 로 내보낸다(기준 커밋에서 확인).

- [ ] **Step 2: 해석과 분석 실행**

```bash
cd "$TEMP/dp-core-git-spike" && dart pub get && dart analyze
```

Expected: `pub get` 이 `dp_core` 를 git 소스로 받고(`pubspec.lock` 의 `dp_core` 항목에 `source: git`, `resolved-ref: 7634b63d…`), `dart analyze` 가 `No issues found!`.

- [ ] **Step 3: 결과 판정**

- 성공 → Task 2 로 진행.
- `pub get` 이 `resolution: workspace` 때문에 실패 → **멈추고 사용자에게 보고한다.** 대안은 D4 를 다시 여는 결정이다(둘 다 포크 / frontend 의 `dp_core` 에서 `resolution` 분리). 이 계획 안에서 즉흥으로 고르지 않는다.

- [ ] **Step 4: 정리**

```bash
rm -rf "$TEMP/dp-core-git-spike"
```

커밋 없음(레포 밖 스파이크).

---

### Task 2: 이력 보존 추출과 새 레포 생성

**Files:**
- Create: `D:\workspace\dpa\devpath-mobile\` (새 로컬 레포, 추출 이력)
- Create: GitHub 레포 `DevPathAi/devpath-mobile` (public — frontend 와 같다)

**Interfaces:**
- Consumes: Task 1 = yes.
- Produces: `DevPathAi/devpath-mobile` 의 `main`·`develop` 브랜치(같은 커밋), 그 안의 경로 `apps/mobile/`, `packages/dp_design/`, `tools/mobile_source_guard.dart`, `.github/workflows/mobile.yml`, `.gitignore`, `.gitattributes`. Task 3 은 `develop` 에서 분기한다.

- [ ] **Step 1: 대상 확인 — 새 레포와 로컬 경로가 비어 있는지**

```bash
gh repo view DevPathAi/devpath-mobile --json name 2>&1 | head -1
ls -la /d/workspace/dpa/devpath-mobile 2>&1 | head -3
```

Expected: 첫 줄은 `Could not resolve to a Repository`, 둘째는 `No such file or directory`. 둘 중 하나라도 존재하면 **멈추고 보고한다**(덮어쓰지 않는다).

- [ ] **Step 2: `git-filter-repo` 설치**

```bash
py -m pip install --user git-filter-repo && py -m git_filter_repo --version
```

Expected: 버전 해시 한 줄. (`python` 은 이 PC 에서 스텁이다 — 반드시 `py`.)

- [ ] **Step 3: 깨끗한 클론에서 추출**

```bash
git clone --no-local --single-branch --branch develop https://github.com/DevPathAi/devpath-frontend.git /d/workspace/dpa/devpath-mobile
git -C /d/workspace/dpa/devpath-mobile rev-parse HEAD
```

Expected: `7634b63d6a0127eafb4d164b07d71ea1d380c40f` 또는 그 뒤의 develop 커밋. 더 뒤라면 그 값을 기록하고 Task 3 의 `ref` 핀에도 **같은 값**을 쓴다.

```bash
cd /d/workspace/dpa/devpath-mobile && py -m git_filter_repo \
  --path apps/mobile \
  --path packages/dp_design \
  --path tools/mobile_source_guard.dart \
  --path .github/workflows/mobile.yml \
  --path .gitignore \
  --path .gitattributes
```

Expected: `New history written`. `git-filter-repo` 는 끝나면 `origin` remote 를 지운다(의도된 동작 — frontend 로 잘못 push 할 수 없게 된다).

- [ ] **Step 4: 추출 결과 검증**

```bash
git -C /d/workspace/dpa/devpath-mobile remote -v
git -C /d/workspace/dpa/devpath-mobile ls-tree --name-only HEAD
git -C /d/workspace/dpa/devpath-mobile ls-tree -r --name-only HEAD | grep -cE '^apps/mobile/'
git -C /d/workspace/dpa/devpath-mobile log --oneline | wc -l
git -C /d/workspace/dpa/devpath-mobile log --oneline -- apps/web | wc -l
```

Expected: remote 없음 · 최상위는 `.gitattributes .github .gitignore apps packages tools` 만 · `apps/mobile/` 파일 207개(기준 커밋 기준, ±는 기준 커밋이 달라진 경우만) · 커밋 수 > 0 · `apps/web` 이력 0.

- [ ] **Step 5: GitHub 레포 생성과 최초 push**

```bash
git -C /d/workspace/dpa/devpath-mobile branch -M main
cd /d/workspace/dpa && gh repo create DevPathAi/devpath-mobile --public \
  --description "Leva 네이티브 모바일 앱(Flutter). devpath-frontend 에서 2026-09 분리." \
  --source /d/workspace/dpa/devpath-mobile --remote origin --push
git -C /d/workspace/dpa/devpath-mobile push origin main:develop
git -C /d/workspace/dpa/devpath-mobile fetch origin && git -C /d/workspace/dpa/devpath-mobile branch -r
```

Expected: `origin/main`, `origin/develop` 두 브랜치, 같은 커밋. 이 push 는 Global Constraints 의 "빈 레포 최초 push 예외"다. 이후 직접 push 없음.

- [ ] **Step 6: 기본 브랜치 확인**

```bash
gh repo view DevPathAi/devpath-mobile --json defaultBranchRef -q .defaultBranchRef.name
```

Expected: `main`.

이 Task 는 새 커밋을 만들지 않는다(이력 이식만).

---

### Task 3: 독립 워크스페이스로 전환 (`dp_core` git 핀, 루트 pubspec, lock)

추출 직후 레포는 해석되지 않는다: 루트 `pubspec.yaml`/`pubspec.lock` 이 없고 `apps/mobile/pubspec.yaml` 이 없는 경로 `../../packages/dp_core` 를 가리킨다.

**Files:**
- Create: `pubspec.yaml` (루트 워크스페이스)
- Create: `pubspec.lock` (frontend lock 을 씨앗으로 재해석)
- Modify: `apps/mobile/pubspec.yaml:16-21` (`dp_core` 를 git 의존성으로)
- Test: 기존 `apps/mobile/test/**`, `packages/dp_design/test/**` (새 테스트 없음 — 동작 변경이 아니라 해석 경로 변경이며, 기존 스위트 전체가 회귀 게이트다)

**Interfaces:**
- Consumes: Task 2 의 `origin/develop`.
- Produces: 루트에서 `flutter pub get --enforce-lockfile` 가 성공하는 레포. 브랜치 `chore/standalone-workspace`. Task 4 의 CI 가 이 lock 을 쓴다.

- [ ] **Step 1: 작업 브랜치**

```bash
git -C /d/workspace/dpa/devpath-mobile switch -c chore/standalone-workspace origin/develop
```

- [ ] **Step 2: 실패를 먼저 본다(red)**

```bash
cd /d/workspace/dpa/devpath-mobile/apps/mobile && flutter pub get 2>&1 | tail -5
```

Expected: FAIL — 워크스페이스 루트를 찾지 못했다는 오류(`resolution: workspace` 인데 상위에 workspace pubspec 없음). 이것이 이 Task 가 고치는 상태다.

- [ ] **Step 3: 루트 `pubspec.yaml` 작성**

`/d/workspace/dpa/devpath-mobile/pubspec.yaml`:

```yaml
name: devpath_mobile_workspace
publish_to: none
environment:
  sdk: ^3.12.1

# Dart pub workspace — 모바일 앱과 그 디자인 시스템 포크를 단일 해석으로 묶는다.
# dp_core 는 워크스페이스 멤버가 아니다: devpath-frontend 를 커밋 핀 git 의존성으로 참조한다.
workspace:
  - packages/dp_design
  - apps/mobile
```

melos 는 넣지 않는다 — 멤버가 둘이고 CI(`mobile.yml`)가 이미 디렉터리별로 직접 명령을 실행한다.

- [ ] **Step 4: `apps/mobile/pubspec.yaml` 의 `dp_core` 를 git 핀으로**

바꾸기 전:

```yaml
  # workspace 멤버(path 결선, resolution: workspace) — web과 동일 공유 계층
  dp_core:
    path: ../../packages/dp_core
  dp_design:
    path: ../../packages/dp_design
```

바꾼 뒤(`ref` 는 Task 2 Step 3 에서 기록한 커밋):

```yaml
  # dp_core(API·모델)는 devpath-frontend 가 소유한다 — 커밋 핀 git 의존성.
  # 핀 갱신은 이 레포의 PR 로만 한다(서버 계약 변경을 의식적으로 받아들이는 지점).
  dp_core:
    git:
      url: https://github.com/DevPathAi/devpath-frontend.git
      ref: 7634b63d6a0127eafb4d164b07d71ea1d380c40f
      path: packages/dp_core
  # dp_design 은 이 레포가 소유하는 포크다(워크스페이스 멤버).
  dp_design:
    path: ../../packages/dp_design
```

- [ ] **Step 5: frontend lock 을 씨앗으로 재해석**

버전 표류를 막기 위해 빈 상태에서 풀지 않고 frontend 의 lock 에서 출발한다(pub 는 가능한 한 잠긴 버전을 유지하고, 안 쓰는 항목만 덜어낸다).

```bash
export MSYS_NO_PATHCONV=1
git -C D:/workspace/dpa/devpath-frontend show 7634b63d6a0127eafb4d164b07d71ea1d380c40f:pubspec.lock > /d/workspace/dpa/devpath-mobile/pubspec.lock
cd /d/workspace/dpa/devpath-mobile && flutter pub get
```

Expected: 성공. 이어서 표류 확인:

```bash
git -C D:/workspace/dpa/devpath-frontend show 7634b63d6a0127eafb4d164b07d71ea1d380c40f:pubspec.lock > "$TEMP/frontend.lock"
py - <<'PY'
import os, re
def versions(path):
    out, name = {}, None
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^  ([a-z0-9_]+):\s*$', line)
        if m: name = m.group(1)
        m = re.match(r'^    version: "(.+)"', line)
        if m and name: out[name] = m.group(1)
    return out
a = versions(os.path.join(os.environ['TEMP'], 'frontend.lock'))
b = versions(r'D:\workspace\dpa\devpath-mobile\pubspec.lock')
drift = {k: (a[k], b[k]) for k in b if k in a and a[k] != b[k]}
print('drift:', drift)
print('only-in-mobile:', sorted(set(b) - set(a)))
PY
```

Expected: `drift: {}` 그리고 `only-in-mobile: []`. 표류가 있으면 **멈추고** 어떤 패키지가 왜 움직였는지 확인한다(추측으로 넘어가지 않는다).

- [ ] **Step 6: 잠금 강제 해석·분석·테스트(green)**

```bash
cd /d/workspace/dpa/devpath-mobile && flutter pub get --enforce-lockfile
cd /d/workspace/dpa/devpath-mobile/apps/mobile && flutter analyze && flutter test --exclude-tags golden
cd /d/workspace/dpa/devpath-mobile/packages/dp_design && flutter analyze && flutter test --exclude-tags golden
```

Expected: 전부 PASS. 알려진 예외: `apps/mobile/test/architecture/mobile_source_guard_negative_test.dart` 는 로컬 병렬 부하에서 간헐 실패한 이력이 있다(2026-09-17, CI 는 통과) — 단독 재실행으로 확인한다. `dp_design` 골든 `DpKillSwitch` 2건은 Windows 에서 사전 실패라 `--exclude-tags golden` 으로 제외된다.

- [ ] **Step 7: 포맷 확인**

```bash
cd /d/workspace/dpa/devpath-mobile && dart format --set-exit-if-changed apps/mobile packages/dp_design tools/mobile_source_guard.dart
```

Expected: `0 changed`.

- [ ] **Step 8: 커밋**

```bash
git -C /d/workspace/dpa/devpath-mobile add pubspec.yaml pubspec.lock apps/mobile/pubspec.yaml
git -C /d/workspace/dpa/devpath-mobile commit -m "chore: make the repo a standalone workspace with dp_core pinned by git

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

PR 은 Task 4 의 변경과 함께 올린다(CI 워크플로가 이 lock·경로에 맞춰져야 녹색이 된다).

---

### Task 4: CI·소스 가드를 새 레포에 맞추기

**Files:**
- Modify: `.github/workflows/mobile.yml:4-22` (트리거 경로), `:60` (포맷 대상)
- Modify: `tools/mobile_source_guard.dart` (필요 시 — Step 2 의 실행 결과가 정한다)
- Test: `tools/mobile_source_guard.dart` 자체 실행, `apps/mobile/test/architecture/mobile_source_guard_negative_test.dart`

**Interfaces:**
- Consumes: Task 3 의 브랜치 `chore/standalone-workspace`.
- Produces: `DevPathAi/devpath-mobile` 의 PR #1 에서 `contract-test-android`·`ios-no-codesign` 두 잡이 녹색. S2c 의 전제 조건.

- [ ] **Step 1: `mobile.yml` 트리거에서 `dp_core` 경로 제거, `develop` push 추가**

바꾸기 전(4–22행):

```yaml
  pull_request:
    paths:
      - 'apps/mobile/**'
      - 'packages/dp_core/**'
      - 'packages/dp_design/**'
      - 'tools/mobile_source_guard.dart'
      - 'pubspec.yaml'
      - 'pubspec.lock'
      - '.github/workflows/mobile.yml'
  push:
    branches: [main]
    paths:
      - 'apps/mobile/**'
      - 'packages/dp_core/**'
      - 'packages/dp_design/**'
      - 'tools/mobile_source_guard.dart'
      - 'pubspec.yaml'
      - 'pubspec.lock'
      - '.github/workflows/mobile.yml'
```

바꾼 뒤(이 레포는 전부 모바일이라 경로 필터가 의미 없다):

```yaml
  pull_request:
  push:
    branches: [main, develop]
```

- [ ] **Step 2: 포맷 단계에서 `packages/dp_core` 제거**

바꾸기 전(60행):

```yaml
        run: dart format --set-exit-if-changed apps/mobile packages/dp_core packages/dp_design tools/mobile_source_guard.dart
```

바꾼 뒤:

```yaml
        run: dart format --set-exit-if-changed apps/mobile packages/dp_design tools/mobile_source_guard.dart
```

- [ ] **Step 3: 소스 가드를 새 레포에서 실행해 본다**

```bash
cd /d/workspace/dpa/devpath-mobile && dart run tools/mobile_source_guard.dart
```

Expected: `mobile source guard: OK`.

가드는 `pubspec.lock`·`mobile.yml`·Android/iOS 설정을 문자열로 검사한다. 실패하면 메시지가 `mobile source guard: <사유>` 로 **무엇을 기대했는지** 알려 준다. 그때만, 그 검사 하나에 대해:
  - Step 1·2 로 바뀐 워크플로 문자열을 기대하는 검사라면 가드의 기대 문자열을 새 워크플로에 맞춘다.
  - `dp_core` 의 lock 항목이 `path` 소스이기를 기대하는 검사라면 `git` 소스 + `resolved-ref` 가 40자 SHA 인지 검사하도록 바꾼다(핀이 브랜치명으로 풀리는 것을 막는 쪽이 원래 의도에 맞다).
  - 그 밖의 실패는 **고치지 말고 멈춰 보고한다**(가드는 공급망 방어선이다 — 추측으로 느슨하게 하지 않는다).

- [ ] **Step 4: 가드 음성 테스트**

```bash
cd /d/workspace/dpa/devpath-mobile/apps/mobile && flutter test test/architecture/mobile_source_guard_negative_test.dart
```

Expected: PASS.

- [ ] **Step 5: 커밋·push·PR**

```bash
git -C /d/workspace/dpa/devpath-mobile add .github/workflows/mobile.yml tools/mobile_source_guard.dart
git -C /d/workspace/dpa/devpath-mobile commit -m "ci: run Mobile CI for every PR and drop the dp_core workspace paths

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C /d/workspace/dpa/devpath-mobile push -u origin chore/standalone-workspace
cd /d/workspace/dpa && gh pr create -R DevPathAi/devpath-mobile --base develop --head chore/standalone-workspace \
  --title "chore: standalone workspace with dp_core pinned by git" \
  --body "Makes the extracted repo resolve on its own: root workspace pubspec, dp_core as a commit-pinned git dependency on devpath-frontend, lockfile re-resolved from the frontend lock with zero version drift, Mobile CI triggers adapted.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 6: CI 판정**

```bash
cd /d/workspace/dpa && timeout 570 gh pr checks 1 -R DevPathAi/devpath-mobile --watch --interval 30
```

Expected: `contract-test-android` pass, `ios-no-codesign` pass. 실패하면 `gh run view <id> -R DevPathAi/devpath-mobile --log-failed` 로 원인을 읽고 고친다(추측 금지). 새 레포에서는 Actions 가 처음이라 워크플로 권한·macOS 러너 사용이 막혀 있을 수 있다 — 그 경우 오류 문구를 그대로 사용자에게 보고한다.

- [ ] **Step 7: 머지**

```bash
cd /d/workspace/dpa && gh pr merge 1 -R DevPathAi/devpath-mobile --merge
```

---

### Task 5: 레포 문서와 규칙 (`CLAUDE.md`·`README.md`)

**Files:**
- Create: `CLAUDE.md`
- Create: `README.md`
- Create: `docs/dp-core-pin.md`

**Interfaces:**
- Consumes: Task 4 머지 후의 `origin/develop`.
- Produces: 다음 작업자가 이 레포만 보고 브랜치 전략·빌드·`dp_core` 핀 갱신 절차를 알 수 있는 문서.

- [ ] **Step 1: 브랜치**

```bash
git -C /d/workspace/dpa/devpath-mobile fetch origin && git -C /d/workspace/dpa/devpath-mobile switch -c docs/repo-rules origin/develop
```

- [ ] **Step 2: `CLAUDE.md` 작성**

```markdown
# CLAUDE.md — devpath-mobile

> Leva 네이티브 모바일 앱(Flutter). 2026-09 에 `devpath-frontend` 에서 분리했다.
> 멤버: `apps/mobile`(앱) · `packages/dp_design`(디자인 시스템 — **이 레포가 소유하는 포크**).
> `dp_core`(API·모델)는 `DevPathAi/devpath-frontend` 를 커밋 핀 git 의존성으로 참조한다.

## 절대 조건

1. 추측·예상 금지 — 모르면 파일을 읽고 명령을 실행해 확인한다.
2. 테스트 우선 — 실패하는 테스트를 먼저 쓰고 통과시키는 최소 구현을 쓴다.
3. 문제가 생기면 코드·로그를 읽어 원인을 규명한 뒤 고친다.
4. 신규 작업은 `develop` 에서 새 브랜치를 분기한다.
5. 검증되지 않은 완료를 보고하지 않는다.

## Git 브랜치 전략

`main` 은 보호 브랜치다. 직접 커밋·푸시·force-push 금지. `develop` 이 통합 브랜치다.
작업 브랜치(`feat/*`·`fix/*`·`chore/*`·`docs/*`) → `develop` PR → CI 녹색 → merge commit.
릴리스 때만 `develop` → `main` PR.

## 빌드·테스트 (레포 루트 기준)

- 의존성: `flutter pub get --enforce-lockfile`
- 소스 가드: `dart run tools/mobile_source_guard.dart`
- 분석·테스트: `cd apps/mobile && flutter analyze && flutter test --exclude-tags golden` (`packages/dp_design` 동일)
- 포맷: `dart format --set-exit-if-changed apps/mobile packages/dp_design tools/mobile_source_guard.dart`
- Android/iOS 빌드 계약은 CI(`.github/workflows/mobile.yml`)가 판정한다.

## 디자인 시스템

`packages/dp_design` 은 mobile-first 시각 언어(플로팅 하단 내비, 큰 반경, 44px 터치 타깃)를 유지한다.
`devpath-frontend` 의 `dp_design` 은 2026-09 부터 데스크톱 웹 문법으로 갈라졌다 — **두 패키지를 서로 동기화하지 않는다.**
공통으로 남는 것은 브랜드 색·타이포 값뿐이다.

## `dp_core` 핀

갱신 절차는 `docs/dp-core-pin.md`.
```

- [ ] **Step 3: `docs/dp-core-pin.md` 작성**

````markdown
# `dp_core` 핀 갱신

`apps/mobile/pubspec.yaml` 의 `dp_core.git.ref` 는 `devpath-frontend` 의 40자 커밋 SHA 다. 브랜치명·태그를 쓰지 않는다.

## 언제

서버 API·모델 계약이 바뀌어 모바일이 그 변경을 받아야 할 때.

## 절차

1. 대상 커밋을 고른다: `git ls-remote https://github.com/DevPathAi/devpath-frontend.git refs/heads/main`
2. `develop` 에서 `chore/bump-dp-core-<짧은SHA>` 브랜치를 만든다.
3. `apps/mobile/pubspec.yaml` 의 `ref` 를 새 SHA 로 바꾼다.
4. `flutter pub get` → `pubspec.lock` 의 `dp_core.resolved-ref` 가 새 SHA 인지 확인한다.
5. `cd apps/mobile && flutter analyze && flutter test --exclude-tags golden`
6. PR → CI 녹색 → 머지. PR 본문에 frontend 쪽 변경 범위를 적는다:
   `git -C <frontend clone> log --oneline <옛SHA>..<새SHA> -- packages/dp_core`
````

- [ ] **Step 4: `README.md` 작성**

```markdown
# devpath-mobile

Leva 네이티브 모바일 앱(Flutter, Android·iOS).

- 앱: `apps/mobile`
- 디자인 시스템(포크): `packages/dp_design`
- API·모델: `dp_core` — [devpath-frontend](https://github.com/DevPathAi/devpath-frontend) 의 `packages/dp_core` 를 커밋 핀으로 참조

시작: `flutter pub get --enforce-lockfile` 후 `cd apps/mobile && flutter run`.
규칙과 명령은 [CLAUDE.md](./CLAUDE.md).
```

- [ ] **Step 5: 커밋·PR·머지**

```bash
git -C /d/workspace/dpa/devpath-mobile add CLAUDE.md README.md docs/dp-core-pin.md
git -C /d/workspace/dpa/devpath-mobile commit -m "docs: repo rules, build commands, and the dp_core pin procedure

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git -C /d/workspace/dpa/devpath-mobile push -u origin docs/repo-rules
cd /d/workspace/dpa && gh pr create -R DevPathAi/devpath-mobile --base develop --head docs/repo-rules \
  --title "docs: repo rules and the dp_core pin procedure" \
  --body "Adds CLAUDE.md, README.md and docs/dp-core-pin.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

CI 녹색 확인 후 `gh pr merge <번호> -R DevPathAi/devpath-mobile --merge`.

---

### Task 6: 워크스페이스·스펙 기록

**Files:**
- Modify: `D:\workspace\dpa\CLAUDE.md` 는 건드리지 않는다(레포 목록이 없다).
- Modify: documents `docs/superpowers/specs/2026-09-19-web-native-redesign-and-mobile-split-design.md` §6.2-1
- Create: memory `C:\Users\deepe\.claude\projects\D--workspace-dpa\memory\devpath-mobile-repo-split.md` + `MEMORY.md` 한 줄

**Interfaces:**
- Consumes: Task 1–5 의 실제 결과(레포 URL, 핀 SHA, CI run 링크).
- Produces: S2c(frontend 정리) 착수 조건이 문서로 고정된다.

- [ ] **Step 1: 스펙 §6.2-1 을 실제 구조에 맞춘다**

documents `develop` 에서 `docs/s2b-record-<날짜>` 브랜치를 만들고, §6.2-1 의

```
   새 레포 구조는 `app/`(구 `apps/mobile`) + `packages/dp_design/`(포크).
```

를 다음으로 바꾼다:

```
   새 레포 구조는 frontend 와 같은 경로를 유지한다: `apps/mobile/` + `packages/dp_design/`(포크). 경로를 바꾸면
   `tools/mobile_source_guard.dart` 와 `mobile.yml` 의 하드코딩 경로를 전부 다시 써야 해서 유지했다(S2b 계획).
```

PR → CI → 머지.

- [ ] **Step 2: 메모리 기록**

`devpath-mobile-repo-split.md` 에 다음 사실을 적는다(각 값은 실행 결과에서 복사한다 — 기억으로 쓰지 않는다): 레포 URL · 로컬 경로 `D:\workspace\dpa\devpath-mobile` · `dp_core` 핀 SHA · 첫 녹색 CI run URL · "frontend 의 `apps/mobile` 은 아직 남아 있다(다음 계획 S2c 가 지운다)" · "서명 릴리스 파이프라인은 미이관(후속 계획)". `MEMORY.md` 에 한 줄 포인터를 추가한다.

- [ ] **Step 3: 인접 레포 스팟체크**

```bash
git -C /d/workspace/dpa/devpath-frontend status -sb | head -3
git -C /d/workspace/dpa/devpath-frontend branch --list 'chore/standalone*' 'docs/repo-rules'
```

Expected: frontend 주 checkout 은 여전히 `feat/evidence-auth-smoke` 이고 이 계획의 브랜치가 frontend 에 생기지 않았다.

---

## 범위 밖 (의도적)

- frontend 에서 `apps/mobile`·모바일 워크플로·모바일 ET13 fixture 삭제 → **S2c**(이 계획 다음. gitops 계약 변경 S2a 는 S2c 가 확정한 카탈로그 값을 미러하므로 그 뒤 — 스펙 §6.5).
- 독립 서명·배포 파이프라인 → 모바일 레포의 후속 계획.
- 모바일 앱의 기능·디자인 변경 없음.
