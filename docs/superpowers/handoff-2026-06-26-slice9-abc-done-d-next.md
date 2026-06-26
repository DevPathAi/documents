# 핸드오프 — 슬라이스 #8 릴리스 완료 / 슬라이스 #9 LCS A·B·C 완료 (2026-06-26)

> 다음 세션 이관용. **슬라이스 #8(커뮤니티 Q&A) 프로덕션 릴리스 완료.** **슬라이스 #9(LCS) Build A·B·C 완료·CI 검증.** 남은 = #9 Build D(프론트)·통합 릴리스 → 이후 #10 모바일·#11 랜딩·평판 기초. **WSL+Bash 메인 직접 진행(antml 마찰 0건).**

## 1. 이번 세션 종착점

### 슬라이스 #8 — 프로덕션 릴리스 완료 ✅
- **빌드 E(프론트 실API)**: PR #35 → develop. 백엔드 실계약 직독 정렬(상세 `/community/questions/{id}`, 목록 bare 배열, 모델 5종 재구성) + 골든패스(작성 FAB·답변 스레드·채택·투표·🤖 AI 초안 뱃지·유사질문). web 139·dp_core 48 green.
- **통합 릴리스(사용자 "4개 모두 머지")**: community **#11**(`87be03f`)·ai-svc **#24**(`d5a5237`)·gateway **#20**(`dcf6534`)·frontend **#36**(`6e063c3`) develop→main. 백엔드 3종 **ArgoCD 프로덕션 배포**(gitops `ad1fa47`/`262225a`/`38e5fd0`, build→image→ghcr→gitops 커밋 검증). frontend는 deploy 잡 없음(릴리스만). documents **#42** → develop.
- **CLAUDE.md 정리(Windows 한정, 사용자 결정)**: 규칙이 실제 커밋된 community-svc만 "메인 도구 직접 호출 금지"→**환경별(Windows 위임 / WSL+Bash 직접 OK)**로 수정(PR #12 → develop). 나머지 9개 레포 미커밋 strict cruft 제거.

### 슬라이스 #9 — LCS Build A·B·C 완료 ✅
- **설계서·플랜**: PR **#43** → develop(documents). `specs/2026-06-26-md3-slice9-lcs-design.md`·`plans/2026-06-26-md3-slice9-lcs-build.md`. 권위 출처 `26_학습맥락_자동첨부_구현.md`·ERD `02_§8.5`·스케줄 `17_§9`.
  - **결정**: ①전용 신규 서비스 `devpath-lcs-svc`(사용자) ②on-demand 풀 조립(멘토 패턴 승계, 실시간 Kafka/Redis 캐시는 Phase 2) ③에러수집+3단계 Sanitize는 Phase 2 ④BIGINT(문서 UUID 대신 시스템 규약) ⑤LCS 자체 DB·논리참조.
- **Build A(shared 마이그레이션)**: PR **#28** → main + publish. `V202606261001__lcs_snapshots.sql`(`learning_context_snapshots`+`user_context_preferences`, BIGINT 논리참조, 스냅샷 불변, recent_errors 기본 OFF). `FlywayMigrationTest` 검증.
- **Build B(lcs-svc 코어)**: 신규 레포 **`DevPathAi/devpath-lcs-svc`**(public), PR **#1** → develop, **CI build pass**(postgres+redis, GitHub Packages shared, LcsJpaTest 엔티티 validate). 엔티티·리포·`SnapshotAssembler`(learning-svc `/internal/contents/{id}`+sandbox recent 풀, graceful)·`LcsController`(draft/commit/get/preferences)·SecurityConfig(HS256)·GlobalExceptionHandler·Redis draft(TTL 10분). 단위 23 + JPA.
- **Build C(gateway 라우트)**: PR **#21** → develop. `/lcs/**`→8087(`LCS_SVC_URI`). `LcsRouteTest`+`RouteConfigTest`(lcs ID·predicate). **Test-First가 `application-test.yml` 누락 버그를 잡음**(라우트는 main+test yml 둘 다 필요).

## 2. 슬라이스 #9 잔여 (다음 세션 진입점)

### Build D — 프론트(맥락 카드 + 답변자 패널) ⬜
- ⚠️ **통합 갭 먼저 해결**: community `QuestionDetailView`가 `snapshotId`를 노출 안 함(B/C에서 community 무변경). → **lcs-svc에 `GET /lcs/snapshots/by-question/{questionId}`** 추가(attached_to_id로 committed 스냅샷 조회, 없으면 404). 프론트 상세가 이걸 호출해 패널 표시(community 무변경 유지). **Build D 첫 단계.**
- 프론트(apps/web, frontend develop에서 분기): 작성 폼 **맥락 카드**(opt-in 토글→`POST /lcs/snapshots/draft`→필드 칩 토글·미리보기·노출범위→질문 게시 후 questionId로 `POST /lcs/snapshots/{draftId}/commit`) + 질문 상세 **답변자 맥락 패널**(by-question 조회→렌더). dp_core 모델 + provider + 목 `MockHttpAdapter` 픽스처(`/lcs/**`) + 위젯/컨트롤러 테스트. `melos run analyze/test/format` 녹색.

### 통합 릴리스 ⬜
- **gitops 앱 등록**: `apps/devpath-lcs-svc/base/{deployment,service,kustomization}.yaml`(community 미러, ApplicationSet 자동발견). gitops main에 있어야 lcs-svc deploy 잡(`apps/devpath-lcs-svc/base` kustomize edit)이 성공.
- **lcs-svc develop→main 릴리스 PR**(deploy 잡 발동=ArgoCD 배포) + gateway·frontend develop→main + documents 보고서. ⚠️ **lcs-svc `main`은 아직 gradlew 실행비트 깨짐 + ci.yml 없음**(develop만 PR #1로 수정). 릴리스 develop→main이 fix를 main에 반영.

## 3. ⚠️ 환경/도구 (필수 — 메모리 [[wsl-build-environment]]·[[antml-prefix-windows-only]])
- **WSL Flutter**: `~/flutter` stable(3.44.4/Dart 3.12.2), `~/.zshrc`·`~/.profile` PATH. `melos bootstrap`이 `sky_engine 없음` 실패 시 `flutter doctor`로 precache 후 재실행. 게이트 `melos run analyze/test/format`(format=CI 게이트, info 린트도 비-green). 모델(freezed) 변경 시 `cd packages/dp_core && dart run build_runner build --delete-conflicting-outputs`. build_runner가 무관 모델 `.freezed/.g`를 줄바꿈만 바꿔 status에 뜸→`git checkout --`로 되돌림.
- **WSL JVM**: JDK 21 `~/jdks/jdk-21.0.11+10`(`JAVA_HOME`). shared 의존성은 GitHub Packages 401 → `cd devpath-shared && ./gradlew publishToMavenLocal -x test` + `~/.gradle/init.gradle` mavenLocal(전역). **shared 변경 시 재publish**(lcs-svc 로컬 빌드용). CI는 GitHub Packages SNAPSHOT(stale 방지 `--refresh-dependencies`).
- **신규 서비스 레포 생성**(이번 처음): `cp -r devpath-svc-template devpath-X-svc` → `.git`·`build`·`.gradle` 삭제 → 패키지 dir rename `template`→`X` → settings/build.gradle.kts/application.yml/Application/config(community-svc 미러). **gradlew 실행비트 손실 주의** → `git update-index --chmod=+x gradlew`(안 하면 CI `Permission denied` exit 126). **신규 레포 ci.yml 푸시는 `workflow` 스코프 필요** → 사용자 `! gh auth refresh -h github.com -s workflow` 1회. 신규 서비스 CI 검증은 **PR(build 잡, deploy는 main 한정 skip)**로.
- **포트**: gateway 8080·platform 8081·learning 8082·ai-svc 8084·sandbox 8085·community 8086·**lcs 8087**. 클러스터는 컨테이너 8080 + gateway env URI.
- **gitops**: ApplicationSet(`argocd/applicationset.yaml`)가 `apps/*/base` 자동발견 → 새 앱은 디렉터리만 만들면 됨. 서비스 deploy 잡이 main push 시 gitops에 이미지 태그 커밋 → ArgoCD 동기화(=프로덕션 배포). 배포는 사용자 확인 후.
- **lcs-svc 재사용 패턴**: ai-svc `mentor/MentorContextAssembler`·`LearningClient`(`/internal/contents/{id}`)·`review/SandboxClient`(`/internal/sandbox/sessions/recent`). learning-svc `/internal/**` permitAll(게이트웨이 미경유 내부 호출).
- **DB**: 로컬 `devpath` DB는 dirty 가능(다른 서비스 테이블) → lcs JPA 테스트는 clean DB/CI에서. CI postgres=`pgvector/pgvector:pg17`.

## 4. Tier-2 전체 잔여 (스케줄 `17_§9`·§3 컷라인)
- **#9 LCS**: Build D + 통합 릴리스(위).
- **#10 모바일(P6)**: apps/mobile 실API+StatefulShellRoute+drift 오프라인+FCM+OAuth 딥링크+secure_storage / 홈대시보드·학습뷰어·퀵캡처. 독립(백엔드 재사용).
- **#11 랜딩(P7)**: landing(Jaspr SSG)+전용 CI+`lang=ko`. 독립. (documents에 `2026-06-24-office-hours-landing-validation-{design,test-plan}.md` untracked 선행 존재.)
- **평판 기초**: 평판엔진(vote/채택)+태그별 평판+레벨권한(15/125/500/1000)+Bronze 배지 9종+sockpuppet / 스트릭·주간리포트·푸시. (#8에서 "투표 집계만" 컷한 후속.)
- **릴리스 위생**: platform-svc develop +2 미릴리스(Tier-1 잠재결함 fix #13, WelcomeConsumer poison-skip) → 다음 릴리스 때 main.
- **#8 컷 후속**: ES 전문검색·자유게시판·프로젝트 게시판.
- **MD3 완료 기준**: 풀 골든패스(멘토·커뮤니티·LCS) web 실동작 + 모바일 작동 + 랜딩 배포 + 3R IR.

## 5. 참고
- 설계/플랜: `specs/2026-06-26-md3-slice9-lcs-design.md`·`plans/2026-06-26-md3-slice9-lcs-build.md`(PR #43).
- 슬라이스 #8 릴리스/E: `reports/2026-06-26-slice8-e-build-report.md`(PR #42 merged).
- 직전 핸드오프: `handoff-2026-06-26-slice8-d-done-e-next.md`.

## 다음 세션 진입점
**슬라이스 #9 Build D** — ① lcs-svc `GET /lcs/snapshots/by-question/{questionId}` 추가(by-question 조회) → ② 프론트 맥락 카드 + 답변자 패널(목 픽스처·melos green) → ③ gitops 앱 + 통합 릴리스. 그 후 #10 모바일 → #11 랜딩 → 평판 기초. WSL 메인 직접 진행 가능.
