# Handoff — AWS 전면 정지·로컬 전환·4이슈 착수(콘텐츠 한국어화 spec/plan 완료) (2026-07-28 밤)

> 이 세션의 최종 상태. 앞선 [handoff-2026-07-28-diagnostic-restored-ollama-embed-gpu-quota-pending.md](handoff-2026-07-28-diagnostic-restored-ollama-embed-gpu-quota-pending.md)(AWS 작업 완료 시점)를 잇고, 이후 **사용자 지시로 AWS 전면 정지 + 로컬 4이슈 작업으로 전환**했다.

## 세션 아크 요약

1. **AWS 트랙1/2 실행·검증**(상세=앞 핸드오프): 진단 시드 운영 복구(RDS qb=500·contents=150, 게스트 진단 라이브), Ollama 배포·embed 실증. **path 생성=CPU 근본 불가**(~3000토큰·>600s) 확정 → 타임아웃 완화 스톱갭도 실패 → 원복(PT8S). GPU(Phase B) 결정했으나 세션 내 불가(쿼터0+AZ) → **GPU 쿼터 증설요청 제출**(PENDING).
2. **사용자 피드백 4건 + 지시**: ①진단 문항/응답 영어 ②멘토 응답 Ollama 우선 ③커뮤니티 자유/질의응답/피드백 ④UI/UX 전면 미흡. **"AWS 모두 중단하고 위 문제 해결까지 로컬에서 진행."**
3. **AWS 전면 정지**: EC2 `i-09e252854566cc123` **stopped** + RDS `devpath-pg` **stopped**(비용 차단, 삭제 아님·리소스 보존). EIP 유지. **RDS는 7일 후 자동 재시작** 주의.
4. **4이슈 분해·우선순위 확정**(사용자): **①콘텐츠 한국어화 → ②멘토 Ollama+커뮤니티 → ③UI/UX**. 하나씩 spec→plan→구현.
5. **워크스트림① 콘텐츠 한국어화 = spec+plan 완료**(이 세션은 여기까지, 구현은 다음 세션).

## 현재 상태

- **AWS**: EC2·RDS 정지. **GPU 쿼터 증설요청 Id `33d1b4db79d54d0a894150fba2af1f42ofhayrCs` PENDING**(desired 4vCPU, G/VT). 재개 시 `aws ec2 start-instances`·`aws rds start-db-instance --db-instance-identifier devpath-pg`. 상태확인 `aws service-quotas get-requested-service-quota-change --request-id <id>`.
- **운영 클러스터(정지 전)**: 진단 복구됨(단 시드가 **영어 필러** — 한국어화 대상). Ollama embed 작동, path-gen PT8S fail-fast. gitops/shared 이 세션 릴리스 반영(shared#51, gitops#50/#51/#52/#53/#54/#55). **재가동마다 콜드스타트 CrashLoop**(startupProbe 부재 — 순차 재기동 밴드에이드, 하드닝 백로그).
- **로컬 환경**: **NVIDIA RTX 2080 Ti(11GB)** 보유. **Ollama 미설치**(설치 필요). 로컬 Postgres=`devpath-shared/docker-compose.yml`(pgvector pg17, devpath/localdev/devpath:5432).

## 4이슈 현황(코드 실측) + 다음 작업

### ① 콘텐츠 한국어화 — **spec+plan 완료, 다음 세션 착수**
- **핵심**: 콘텐츠는 "영어"가 아니라 **템플릿 필러**(`generated/approved/questions.jsonl`=`"TRACK NNN: Which option..."`). **생성 파이프라인·검증·쿼터·프롬프트 슬롯 완비**(gradle 태스크 `generateQuestionsLocal`·`validateQuestions`·`makeQuestionSeedSql`·콘텐츠 3종). 프롬프트가 영어/제네릭이라 필러가 나옴.
- **결정**: 로컬 Ollama 생성(무비용, GPU), 모델 `qwen2.5:7b`(부족시 14b), 쿼터 500 유지, 자동검증+스팟체크.
- **산출물**: spec `devpath-learning-svc/docs/superpowers/specs/2026-07-28-korean-content-generation-design.md` · plan `devpath-learning-svc/docs/superpowers/plans/2026-07-28-korean-content-generation.md` · 브랜치 `feat/korean-content-generation`(develop 머지 예정).
- **다음**: plan Task1(Ollama 설치·모델pull)→Task2(문항 프롬프트 한국어 재작성)→Task3(생성·큐레이션·검증 그린)→Task4(시드SQL·로컬재시드·진단 한국어 실증)→Task5/6(콘텐츠·임베딩). subagent-driven 부적합(로컬 설치·LLM 생성·큐레이션) → **인라인 실행 권장**.

### ② 멘토 Ollama 우선 (워크스트림2)
- `devpath-ai-svc`에 **`OllamaMentorClient` 이미 존재**(Claude/Mock 병존, MentorService). 대체로 **`MENTOR_PROVIDER=ollama` 설정 전환**(+필요시 ollama-우선 폴백 로직). 로컬이면 로컬 Ollama 사용.

### ② 커뮤니티 자유/질의응답/피드백 (워크스트림2)
- `devpath-community-svc`에 `post`(`boardType`, **QNA 존재**)·`reputation`·`badge`·`abuse` 존재. **자유(FREE)·피드백(FEEDBACK) 보드 + 화면/흐름 추가** 필요. `QuestionService`가 QNA 처리.

### ③ UI/UX 전면 (워크스트림3)
- `devpath-frontend` = Flutter **Melos 모노레포**(apps: web/admin/mobile, packages: dp_core/dp_design). **`DESIGN.md`에 정교한 디자인 시스템(M3·인디고/slate·WCAG·다크모드) 존재**하나 **실제 구현 화면이 못 따라감**(구현 품질 문제). **로컬 기동 후 실제 화면을 봐야 진단·설계 가능**(CanvasKit이라 자동분석 무효 — 스크린샷/소스감사).

## ⏭ 다음 세션 착수 순서

1. (필요시) 이 세션 문서 브랜치 머지 확인(learning-svc `feat/korean-content-generation` develop 머지·documents 핸드오프).
2. **콘텐츠 한국어화 plan 실행**(인라인): Ollama 설치 → 프롬프트 재작성 → 생성·검증·재시드 → 진단 한국어 실증.
3. 워크스트림② 멘토(config)+커뮤니티(FREE/FEEDBACK 보드) spec→plan→구현.
4. 워크스트림③ UI/UX — 로컬 기동·현행 진단 후 spec→plan→구현.
5. (후속·AWS) GPU 쿼터 승인 시 Phase B(AZ 이전+GPU 노드+드라이버+device plugin+ollama nvidia.com/gpu) → 로드맵 복구 → 운영 한국어 시드 마이그레이션 → E2E.

## 교훈(이 세션)

- **CPU LLM 생성은 완화로도 불가**(path-gen 3000토큰·>600s 실측). GPU는 쿼터(기본0)+AZ 이중 게이트.
- **"영어 콘텐츠"의 실체는 가짜 필러** — 표면 증상 뒤 근본(생성 파이프라인 미가동)을 코드로 규명.
- **인프라·툴체인이 이미 있는지 먼저 확인**: contentGen 파이프라인·프롬프트 슬롯·gradle 태스크·로컬 GPU 전부 존재 → 만들 게 아니라 프롬프트만 바꾸면 됨.
- SSH 키 CRLF→libcrypto 에러(LF 사본 우회). immutable Job은 새 rev 관측 후 delete→재생성.
