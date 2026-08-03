# Handoff — ④ 오류 신고·문의 구현 완료 (2026-08-03)

> 앞 세션([핸드오프 2026-08-02](handoff-2026-08-02-support-request-spec.md))이 스펙까지 확정하고 멈췄다. 이번 세션은 **계획 작성 → 13 Task 구현 → 5레포 PR 머지 → 게이트웨이 경유 통합 실측**까지 마쳤다.

## 0. 한눈에

| 작업 | 상태 |
|---|---|
| 구현 계획(writing-plans) | ✅ 13 Task · 98 스텝 — `devpath-frontend/docs/superpowers/plans/2026-08-03-support-request.md` |
| 구현 | ✅ 13 Task 전부 |
| PR | ✅ **5개 전부 develop 머지** |
| 통합 검증 | ✅ 게이트웨이 경유 8단계 실측 통과 |
| 브라우저 E2E | ⬜ 미실시(위젯 테스트만) — 계획 범위 밖 |
| ①전반 디자인 | ⬜ **다음 세션 시작점** |

## 1. 머지된 PR

| 레포 | PR | 내용 |
|---|---|---|
| `devpath-shared` | **#54** | `V202608031001__support_requests.sql` — 부모+자식 테이블. **수동 발행까지 완료** |
| `devpath-platform-svc` | **#44** | 마스커 · 접수 API · admin API(목록/상세/전이) |
| `devpath-gateway` | **#29** | `/support/**` 라우트 |
| `devpath-frontend` | **#102** | dp_core(마스커·링버퍼·인터셉터) · dp_design(보조 액션) · web(다이얼로그·진입점) · admin(콘솔) |
| `documents` | **#90** | API 명세 **§12** 신설 + 사용자 문서 정합 |

계획서는 스펙 PR #101에 함께 담겨 develop에 들어갔다.

## 2. 통합 검증 — 실제 서버 2개 기동, 게이트웨이 경유 8단계

위젯/단위 테스트가 아니라 **platform-svc(8081) + gateway(8080)를 띄워** 실측했다.

| # | 검증 | 결과 |
|---|---|---|
| ① | 접수(게이트웨이 8080 경유) | **201** `{"id":31}` |
| ② | admin 목록 | 최신순(31·30·29) + `nextCursor` 정확 + `failureCount` 정확 |
| ③ | 권한 | LEARNER **403** · 무토큰 **401** |
| ④ | 상세 | **서버 재마스킹 실증** — `담당자 [EMAIL] 에게 문의, 카드 [CARD]` · `서버 [IP] 응답 없음` / `pagePath`에서 `?draft=1` 제거 / `failures` seq 오름차순 |
| ⑤ | `IN_PROGRESS` 전이 | `handledBy=3` · `handledAt` 기록 · 메모 저장 |
| ⑥ | `OPEN` 복귀 | **`handledBy`·`handledAt` 둘 다 NULL 초기화** |
| ⑦ | 이상 상태값 | **400** `VALIDATION_FAILED` |
| ⑧ | 없는 id | **404** |

테스트 총계: platform-svc 신규 28 · dp_core 88 · dp_design 61 · web 291 · admin 50 · mobile 100 — 전 스위트 green.

## 3. ★계획이 틀렸던 3건 — 실측이 뒤집었다★

계획을 아무리 파일을 열어 쓰더라도 **열지 않은 파일이 계약을 바꾼다.**

### 3-1. 게이트웨이는 `application-test.yml`이 routes를 통째로 오버라이드한다

`src/main/resources/application.yml`에만 `/support/**`를 넣고 테스트를 돌렸더니 라우트 미매칭 **404**로 실패했다. `src/test/resources/application-test.yml`이 `routes` 목록 전체를 다시 정의하고 있어 main의 변경이 테스트에 도달하지 않는다.

**게이트웨이 라우트를 바꿀 때는 두 파일을 모두 고친다.** 계획 작성 시 test 리소스를 확인하지 않은 것이 원인이었다.

### 3-2. dio는 index 0에 `ImplyContentTypeInterceptor`를 기본 장착한다

불변식 테스트에 "첫 인터셉터가 `AuthInterceptor`"라고 썼는데 실패했다. 실측 체인은:

```
[ImplyContentTypeInterceptor, AuthInterceptor, InterceptorsWrapper]
```

**보호해야 할 불변식은 "정규화(InterceptorsWrapper)가 마지막"뿐**이고, `insert(length - 1, recorder)` 배선은 그 위에서 정확하다. 테스트를 "정규화가 마지막" + "Auth가 recorder보다 앞" 두 가지로 다시 썼다.

### 3-3. 스펙이 지목한 문서 위치가 부정확했다

스펙 §9는 `04_API_명세서 §8.1.3`을 지목했으나 **§8은 커뮤니티 섹션**이다. ④는 platform-svc 소유의 서비스 전역 기능이라 그 아래 둘 수 없어 **독립 `## 12. 오류 신고·문의`를 신설**하고 기존 §12 Rate Limit·§13 관련 문서를 §13·§14로 밀었다(외부 문서가 섹션 앵커를 참조하지 않음을 확인 후 진행). §8.1.2에는 상호참조를 넣어 두 기능의 경계를 문서에 고정했다.

