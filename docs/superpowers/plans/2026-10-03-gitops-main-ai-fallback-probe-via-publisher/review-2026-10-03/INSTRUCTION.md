# 독립 리뷰 지시 — AI fallback probe publisher 준비물 (2026-10-03)

당신은 이 준비물을 처음 보는 독립 리뷰어다. **읽기 전용**으로 검토하고, 결과를 이 디렉터리의 `REPORT.md` 하나에만 쓴다.

## 범위 고정 (Scope Lock)

- 이 리뷰(이 지시서의 질문들)만 수행하라. 끝나면 `REPORT.md` 를 쓰고 보고한 뒤 정지하라. 다른 작업으로 진행하지 말라.
- **어떤 파일도 고치지 말라**(REPORT.md 작성만 허용). git commit·push·branch 생성·`gh api` 의 POST/PUT/PATCH/DELETE·
  `gh workflow run`·kubectl/ssh 를 **금지**한다. 읽기용 `git show`/`git log`/`git diff`/`gh api`(GET)는 허용.
- 모든 git 명령에 `-C <절대경로>` 를 써라. `cd` 후 상대경로 명령 금지(호출 사이 cwd 가 리셋된다).
- 판단 근거가 부족하면 추측하지 말고 REPORT.md 에 `NEEDS_CONTEXT: <무엇>` 으로 적어라.

## 대상

- 계획서: `D:/workspace/dpa/.worktrees/documents-aifb-publisher-1003/docs/superpowers/plans/2026-10-03-gitops-main-ai-fallback-probe-via-publisher.md`
- 스크립트·산출물: 같은 이름의 디렉터리(`make_ai_fallback_probe_target.py` · `prove_next_base.py` · `render_ai_fallback_probe_publisher.py` ·
  `negative_controls.py` · `target.txt` · `rendered/` 5종)
- gitops 클론: `D:/workspace/dpa/devpath-gitops` — 아래 커밋은 **아직 push 되지 않았고 이 로컬 클론에만 있다**:
  target `a97a175466962e33ca1823edbb6656091700db81` · 헬퍼 `868afacd7566d9f4bda2612e6751673a7824864b`(브랜치 `chore/ai-fallback-probe-publish-20261003`) ·
  staged `3b424ff1fb773fe46ac499fb81812f13264b00ce`(브랜치 `chore/ai-fallback-probe-publish-dispatcher-staged-20261003`) · 소스 `913757e`(`dev/ai-fallback-probe-20261003`)
- 선례(실행 완료): 9/21 헬퍼 `origin/chore/pipeline-defects-publish-20260921` · 9/24 헬퍼 `origin/chore/gateway-edge-cors-publish-20260924` ·
  documents `docs/superpowers/plans/2026-09-24-gitops-main-gateway-edge-cors-via-publisher*`
- 운영 ai-svc 소스: `D:/workspace/dpa/devpath-ai-svc` 커밋 `83cfe792`(운영 이미지 `107fd20a` 의 소스)

## 줄바꿈 사실 (헛걸음 방지)

gitops·documents 의 커밋된 blob 은 LF 다. 일부 작업 트리는 `core.autocrlf=true` 라 CRLF 로 보일 수 있다 — 바이트 비교는 `git show <sha>:<path>` 로 하라.
렌더 산출물(`rendered/`)은 LF 로 쓰였다.

## 질문 (각각 근거와 함께 Yes/No/Concern)

1. **target 내용**: `a97a175` 가 `cea3610` 의 단일 자식이고, 정확히 5경로(M)만 바꾸며, 각 blob 이 gitops `origin/develop`(`e6730ed`)의 같은 경로와 동일한가?
   릴리스가 관리하는 kustomization(web·ai-svc·migration)이 main 과 바이트 동일한가? (develop 에는 r3 값이 남아 있다 — 섞이면 운영이 되돌아간다)
2. **운영 효과**: ai-svc deployment 에 추가된 env 9개가 `83cfe792` 의 `src/main/resources/application.yml` 에 모두 바인딩되는가?
   `ollama-gpu.devpath.svc:11434` 가 gitops 의 실제 Service 이름·포트와 맞는가(`apps/devpath-ollama-gpu/base/`)?
   ollama-gpu 의 `strategy: Recreate` 전환과 template 변경이 한 번에 적용될 때 단일 GPU 노드에서 교착 없이 롤아웃되는가?
3. **다음 base**: target 위에서 다음 릴리스의 체인이 성립하는가 — `prove_next_base.py` 의 검사가 충분한가, 빠진 base 조건이 있는가
   (`scripts/release/verify_promotion_chain.py` 의 base 경로를 직접 읽어 대조)?
4. **publisher 파생**: `rendered/` 5종이 9/24 산출물 대비 이름·SHA·경로 5행·`-eq 5` 외에 달라진 것이 없는가?
   계약 가드를 완화하지 않은 판단(target 이 체인·마이그레이션 검증기를 건드리지 않음)이 맞는가?
   `scripts/release/cloudflare_pages.py` 를 바꾸는 target 을 헬퍼가 자기 테스트로 검증하는 구조에 순환 위험이 있는가?
5. **음성 대조·계약 테스트**: `negative_controls.py` 의 5종 변조가 실제로 적용되고 거부되는가? 계약 테스트가 놓치는 위험한 변조를 하나라도 찾을 수 있는가?
6. **실행 시 위험**: Part B 를 실행할 때 운영·롤백·다음 캠페인에 생길 수 있는 문제 중 계획서가 다루지 않은 것이 있는가?

## REPORT.md 형식

맨 위에 `Ready: Yes|No` 와 한 줄 요약. 그 아래 발견 사항을 심각도(High/Medium/Low/Info)로, 각 항목에 근거(파일:줄 또는 명령과 출력)를 붙여라.
