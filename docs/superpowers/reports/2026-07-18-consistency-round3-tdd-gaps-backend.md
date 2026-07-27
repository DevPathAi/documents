# 정합성 3차 — 축④ TDD 갭(백엔드)

## 기준

- **기준 문서**: `11_테스트_전략서.md` (origin/develop, `git -C D:\workspace\dpa\documents show origin/develop:11_테스트_전략서.md`)
- **피라미드**: Unit 75% / Integration 20% / E2E 5%. 도메인 단위 = JUnit5 + AssertJ + **jqwik**(속성 기반).
- **§2.1 우선 영역(불변식)**:
  - 적응형 진단 알고리즘 (난이도 +0.1 / -0.05 수렴, [0,1])
  - 학습 경로 rationale 빌더
  - 스트릭 계산 (자정 경계, TZ)
  - 피어 매칭 스코어링 (§7: 대칭성 A↔B)
  - 멘토 컨텍스트 스냅샷 조립
  - 커뮤니티: 평판 계산(일일 40점 상한, 7일 신규계정 제한), 에스컬레이션 상태 전이(NONE→ESCALATED→BOUNTY_PLACED→RESOLVED), 현상금 차감/환불(optimistic locking 필수), AI 시드 파이프라인(타임아웃·프롬프트 인젝션·refusal), 모더레이션 심각도+fallback, 학습 맥락 스냅샷(opt-in·민감정보 필터)
- **§7 속성 기반 테스트**: 적응형 난이도 수렴성, 스트릭 TZ 연속성, 피어 매칭 대칭성.

- **기준 SHA(origin/develop 고정, `git rev-parse --short`로 전부 검증됨)**:
  platform-svc=4c1ca4f, learning-svc=0461c4f, community-svc=043b830, sandbox-svc=a6d802e, ai-svc=69d5e0f, lcs-svc=bd64ada, notification-svc=0afddfd, gateway=c8a1282, shared=ff7f5a6, svc-template=b6c33ee.

## 방법

1. **인벤토리**: `git -C <레포> ls-tree -r <ref> --name-only` → `src/main/**.java`, `src/test/**.java` 분류. `*Service.java` 대상 클래스별로 동명 테스트(`<이름>Test|Tests|IT|ITest`) 존재 여부 매칭. 매칭 실패분은 `git -C <레포> grep -ln '<클래스명>' <ref> -- 'src/test'`로 타 테스트에서의 참조 여부 재확인(오탐 제거).
2. **@SpringBootTest 비중**: `git -C <레포> grep -ln '@SpringBootTest' <ref> -- '*.java'` 건수 / `src/test/**.java` 전체 수.
3. **불변식별 테스트 유무**: 불변식 키워드로 `git -C <레포> grep -lnE '<키워드>' <ref> -- 'src/test'` (+ 존재 확인 위해 `-- 'src/main'` 대조).
4. **jqwik**: `git -C <레포> grep -ln 'jqwik' <ref>` 및 `@Property` in `src/test`.

전 명령 절대경로 `git -C D:\workspace\dpa\<레포>` 사용. 코드 레포는 읽기 전용(ls-tree/grep/show만). grep의 exit 1은 "매칭 0건"이며 오류 아님(출력 정상).

## 실측

### (1) 레포별 무테스트 *Service 클래스 + @SpringBootTest 비중

동명 테스트 없음 & `src/test` 어디에도 참조 0인 클래스만 "무테스트"로 판정(참조 있으면 제외 표기).

