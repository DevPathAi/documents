# 핸드오프 — 슬라이스 #9(LCS) 완료·프로덕션 배포 / 다음 = #10 모바일 (2026-06-26)

> 다음 세션 이관용. **슬라이스 #9(LCS) Build D + 통합 릴리스 완료·ArgoCD 프로덕션 배포 검증.** 남은 Tier-2 = #10 모바일·#11 랜딩·평판 기초 + 릴리스 위생(platform-svc +2). **WSL+Bash 메인 직접 진행(antml 마찰 0건).**

## 1. 이번 세션 종착점 — 슬라이스 #9 완료 ✅
- **D-1 lcs-svc by-question**(PR #2→develop, #3→main): `GET /lcs/snapshots/by-question/{questionId}` 역조회(community 무변경, `canView` 재사용). 31 test green(파생쿼리 clean DB 실검증).
- **D-2 프론트**(PR #37→develop, #38→main): 작성 폼 맥락 카드(opt-in 토글→draft 미리보기·필드 칩·노출범위→게시 후 commit best-effort) + 질문 상세 답변자 패널(by-question 200→패널, 404→미표시). dp_core LcsDraft/LcsSnapshotView/LcsFieldUnavailable. web 147 + dp_core 48 green.
- **D-3 gitops**(PR #11→develop, #12→main): `apps/devpath-lcs-svc/base` 등록(ApplicationSet 자동발견).
- **통합 릴리스**: gitops #12→lcs-svc #3→gateway #22→frontend #38 순 머지. **deploy 검증**: gitops main `deploy(devpath-lcs-svc): 2bc7398…`·`deploy(devpath-gateway): 86bf756…`, **main HEAD == kustomization newTag** 일치. frontend는 deploy 잡 없음(릴리스만, main `8b732dd…`).
- 보고서 `reports/2026-06-26-slice9-d-build-report.md`, 플랜 `plans/2026-06-26-md3-slice9-lcs-build-d.md`.

## 2. ⚠️ gitops 머지 주의 (반드시 숙지)
- gitops **기본 브랜치 = main**, **deploy 봇이 이미지 SHA를 main에 직접 커밋** → `develop`이 다른 앱 태그에서 뒤처짐.
- **gitops를 develop→main 머지하지 말 것**(7개 서비스 구 이미지 롤백). 신규 앱/구조 변경은 **main에서 분기해 해당 파일만** 담아 main에 PR.
- 후속 위생: gitops `develop`을 main에서 재동기화 고려.

## 3. Tier-2 전체 잔여 (스케줄 `17_§9`·§3 컷라인)
- **#10 모바일(P6)**: apps/mobile 실API+StatefulShellRoute+drift 오프라인+FCM+OAuth 딥링크+secure_storage / 홈대시보드·학습뷰어·퀵캡처. 독립(백엔드 재사용). **다음 진입점.**
- **#11 랜딩(P7)**: landing(Jaspr SSG)+전용 CI+`lang=ko`. 독립. (documents에 `2026-06-24-office-hours-landing-validation-{design,test-plan}.md` untracked 선행 존재.)
- **평판 기초**: 평판엔진(vote/채택)+태그별 평판+레벨권한(15/125/500/1000)+Bronze 배지 9종+sockpuppet / 스트릭·주간리포트·푸시. (#8에서 "투표 집계만" 컷한 후속.)
- **LCS 후속(Phase 2)**: 필드 개별 토글(현재 백엔드는 recent_activity/current_content만 included, 나머지 연기) + active_tags/tag_reputation/current_path/recent_errors 소스 + learning-svc `/internal/users/{userId}/current-context` + 에러수집·3단계 Sanitize + 실시간 Kafka/Redis 캐시 + preferences UI.
- **릴리스 위생**: platform-svc develop +2 미릴리스(Tier-1 잠재결함 fix #13, WelcomeConsumer poison-skip) → 다음 릴리스 때 main.
- **#8 컷 후속**: ES 전문검색·자유게시판·프로젝트 게시판.
- **MD3 완료 기준**: 풀 골든패스(멘토·커뮤니티·LCS) web 실동작 + 모바일 작동 + 랜딩 배포 + 3R IR.

## 4. 환경/도구 (필수 — 메모리 [[wsl-build-environment]]·[[antml-prefix-windows-only]]·[[gitops-deploy-bot-main-drift]])
- **WSL Flutter**: `~/flutter` stable(3.44.4/Dart 3.12.2). `melos bootstrap`이 `sky_engine 없음` 실패 시 `flutter doctor` precache 후 재실행. 게이트 `melos run analyze/test/format`(format=CI 게이트). 모델(freezed) 변경 시 `cd packages/dp_core && dart run build_runner build`(무관 `.freezed/.g` 줄바꿈은 `git checkout --`). riverpod 3.x: `AsyncValue.valueOrNull` 없음 → `switch(AsyncData(:final value))` 사용.
- **WSL JVM**: JDK 21 `~/jdks/jdk-21.0.11+10`(`JAVA_HOME`). shared는 `cd devpath-shared && ./gradlew publishToMavenLocal -x test` + `~/.gradle/init.gradle` mavenLocal. **shared 변경 시 재publish**. CI는 GitHub Packages SNAPSHOT(`--refresh-dependencies`).
- **로컬 JPA 테스트**: `devpath` DB dirty → clean DB 필요. jshell+pg 드라이버로 임시 DB 생성 가능(`DB_URL` override). 또는 CI 검증.
- **포트**: gateway 8080·platform 8081·learning 8082·ai-svc 8084·sandbox 8085·community 8086·lcs 8087(로컬). 클러스터는 컨테이너 8080 + gateway env URI.
- **릴리스 순서**: gitops app(main) 선행 → 서비스 develop→main(deploy 잡 발동). 배포는 사용자 확인 후.

## 다음 세션 진입점
**슬라이스 #10 모바일(P6)** — apps/mobile 실API + StatefulShellRoute + drift 오프라인 + FCM + OAuth 딥링크 + secure_storage / 홈대시보드·학습뷰어·퀵캡처. 백엔드 재사용(독립). 그 후 #11 랜딩 → 평판 기초. WSL 메인 직접 진행 가능.