### 부수적으로 어긋났던 값

- 에러 코드: 스펙 `INVALID_ARGUMENT` → shared 실제 enum은 **`VALIDATION_FAILED`**(`ApiExceptionHandler:39`)
- `DpError` 호출부: 스펙 19개 → 실측 **12개**(web 8 · admin 4). web 8개만 `SupportableError`로 교체하고 **admin은 제외**했다(관리자는 제보자가 아니라 처리자다)

## 4. 검증으로 해소한 미확인 사항

### 마스킹 크로스언어 일치 — 스펙이 남긴 숙제를 풀었다

스펙 §6.3은 "PCRE로만 검증했다. Dart `RegExp`·Java `Pattern`에서 같은 결과가 나오는지는 각 언어 테스트가 다시 확인해야 한다"고 명시적으로 남겨뒀다. **Java 13/13 · Dart 14/14 통과**로 해소했다. 두 테스트는 같은 12케이스 표를 쓴다.

Dart 구현 주의점: `replaceAll`의 치환 문자열은 `$1`을 해석하지 않아 **`replaceAllMapped`**를 써야 한다.

### recorder 배선 근거를 테스트로 고정했다

스펙 §5.1의 "index 0이면 안 되고 정규화 뒤도 안 된다"를 두 테스트로 못박았다.

- `refresh로 복구된 401은 기록되지 않는다` — `AuthInterceptor`가 `handler.resolve(res)`로 체인을 **종료**하므로 recorder에 도달하지 않는다(`auth_interceptor.dart:82`)
- `refresh가 실패한 401은 기록된다` — 실패 시에만 `handler.next(err)`로 뒤로 넘어간다

recorder는 정규화 **앞**이라 `err.error`가 아직 `ApiException`이 아니다. 직접 `ApiException.fromDio`로 정규화하고, `errorCode`는 enum으로 좁히지 않고 **응답 본문 원문**을 읽는다(서버가 `ApiErrorCode`에 없는 `INTERNAL_ERROR`도 보낸다).

## 5. 로컬 환경 — 재현에 필요한 것

### ⚠️ 컨테이너가 없으면 코드와 무관한 실패가 난다

이번 세션에서 두 번 겪었다. **마이그레이션·구현 문제로 오진하지 말 것.**

| 증상 | 원인 | 해소 |
|---|---|---|
| shared 테스트 **31건 실패**(`FlywaySqlException: Connection to localhost:5432 refused`) | Docker Desktop 종료 | Docker 기동 후 `docker start dpa-test-pg` |
| platform-svc 전체 스위트 **10건 실패**(AuthCode·RefreshToken·OAuth 계열, `RedisConnectionFailureException`) | Redis 부재 | `docker run -d --name dpa-test-redis -p 6379:6379 redis:7-alpine` |

`dpa-test-es`·`dpa-test-kafka`는 ④ 범위에 불필요하다.

### 통합 실측 레시피

```bash
# 서버
cd devpath-platform-svc && ./gradlew bootRun --args='--server.port=8081'
cd devpath-gateway     && ./gradlew bootRun            # 8080

# JWT (HS256, secret = application.yml 기본값)
# test-secret-please-change-min-32-bytes-long-0123456789
# PyJWT 없이 순수 python hmac+base64로 생성 가능
```

⚠️ **한글 JSON은 UTF-8 파일 + `--data-binary @file`**. Git Bash에서 `curl -d`로 넘기면 CP949로 깨진다.
⚠️ Windows에서 파이썬은 `python`이 아니라 **`py`**(`python`은 스텁이라 출력 없이 exit 49).
⚠️ platform-svc DB는 **`devpath`**(community-svc의 `devpath_citest`와 다르다).

## 6. 다음 세션이 할 일 — ①전반 디자인

사용자 표현: **"대시보드 이외에는 디자인 개판, 대시보드도 좋은 디자인은 아님"**

**★착수 조건(사용자 명시, 변경 없음)★**
> 전체 구조에 맞는 디자인 테마를 **상세 리서치 + 100건 이상 프리뷰 + 모든 페이지 검토** 후 진행. **즉흥 개선 금지**, 대규모 사전 조사 필수.

## 7. 이월 백로그

**④에서 범위 밖으로 둔 것**: 자동 오류 리포팅(C안) · 관리자 답변을 사용자가 확인하는 흐름(notification-svc 연동) · 스크린샷 첨부 · 비로그인 접수(게이트웨이 미인증 라우트 + IP 레이트리밋 선행 필요)

> **알려진 한계**: 로그인 필수라 **로그인 자체가 실패하는 오류는 이 경로로 제보할 수 없다.** 이메일 안내로 대체한다(사용자 메뉴얼 §13에 명시).

**검색**: shared 에러 핸들러 하드닝(`HttpMessageNotReadableException`이 400 아닌 **500**) · 고아 문서 정리 · 비동기 재색인 · nori 영숫자 토큰 분해 · CI 빌드 캐시
**신고(③)**: 콘텐츠 조치(숨김) · 제재 · AI 모더레이션 · 이의제기 · 신고자 결과 알림
**공통**: **웹 UI 브라우저 E2E 미실시** · k3s 미적용(AWS 정지, ApplicationSet `targetRevision: main`)