| 레포 | main.java | test.java | *Service 수 | 무테스트 Service(참조 0) | 동명無이나 타테스트 참조有(제외) | @SpringBootTest 파일 | 비중 |
|---|---|---|---|---|---|---|---|
| platform-svc | 61 | 41 | 8 | GithubEmailOAuth2UserService, ConsentService, AccountService, UserProfileService | — | 25 | 61% |
| learning-svc | 106 | 42 | 11 | AssessmentService, ClaimService, GuestAssessmentService, ContentService, InternalContentService, InternalSimilarService | LearningPathGenerationService(2), LearningPathQueryService(2) | 30 | 71% |
| community-svc | 69 | 23 | 8 | BadgeQueryService, TagService, CommunitySeedService | AnswerService(2), QuestionService(8), VoteService(2) | 22 | 96% |
| sandbox-svc | 23 | 13 | 2 | SandboxRunPersistenceService | — | 9 | 69% |
| ai-svc | 82 | 41 | 6 | (없음) | — | 16 | 39% |
| lcs-svc | 26 | 4 | 1 | (없음) | — | 0 | 0% |
| notification-svc | 32 | 14 | 2 | (없음) | — | 6 | 43% |
| gateway | 2 | 13 | 0 | — | — | 13 | 100% |
| shared | 25 | 17 | 0 | — | — | 0 | 0% |
| svc-template | 1 | 1 | 0 | — | — | 1 | 100% |

관찰: 피라미드(Unit 75%) 대비 @SpringBootTest(무거운 통합/슬라이스) 비중이 community 96%, learning 71%, platform 61%, gateway 100%로 상단 무거움 경향. lcs-svc는 test 4건으로 절대량 희소.

### (2) §2.1 도메인 불변식별 테스트 유무

| 불변식 | 상태 | 레포 | 근거 |
|---|---|---|---|
| 평판 일일 40점 상한 | 있음 | community-svc | `reputation/ReputationServiceTest.java` L47 `dailyUpvoteGainCappedAtForty`, L53 `isEqualTo(40)`, L57 `acceptanceExemptFromDailyCap` |
| 평판 7일 신규계정 제한 | 미확인/없음 | community-svc | reputation 테스트에 7일/신규계정 키워드 매칭 없음(별도 확인 필요) |
| 에스컬레이션 상태 전이(NONE→ESCALATED→BOUNTY_PLACED→RESOLVED) | 없음(미구현) | community-svc | grep `ESCALAT\|BOUNTY_PLACED` → src/test 0, **src/main 0** (구현 자체 부재) |
| 현상금 차감/환불(optimistic locking) | 없음(미구현) | community-svc | grep `bounty\|refund`, `@Version\|Optimistic` → src/test 0, **src/main 0** |
| 적응형 난이도(+0.1/-0.05 수렴) | 있음 | learning-svc | `assessment/engine/AdaptiveEngineTest.java`, `assessment/NextQuestionSelectorTest.java` |
| 학습 경로 rationale 빌더 | 부분 | learning-svc | `path/LearningPathEngineTest.java`, `path/LearningPathPersistenceServiceTest.java`에서 rationale 참조(전용 rationale-빌더 단위/속성 테스트는 없음) |
| 스트릭 계산(자정 경계, TZ) | 있음 | learning-svc | `progress/StreakRolloverServiceTest.java`, `progress/StreakRolloverStagnationTest.java`, `progress/UserStreakRepositoryTest.java` |
| 피어 매칭 스코어링(대칭성) | 없음 | learning-svc | grep `peer\|Matching` → src/test 0 (src/main도 faint) |
| 멘토 컨텍스트 스냅샷 조립 | 부분 | ai-svc/community-svc | ai-svc mentor eval 존재하나 스냅샷 opt-in/민감정보 필터 전용 테스트 미확인 |
| AI 시드 파이프라인(프롬프트 인젝션·refusal) | 있음 | ai-svc | `community/eval/GoldenCommunitySeedInjectionEvalTest.java`, `mentor/eval/GoldenMentorInjectionEvalTest.java` + `eval/*.jsonl` |
| 학습 맥락 스냅샷(opt-in·민감정보 필터) | 없음 | community-svc | grep `snapshot\|optIn\|consent` → src/test 0 |
| 모더레이션 심각도 판정 + fallback | 없음(미구현) | community-svc | grep `oderation\|Severity\|fallback` → src/test 0, **src/main 0** |

### (3) jqwik / 속성 기반 테스트 사용 레포

