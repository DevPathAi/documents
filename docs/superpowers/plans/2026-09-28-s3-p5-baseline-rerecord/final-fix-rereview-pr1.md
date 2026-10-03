### Findings Verdicts

- ① I1 (밴드 배경·테두리): ADDRESSED — `packages/dp_design/lib/src/mission/dp_next_action_band.dart:87-92` 배경 `context.dpColors.accentSoft`·테두리 `context.dpColors.accentLine` 로 교체, `borderRadius: context.appTokens.panelRadius`·`Padding(DpSpacing.xl)`·`_PrimaryAction`의 foreground/fill switch(라인 108-113)는 diff 밖 — 원본 그대로. `BoxDecoration`에 `boxShadow` 키를 추가하지 않아 그림자는 되살아나지 않음(기존 `boxShadow, isNull` 테스트 그대로 통과 대상). 새 테스트 `dp_next_action_band_test.dart:65-80`가 `decoration.color == DpColors.light.accentSoft`·`border.top.color == DpColors.light.accentLine`을 직접 단언 — `surface`로 되돌리면 실패하는 판별력 있는 테스트. 대비 단언(`dp_colors_contrast_test.dart:59-68`)은 파일 상단 `for (final (label, p) in [('라이트', DpColors.light), ('다크', DpColors.dark)])`(24행) 루프 **안**에 있어 두 테마 모두 실행됨. 토큰 값(accentSoft `#EEF2FF`/`#24244A`, accentLine `#C7D2FE`/`#454589`, `dp_colors.dart:123-124,158-159`)은 컨트롤러가 이미 확인한 대비 계산의 전제와 일치.

- ② M1 승격 (null 폴백): ADDRESSED — `dp_next_action_band.dart:121-124`에서 `semanticLabel`이 `'$displayedLabel, 사용할 수 없음: ${widget.disabledReason ?? '지금은 사용할 수 없습니다'}'`로 바뀌어 `<라벨>, 사용할 수 없음: <이유>` 형식이 그대로 유지됨(보간 대상만 폴백). 주석(라인 118-120)이 `assert`가 릴리스에서 제거되는 이유를 적음. `hint`는 되살아나지 않음 — 기존 "`hint`를 쓰지 않는다" 주석(라인 129-132, diff 밖)이 그대로 있고, `dp_next_action_band_test.dart:345-347`의 `bandNode.getSemanticsData().hint, isEmpty` 단언도 손대지 않음. 테스트는 요구되지 않았고 실제로 추가되지 않음(지시대로).

- ③ I2 (마이페이지 주석 2건): ADDRESSED — 두 주석 모두 코드·레이아웃 변경 없이 텍스트만 교체(`mypage_page.dart:138-141`, `303-308`). (a) `today_panels.dart:112` 실측: `(key: '연속 학습', value: Text('${summary.streakDays}일'))`로 실제 키-값 렌더이고 `'N일 연속'` 합성 문구가 없음 — 새 주석의 "값만 재사용, 문구는 다르다"는 사실과 일치. (b) `mypage_page.dart:218`(프로필 편집 패널)에 동일한 목표 트랙(243)·학습 목표(233, "목표"에 대응)·경력(년)(254) 필드가 존재 — 새 주석이 적은 "같은 세 값이 아래 「프로필 편집」 패널에도 나온다"는 divergence가 실재함. `build()` 위젯 트리·조건문·키는 diff 전후 동일.

- ④ I3 (토큰 doc 상호 참조·비투영): ADDRESSED — `dp_spacing.dart`의 `DpDensity` doc(149-151행)이 `DpWebDensity.rowVerticalPadding`을 가리키고 `rowPadding`(8)이 표 행임을 밝힘. `DpWebDensity` doc(173-176행)이 `DpDensity`를 가리키며 "그 투영 대상이 아니다"(`--dp-density-*` 비투영)를 명시 — 상호 참조·비투영 둘 다 양쪽에 존재. 값은 `rowPadding = 8`·`rowVerticalPadding = 10`·`keyValueGap = 6` 전부 diff에서 안 바뀜(주석 줄만 추가).

- ⑤ M4 (렌더 단언): ADDRESSED — `dp_status_text_test.dart:61`에 `expect(tester.getSize(find.text('✓ 완료')).height, closeTo(16, 0.5))` 추가. 주석(58-60행)이 근거(`labelMedium`의 `height 16/12 × fontSize 12 = 16` 논리픽셀, 실측값도 정확히 16.0)를 적음. 허용오차 0.5는 정수 반올림 오차 정도의 의미 있는 범위(추측성 큰 tolerance 아님). 선언 스타일 단언(`style.height`, 57행)은 그대로 남고 렌더 단언이 그 옆에 추가된 형태.

### New Breakage in the Fix Diff

None. 기존 `DpNextActionBand` 테스트(그림자 null·기본 상태별 시맨틱 라벨·`primary-surface` 관련 단언들)와 새 테스트가 서로 다른 대상(외곽 `DecoratedBox` vs 내부 `_PrimaryAction`의 `surface` 키드 위젯)을 겨냥해 충돌 없음.

### Out-of-Scope Observations

None.

### Verdict

all findings addressed
