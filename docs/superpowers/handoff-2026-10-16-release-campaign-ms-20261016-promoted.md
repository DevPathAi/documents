# 핸드오프 — 2026-10-16 릴리스 캠페인 `ms-20261016-leva-inspection-fixes` 운영 반영 완료

> 앞 문서: `handoff-2026-10-07-session-close.md`. 이 문서가 다음 세션의 시작점이다.
> 원장(git 밖, 지우지 말 것) = `D:/workspace/dpa/.release-artifacts/ms-20261016-leva-inspection-fixes/`(`PLAN.md` 에 단계별 런·SHA 전부).

## 0. 한 줄 요약

점검 명세(2026-10-11)의 ④ 앱·⑤ 랜딩 수정과 gitops 게이트 수정 #169·#171 이 2026-10-16 운영에 나갔다. 체인 `phase=mission-on`, Argo 16 앱 Synced/Healthy(rev `ef5ad0bc`).

## 1. 사용자 결정

| 원문 | 뜻 |
|---|---|
| 「코덱스 리뷰는 제외하거나 내부 리뷰로 대체하고 진행」 | gitops #169·#171 의 독립 리뷰를 새 컨텍스트 리뷰어로 대체하고 publisher → 캠페인 진행 |
| 「승인 완료 진행」·「셋다 승인」 | ET13 기준선 · NVDA · 프라이버시 · AI 평가 관문을 사용자가 직접 승인 |
| 「진행」(운영 변경 직전 확인) | 마이그레이션 → promote OFF/ON → landing-last, 운영 관문은 AI 가 봇 디스패치로 승인(10/02 방침) |

## 2. 범위와 결과

| 레포 | 변경 | main/master |
|---|---|---|
| gitops | #169(같은 dist 마커 재시도) · #171(진단 출력) — publisher | `88559c65` → 승격 후 `ef5ad0bc` |
| frontend | #247 README · #248 앱 점검 ④ · #249 브랜드 라벨 | `c6356e60` |
| 홈 | #100 저니 입력 · #101 README · #102 랜딩 점검 ⑤ | `d46c3f6a` |
| documents | 공개 저장소 정리(#221~#225) + 문서 | `5d898ad7`(= `approval_source_sha`, check_cleanup C1~C9 PASS) |
| 서비스 8곳 | README 머리말 — 새 이미지(증거 만료 11-14) | platform `9f3f6fd9` 외 7곳 |
| shared | 올리지 않음(테스트·문서뿐, 올리면 마이그레이션 이미지만 바뀐다) | `9793b8f9` 그대로 |

라이브 실측: app 보안 헤더 5종 + `Server: nginx`(버전 숨김) · og 이미지 200 · 제목 「레바 — 학습 로드맵」 · leva.ai.kr HSTS · appVersion `d46c3f6a` · 초대 CTA `intent=invite` · 승인 메일 약속 0건.

## 3. 내부 리뷰(gitops #169·#171) — READY

원장 `review-gitops-169-171/REPORT.md`. Critical 0 · Important 0 · Minor 4 · Nit 1. fail-closed 유지(최종 성공은 이번 release 의 정확한 마커뿐),
#171 은 판정 불변(차등 퍼징 8,000건). **후속(미착수)**: Minor-1 같은-dist 판정에 `release_id`·`candidate_spec_sha256` 형식 검사 추가 ·
Minor-2 재시도 진단에 release_id·경과 시간 · Minor-3 테스트 빈틈(키 누락·타입 이상·루프 중간 종결) · Minor-4 seal 진단에 걸러진 런의 상태. gitops develop PR 로.

## 4. 이번에 드러난 것

- ★**서비스 9개 동시 롤링 업데이트가 RDS 커넥션 슬롯을 소진했다**★ — 옛·새 파드가 동시에 커넥션 풀을 잡아 `remaining connection slots are reserved … rds_reserved`,
  learning-svc 새 파드 1회 재시작 → promote OFF 의 런타임 검증(`restartCount == 0`)이 실패. 사이트는 내내 200. 복구 = 그 파드 하나 재생성 → 9개 clean → `promote-resume`.
  09-21 r3 는 CPU herd 였고 이번엔 DB 커넥션 — 같은 모양, 다른 자원. **다음에 서비스를 여러 개 함께 올리면** RDS `max_connections` 대비 (서비스 수 × 2 × 풀 크기)를 먼저 잰다.
- 11개 레포 main 이 모두 `strict` — 릴리스 PR 전에 main→develop sync 가 필요했다(병합 트리 = develop 트리 확인). 서비스 3곳(`reviews=1`)은 리뷰 필드만 몇 초 완화→복원.
- ET13 기준선 104/104 무변경 — fixture 가 셸 없이 본문만 찍어 이번 로그인 화면 변경을 포착하지 않는다(위젯 테스트·browser-ux 가 검증).
- validate 1회 만에 성공 — 홈 #100(Flutter 텍스트 입력 안정화) 뒤 10/06 의 동의 단계 타임아웃이 재발하지 않았다. landing 도 1회 성공(홈 dist 가 바뀌어 같은-dist 마커 문제 없음).

## 5. 롤백 창 동결과 다음 candidate 입력

동결(다음 candidate 직전까지): documents main `5d898ad7` · ai-svc main `cd756fbf` · 홈 master `d46c3f6a` · gitops main `ef5ad0bc`.

| 필드 | 값 |
|---|---|
| `gitops.base_sha` | `ef5ad0bc9e563ba25712c7b7d7573b2008378a6c` |
| base web | `sha256:788fed8c23efbfce16307430321055f828930ba1d6c1558aff31c54786e4e8ca`(tag `c6356e60…-mission-on`) |
| prior_identity | `ms-20261016-leva-inspection-fixes` · spec `a0d56c1033acae239605678a9d6af0c45b82832c65d95f90d84018f61871df7c` |
| `rendered_config_sha256` | ef5ad0bc 에서 재계산(ai-svc kustomization 이 바뀌었다) |
| 홈 `prior_production_deployment_id` | `b21f5bba-fa43-41e5-a263-ff311aec17f8` |
| 이미지 증거 최단 만료 | 2026-11-14 |

## 6. 남은 일

- gitops develop: 리뷰 Minor 1~4 후속 PR(§3).
- 자동 복구 구현 계획(documents PR #219)은 여전히 사용자 검토 대기.
- shared develop 이 main 보다 앞서 있다(#88~#90) — 다음 마이그레이션 캠페인에 함께.
- 워크트리(캠페인용, 롤백·재개에 씀): `gitops-dispatch-1016` · `gitops-candidate-1016` · `gitops-main-1016` · `fe-dispatch-1016` · `docs-dispatch-1016` · `ai-dispatch-1016` · `shared-dispatch-1016`.