| 레포 | jqwik 파일 | @Property(테스트) |
|---|---|---|
| 전 10개 레포(platform·learning·community·sandbox·ai·lcs·notification·gateway·shared·svc-template) | **0** | **0** |

`git grep -ln 'jqwik'` 및 `@Property`(src/test) 모두 전 레포 0건. 전략서 §2.1 예시(`@Property adaptiveDifficulty_...`)·§7이 명시적으로 요구하나 실제 채택 0.

## 갭 후보

| 갭 | 근거 | 우선순위 | 보강 제안(테스트 경로) |
|---|---|---|---|
| jqwik 속성기반 테스트 전무(전략서 §2.1/§7 vs 실제 0) | 전 10레포 jqwik/@Property grep 0 | P0 | 적응형 난이도 수렴 `learning-svc:src/test/java/ai/devpath/learning/assessment/engine/AdaptiveEnginePropertyTest.java`; 피어 매칭 대칭성; 스트릭 TZ 연속성 |
| 피어 매칭 스코어링 무테스트 | learning-svc src/test peer/Matching 0 | P1 | `learning-svc:src/test/.../PeerMatchingTest.java` (구현 존재 여부 선확인 필요) |
| 학습 맥락 스냅샷 opt-in/민감정보 필터 무테스트 | community-svc src/test snapshot/consent 0 | P1 | `community-svc:src/test/java/ai/devpath/community/seed/LearningContextSnapshotTest.java` |
| 평판 7일 신규계정 제한 미확인 | ReputationServiceTest에 해당 케이스 미검출 | P1 | `ReputationServiceTest`에 신규계정 감쇄 케이스 추가 |
| learning-svc 무테스트 Service 6종 | 동명 테스트 없음 & src/test 참조 0 (Assessment/Claim/GuestAssessment/Content/InternalContent/InternalSimilar) | P1 | 각 `*ServiceTest` 신설(도메인 로직 보유분 우선) |
| platform-svc 무테스트 Service 4종 | 동명無 & 참조 0 (GithubEmailOAuth2UserService/Consent/Account/UserProfile) | P1 | 각 `*ServiceTest` 신설(OAuth 사용자매핑·동의 로직 우선) |
| @SpringBootTest 상단 편중 (community 96%·learning 71%·platform 61%·gateway 100%) | (1)표 비중 | P2 | 순수 도메인 로직을 슬라이스/POJO 단위테스트로 하향 이동, 컨텍스트 부팅 테스트 절감 |
| community/sandbox 소형 무테스트 Service | BadgeQueryService·TagService·CommunitySeedService·SandboxRunPersistenceService 참조 0 | P2 | 각 `*Test`(단순 위임이면 최소 스모크) |
| rationale/멘토 스냅샷 전용 테스트 부재(부분 커버) | rationale·snapshot 전용 테스트 없이 상위 테스트만 | P2 | rationale 빌더 단위테스트, 멘토 스냅샷 조립 단위테스트 |

## 관찰

- (판정 보류) **에스컬레이션 상태 전이·현상금 차감/환불·모더레이션 심각도**는 community-svc src/main에도 grep 0으로, "테스트 갭"이 아니라 **기능 미구현**일 가능성이 높다. 축① 구조/축② 정합성 점검 결과와 교차 확인 후 "미구현 vs 테스트 누락"을 확정해야 한다(테스트 신설 제안은 구현 존재를 전제로 함).
- (판정 보류) "무테스트 Service" 목록 중 일부는 얇은 위임/CRUD 어댑터일 수 있어, 도메인 로직 보유 여부를 개별 `git show`로 확인한 뒤에야 P1/P2 확정 가능. 본 보고서는 명명·참조 기반 1차 스크린이다.
- (판정 보류) jqwik 부재는 명백하나, 전략서가 "v1 목표"임을 자체 명시(문서 서두)하므로 P0 확정 전 로드맵상 목표연도 대비 현재 기대치인지 확인 필요.
- 커버리지 수치(전략서 §11: 도메인 Line≥85 등) 실측은 본 축 범위 밖(빌드 실행 금지). 별도 측정 필요.
