BEGIN;
UPDATE question_bank SET content = 'Kafka에서 컨슈머 그룹의 역할은 무엇인가?', options = '["동일한 토픽의 메시지를 다른 그룹이 받지 못하게 독점적으로 소비한다.", "같은 그룹 내에서 각 컨슈머는 서로 다른 파티션을 나누어 소비한다.", "같은 그룹의 모든 컨슈머가 모든 메시지를 중복으로 수신하도록 보장한다.", "컨슈머 그룹은 한 번에 하나의 토픽만 구독할 수 있다."]', answer_key = '{"correct":1}' WHERE id = 504 AND md5(content) = '8d8679ff684eac2be2b7cacbe03f00ec';
UPDATE question_bank SET content = 'Spring Boot 애플리케이션에서 application.yml 파일의 역할로 옳은 것은 무엇인가?', options = '["자바 소스 코드를 컴파일하기 전에 변환 규칙을 정의하는 빌드 스크립트다.", "설정 프로퍼티를 정의해 스프링 빈의 속성에 바인딩할 수 있다.", "운영체제 수준의 환경 변수를 영구적으로 등록하는 파일이다.", "빈 사이의 의존성 주입 순서를 강제로 지정하는 파일이다."]', answer_key = '{"correct":1}' WHERE id = 510 AND md5(content) = '2ce94d792a2efda93482ecae60d50cb2';
UPDATE question_bank SET content = 'Spring Cloud를 사용하지 않는 순수 Spring Boot 애플리케이션에서, jar 내부 classpath의 application.properties와 실행 디렉터리의 config/application.yaml에 같은 프로퍼티가 서로 다른 값으로 정의되어 있다. 기동 시 어떤 값이 적용되는가?', options = '["classpath의 application.properties 값이 적용된다.", "먼저 로드된 파일의 값이 적용되고 나머지는 무시된다.", "실행 디렉터리의 config/application.yaml 값이 적용된다.", "동일 프로퍼티 충돌로 애플리케이션 기동이 실패한다."]', answer_key = '{"correct":2}' WHERE id = 511 AND md5(content) = 'bf225b6a9c98100c2359916968acae35';
UPDATE question_bank SET content = 'Spring Boot 애플리케이션에서 프로파일을 사용하여 환경별 설정을 구분하는 방법은 무엇인가?', options = '["환경별 설정 파일을 만들어 두면 Spring Boot가 실행 호스트명을 보고 자동으로 알맞은 프로파일을 활성화한다.", "spring.profiles.active 프로퍼티에 활성화할 프로파일을 명시하며, 이를 통해 해당 환경에 대한 설정이 로드된다.", "application.yml 파일 내부에서 @Profile 어노테이션으로 분할된 설정을 정의하고, 필요한 프로필 이름을 지정한다.", "운영 환경에서는 메인 클래스에 @ActiveProfiles 어노테이션을 붙여 프로파일을 활성화하는 것이 표준 방법이다."]', answer_key = '{"correct":1}' WHERE id = 517 AND md5(content) = '20d2ca8643fbd9115de24181b337f442';
UPDATE question_bank SET content = 'Spring Boot 애플리케이션에서 @Profile 어노테이션과 application.yml 파일을 사용하여 환경 설정을 변경할 때 주의해야 할 사항으로 옳은 것은 무엇인가요?', options = '["환경 변수를 통해 활성 프로파일을 동적으로 변경하는 것이 가능합니다.", "프로파일은 애플리케이션당 한 번에 하나만 활성화할 수 있습니다.", "비프로필 기본 설정이 프로필별 설정보다 항상 우선 적용됩니다.", "Spring Boot는 프로필 기반 설정을 지원하지 않습니다."]', answer_key = '{"correct":0}' WHERE id = 521 AND md5(content) = '11f00e3b3883ae9af91fa3a7a21b4208';
UPDATE question_bank SET content = 'Spring Security의 폼 로그인에서 요청의 username·password 파라미터를 읽어 인증을 시도하는 필터는 무엇인가요?', options = '["AuthenticationFilter", "AuthenticatingFilter", "UsernamePasswordAuthenticationFilter", "AuthenticationProcessingFilter"]', answer_key = '{"correct":2}' WHERE id = 526 AND md5(content) = '532fa2e6b74041401c3a0b68e320c9e6';
UPDATE question_bank SET content = 'Spring Data JPA에서 엔티티(Entity) 간의 관계를 표현하기 위해 사용하는 어노테이션은 무엇인가?', options = '["@Entity", "@Table", "@Id", "@OneToMany"]', answer_key = '{"correct":3}' WHERE id = 529 AND md5(content) = 'b4b89e5373537801bb855c1b1ed592a9';
UPDATE question_bank SET content = 'Spring AOP에서 advice의 종류에 대한 설명으로 옳은 것은 무엇인가?', options = '["Before, After, Around 세 가지이며, 예외 발생 시점에 실행되는 advice 종류는 따로 존재하지 않는다.", "Before, After returning, After throwing, After (finally), Around의 다섯 가지가 있다.", "advice의 종류는 Pointcut과 JoinPoint 두 가지로, 각각 advice가 적용될 위치와 실행 시점을 지정한다.", "Before와 After 두 가지뿐이며, 대상 메소드 실행을 감싸는 형태의 advice는 지원되지 않는다."]', answer_key = '{"correct":1}' WHERE id = 535 AND md5(content) = 'a075c4156201977cd4f7f5e775adef1c';
UPDATE question_bank SET content = 'Spring Security에서 인증(Authentication)과 인가(Authorization)의 구분으로 옳은 것은 무엇인가?', options = '["인증과 인가는 동일한 개념이며 Spring Security는 둘을 구분하지 않는다.", "인증은 사용자의 권한을 확인하고 인가는 로그인 여부를 확인한다.", "인증은 사용자의 신원을 확인하고 인가는 접근 허용 여부를 확인한다.", "인가가 항상 인증보다 먼저 수행된 뒤에 신원 확인이 이루어진다."]', answer_key = '{"correct":2}' WHERE id = 539 AND md5(content) = '505882f833218806846aae379f7fa4aa';
UPDATE question_bank SET content = 'JPA에서 연관 엔티티 조회 시 발생하는 N+1 문제를 해결하는 방법으로 옳은 것은 무엇인가?', options = '["JPQL의 fetch join으로 연관 엔티티를 한 번의 쿼리로 함께 조회한다.", "@Transactional을 메소드에 붙이면 영속성 컨텍스트가 개별 쿼리들을 자동으로 하나로 합쳐 준다.", "모든 연관관계를 EAGER 로딩으로 변경한다.", "엔티티의 equals와 hashCode를 오버라이드해 중복 조회를 막는다."]', answer_key = '{"correct":0}' WHERE id = 543 AND md5(content) = 'df90e3d4e332f6f7c43fa753c06467ba';
UPDATE question_bank SET content = '브라우저 세션 쿠키 기반의 Spring Security 애플리케이션에서 CSRF(Cross-Site Request Forgery) 공격에 대비하기 위한 올바른 설정은 무엇인가?', options = '["@EnableWebSecurity 설정 클래스에서 csrf().disable()을 호출한다.", "기본 활성화된 CSRF 보호를 유지하고, 상태 변경 요청에 CSRF 토큰을 담아 검증받는다.", "CSRF 보호는 기본 비활성 상태이므로 spring.security.csrf.enable=true 프로퍼티를 명시해야만 켜진다.", "스프링 시큐리티 필터 체인에서 CsrfFilter를 제거해 토큰 충돌을 방지한다."]', answer_key = '{"correct":1}' WHERE id = 548 AND md5(content) = '879c9764cb3865c1218f4ae8f7d9d361';
UPDATE question_bank SET content = 'Spring Boot에서 Spring Data Redis를 사용할 때, opsForValue() 등의 연산으로 Redis 명령을 직접 실행하는 데 사용하는 핵심 클래스는 무엇인가?', options = '["CacheManager", "RedisTemplate", "JedisClient", "CachingConfigurer"]', answer_key = '{"correct":1}' WHERE id = 549 AND md5(content) = 'b64e9ad4aba6be94fca9da642c935131';
UPDATE question_bank SET content = 'Spring에서 비동기 작업을 처리할 때 `@Async` 어노테이션의 사용은 중요합니다. 다음 중 올바른 설명을 선택하세요.', options = '["비동기 메서드는 항상 새로운 쓰레드를 생성하여 실행되며, 쓰레드 풀은 사용되지 않습니다.", "스프링 컨텍스트가 모든 비동기 메서드 호출에 대해 결과를 기다리는 동안 블로킹합니다.", "void 반환 비동기 메서드에서 발생한 예외는 호출자 스레드로 항상 자동 전파되어 호출부의 try-catch로 잡을 수 있습니다.", "비동기 메서드의 반환값을 호출자가 받아오려면 메서드가 Future 계열(예: CompletableFuture) 타입을 반환해야 합니다."]', answer_key = '{"correct":3}' WHERE id = 553 AND md5(content) = '0f8bfbe66ab5ef3c75c1883e92eefc82';
UPDATE question_bank SET content = 'Kafka에서 Consumer Group의 역할과 파티션 배정은 어떻게 이루어지는지 설명해보자.', options = '["Consumer Group은 여러 컨슈머를 하나의 단위로 취급하며, 하나의 파티션을 그룹 내 여러 컨슈머가 동시에 나눠 읽도록 할당하여 처리량을 높인다.", "Consumer Group은 동일한 주제에 대한 모든 메시지를 읽기 위해 독립적으로 작동하는 컨슈머들의 집합이며, 각 파티션은 배정 전략 없이 매 폴링마다 임의의 컨슈머에게 새로 할당된다.", "Consumer Group은 Kafka 클러스터 내에서 중복된 메시지 처리를 방지하기 위한 식별자로서 동작하며, 모든 파티션이 단일 Consumer Group에 속한다.", "각 파티션은 특정 소비그룹의 컨슈머에게 고유하게 할당되며, 리밸런싱 시점에서 자동적으로 파티션이 재할당된다."]', answer_key = '{"correct":3}' WHERE id = 556 AND md5(content) = '9cecf8b55f65e40d6110c77ddc0fb425';
UPDATE question_bank SET content = 'Spring Boot에서 application.yml 안에 `spring.config.activate.on-profile: prod`로 구분한 prod 전용 설정 블록을 정의했는데, 애플리케이션을 아무 옵션 없이 실행하면 이 블록이 적용되지 않는다. 가장 가능성 높은 원인은 무엇인가?', options = '["spring.profiles.active 등으로 prod 프로파일을 활성화하지 않아 해당 문서 블록이 로드 대상에서 제외되었다.", "application.yml은 한 파일 안에 여러 프로파일 문서를 담을 수 없으므로 항상 application-prod.yml 같은 별도 파일로 분리해야만 한다.", "YAML 형식 자체가 프로파일 조건 설정을 지원하지 않으므로 .properties 형식으로 변환해야만 프로파일이 동작한다.", "on-profile 조건 블록은 클라우드 배포 환경에서만 평가되며 로컬 실행에서는 스프링이 항상 무시하도록 설계되어 있다."]', answer_key = '{"correct":0}' WHERE id = 560 AND md5(content) = 'b06196fe645ffc1dd5285879d5fcbcb0';
UPDATE question_bank SET content = 'JPA에서 N+1 문제를 해결하기 위해 사용할 수 있는 방법 중 하나는 무엇인가?', options = '["fetch join 사용", "연관 컬럼에 데이터베이스 인덱스 추가", "Lazy Loading 사용", "Eager Loading 사용"]', answer_key = '{"correct":0}' WHERE id = 564 AND md5(content) = 'd442918ec99e9699fbd34f88b22ee66f';
UPDATE question_bank SET content = 'Kafka에서 메시지 발행을 담당하는 KafkaProducer 클래스가 속한 패키지는 무엇인가?', options = '["org.springframework.kafka.core", "org.apache.kafka.clients.consumer", "org.apache.kafka.clients.producer", "org.apache.kafka.connect.runtime"]', answer_key = '{"correct":2}' WHERE id = 565 AND md5(content) = 'cbd576203454ab27efe611fa34b15237';
UPDATE question_bank SET content = '다음 코드는 @Cacheable 어노테이션을 사용하여 데이터베이스 쿼리를 캐시합니다.

@Cacheable("userCache")
public User findUserById(Integer id) {
    return userRepository.findById(id).orElse(null);
}
', options = '["데이터를 성공적으로 캐싱하고 요청 시 복잡성을 줄입니다.", "데이터베이스의 값이 변경되면 캐시가 이를 자동으로 감지해 무효화되므로 항상 최신 값이 반환됩니다.", "findUserById 메서드는 캐시에 저장된 데이터만 반환합니다.", "이 코드는 퍼포먼스 저하를 일으킵니다."]', answer_key = '{"correct":0}' WHERE id = 584 AND md5(content) = 'f502888f3a21a6dc306fd46b9140e49c';
UPDATE question_bank SET content = '다음 코드에서 @Transactional(readOnly = true) 메서드 안에서 조회한 엔티티의 필드를 수정하면 어떤 일이 발생하는가? (JPA 구현체는 Hibernate 기본 구성)

@Transactional(readOnly = true)
public void readOnlyMethod() {
    User user = repository.findById(1L).orElseThrow();
    user.setName("changed");
}
', options = '["readOnly 트랜잭션에서는 엔티티의 setter를 호출하는 시점에 즉시 예외가 발생한다.", "변경 감지(dirty checking)가 정상 동작하여 커밋 시점에 UPDATE 쿼리가 실행된다.", "Hibernate가 세션 플러시 모드를 MANUAL로 설정해 자동 플러시가 생략되므로, 필드 변경이 DB에 반영되지 않는다.", "readOnly 설정으로 트랜잭션 자체가 시작되지 않아 영속성 컨텍스트가 아예 만들어지지 않는다."]', answer_key = '{"correct":2}' WHERE id = 586 AND md5(content) = '7271b2d39102ccce924f37e63f8c23b2';
UPDATE question_bank SET content = '다음 코드에서 @Transactional(readOnly = true) 설정은 어떤 역할을 하는가?

@Transactional(readOnly = true)
public void readData() {
    List<User> users = userRepository.findAll();
}
', options = '["트랜잭션을 시작하지 않고 데이터를 읽는다.", "findAll() 결과의 모든 행에 자동으로 비관적 읽기 잠금(SELECT ... FOR SHARE)을 걸어 다른 트랜잭션의 수정을 막는다.", "트랜잭션이 읽기 전용임을 하위 계층에 힌트로 전달해 플러시 생략 같은 최적화를 유도하지만, 모든 쓰기 시도의 실패를 절대적으로 보장하지는 않는다.", "JPA 2차 캐시를 강제로 활성화하여 이후 동일한 조회는 데이터베이스 대신 캐시에서만 읽어오도록 만든다."]', answer_key = '{"correct":2}' WHERE id = 591 AND md5(content) = '124e4d000eeb3bf192eb67359e49978a';
UPDATE question_bank SET content = '다음 코드에서 @Transactional(readOnly = true) 설정이 주어진 상황에서, readOnlyMethod() 메서드의 호출은 어떻게 작동하는가? (JPA 구현체는 Hibernate 기본 구성)

@Transactional(readOnly = true)
public void readOnlyMethod() {
    repository.delete(entity);
}
', options = '["delete() 호출 시점에 DELETE 쿼리가 즉시 실행되어 엔티티가 데이터베이스에서 삭제된다.", "삭제 요청은 영속성 컨텍스트에 등록되지만, 플러시 모드가 MANUAL이라 커밋 시 자동 플러시가 생략되어 DELETE가 DB에 반영되지 않는다.", "readOnly 위반을 감지한 Spring이 delete() 호출 시점에 UnsupportedOperationException을 던지도록 표준으로 보장한다.", "삭제는 정상적으로 수행되지만 트랜잭션이 커밋 대신 자동으로 롤백 처리된다."]', answer_key = '{"correct":1}' WHERE id = 592 AND md5(content) = '4d2eecfd3f5ac32f2d080d151380694c';
UPDATE question_bank SET content = '@Transactional(readOnly = true) 메서드 안에서 repository.save(entity)를 호출했을 때의 동작에 대한 가장 정확한 설명은 무엇인가?

@Transactional(readOnly = true)
public void readOnlyMethod() {
    repository.save(entity);
}
', options = '["JPA 표준이 readOnly 트랜잭션에서의 save() 호출에 대해 항상 즉시 예외를 던지도록 강제한다.", "save()는 readOnly 설정과 완전히 무관하게 동작하도록 규정되어 있어, 어떤 구성에서도 커밋 시점의 INSERT 실행이 예외 없이 항상 보장된다.", "readOnly는 최적화 힌트일 뿐이라 결과가 구성에 따라 갈린다 — ID 생성 전략과 JPA 구현체에 따라 INSERT가 즉시 실행될 수도, 플러시 생략으로 조용히 무시될 수도 있다.", "Spring이 save() 호출을 감지해 메서드 전체를 no-op으로 바꾸므로 아무 일도 일어나지 않음이 항상 보장된다."]', answer_key = '{"correct":2}' WHERE id = 600 AND md5(content) = 'bdd57facf82271bcdd18c8fe7b15b5d1';
UPDATE question_bank SET content = '리액트에서 `React.memo`로 감싼 컴포넌트가 재렌더링을 건너뛰는 조건은 무엇입니까?', options = '["컴포넌트의 key 값이 고유하게 유지될 때", "props로 매 렌더링마다 새로운 객체 리터럴이나 인라인 함수를 만들어 전달할 때", "컴포넌트 내부의 state가 변경되었을 때", "부모가 재렌더링되어도 전달된 props가 얕은 비교(shallow compare)로 이전과 같을 때"]', answer_key = '{"correct":3}' WHERE id = 603 AND md5(content) = '5b8505121fcdddf3c7e4b3402ab07633';
UPDATE question_bank SET content = 'Redux 스토어와 Context API를 비교할 때, 어떤 상황에서 Redux가 더 적합한가?', options = '["미들웨어와 개발자 도구 기반 디버깅을 활용해 복잡한 전역 상태 갱신 로직을 다뤄야 할 때", "단일 컴포넌트 내부에서만 쓰이는 폼 입력 상태를 관리할 때", "거의 변하지 않는 테마나 로케일 값을 하위 트리에 단순히 전달하기만 하면 될 때", "외부 라이브러리 의존성을 최소화하고 싶을 때"]', answer_key = '{"correct":0}' WHERE id = 604 AND md5(content) = 'c37aba9c10b64bd53f3023e7dabb970f';
UPDATE question_bank SET content = '리액트 컴포넌트에서 `useEffect` 훅으로 API 요청을 할 때, 이전 요청의 늦은 응답이 최신 상태를 덮어쓰는 경쟁 상태(race condition)를 피하는 방법은 무엇인가요?', options = '["API 요청 전에 상태를 미리 업데이트해 두어 응답 지연을 숨긴다.", "setTimeout으로 요청 사이에 일정한 간격을 강제로 두어 응답이 항상 순서대로 도착하게 만든다.", "cleanup 함수에서 ignore 플래그를 설정하거나 AbortController로 이전 요청을 취소한다.", "useMemo로 응답 데이터를 캐싱해 같은 요청을 반복하지 않는다."]', answer_key = '{"correct":2}' WHERE id = 608 AND md5(content) = '634bd96db3ea552b159b38b79538d192';
UPDATE question_bank SET content = 'React 함수형 컴포넌트에서 `useState` 훅으로 초기 상태 값을 설정하는 올바른 방법은?', options = '["const [count, setCount] = useState(0);", "const [count, setCount] = setState(0);", "const count = useState(0); count.value = 0;", "함수 컴포넌트 본문에 this.state = { count: 0 }; 을 작성한다."]', answer_key = '{"correct":0}' WHERE id = 609 AND md5(content) = 'dc6b29f5f33658b6c1ca4fefb28d070c';
UPDATE question_bank SET content = 'React 컴포넌트의 props에 대한 설명으로 옳은 것은 무엇인가요?', options = '["props는 반드시 문자열 형태로만 전달할 수 있다.", "자식 컴포넌트는 전달받은 props를 직접 수정해서 부모의 상태를 갱신하는 것이 권장된다.", "props가 바뀌어도 자식 컴포넌트는 다시 렌더링되지 않는다.", "props는 부모 컴포넌트에서 자식 컴포넌트로 전달되는 읽기 전용 데이터다."]', answer_key = '{"correct":3}' WHERE id = 610 AND md5(content) = '72c0e99427696324dd67e00c25ee99bd';
UPDATE question_bank SET content = 'React 컴포넌트에서 비제어(uncontrolled) 컴포넌트를 사용하는 장점은 무엇인가요?', options = '["입력값이 항상 React state와 자동으로 동기화된다.", "React가 입력값 유효성 검사를 자동으로 수행해 준다.", "키 입력마다 setState가 호출되지 않아 리렌더링이 발생하지 않는다.", "value prop 값을 바꾸는 것만으로 언제든 입력값을 즉시 재설정할 수 있다."]', answer_key = '{"correct":2}' WHERE id = 611 AND md5(content) = '6ff09b9aa4ba861e7ba489779c598e72';
UPDATE question_bank SET content = 'React 함수형 컴포넌트에서 상태(state)를 선언하고 업데이트하기 위해 사용하는 가장 기본적인 훅은 무엇인가요?', options = '["useContext()", "useState()", "useCallback()", "useMemo()"]', answer_key = '{"correct":1}' WHERE id = 618 AND md5(content) = 'fb216352b6db0f371c7dab6ee23fe0e3';
UPDATE question_bank SET content = '부모 컴포넌트가 리렌더링될 때, props가 변하지 않은 자식 컴포넌트의 불필요한 재렌더링을 막으려면 어떤 방법을 사용해야 하나?', options = '["useEffect() 안에서 상태 업데이트를 모아 배치로 처리한다.", "자식 컴포넌트를 React.memo()로 감싼다.", "자식 컴포넌트에서 useState() 호출을 제거하고 전역 변수에 값을 보관한다.", "부모의 setState() 호출을 setTimeout으로 지연시킨다."]', answer_key = '{"correct":1}' WHERE id = 621 AND md5(content) = '6bf8622cebedcfdb07a22229a9610943';
UPDATE question_bank SET content = 'React 함수형 컴포넌트에서 useState의 setter를 호출하면, 새 상태 값은 언제 반영됩니까?', options = '["setter 호출 직후 같은 함수 안에서 즉시 새 값을 읽을 수 있다.", "다음 렌더링에서 새 값으로 반영된다.", "useEffect의 cleanup 함수가 실행된 뒤에만 반영된다.", "브라우저 이벤트 루프가 한 바퀴 돈 뒤 렌더링 없이 조용히 반영된다."]', answer_key = '{"correct":1}' WHERE id = 626 AND md5(content) = '94102fa26daf5cd48fe15f7d04cdb220';
UPDATE question_bank SET content = 'React에서 제어(controlled) 컴포넌트로 입력값 state를 관리할 때, 올바르게 작성된 코드는?', options = '["function MyComponent() { const [value, setValue] = useState(''''); return <input value={value} onChange={(e) => setValue(e.target.value)} />; }", "function MyComponent() { let value = ''''; return <input value={value} onChange={(e) => value = e.target.value} />; }", "function MyComponent() { const value = ''''; return <input value={value} onChange={(e) => value = e.target.value} />; }", "function MyComponent() { let [value, setValue] = useState(''''); return <input value={value} onChange={(e) => value = e.target.value} />; }"]', answer_key = '{"correct":0}' WHERE id = 631 AND md5(content) = 'b37726feaf4053fe2e58255d791a0c14';
UPDATE question_bank SET content = 'useEffect 내부에서 참조하는 상태 값을 의존성 배열에 포함하지 않으면 어떤 문제가 발생할 수 있습니까?', options = '["이펙트가 매 렌더링마다 무조건 다시 실행된다.", "React가 컴파일 단계에서 오류를 내며 렌더링을 중단한다.", "이펙트가 이전 렌더링 시점의 낡은(stale) 값을 계속 참조한다.", "상태 업데이트가 동기적으로 즉시 반영되어 배치 처리가 깨진다."]', answer_key = '{"correct":2}' WHERE id = 634 AND md5(content) = '8bb4402d508d09979ae13c848a591028';
UPDATE question_bank SET content = 'React 컴포넌트에서 props를 전달받아 사용할 때, 다음 중 올바르게 작성된 코드는?', options = '["function MyComponent(name) { return <div>Hello, {name}</div>; }", "function MyComponent(props) { return <div>Hello, {props.name}</div>; }", "function MyComponent() { return <div>Hello, props.name</div>; }", "function MyComponent({ name: ''John'' }) { return <div>Hello, {name}</div>; }"]', answer_key = '{"correct":1}' WHERE id = 636 AND md5(content) = 'b0f30629ae7459545ede0ce72b910c4b';
UPDATE question_bank SET content = 'React에서 비제어(uncontrolled) 컴포넌트로 입력 폼의 값을 다룰 때 올바른 방법은 무엇인가요?', options = '["onChange 이벤트 핸들러에서 useState 훅으로 매 입력마다 value를 갱신한다.", "value 속성을 props로 전달해 입력값을 강제한다.", "defaultValue로 초기값을 주고 ref로 현재 값을 읽는다.", "useContext 훅으로 폼 값을 구독한다."]', answer_key = '{"correct":2}' WHERE id = 646 AND md5(content) = '9487a4b533d3cf90137b0928f9013811';
UPDATE question_bank SET content = 'React 함수형 컴포넌트에서 state 값을 업데이트하려면 어떤 방법을 사용해야 하나요?', options = '["props로 전달받은 값을 직접 수정한다.", "this.setState() 메서드를 호출한다.", "useState 훅이 반환한 setter 함수를 호출한다.", "this.state 객체의 속성을 직접 변경한다."]', answer_key = '{"correct":2}' WHERE id = 649 AND md5(content) = '78ba94af7ea77a97157bdcc0afe99d96';
UPDATE question_bank SET content = '리액트에서 리스트로 렌더링되는 요소들에 key 속성을 부여하는 이유는 무엇인가요?', options = '["서버와 클라이언트에서 렌더링 결과가 항상 동일하게 보이도록 보장하기 위해서다.", "key가 각 요소의 CSS 클래스로 자동 부여되어 스타일링에 활용되기 때문이다.", "리액트가 key를 전역 상태 저장소의 식별자로 사용해 상태를 보존하기 때문이다.", "각 아이템을 고유하게 식별해 재조정(reconciliation) 시 변경·추가·제거된 항목을 판별하게 한다."]', answer_key = '{"correct":3}' WHERE id = 653 AND md5(content) = 'e48673c86aa8ec913d7b4c29f19d893e';
UPDATE question_bank SET content = 'react-router에서 useNavigate로 페이지를 이동하되, 브라우저 히스토리에 새 항목을 추가하지 않고 현재 항목을 대체하려면 어떻게 해야 하나요?', options = '["const navigate = useNavigate(); navigate(''/path'', { replace: true });", "const navigate = useNavigate(); navigate(''/path'', { state: { data } });", "const navigate = useNavigate(); navigate(''/path'', { preventDefault: true });", "useNavigate({ replace: true })를 호출하면 반환 함수 없이 즉시 대체 이동이 일어난다."]', answer_key = '{"correct":0}' WHERE id = 657 AND md5(content) = '3f3a43cb10cc75c613754147dbd3094e';
UPDATE question_bank SET content = '다음 중 React의 훅 규칙(Rules of Hooks)을 올바르게 지킨 코드는?', options = '["function MyComponent({ show }) { if (show) { const [n, setN] = useState(0); } return <div>Content</div>; }", "function MyComponent() { const [count, setCount] = useState(0); useEffect(() => {}, []); return <div>Content</div>; }", "function handleClick() { const [on, setOn] = useState(false); return on; }", "function MyComponent() { for (let i = 0; i < 3; i++) { useState(i); } return <div>Content</div>; }"]', answer_key = '{"correct":1}' WHERE id = 659 AND md5(content) = '5a402f931d6b80c373a3abd1b7041dec';
UPDATE question_bank SET content = 'React 함수 컴포넌트에서 useState 훅의 상태 초기값은 어떻게 지정하는가?', options = '["첫 렌더링이 끝난 뒤 setState를 한 번 호출해서 지정한다", "useEffect 안에서 setState를 호출해서 지정한다", "useState를 호출할 때 인자(initialState)로 전달한다", "props로 넘기기만 하면 자동으로 상태 초기값이 된다"]', answer_key = '{"correct":2}' WHERE id = 668 AND md5(content) = '3cb68d7f38e6dda83967b62bf603da41';
UPDATE question_bank SET content = '다음 Counter 컴포넌트가 처음 마운트된 뒤 버튼을 한 번 클릭했다. 2초 후 setTimeout 콜백 안의 console.log(count)가 출력하는 값은 무엇인가?

import React, { useState } from ''react'';
function Counter() {
  const [count, setCount] = useState(0);
  function handleClick() {
    setTimeout(() => {
      setCount(count + 1);
      console.log(count);
    }, 2000);
  }
  return <button onClick={handleClick}>Increment</button>;
}', options = '["0 — 콜백은 클릭 시점 렌더의 count 값을 클로저로 캡처한다", "1 — 콜백 실행 시점에는 setCount가 반영된 최신 state를 읽는다", "undefined — 타이머가 실행될 때 count 변수는 이미 소멸해 있다", "TypeError — 함수 컴포넌트의 state는 setTimeout 안에서 읽을 수 없다"]', answer_key = '{"correct":0}' WHERE id = 672 AND md5(content) = 'b41a5412e3eb813cc684ec41dd71aed4';
UPDATE question_bank SET content = '다음 코드는 정상 동작하지만 상태 업데이트 방식에 개선할 점이 있다. 무엇인가?

import React from ''react'';
class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = { count: 0 };
  }
  handleClick = () => {
    this.setState({ count: this.state.count + 1 });
  };
  render() {
    return (
      <div>
        <p>카운트: {this.state.count}</p>
        <button onClick={this.handleClick}>증가</button>
      </div>
    );
  }
}
export default App;', options = '["stale closure 때문에 setState에 전달한 객체가 렌더 시점의 값을 캡처해 count가 영원히 0에서 1 사이만 오간다", "다음 상태를 this.state.count에서 직접 계산하므로 한 배치에서 연속 호출되면 업데이트가 유실될 수 있다 — 업데이터 함수가 안전하다", "클래스 컴포넌트에서는 setState를 쓸 수 없으므로 useState 훅으로 바꿔야 한다", "handleClick을 화살표 함수 클래스 필드로 정의하면 this 바인딩이 깨져 클릭 시 TypeError가 발생한다"]', answer_key = '{"correct":1}' WHERE id = 677 AND md5(content) = '11f089db53a0b6746f7494868b9d00c5';
UPDATE question_bank SET content = '다음 컴포넌트가 리렌더링될 때, JSX가 반환하는 React 엘리먼트 객체와 실제 DOM 노드에 대한 설명으로 옳은 것은?

const [items, setItems] = useState([{id: 1, text: ''a''}]);
return (
  <div key={items[0].id}>{items[0].text}</div>
);', options = '["엘리먼트 객체는 렌더마다 새로 생성되지만, type과 key가 같으면 기존 DOM 노드는 재사용된다.", "엘리먼트 객체는 최초 렌더에 한 번만 생성되고, 이후 렌더에서는 같은 객체가 캐시에서 반환되어 그대로 재사용된다.", "key가 같으면 JSX 평가 자체가 생략되어 엘리먼트 객체가 생성되지 않는다.", "렌더마다 DOM 노드가 새로 만들어지고 이전 노드는 항상 제거된다."]', answer_key = '{"correct":0}' WHERE id = 684 AND md5(content) = '59c14f9908e4c36567a1080a7b4a271a';
UPDATE question_bank SET content = '다음 코드에서 `React.memo`를 사용했지만, 컴포넌트가 계속해서 렌더링되는 이유는 무엇인가요?

const MyComponent = React.memo(({ count }) => {
  console.log(''MyComponent rendered'');
  return <div>{count}</div>;
});

function App() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    setInterval(() => setCount(prev => prev + 1), 1000);
  }, []);

  return <MyComponent count={count} />;
}', options = '["React.memo는 함수형 컴포넌트에는 적용되지 않아 메모이제이션이 무시되기 때문이다.", "React.memo는 이벤트 핸들러의 변경사항을 감지하지 못하기 때문이다.", "React.memo로 감싼 컴포넌트는 부모가 렌더링되면 props와 무관하게 무조건 다시 렌더링되기 때문이다.", "setInterval로 count prop이 매초 변경되어 memo의 얕은 비교가 매번 다르다고 판정하기 때문이다."]', answer_key = '{"correct":3}' WHERE id = 685 AND md5(content) = '6b522e308f5aee3ab56b777e175cbfbb';
UPDATE question_bank SET content = '다음 코드에서 `React.memo`를 사용했지만, 컴포넌트가 계속해서 렌더링되는 이유는 무엇인가요?

const MemoComponent = React.memo(function Component({ count }) {
  console.log(''MemoComponent rendered'');
  return <div>{count}</div>;
});

function App() {
  const [count, setCount] = useState(0);
  useEffect(() => {
    setInterval(() => setCount(prev => prev + 1), 1000);
  }, []);

  return <MemoComponent count={count} />;
}', options = '["React.memo는 props를 깊은 비교하므로 숫자 타입 prop의 변경은 감지하지 못하기 때문이다.", "React.memo는 이벤트 핸들러의 변경사항을 감지하지 못하기 때문이다.", "React.memo로 감싼 컴포넌트는 state를 가진 부모 아래에서는 항상 리렌더링되기 때문이다.", "매초 count prop이 바뀌어 memo의 props 비교에서 이전 값과 달라지므로 정상적으로 리렌더링되기 때문이다."]', answer_key = '{"correct":3}' WHERE id = 687 AND md5(content) = '890d9b889569b1e332c8ac5219527464';
UPDATE question_bank SET content = '다음 코드의 useLayoutEffect 훅은 useEffect와 비교해 언제 실행되는가?

useLayoutEffect(() => {
  console.log(''layout effect'');
}, []);

// 컴포넌트 내용', options = '["브라우저가 화면을 페인트한 후에 비동기적으로 실행되어 페인트를 막지 않는다", "DOM 변경이 반영된 후, 브라우저가 화면을 페인트하기 전에 동기적으로 실행된다", "컴포넌트 함수가 호출(렌더)되기 전에 먼저 실행된다", "실행 시점이 보장되지 않아 페인트 전후 어느 쪽에서든 실행될 수 있다"]', answer_key = '{"correct":1}' WHERE id = 690 AND md5(content) = 'e9c212dc157daa7e6d684b0569607c37';
UPDATE question_bank SET content = '다음 코드가 실행될 때 어떤 문제가 발생할 수 있을까요?

import React, { useState } from ''react'';
function Counter() {
  const [count, setCount] = useState(0);
  const handleClick = () => {
    setTimeout(() => {
      setCount(count + 1); // 문제점이 있는 코드
    }, 500);
  };
  return (
    <div>
      <p>카운트: {count}</p>
      <button onClick={handleClick}>증가</button>
    </div>
  );
}
export default Counter;', options = '["setTimeout 내부에서 setCount를 호출하는 것 자체가 React에서 금지되어 있어 경고가 출력됩니다.", "setTimeout 콜백이 클릭 시점의 count 값을 클로저로 캡처하므로, 500ms 안에 여러 번 클릭해도 stale closure 때문에 카운트가 1만 증가할 수 있습니다.", "함수 컴포넌트에서는 setTimeout을 사용할 수 없습니다.", "setCount가 setTimeout 안에서는 배치되지 않고 동기적으로 즉시 실행되어 카운트가 매 클릭마다 두 배씩 증가합니다."]', answer_key = '{"correct":1}' WHERE id = 691 AND md5(content) = '5b041101a841b64cedbda58a4f4e29af';
UPDATE question_bank SET content = '다음 코드에서 useLayoutEffect 훅이 사용된 이유는 무엇인가?

import React, { useLayoutEffect } from ''react'';
const Example = () => {
  useLayoutEffect(() => {
    console.log(''useLayoutEffect called'');
    document.body.style.backgroundColor = ''#fff'';
  }, []);

  return <div>Example</div>;
};', options = '["useLayoutEffect와 useEffect는 실행 시점까지 완전히 동일하므로 어느 것을 써도 아무 차이가 없다.", "DOM 변경이 반영된 뒤 브라우저가 화면을 페인트하기 전에 동기적으로 배경색을 적용해, 이전 배경이 잠깐 보이는 깜빡임을 막기 위해 사용되었다.", "렌더링 도중(render phase)에 컴포넌트의 상태를 변경하기 위해 사용되었다.", "서버 사이드 렌더링 환경에서만 실행되는 훅이기 때문에 사용되었다."]', answer_key = '{"correct":1}' WHERE id = 694 AND md5(content) = 'bffd1d3e2e0a0e72ae56fe0b94b45b29';
UPDATE question_bank SET content = '다음 코드에서 ''증가'' 버튼을 클릭하면 어떤 문제가 발생할까요?

import React from ''react'';
class Counter extends React.Component {
  constructor(props) {
    super(props);
    this.state = { count: 0 };
  }
  handleClick() {
    setTimeout(() => {
      const latestCount = this.state.count; // 문제점이 있는 코드
      this.setState({ count: latestCount + 1 });
    }, 500); 
  }
  render() {
    return (
      <div>
        <p>카운트: {this.state.count}</p>
        <button onClick={this.handleClick}>증가</button>
      </div>
    );
  }
}
export default Counter;', options = '["setTimeout 내부에서 this.setState를 호출하는 것 자체가 React에서 금지되어 있어 개발 모드에서 경고가 출력되고 업데이트가 무시됩니다.", "setState 메서드는 setTimeout 내부에서는 동작하지 않습니다.", "handleClick이 this에 바인딩되지 않은 채 onClick에 전달되어 콜백 실행 시 this가 undefined가 되고, this.state.count를 읽는 순간 TypeError가 발생합니다.", "클래스 컴포넌트에서는 setTimeout을 사용할 수 없습니다."]', answer_key = '{"correct":2}' WHERE id = 695 AND md5(content) = '85433f23873e6df5c3ba065f50492206';
UPDATE question_bank SET content = '다음 코드에서 ''증가'' 버튼을 한 번 클릭했을 때 발생하는 문제점은 무엇인가?

import React from ''react'';
class Counter extends React.Component {
  constructor(props) {
    super(props);
    this.state = { count: 0 };
    this.handleClick = this.handleClick.bind(this);
  }
  handleClick() {
    this.setState({ count: this.state.count + 1 });
    this.setState({ count: this.state.count + 1 });
    this.setState({ count: this.state.count + 1 }); // 3 증가를 의도한 코드
  }
  render() {
    return (
      <div>
        <p>카운트: {this.state.count}</p>
        <button onClick={this.handleClick}>증가</button>
      </div>
    );
  }
}
export default Counter;', options = '["세 번의 setState가 한 이벤트 핸들러 안에서 배치 병합되고 this.state.count는 그동안 갱신되지 않아, 카운트가 3이 아니라 1만 증가합니다.", "한 핸들러에서 setState를 연속 호출하면 React가 예외를 던져 컴포넌트가 언마운트됩니다.", "각 setState가 호출 즉시 재렌더링을 일으키므로 클릭당 3씩 정상적으로 증가하며 아무 문제가 없습니다.", "클래스 컴포넌트에서는 객체를 인자로 넘기는 setState 호출이 허용되지 않습니다."]', answer_key = '{"correct":0}' WHERE id = 699 AND md5(content) = 'df25e80c300907819cb009030c284d7d';
UPDATE question_bank SET content = '다음 코드에서 `useContext` 훅이 어떻게 작동하는지를 설명해 주세요.

const ThemeContext = React.createContext(''light'');

function App() {
  const [theme, setTheme] = useState(''dark'');
  return (
    <ThemeContext.Provider value={theme}>
      <Child />
    </ThemeContext.Provider>
  );
}

function Child() {
  const theme = useContext(ThemeContext);
  useEffect(() => {
    console.log(`Current Theme: ${theme}`);
  }, [theme]);
  return null;
}', options = '["useContext는 컴포넌트 트리에서 가장 가까운 컨텍스트 값을 가져온다.", "useContext 훅은 직접 제공된 value값을 무시하고, 최상위 Provider의 값만 사용한다.", "useEffect 내부에서 useContext 훅이 호출되면, 이 컴포넌트는 렌더링되지 않는다.", "ThemeContext.Provider가 없으면 useContext는 createContext에 준 기본값을 무시하고 항상 undefined를 반환한다."]', answer_key = '{"correct":0}' WHERE id = 700 AND md5(content) = '11ca8164598e0fdf063c51a922484ec7';
UPDATE question_bank SET content = 'Dart에서 Future를 사용하여 비동기 작업을 처리할 때, 다음 중 올바른 사용법은?', options = '["async 로 선언하지 않은 일반 함수의 본문 안에서 await 키워드 사용하기", "async 함수 안에서 await 키워드로 다른 Future 의 완료를 기다리기", "완료된 Future 의 값을 await 대신 .result 속성으로 동기적으로 꺼내기", "Future.delayed 의 콜백이 동기적으로 즉시 실행된다고 가정하고 반환값 바로 사용하기"]', answer_key = '{"correct":1}' WHERE id = 706 AND md5(content) = '82b3a1c3af14f8055ac159d87f0fa627';
UPDATE question_bank SET content = '다음 코드에서 Provider 로 제공된 int 값이 변경되면 위젯 트리에는 어떤 일이 일어나는가?

```
class MyHomePage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(''Provider Example'')),
      body: Center(child: ValueCounter()),
    );
  }
}

class ValueCounter extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final int value = Provider.of<int>(context); // Provider 사용
    return Text(''Value: $value'');
  }
}
```', options = '["MyHomePage 를 포함한 위젯 트리 전체가 rebuild 된다.", "Provider.of 는 값을 한 번만 읽으므로 값이 변경되어도 아무 위젯도 rebuild 되지 않는다.", "Provider.of(context) 로 값을 구독한 ValueCounter 위젯만 rebuild 된다.", "BuildContext 가 무효화되어 Scaffold 부터 새로운 트리가 생성된다."]', answer_key = '{"correct":2}' WHERE id = 707 AND md5(content) = '1f3d948bd49b69275565146167e5a51c';
UPDATE question_bank SET content = 'Flutter의 비동기 처리와 관련된 다음 설명 중 올바른 것은 무엇인가요?', options = '["FutureBuilder 의 future 파라미터에는 Future 객체를 전달한다.", "StreamBuilder 는 Future 객체를 구독하며 Stream 은 처리할 수 없다.", "await 는 함수 전체를 블로킹해 UI 스레드를 멈추게 하는 동기 키워드다.", "위젯 트리에 다시 삽입될 State 객체라도 dispose 는 build 직후마다 반드시 호출된다."]', answer_key = '{"correct":0}' WHERE id = 710 AND md5(content) = 'b2a130028e626b6f67ad815b5ac957da';
UPDATE question_bank SET content = 'StatefulWidget 의 생명주기 메서드 initState 와 dispose 는 각각 언제 호출되고 어떤 역할을 하는가?', options = '["initState 는 build 가 호출될 때마다 매번 다시 실행되어 상태를 재초기화한다.", "initState 는 State 가 트리에 삽입될 때 한 번 호출되어 초기화를 수행하고, dispose 는 State 가 영구 제거될 때 호출되어 리소스를 해제한다.", "dispose 는 setState 가 호출될 때마다 실행되어 이전 프레임의 상태를 정리한다.", "initState 와 dispose 는 모두 State 객체가 처음 생성되는 시점에 연달아 호출되어 초기 설정과 정리 콜백 등록을 동시에 수행한다."]', answer_key = '{"correct":1}' WHERE id = 713 AND md5(content) = '675613c097b1b42cf2079be5a1bdd481';
UPDATE question_bank SET content = 'Flutter 에서 Row 의 자식 위젯들의 너비 합이 화면 너비를 넘어 오버플로(RenderFlex overflowed) 경고가 발생합니다. 자식들이 가용 공간에 맞춰 유연하게 줄어들도록 하려면 어떻게 해야 할까요?', options = '["mainAxisAlignment 를 MainAxisAlignment.spaceBetween 으로 설정한다.", "crossAxisAlignment 를 CrossAxisAlignment.stretch 로 설정해 자식을 세로로 늘인다.", "Row 의 mainAxisSize 를 MainAxisSize.min 으로 설정해 자식들의 크기를 줄인다.", "각 자식 위젯을 Expanded 로 감싸 가용 공간을 나눠 갖게 한다."]', answer_key = '{"correct":3}' WHERE id = 717 AND md5(content) = '80eceb0768378485b02bfd78ebeec72c';
UPDATE question_bank SET content = 'Flutter에서 StatelessWidget과 StatefulWidget을 사용할 때, 각각 어떤 상황에 적합한가?', options = '["상태 변경이 필요한 화면에는 StatelessWidget 을, 정적인 화면에는 StatefulWidget 을 사용한다.", "변경 가능한 내부 상태가 있으면 StatefulWidget 을, 없으면 StatelessWidget 을 사용한다.", "모든 위젯은 성능을 위해 항상 StatefulWidget 으로 작성해야 한다.", "StatelessWidget 은 setState 호출로 자신의 필드 값을 갱신해 화면을 다시 그릴 수 있다."]', answer_key = '{"correct":1}' WHERE id = 721 AND md5(content) = '3d98b0371f5359b70219bc700802b373';
UPDATE question_bank SET content = 'Flutter에서 Stack과 Positioned 위젯을 사용하여 화면에 아이콘을 표시하려고 한다. 아이콘이 항상 화면의 중앙에 위치하도록 설정해야 하는데, 어떻게 해야 할까?', options = '["Positioned 위젯의 top 과 left 속성을 0 으로 설정해 아이콘을 배치한다.", "Positioned 위젯의 top 과 left 속성을 각각 화면 높이와 너비의 절반 값으로 설정해 아이콘을 배치한다.", "Stack 의 alignment 를 Alignment.center 로 설정하고 아이콘을 Positioned 없이 자식으로 둔다.", "Stack 대신 Expanded 위젯으로 아이콘을 직접 감싸 중앙에 배치한다."]', answer_key = '{"correct":2}' WHERE id = 723 AND md5(content) = 'fa951e4c67df5264ccd0192174782c8c';
UPDATE question_bank SET content = 'ListView.builder가 많은 항목을 가진 리스트에서 성능을 최적화하는 핵심 메커니즘은 무엇인가?', options = '["모든 항목 위젯을 리스트 생성 시점에 한꺼번에 만들어 메모리에 캐시해 둔다.", "화면에 보일 항목만 필요한 시점에 itemBuilder로 생성한다.", "각 항목 위젯을 별도 isolate에서 병렬로 빌드한다.", "itemExtent를 지정하지 않으면 항목을 자동으로 압축해 메모리 사용량을 줄인다."]', answer_key = '{"correct":1}' WHERE id = 724 AND md5(content) = 'd7837b72b3c5e37c77982f8c25d0395b';
UPDATE question_bank SET content = 'Flutter에서 Navigator를 사용하여 페이지 이동을 구현하고 있다. 다음 중 Navigator의 동작에 대한 설명으로 옳은 것은?', options = '["Navigator의 push 메서드는 현재 스택에 있는 모든 라우트를 제거한 뒤 새 라우트를 넣는다.", "Navigator의 pop 메서드는 스택의 가장 아래에 있는 첫 번째 라우트를 제거한다.", "Navigator의 push 메서드는 새로운 라우트를 스택 맨 위에 추가하여 해당 화면으로 전환한다.", "Navigator의 pop 메서드는 남은 스택 깊이와 무관하게 항상 첫 화면으로 즉시 이동한다."]', answer_key = '{"correct":2}' WHERE id = 728 AND md5(content) = '0442352ed97a524c7f12793342521767';
UPDATE question_bank SET content = 'Provider 패키지로 상태 관리를 할 때, ChangeNotifierProvider가 수행하는 역할은 무엇인가?', options = '["상태를 앱 재시작 후에도 유지되도록 SharedPreferences에 자동으로 직렬화해 저장한다.", "하위 위젯의 build 메서드를 별도 isolate에서 비동기로 실행해 성능을 높인다.", "ChangeNotifier 인스턴스를 하위 트리에 제공하고, notifyListeners() 호출 시 이를 구독(watch)하는 위젯을 다시 빌드하게 한다.", "하위 위젯의 setState 호출을 가로채 한 프레임으로 병합한다."]', answer_key = '{"correct":2}' WHERE id = 736 AND md5(content) = '6041ffc4214fd27e38f32c4e58d8d0f9';
UPDATE question_bank SET content = '다음 코드에서 `Positioned` 위젯은 어떤 좌표계를 기준으로 위치를 지정하는가?

```
Stack(
  children: [
    Positioned(left: 50, top: 30, child: Container(color: Colors.red)),
  ],
)
```', options = '["Container 위젯의 크기", "Stack 위젯의 크기", "화면 전체의 크기", "가장 가까운 Scaffold body의 크기"]', answer_key = '{"correct":1}' WHERE id = 737 AND md5(content) = 'ceb69687398ddf8d580ae7bd408cc34f';
UPDATE question_bank SET content = 'Dart에서 비동기 코드를 작성할 때, 이벤트 루프와 isolate의 개념을 이해하고 적절히 활용하는 것이 중요하다. 다음 중 이벤트 루프와 isolate에 대한 올바른 설명은 무엇인가?', options = '["isolate는 Dart VM에서 메모리를 공유하지 않는 별도의 실행 컨텍스트이며, 메인 isolate와는 SendPort/ReceivePort로 메시지를 주고받는다.", "이벤트 루프는 비동기 작업이 완료될 때마다 이벤트를 처리하며, 동기 코드가 실행되는 동안에도 큐의 이벤트를 계속 꺼내 처리한다.", "isolate는 프로그램의 전체 생명주기를 관리하며, 메인 isolate에서 생성된 모든 isolate는 자동으로 종료된다.", "이벤트 루프는 비동기 작업을 큐에 넣어 처리하지만, 이벤트가 발생하지 않으면 이벤트 루프 자체가 영구히 중단된다."]', answer_key = '{"correct":0}' WHERE id = 744 AND md5(content) = '8d43d15277d610538bbd91dace98efa7';
UPDATE question_bank SET content = '다음 중 Flutter 앱에서 플랫폼(OS) 권한 요청을 처리하는 방법이 아닌 것은?', options = '["Platform Channel로 네이티브 권한 요청 코드를 호출한다.", "permission_handler 패키지의 request()를 사용한다.", "firebase_messaging의 requestPermission()으로 알림 권한을 요청한다.", "shared_preferences에 권한 상태 플래그를 저장한다."]', answer_key = '{"correct":3}' WHERE id = 754 AND md5(content) = 'f99f6ce8368535c872b0d091f651c5d8';
UPDATE question_bank SET content = 'Provider 패키지와 비교했을 때 Riverpod가 제공하는 차별점으로 옳은 것은 무엇인가요?', options = '["Riverpod의 프로바이더는 위젯 트리 바깥에 선언되며, BuildContext 없이도 상태를 읽을 수 있다.", "Riverpod는 상태가 하나라도 변경되면 앱의 전체 위젯 트리를 루트부터 다시 빌드해 일관성을 보장한다.", "Provider는 InheritedWidget을 사용하지 않지만 Riverpod는 InheritedWidget에 의존한다.", "Riverpod의 프로바이더는 StatefulWidget 내부에서만 선언하고 사용할 수 있다."]', answer_key = '{"correct":0}' WHERE id = 758 AND md5(content) = '6f1be800378bae842d7aa3409230d4ff';
UPDATE question_bank SET content = '다음 코드에서 MyInheritedWidget의 data가 새 값으로 바뀌어 위젯이 다시 생성되어도, 이를 참조(dependOnInheritedWidgetOfExactType)하는 하위 위젯들이 다시 빌드되지 않습니다. 원인은 무엇일까요?

class MyInheritedWidget extends InheritedWidget {
  final int data;
  const MyInheritedWidget({super.key, required this.data, required super.child});

  @override
  bool updateShouldNotify(MyInheritedWidget oldWidget) => false;
}', options = '["updateShouldNotify가 항상 false를 반환해 의존 위젯에 갱신이 통지되지 않는다.", "InheritedWidget의 필드는 final로 선언할 수 없으므로 data 선언 자체가 잘못되어 값 비교가 항상 실패한다.", "생성자가 const로 선언되어 있어 데이터 변경이 프레임워크에 감지되지 않는다.", "child를 super 생성자에 넘기면 하위 위젯이 트리에서 분리되어 갱신을 받지 못한다."]', answer_key = '{"correct":0}' WHERE id = 790 AND md5(content) = 'c5041f52f4f1d5c37cc2e2c90a7c4ff4';
UPDATE question_bank SET content = '다음 코드에서 Stack의 자식인 빨간 Container를 좌측 상단 기준 (left: 50, top: 10) 좌표에 배치하려고 합니다. Container를 어떤 위젯으로 감싸야 할까요?

Stack(
  children: [
    Container(width: 20, height: 20, color: Colors.red),
  ],
)', options = '["Expanded 위젯", "Flexible 위젯", "Center 위젯", "Positioned 위젯"]', answer_key = '{"correct":3}' WHERE id = 793 AND md5(content) = '3a9eaa5aba8e614aacf136d616b6b9bb';
UPDATE question_bank SET content = '다음 코드는 StatelessWidget을 사용하여 상수(const) 위젯을 정의합니다.

return const MyWidget();

class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Text(''Hello World'');
  }
}', options = '["MyWidget은 StatefulWidget처럼 내부 상태를 setState로 변경할 수 있습니다.", "const 키워드로 생성하지 않으면 MyWidget의 필드 값은 생성 이후에도 자유롭게 변경할 수 있는 가변 상태가 됩니다.", "const로 생성하면 build 메서드는 최초 한 번도 호출되지 않습니다.", "부모가 다시 빌드될 때 const로 생성된 동일 인스턴스는 재사용되어 불필요한 rebuild를 건너뛸 수 있습니다."]', answer_key = '{"correct":3}' WHERE id = 796 AND md5(content) = '92d8157d46619a0965997680da85a60a';
UPDATE question_bank SET content = '다음 코드에서 ListView.builder가 정상적으로 동작하지 않도록 설계되었습니다. 이 문제를 해결하기 위해 어떤 수정이 필요할까요?

ListView.builder(
itemBuilder: (context, index) {
return Container(height: 50);
},
count: 100,
)
', options = '["Container 위젯에서 height 속성을 제거한다.", "ListTile 위젯을 사용하도록 itemBuilder 메소드를 수정한다.", "ListView.builder에서 count 대신 itemCount를 사용한다.", "itemBuilder 메서드에서 setState 호출을 제거한다."]', answer_key = '{"correct":2}' WHERE id = 797 AND md5(content) = '1cd91500fa3ca86fec2f731e3b9c3e50';
UPDATE question_bank SET content = '다음 코드에서 setState 메서드의 사용과 상태 관리에 대한 설명으로 옳은 것을 고르세요.

class Counter extends StatefulWidget {
  final int initialCount;
  const Counter({super.key, required this.initialCount});
  @override
  State<Counter> createState() => _CounterState();
}

class _CounterState extends State<Counter> {
  late int count = widget.initialCount;
  void increment() { setState(() { count++; }); }
  @override
  Widget build(BuildContext context) {
    return Text(count.toString());
  }
}
', options = '["increment()의 setState 호출은 _CounterState의 build를 다시 실행하게 하여 변경된 count가 화면에 반영됩니다.", "setState 없이 count++만 실행해도 다음 프레임에서 화면이 자동으로 갱신됩니다.", "setState는 count 값을 변경하지만 build가 반환하는 Text는 이전 값을 유지합니다.", "setState의 콜백은 다음 프레임이 그려진 뒤 비동기로 실행되므로 count 증가가 한 프레임 늦게 반영됩니다."]', answer_key = '{"correct":0}' WHERE id = 799 AND md5(content) = '827dde99874e8dbd32def72b276598a9';
UPDATE question_bank SET content = '다음 코드는 FutureBuilder를 사용하여 비동기 작업의 결과를 화면에 표시하려고 합니다.

FutureBuilder<String>(
  future: _fetchData(), // 비동기 작업
  builder: (context, snapshot) {
    if (snapshot.hasError) return Text(''Error: ${snapshot.error}'');
    switch (snapshot.connectionState) {
      case ConnectionState.none:
        return Text(''Awaiting connection...'');
      case ConnectionState.active:
        return Text(''Connection active'');
      case ConnectionState.waiting:
        return Text(''Loading...'');
      case ConnectionState.done:
        if (snapshot.hasData) {
          return Text(snapshot.data!);
        } else {
          return Text(''No data available'');
        }
    }
  },
)', options = '["비동기 작업이 완료되면 ''Loading...''이라는 텍스트가 계속 표시됩니다.", "비동기 작업 중 오류 발생 시 에러 메시지가 화면에 표시됩니다.", "비동기 작업이 성공적으로 완료되어도 화면에는 항상 ''No data available''이 표시됩니다.", "비동기 작업이 완료되지 않은 동안에는 ''Awaiting connection...''이라는 텍스트만 표시됩니다."]', answer_key = '{"correct":1}' WHERE id = 800 AND md5(content) = 'a6c0bd2bab7043c8ff07be8b6340c6e0';
UPDATE question_bank SET content = '다음은 Kubernetes에서 Pod를 정의하는 YAML 파일입니다. 이 설정의 문제점은 무엇인가요?

apiVersion: v1
kind: Pod
metadata:
  name: web
spec:
  containers:
  - name: app
    image: nginx:1.27
    resources:
      requests:
        memory: "2Gi"
      limits:
        memory: "1Gi"', options = '["memory limits(1Gi)가 requests(2Gi)보다 작아 Pod 생성이 거부된다.", "restartPolicy를 지정하지 않으면 컨테이너가 종료 후 다시 시작되지 않는다.", "containers 항목이 하나뿐이라 Pod 스펙 검증을 통과하지 못한다.", "이미지에 태그를 명시하면 Pod를 생성할 수 없다."]', answer_key = '{"correct":0}' WHERE id = 802 AND md5(content) = '017070ae34102463d9bd761e769d4671';
UPDATE question_bank SET content = 'Docker 빌드에서 레이어 캐시를 효과적으로 활용하는 방법으로 옳은 것은?', options = '["자주 바뀌는 소스 코드의 COPY 단계를 의존성 설치 단계 뒤에 배치한다.", "COPY . . 명령을 Dockerfile의 첫 단계에 두어 모든 파일을 먼저 복사해 둔다.", "매 빌드마다 --no-cache 옵션을 사용해 캐시를 새로 만든다.", "베이스 이미지 태그를 빌드마다 변경해 캐시 충돌을 예방한다."]', answer_key = '{"correct":0}' WHERE id = 805 AND md5(content) = 'b4a855e1c25bfc2142a8d9df2d61df1a';
UPDATE question_bank SET content = 'CI/CD 파이프라인에서, 새 버전을 소수의 사용자 트래픽에만 먼저 노출해 지표를 관찰하고 문제가 없으면 점차 비율을 늘려 가는 배포 전략은?', options = '["blue-green 배포", "canary 배포", "rolling 배포", "big-bang 배포"]', answer_key = '{"correct":1}' WHERE id = 808 AND md5(content) = 'b9ca8dda37b6fbe5b2606269e15d8b31';
UPDATE question_bank SET content = 'Prometheus 메트릭 타입 중, 값이 증가만 하고 감소하지 않는(프로세스 재시작 시 0으로 리셋될 수는 있음) 누적 값을 표현하는 타입은?', options = '["Counter", "Gauge", "Histogram", "Summary"]', answer_key = '{"correct":0}' WHERE id = 811 AND md5(content) = '2fcf749836371d7d868cf9c319e610f6';
UPDATE question_bank SET content = 'Kubernetes에서 컨테이너가 요청을 받을 준비가 되었는지 판단하여, 준비되지 않은 동안 해당 Pod를 Service 엔드포인트에서 제외하는 프로브 유형은?', options = '["livenessProbe", "readinessProbe", "startupProbe", "execProbe"]', answer_key = '{"correct":1}' WHERE id = 815 AND md5(content) = 'f85dffe51562c83663834e00c806d064';
UPDATE question_bank SET content = 'Dockerfile에서 빌드 컨텍스트의 파일을 이미지로 복사할 때, 원격 URL 다운로드나 압축 자동 해제 같은 부가 동작 없이 단순 복사만 수행해 빌드의 예측 가능성 측면에서 권장되는 명령어는?', options = '["ADD", "COPY", "RUN", "SHELL"]', answer_key = '{"correct":1}' WHERE id = 816 AND md5(content) = '4357b55cade2c03c1252355c39526d7b';
UPDATE question_bank SET content = '다음은 Kubernetes에서 Service를 정의하는 YAML 파일입니다. Deployment의 Pod 라벨은 app: web 입니다. 이 설정의 문제점은 무엇인가요?

apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web-api
  ports:
  - port: 80
    targetPort: 8080', options = '["selector가 Pod 라벨(app: web)과 일치하지 않아 엔드포인트가 생성되지 않고 트래픽이 전달되지 않는다.", "targetPort는 port와 반드시 같은 값이어야 하므로 8080을 지정하면 Service 생성이 거부된다.", "type 필드를 생략하면 Service가 생성되지 않는다.", "port 80은 시스템 예약 포트라 Service에서 사용할 수 없다."]', answer_key = '{"correct":0}' WHERE id = 817 AND md5(content) = '5ad2eaf854ba47b1233c7f9a8132c382';
UPDATE question_bank SET content = 'Docker 컨테이너에서 볼륨(volume)과 바인드 마운트(bind mount)의 가장 중요한 차이는 무엇인가?', options = '["볼륨은 Docker가 관리하는 저장 영역에 데이터를 두고, 바인드 마운트는 호스트의 특정 경로를 직접 지정해 연결한다.", "볼륨은 컨테이너 삭제 시 항상 함께 삭제되지만, 바인드 마운트는 컨테이너와 무관하게 데이터가 남는다.", "바인드 마운트는 읽기 전용으로만 사용할 수 있고, 볼륨은 읽기와 쓰기가 모두 가능하다.", "볼륨은 리눅스 호스트에서만 동작하고, 바인드 마운트는 모든 운영체제에서 동작한다."]', answer_key = '{"correct":0}' WHERE id = 819 AND md5(content) = 'f6a8cc055716ec8b0dcb13f9762f944b';
UPDATE question_bank SET content = 'Kubernetes에서 readinessProbe를 사용하기에 가장 적절한 시나리오는?', options = '["컨테이너가 응답 불능(교착) 상태에 빠지면 kubelet이 자동으로 재시작하도록 하고 싶을 때.", "초기화를 마치고 준비가 끝난 Pod만 Service의 트래픽 대상에 포함시키고 싶을 때.", "Pod의 CPU 사용량에 따라 복제본 수를 자동으로 조절하고 싶을 때.", "컨테이너 기동이 오래 걸려 초기 기동 동안 다른 프로브 검사를 유예하고 싶을 때."]', answer_key = '{"correct":1}' WHERE id = 821 AND md5(content) = '7428d1e6ac5b80bf3b0da53f9bf72ac0';
UPDATE question_bank SET content = 'Kubernetes에서 Pod에 설정하는 startupProbe의 목적은 무엇인가요?', options = '["실행 중인 컨테이너가 교착 상태에 빠졌는지 주기적으로 확인해 재시작을 유발한다.", "서비스 준비 상태를 확인하고 요청을 받아들일 수 있는지 여부를 결정한다.", "초기화가 긴 컨테이너의 기동이 끝날 때까지 liveness·readiness 검사를 유예한다.", "리소스 사용량을 모니터링하여 과부하를 감지한다."]', answer_key = '{"correct":2}' WHERE id = 825 AND md5(content) = '3ac586e3f6e3ab3febf09bf8b81bebee';
UPDATE question_bank SET content = 'GitOps 방식으로 애플리케이션 배포를 관리할 때 실제로 고려해야 하는 한계(도전 과제)는 무엇인가요?', options = '["시크릿(비밀 값)을 Git에 평문으로 둘 수 없어 별도의 시크릿 관리 방안이 필요하다.", "커밋 이력이 배포 상태와 무관하게 저장되므로 이전 상태로의 롤백을 전혀 지원하지 않는다.", "선언형 매니페스트를 사용할 수 없어 모든 배포를 명령형 스크립트로 작성해야 한다.", "Argo CD나 Flux 같은 도구와 함께 사용할 수 없다."]', answer_key = '{"correct":0}' WHERE id = 826 AND md5(content) = 'f86831a42b630d62ca9f24612f9c4c03';
UPDATE question_bank SET content = 'Docker에서 바인드 마운트가 아닌 볼륨(volume)을 사용하기에 가장 적절한 시나리오는?', options = '["컨테이너가 삭제돼도 데이터베이스 데이터를 Docker가 관리하는 저장소에 영속적으로 보존해야 할 때.", "컨테이너 이미지의 크기를 줄여야 할 때.", "호스트의 소스 코드 디렉터리를 경로 그대로 컨테이너에 노출해 편집 내용을 즉시 반영해야 할 때.", "이미지 빌드 시 레이어 캐시를 최대한 활용해야 할 때."]', answer_key = '{"correct":0}' WHERE id = 830 AND md5(content) = '32925f1cc430c15064088282b8367554';
UPDATE question_bank SET content = 'Kubernetes에서 Pod의 livenessProbe와 readinessProbe를 구분하는 가장 중요한 차이는 무엇인가요?', options = '["livenessProbe 실패는 컨테이너 재시작을 유발하고, readinessProbe 실패는 Service 트래픽 대상에서 제외를 유발한다.", "livenessProbe는 Pod가 배치된 노드의 하드웨어 상태를 확인하고, readinessProbe는 클러스터 전체의 네트워크 상태를 확인한다.", "livenessProbe는 HTTP 방식만 지원하고, readinessProbe는 TCP 방식만 지원한다.", "readinessProbe가 실패하면 Pod가 즉시 삭제되고 새 Pod가 생성된다."]', answer_key = '{"correct":0}' WHERE id = 833 AND md5(content) = '280f9e0e119d271eafc6a5a2d68ca050';
UPDATE question_bank SET content = 'Kubernetes Deployment에서 매니페스트 파일을 수정하지 않고 명령 한 줄로 컨테이너 이미지를 교체해 롤링 업데이트를 트리거하는 명령어는?', options = '["kubectl apply -f deployment.yaml", "kubectl rollout status deployment/name", "kubectl set image deployment/name container=image:tag", "kubectl rollout undo deployment/name"]', answer_key = '{"correct":2}' WHERE id = 835 AND md5(content) = 'ddbad386c9fa2f1f300a8a8be5fdd081';
UPDATE question_bank SET content = 'CI/CD 파이프라인에서 Blue-Green 배포 전략의 주요 특징은 무엇인가?', options = '["하나의 환경 안에서 Pod를 순차적으로 교체하며 구버전과 신버전 Pod에 트래픽이 섞여 들어가게 한다.", "새로운 버전만 먼저 실행한 후 기존 버전 환경을 즉시 삭제해 롤백 경로를 없앤다.", "기존 애플리케이션을 완전히 중지한 다음 새로운 버전으로 대체한다.", "두 환경을 나란히 두고 새 환경 검증이 끝나면 트래픽을 한 번에 새 환경으로 전환한다."]', answer_key = '{"correct":3}' WHERE id = 836 AND md5(content) = 'f0ca854f6ab2e8090c288b169253e4d2';
UPDATE question_bank SET content = 'Docker 이미지 최적화를 위해 다음과 같은 Dockerfile을 사용합니다. 이 코드의 문제점은 무엇인가요?

FROM node:20
WORKDIR /app
COPY . .
RUN npm install
CMD ["node", "server.js"]', options = '["소스 전체를 먼저 복사한 뒤 의존성을 설치해, 코드가 한 줄만 바뀌어도 npm install 레이어 캐시가 무효화된다.", "WORKDIR 명령은 반드시 모든 COPY 뒤에 위치해야 하므로 이 순서로는 이미지 빌드 자체가 실패한다.", "CMD는 배열(exec) 형식을 사용할 수 없어 컨테이너가 시작되지 않는다.", "FROM에 태그를 지정하면 레이어 캐시를 사용할 수 없다."]', answer_key = '{"correct":0}' WHERE id = 842 AND md5(content) = '9e46986a6c8b01971a7b142a5bfac5af';
UPDATE question_bank SET content = 'COPY . . 으로 빌드 컨텍스트 전체를 복사하는 Dockerfile에서, .git 디렉터리와 node_modules 등 불필요한 파일이 이미지에 함께 들어가고 빌드 컨텍스트 전송도 느립니다. 가장 직접적인 해결 방법은 무엇인가요?', options = '[".dockerignore 파일에 해당 경로를 추가해 빌드 컨텍스트에서 제외한다.", "이미지 빌드 시마다 --no-cache 옵션으로 모든 레이어를 새로 만든다.", "CMD 명령을 ENTRYPOINT로 바꿔 실행 시점에 해당 파일을 무시하게 한다.", "빌드가 끝난 뒤 컨테이너 안에서 해당 파일을 삭제하는 RUN 명령을 Dockerfile 마지막에 추가한다."]', answer_key = '{"correct":0}' WHERE id = 846 AND md5(content) = '906687f95bf83ad5dd6d6e5118af1901';
UPDATE question_bank SET content = 'CI/CD 파이프라인에서 Blue-Green 배포 전략과 Canary 배포 전략은 어떻게 다른가요?', options = '["Blue-Green 배포는 새로운 버전의 서비스를 실행시키지 않고 기존 서비스만 제자리에서 업데이트한다.", "Canary 배포는 전체 트래픽을 단번에 새 서비스로 이동시킨다.", "Blue-Green 배포는 두 환경을 나란히 두고 검증 후 트래픽을 전환하며, Canary 배포는 일부 트래픽만 새 버전으로 보내 점진적으로 확대한다.", "Canary 배포는 트래픽 비율을 조절하지 않고 항상 절반씩 고정 분배하며, Blue-Green 배포는 Pod를 하나씩 순차 교체해 두 버전이 섞이는 것을 전제로 한다."]', answer_key = '{"correct":2}' WHERE id = 851 AND md5(content) = '7d1b693e2b56a6a0f01219e08c5822ae';
UPDATE question_bank SET content = 'Dockerfile로 이미지를 빌드할 때, 다음 중 이미지 크기 최적화에 실제로 도움이 되는 방법은?', options = '["RUN 명령을 최대한 여러 개로 쪼개 레이어 수를 늘린다.", "이미지 빌드 시마다 --no-cache 옵션으로 항상 새로 빌드한다.", "볼륨 마운트를 사용하여 실행 시점의 변경 사항을 반영한다.", ".dockerignore 파일로 빌드 컨텍스트의 불필요한 파일을 배제한다."]', answer_key = '{"correct":3}' WHERE id = 852 AND md5(content) = '3bb2064a819dcf59cb56dbfcda872a03';
UPDATE question_bank SET content = 'Docker 이미지 빌드 시 다음 명령어가 어떤 역할을 하는지 고르세요.

docker build -t myapp:1.0 .', options = '["myapp:1.0 이미지를 컨테이너로 실행한다.", "현재 디렉터리를 빌드 컨텍스트로 삼아 Dockerfile로 이미지를 빌드하고 myapp:1.0 태그를 붙인다.", "myapp:1.0 이미지를 원격 레지스트리에 업로드한다.", "로컬의 기존 myapp 이미지와 파일을 비교해 달라진 파일만 담은 증분 이미지를 별도로 생성한다."]', answer_key = '{"correct":1}' WHERE id = 858 AND md5(content) = '824423ae743913f475550e29d0e8ff52';
UPDATE question_bank SET content = '다음 중 Docker 이미지 크기를 줄이는 데 효과적인 방법은 무엇인가요?', options = '["컨테이너를 루트 권한으로 실행한다", "빌드 도구와 캐시 파일을 디버깅 편의를 위해 최종 이미지에 그대로 남겨 둔다", "멀티 스테이지 빌드로 빌드 단계의 산출물만 최종 이미지에 복사한다", "실행 중인 도커 인스턴스 수를 늘린다"]', answer_key = '{"correct":2}' WHERE id = 861 AND md5(content) = 'dd04f067524adcbf92f148628787a354';
UPDATE question_bank SET content = 'CI/CD 파이프라인에서 Blue-Green 배포 전략의 장점으로 옳은 것은 무엇인가요?', options = '["두 환경을 동시에 운영할 필요가 없어 인프라 비용이 절감된다", "이전 버전 환경이 그대로 남아 있어 트래픽 전환만으로 빠르게 롤백할 수 있다", "데이터베이스 스키마 동기화 문제가 자동으로 해결된다", "구버전과 신버전 파드가 섞인 채 순차 교체되므로 추가 자원이 거의 들지 않는다"]', answer_key = '{"correct":1}' WHERE id = 863 AND md5(content) = 'f65113ecf4e1ab26d0585961598c7a4e';
UPDATE question_bank SET content = 'Kubernetes의 HPA(Horizontal Pod Autoscaler)에 대한 설명으로 옳은 것은 무엇인가요?', options = '["HPA는 metrics server 없이도 기본적으로 CPU 사용률 지표를 수집한다", "HPA는 파드 수 대신 개별 파드의 CPU·메모리 요청량(requests)을 조정한다", "HPA는 minReplicas 설정과 무관하게 파드를 0개까지 자동으로 축소한다", "HPA는 autoscaling/v2부터 CPU 외에 메모리·커스텀 메트릭 기준으로도 스케일링할 수 있다"]', answer_key = '{"correct":3}' WHERE id = 864 AND md5(content) = 'ce5e961b1bcce0247607dc4cc573dcef';
UPDATE question_bank SET content = '동일한 운영 환경 두 벌을 준비해 두고, 새 버전 검증이 끝나면 라우터에서 트래픽을 한 번에 새 환경으로 전환하는 배포 전략은 무엇인가요?', options = '["Canary Release", "Blue-Green Deployment", "Rolling Update", "Recreate Deployment"]', answer_key = '{"correct":1}' WHERE id = 865 AND md5(content) = '945f15ea351fa4a0228e21afdc0f88f1';
UPDATE question_bank SET content = 'Prometheus의 메트릭 타입에 대한 설명으로 옳은 것은 무엇인가?', options = '["Gauge는 한 번 기록되면 감소할 수 없는 누적 측정값이다", "Histogram은 관측된 원시 값을 모두 저장해 서버가 임의의 분위수를 정확히 계산한다", "Counter는 감소하지 않으며, 프로세스 재시작 시 0으로 리셋될 수 있는 누적 값이다", "Summary가 클라이언트에서 계산한 분위수는 여러 인스턴스에 걸쳐 평균 내어 합산해도 유효하다"]', answer_key = '{"correct":2}' WHERE id = 867 AND md5(content) = '295f2eae45d00d265d254e21ab189299';
UPDATE question_bank SET content = 'Kubernetes의 Pod와 Deployment 간의 주요 차이점은?', options = '["Pod는 일회성 배치 작업 전용이고, 지속 서비스는 Deployment가 컨테이너를 직접 실행한다", "Deployment는 ReplicaSet을 통해 Pod 집합의 선언적 배포·스케일링을 관리하고, Pod는 하나 이상의 컨테이너를 묶은 최소 배포 단위다", "Pod는 복수의 컨테이너를 포함할 수 있지만, Deployment는 단일 컨테이너 Pod만 관리할 수 있다", "Deployment를 삭제해도 그것이 생성한 Pod들은 기본 설정에서 계속 실행된다"]', answer_key = '{"correct":1}' WHERE id = 869 AND md5(content) = 'fbc9d661a00ad9bc3eaa458babdc2b8d';
UPDATE question_bank SET content = '다음 중 시계열 메트릭을 pull 방식으로 수집·저장하고 PromQL로 질의할 수 있는 관측성 도구는 무엇인가요?', options = '["Prometheus", "Grafana", "Kibana", "Jenkins"]', answer_key = '{"correct":0}' WHERE id = 870 AND md5(content) = '0ab078a06a4a79e35f6527f97b7e290f';
UPDATE question_bank SET content = '다음 Dockerfile에서 마지막 줄 CMD ["npm", "start"]의 역할은 무엇인가?

FROM node:14-alpine
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
CMD ["npm", "start"]', options = '["이미지 빌드 시점에 npm start를 실행해 그 결과를 이미지에 굽는다", "컨테이너 시작 시 실행할 기본 명령을 지정하며, docker run에서 다른 명령을 주면 대체된다", "빌드 결과 이미지에 npm 의존성 패키지를 설치한다", "컨테이너가 종료될 때 실행할 정리 명령을 등록한다"]', answer_key = '{"correct":1}' WHERE id = 875 AND md5(content) = 'a522525cd7f10abc392a7c20a256996d';
UPDATE question_bank SET content = '다음 YAML 파일은 Kubernetes HorizontalPodAutoscaler를 정의합니다. 문제가 될 부분은 무엇일까요?

apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp-deployment
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 50', options = '["minReplicas(2)가 maxReplicas(6)보다 커서 스케일링 범위가 유효하지 않습니다.", "targetCPUUtilizationPercentage는 autoscaling/v1 전용 필드라서, v2beta2에서는 metrics 배열로 지정해야 합니다.", "spec 아래에는 scaleTargetRef를 둘 수 없으므로 제거해야 합니다.", "CPU 사용률은 HPA가 지원하지 않는 메트릭 종류입니다."]', answer_key = '{"correct":1}' WHERE id = 880 AND md5(content) = 'd2ac780a2082e6c7226c15e593b61a8e';
UPDATE question_bank SET content = '다음 Dockerfile에서 package.json만 먼저 복사해 npm install을 실행한 뒤, 그 다음에 나머지 소스 코드를 복사하는 이유는 무엇인가?

FROM node:14-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "start"]', options = '["최종 이미지 크기가 절반 이하로 줄어들기 때문", "package.json을 나중에 복사하면 npm install이 아예 실행되지 않기 때문", "소스 코드만 변경된 경우 npm install 레이어의 캐시를 재사용해 빌드 시간을 줄이기 위해", "COPY . . 명령이 node_modules 디렉터리를 덮어쓰는 것을 방지하기 위해"]', answer_key = '{"correct":2}' WHERE id = 881 AND md5(content) = '020c2729c404cd49aec2401c2ef525e1';
UPDATE question_bank SET content = '다음 Docker Compose 파일이 정의하는 구성으로 옳은 것은 무엇인가?

version: ''3''
services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - .:/code
    environment:
      - DATABASE_HOST=db
  db:
    image: postgres', options = '["web 하나의 서비스만 정의하며 db는 외부 클러스터에 대한 참조다", "web 컨테이너와 db 컨테이너를 병합해 하나의 컨테이너에서 단일 프로세스로 실행하도록 정의한다", "postgres 이미지를 베이스 이미지로 삼아 web 이미지를 다시 빌드하도록 정의한다", "현재 디렉터리에서 빌드하는 web 서비스와 postgres 이미지를 사용하는 db 서비스, 두 개의 서비스를 정의한다"]', answer_key = '{"correct":3}' WHERE id = 884 AND md5(content) = 'ae2483a999135ffa62ae319c5b64514f';
UPDATE question_bank SET content = '다음 Kubernetes YAML 파일은 ReplicaSet을 정의합니다. 이 매니페스트를 적용(kubectl apply)하면 어떻게 되나요?

apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: example-replicaset
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example-app
  template:
    metadata:
      labels:
        app: another-app
    spec:
      containers:
      - name: example-container
        image: nginx:latest', options = '["ReplicaSet이 생성되고 ''another-app'' 라벨을 가진 Pod 3개가 정상적으로 만들어집니다.", "selector가 template의 라벨과 일치하지 않아 API 서버가 생성 요청 자체를 거부합니다.", "ReplicaSet이 생성되고 ''example-app'' 라벨을 가진 Pod 3개가 만들어집니다.", "ReplicaSet은 생성되지만 라벨은 무시하고 이름 기준으로 Pod를 관리합니다."]', answer_key = '{"correct":1}' WHERE id = 886 AND md5(content) = '92250b5164d0c8856d26e5d51fa11c46';
UPDATE question_bank SET content = '다음 Dockerfile의 빌드 캐시 동작에 대한 설명으로 옳은 것은?

FROM node:14-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "start"]', options = '["소스 코드가 한 줄이라도 바뀌면 npm install 레이어까지 항상 다시 실행된다", "package.json이 변경되지 않는 한 npm install 레이어는 캐시에서 재사용된다", "컨테이너를 시작할 때마다 모든 노드 모듈이 다시 설치된다", "COPY . . 명령은 캐시를 사용할 수 없어 매 빌드마다 베이스 이미지 전체를 새로 내려받는다"]', answer_key = '{"correct":1}' WHERE id = 887 AND md5(content) = '04c5ef363ceb7cd1c4d259d852df6209';
UPDATE question_bank SET content = '서버가 클라이언트가 제시한 JWT를 위변조되지 않았다고 신뢰할 수 있는 핵심 근거는 무엇인가요?', options = '["페이로드가 암호화되어 있어 발급자 외에는 아무도 내용을 읽을 수 없기 때문", "비밀키(또는 개인키)로 생성된 서명을 검증해 토큰의 위변조 여부를 확인할 수 있기 때문", "JWT는 프로토콜상 HTTPS로만 전송되도록 강제되어 있기 때문", "서버가 발급한 모든 토큰을 데이터베이스에 저장해 두고 매 요청마다 원본과 대조하기 때문"]', answer_key = '{"correct":1}' WHERE id = 904 AND md5(content) = '204453b813a5376fd8bf634c0c03db6a';
UPDATE question_bank SET content = '프론트엔드-백엔드 통신에서 XSS 공격으로 주입된 스크립트가 인증 자격 증명을 직접 읽어 탈취하지 못하도록 하는 저장 방식은 무엇인가요?', options = '["세션 식별자를 HttpOnly 속성이 설정된 쿠키에 담아 스크립트에서 읽을 수 없게 한다.", "JWT를 localStorage에 저장하고 매 요청마다 자바스크립트로 읽어 헤더에 담는다.", "토큰을 URL 쿼리 스트링에 붙여 페이지 간에 전달한다.", "HttpOnly 없이 document.cookie로 접근 가능한 쿠키에 토큰을 저장하고 스크립트로 관리한다."]', answer_key = '{"correct":0}' WHERE id = 912 AND md5(content) = '0fa9fd839d28367dd36c985b00c432b3';
UPDATE question_bank SET content = '프론트-백 연동에서 게이트웨이(프록시) 서버가 업스트림 백엔드 서버의 응답을 제한 시간 안에 받지 못했을 때, 클라이언트에 반환하는 표준 HTTP 상태 코드는 무엇인가?', options = '["408 Request Timeout", "504 Gateway Timeout", "502 Bad Gateway", "500 Internal Server Error"]', answer_key = '{"correct":1}' WHERE id = 920 AND md5(content) = '7ee7cef95cca225d5bd32c874da86874';
UPDATE question_bank SET content = '다음 JWT 전달 방식 중 토큰이 서버 접근 로그와 브라우저 방문 기록, Referer 헤더에 그대로 남아 유출 위험이 가장 큰 것은 무엇인가?', options = '["Authorization 헤더에 담아 전송", "HttpOnly 쿠키에 담아 전송", "URL 쿼리 스트링에 담아 전송", "POST 요청 본문에 담아 전송"]', answer_key = '{"correct":2}' WHERE id = 926 AND md5(content) = '76728b6570d2b820b9a958e946ed5039';
UPDATE question_bank SET content = '다음 클라이언트-서버 인증 설계 중 명백히 안전하지 않은 것은 무엇인가요?', options = '["HttpOnly 쿠키 기반의 서버측 세션을 사용한다.", "만료 시간이 짧은 액세스 토큰과 리프레시 토큰을 함께 사용한다.", "사용자 암호를 브라우저에 평문으로 저장해 두고 매 API 요청에 함께 전송한다.", "OAuth 2.0 인가 코드 플로우로 외부 신원 제공자에 인증을 위임한다."]', answer_key = '{"correct":2}' WHERE id = 933 AND md5(content) = 'b7d43fd8aa5831ae29f5b7f31cd72734';
UPDATE question_bank SET content = '서로 다른 수천 명의 사용자가 몇 분간 내용이 바뀌지 않는 같은 인기 게시글 목록 API를 반복 호출하고 있다. 데이터베이스로 가는 조회 요청 수 자체를 줄이는 데 가장 직접적인 기법은 무엇인가요?', options = '["각 사용자 브라우저에 적용되는 클라이언트 측 캐싱", "응답 결과를 Redis 등 서버 사이드 캐시에 저장해 두고 DB 조회 없이 반환", "게시글 테이블에 데이터베이스 인덱스 추가", "모든 요청에 대한 처리 로직 단순화"]', answer_key = '{"correct":1}' WHERE id = 936 AND md5(content) = 'e4ceeebdf04eec98b7d2af30f35a4ad0';
UPDATE question_bank SET content = '전형적인 서버측 세션 방식의 웹 애플리케이션에서, 브라우저 쿠키에 담기는 것은 무엇인가?', options = '["세션 식별자(세션 ID)만 담기고, 실제 세션 데이터는 서버측 저장소(메모리·Redis·DB 등)에 보관된다.", "직렬화된 세션 데이터 전체가 쿠키에 담긴다.", "사용자 암호의 해시값이 담긴다.", "서버가 세션 서명에 쓰는 비밀키가 함께 담긴다."]', answer_key = '{"correct":0}' WHERE id = 937 AND md5(content) = 'd9be803797752baf78dec7de89cfde1b';
UPDATE question_bank SET content = '리프레시 토큰을 발급받아 둔 SPA에서, 액세스 토큰이 만료되었을 때 사용자의 재로그인 없이 인증 상태를 이어 가려면 프론트엔드는 어떻게 처리해야 하는가?', options = '["무조건 로그아웃 처리하고 새로 로그인하라는 메시지를 띄운다", "리프레시 토큰으로 새 액세스 토큰을 발급받은 뒤 실패했던 요청을 재시도한다", "만료된 액세스 토큰을 그대로 계속 전송해 서버가 자동으로 유효기간을 연장하게 한다", "액세스 토큰의 exp 클레임을 프론트엔드에서 미래 시각으로 수정해 다시 사용한다"]', answer_key = '{"correct":1}' WHERE id = 962 AND md5(content) = '3a204f71cb9601c0686f81e0230e4476';
UPDATE question_bank SET content = '프론트엔드에서 유효한 인증 정보 없이 로그인 필수 API를 호출했을 때, 서버가 반환하는 표준 HTTP 상태 코드를 선택하세요.', options = '["200 OK", "302 Found", "401 Unauthorized", "500 Internal Server Error"]', answer_key = '{"correct":2}' WHERE id = 963 AND md5(content) = '22bcc9a03c96bd65a9e63f1ba03e2140';
UPDATE question_bank SET content = '다음 JavaScript 코드는 프론트엔드에서 API 호출을 수행합니다.

fetch(''/api/user'', { method: ''GET'' })
.then(response => response.json())
.catch(error => console.log(''Error:'', error));

이 코드의 문제점은 무엇인가요?', options = '["네트워크 장애가 발생해도 catch 블록이 실행되지 않아 오류가 유실된다.", "response.ok 를 확인하지 않아 4xx/5xx 오류 응답도 성공 경로로 처리된다.", "fetch 는 method 옵션으로 GET 을 지정할 수 없다.", "response.json() 은 동기 함수라서 then 콜백 안에서 호출할 수 없다."]', answer_key = '{"correct":1}' WHERE id = 973 AND md5(content) = '40783d95d05416b528702256cfa43e99';
UPDATE question_bank SET content = '다음 코드 스니펫은 MySQL에서 데이터베이스 트랜잭션을 처리하는데 사용됩니다.

@Transactional
public void updateUserData(User user) {
    user.setLastLogin(new Date());
    userRepository.save(user);
}

이 코드의 동작으로 가장 정확한 설명은 무엇인가요?', options = '["트랜잭션 안에서 사용자의 마지막 로그인 시각을 갱신해 저장합니다.", "사용자의 모든 데이터를 삭제합니다.", "런타임 예외가 발생해도 변경 사항이 롤백되지 않고 그대로 커밋됩니다.", "HTTP 요청을 직접 수신해 파싱하고 처리합니다."]', answer_key = '{"correct":0}' WHERE id = 975 AND md5(content) = 'aca4f176cc9899d0b7bb5d63687e4466';
UPDATE question_bank SET content = '다음 SQL 은 수백만 행이 있는 PostgreSQL users 테이블에서 자주 실행되는데, 실행 계획(EXPLAIN)에 Seq Scan 이 나타나며 느립니다.

SELECT * FROM users WHERE email = ''user@example.com'' AND status = ''active'';

조회 성능을 개선하는 가장 직접적인 방법은 무엇인가요?', options = '["SELECT * 를 SELECT email 로 바꿔 반환 컬럼 수를 줄인다.", "WHERE 절에서 status 조건을 제거해 비교 횟수를 줄인다.", "email(과 status) 컬럼에 인덱스를 생성해 인덱스 스캔이 가능하게 한다.", "테이블을 비정규화해 users 데이터를 여러 테이블에 복제한다."]', answer_key = '{"correct":2}' WHERE id = 976 AND md5(content) = 'a658c72a3bc16772c5de86dee1199f03';
UPDATE question_bank SET content = '다음 코드는 서버에서 클라이언트에게 데이터를 반환하는 API 핸들러입니다.

@GetMapping("/users")
public List<User> getUsers() {
    return userRepository.findAll();
}

userRepository.findAll() 메서드는 모든 사용자 정보를 가져옵니다.

이 API 의 동작으로 옳은 것은 무엇인가요?', options = '["API 는 POST 요청도 이 핸들러로 받아 동일하게 사용자 목록을 반환합니다.", "GET 요청이 성공해도 응답 본문 없이 상태 코드만 반환됩니다.", "GET 요청은 항상 500 Internal Server Error 를 반환합니다.", "GET 요청이 성공하면 200 OK 와 함께 사용자 목록이 반환됩니다."]', answer_key = '{"correct":3}' WHERE id = 978 AND md5(content) = 'bdb7fe1e8545f22f386654d32446899b';
UPDATE question_bank SET content = '다음은 배포 환경에서 헬스 체크를 수행하는 코드 스니펫입니다.

@GetMapping("/actuator/health")
public Health health() {
    return new Health.Builder()
            .up()
            .withDetail("database", "connected")
            .build();
}

이 구현의 문제점은 무엇인가요?', options = '["이 엔드포인트는 항상 ''DOWN'' 상태를 반환한다.", "실제 데이터베이스 연결을 검사하지 않고 ''connected'' 를 하드코딩해 반환한다.", "Health 객체는 JSON 으로 직렬화될 수 없어 호출이 항상 실패한다.", "withDetail 로 추가한 세부 정보는 응답 본문에서 항상 제외된다."]', answer_key = '{"correct":1}' WHERE id = 985 AND md5(content) = '230f42fbb04af38d1c59541dce668e96';
UPDATE question_bank SET content = '다음은 사용자 로그인 정보를 데이터베이스에서 검색하는 SQL 쿼리입니다.

SELECT * FROM users WHERE username = ? AND password = PASSWORD(?)

WHERE 절의 비밀번호 필드는 해시 함수로 처리됩니다.

이 쿼리의 동작으로 가장 정확한 설명은 무엇인가요?', options = '["쿼리 자체가 인증된 사용자의 로그인 세션을 생성한다.", "비밀번호가 일치하지 않아도 username 이 일치하면 해당 사용자의 행을 반환한다.", "입력 비밀번호의 해시가 저장된 값과 일치하는 행만 반환해 자격 증명을 확인한다.", "저장된 비밀번호 해시를 평문 암호로 복호화해 반환한다."]', answer_key = '{"correct":2}' WHERE id = 987 AND md5(content) = '4689c468883a72b0ddaa33f386dc61fc';
UPDATE question_bank SET content = '다음 코드는 사용자의 프로필 정보를 가져오는 API 인데, 사용자가 없으면 userRepository.findByUserId() 가 null 을 반환해 modelMapper.map() 에서 예외가 발생합니다.

@GetMapping("/profile")
public UserDTO getUserProfile(@RequestParam String userId) {
    User user = userRepository.findByUserId(userId); // 없으면 null 반환
    return modelMapper.map(user, UserDTO.class);
}

사용자가 없을 때 404 Not Found 를 반환하도록 수정하는 가장 적절한 방법은 무엇인가요?', options = '["NullPointerException 을 try-catch 로 잡은 뒤 null 을 그대로 반환한다.", "메서드 시그니처에 throws NullPointerException 을 선언해 예외를 컨테이너로 전파한다.", "user == null 이면 @ResponseStatus(HttpStatus.NOT_FOUND) 가 붙은 ResourceNotFoundException 을 던진다.", "컨트롤러 메서드에 @ResponseStatus(HttpStatus.NOT_FOUND) 를 직접 붙여 응답 상태를 지정한다."]', answer_key = '{"correct":2}' WHERE id = 988 AND md5(content) = '137196cf482c273634eca047895ae5d2';
UPDATE question_bank SET content = '다음은 프론트엔드에서 REST API로 데이터를 요청하는 코드입니다. 

fetch(`/api/products/${productId}`, {
  method: ''GET'',
  headers: {
    ''Authorization'': `Bearer ${token}`
  }
})
.then(response => response.json())

이 코드에 대한 설명으로 옳은 것은 무엇인가요?', options = '["네트워크 오류가 발생하면 이 코드가 오류를 잡아 사용자에게 알린다.", "응답이 4xx/5xx 상태 코드이면 fetch 프라미스가 자동으로 reject 된다.", "Authorization 헤더에 Bearer 토큰을 담아 요청을 전송한다.", "토큰이 만료되면 fetch 가 자동으로 토큰을 갱신한 뒤 재요청한다."]', answer_key = '{"correct":2}' WHERE id = 990 AND md5(content) = '4f68c031496ab3694f9e068014531ecf';
UPDATE question_bank SET content = 'WSGI와 ASGI의 주요 차이점은 무엇인가?', options = '["WSGI는 동기 호출뿐 아니라 WebSocket 같은 장수명 연결도 표준 스펙 차원에서 기본 지원하므로, ASGI와 기능상 차이가 없다.", "ASGI는 이름과 달리 실제로는 WSGI와 동일하게 동기 방식의 호출만 지원하고 비동기 프로토콜은 다루지 못한다.", "WSGI는 HTTP 요청 응답 프로토콜을 사용하며, ASGI는 HTTP 및 WebSocket 연결을 동시에 처리할 수 있다.", "ASGI는 WSGI와 마찬가지로 HTTP 요청·응답 프로토콜만 지원하며 WebSocket 같은 장수명 연결은 다루지 못한다."]', answer_key = '{"correct":2}' WHERE id = 1001 AND md5(content) = '16be21c30acd55fd79f122b9b2647471';
UPDATE question_bank SET content = '다음 코드에서 두 번째 for 루프는 몇 번의 추가 쿼리를 실행하는가?

qs = Order.objects.prefetch_related(''items'').filter(status=''paid'')

for order in qs.iterator():
    pass

for order in qs:
    print(order.items.count())', options = '["iterator()로 이미 한 번 순회했으므로 그 결과가 내부 결과 캐시에 자동으로 남아, 두 번째 루프는 추가 쿼리 없이 캐시된 결과만 그대로 재사용한다고 오해하기 쉽다. 실제로는 iterator가 캐시를 아예 만들지 않는다.", "iterator()는 내부 결과 캐시를 채우지 않으므로 두 번째 for 루프는 쿼리셋을 처음부터 다시 평가한다. 이때 주문 목록 조회 1번과 prefetch_related에 의한 items 일괄 조회 1번, 총 2번의 추가 쿼리가 실행되며, order.items.count()는 채워진 prefetch 캐시의 길이를 반환하므로 건당 추가 쿼리는 없다.", "iterator()를 한 번이라도 호출한 쿼리셋은 그 뒤로 완전히 재사용이 금지되어 두 번째 순회를 시도하는 시점에 곧바로 예외가 발생한다고 잘못 알려져 있다. 실제로는 재평가가 일어날 뿐 예외는 없다.", "prefetch_related는 iterator() 사용 여부와 완전히 무관하게 항상 내부적으로 결과를 캐시해두므로, 두 번째 순회에서도 캐시된 prefetch 결과가 재사용되어 추가 쿼리가 전혀 발생하지 않는다고 오해하기 쉽다."]', answer_key = '{"correct":1}' WHERE id = 1093 AND md5(content) = 'b5b900da9496d3aaeb1e923f62ae45b9';
UPDATE question_bank SET content = 'Order 모델은 nullable ForeignKey인 coupon(Coupon, null=True)을 갖고, Coupon은 여러 Order와 연결되는 역참조 관계다. 다음 코드에서 문제가 되는 부분은?

orders = Order.objects.select_related(''coupon'', ''coupon__campaigns'')

for order in orders:
    print(order.coupon.code if order.coupon else ''no coupon'')
    for campaign in order.coupon.campaigns.all() if order.coupon else []:
        print(campaign.name)', options = '["select_related(''coupon'')는 coupon 필드가 null인 주문을 만나는 순간 예외를 던져버려서 이 쿼리 자체가 실행 도중 실패한다고 오해하기 쉽다. 실제로는 nullable FK에도 select_related가 정상적으로 동작한다.", "coupon__campaigns가 역참조(reverse FK) 또는 M2M 관계라면 select_related가 따라갈 수 없는 경로이므로 쿼리셋 평가 시점에 FieldError(''Invalid field name(s) given in select_related'')가 발생한다. 이런 관계는 prefetch_related(''coupon__campaigns'')로 가져와야 한다.", "coupon이 nullable FK이니 select_related가 항상 INNER JOIN을 강제해서 coupon이 없는 주문은 결과 집합에서 자동으로 완전히 제외되고 반환되지 않는다고 잘못 알려져 있다. 실제로는 LEFT OUTER JOIN을 사용한다.", "select_related에 필드를 여러 개 한꺼번에 넘기면 두 번째 인자부터는 조용히 무시되어 coupon만 조인되고 campaigns는 애초에 요청조차 되지 않는다고 오해하기 쉽다. 실제로는 두 필드 모두 처리를 시도한다."]', answer_key = '{"correct":1}' WHERE id = 1098 AND md5(content) = '2774f115d7a678ed7b963b7ca4a326dc';
UPDATE question_bank SET content = 'TypeScript에서 ''unknown'' 타입은 어떤 용도로 사용됩니까?', options = '["타입 검사 없이 어떤 타입의 변수에도 바로 할당할 수 있습니다.", "any 타입과 동일하게 모든 유형에 대해 호환됩니다.", "타입을 확정할 수 없는 값을 담고, 사용 전에 타입 검사를 강제하고 싶을 때 사용합니다.", "never 타입과 마찬가지로 존재할 수 없는 상태를 표현하는 데 사용됩니다."]', answer_key = '{"correct":2}' WHERE id = 1103 AND md5(content) = '74d975a29965455360415c082f040e8f';
UPDATE question_bank SET content = 'Node.js에서 process.nextTick()에 등록한 콜백은 언제 실행되는가?', options = '["setTimeout(fn, 0)으로 등록한 타이머 콜백보다 나중에 실행된다.", "다음 이벤트 루프 반복이 시작될 때 타이머 단계에서 다른 매크로태스크와 함께 실행된다.", "현재 실행 중인 작업이 끝난 직후, 이벤트 루프가 다음 단계로 진행하기 전에 실행된다.", "등록하는 즉시 그 자리에서 동기적으로 실행된다."]', answer_key = '{"correct":2}' WHERE id = 1106 AND md5(content) = '581c3c2324482686511f71986e00e0eb';
UPDATE question_bank SET content = 'TypeScript에서 하나의 파일이 ''모듈(module)''로 취급되는 조건은 무엇인가?', options = '["확장자가 .ts인 파일은 내용과 무관하게 항상 독립 모듈로 컴파일된다.", "namespace 키워드로 감싸야만 모듈로 취급된다.", "파일 최상위에 import 또는 export 문이 하나라도 있으면 모듈로 취급된다.", "tsconfig.json이 있는 디렉터리 안의 파일만 모듈이 된다."]', answer_key = '{"correct":2}' WHERE id = 1107 AND md5(content) = 'e977c88fdc4fdf5659cafe236764c168';
UPDATE question_bank SET content = 'Node.js의 이벤트 루프에서 `setTimeout(fn, 0)`은 어떻게 동작하나?', options = '["함수 fn이 현재 실행 중인 동기 코드보다 먼저 즉시 실행된다.", "타이머 단계(timers phase)에서 실행되도록 매크로태스크로 예약된다.", "마이크로태스크 큐에 들어가 콜 스택이 비면 프로미스 콜백보다 먼저 실행된다.", "지연이 0이므로 이벤트 루프를 거치지 않고 동기적으로 호출된다."]', answer_key = '{"correct":1}' WHERE id = 1111 AND md5(content) = 'b51c80a6bd994aeb4e4622c766008ee0';
UPDATE question_bank SET content = '다음 코드에서 `User`의 `id`와 `name` 속성만 갖는 타입을 만들기 위해 빈칸에 들어갈 TypeScript 유틸리티 타입은 무엇인가?
interface User { id: number; name: string; email: string; }
type UserSummary = ____<User, ''id'' | ''name''>;', options = '["Partial", "Pick", "Record", "Omit"]', answer_key = '{"correct":1}' WHERE id = 1112 AND md5(content) = '33722aedc596ab3a637be58846a09ecf';
UPDATE question_bank SET content = 'TypeScript에서 `unknown`과 `any`의 주요 차이는 무엇인가?', options = '["`unknown` 타입 값은 타입 좁히기 없이도 임의의 프로퍼티 접근과 메서드 호출이 허용된다.", "`any`는 타입 검사를 우회해 어떤 연산도 허용하지만, `unknown`은 좁히기 전까지 대부분의 연산을 금지한다.", "`unknown`을 사용하면 컴파일러가 런타임 타입 검사 코드를 자동으로 삽입해 준다.", "`any`는 사용 전에 반드시 타입 단언이 필요하고, `unknown`은 그렇지 않다."]', answer_key = '{"correct":1}' WHERE id = 1116 AND md5(content) = '16a50906aa2eded73cc63d57ad0b110b';
UPDATE question_bank SET content = 'TypeScript에서 `unknown` 타입은 어떤 상황에 주로 사용됩니까?', options = '["이미 타입이 확정된 값을 더 좁은 리터럴 타입으로 고정하고 싶을 때", "타입 검사를 완전히 우회해 어떤 프로퍼티 접근이나 연산이든 자유롭게 수행하고 싶을 때", "외부 API 응답처럼 타입을 미리 알 수 없는 값을 받아, 검사로 좁힌 뒤 사용하려 할 때", "배열이나 객체 내부 요소의 타입을 구체적으로 정의하는 상황"]', answer_key = '{"correct":2}' WHERE id = 1117 AND md5(content) = '79f42d76ef2dfda55ed73977c7802b3a';
UPDATE question_bank SET content = 'Express.js에서 4개의 인자 `(err, req, res, next)`를 받는 미들웨어 함수의 역할은 무엇인가?', options = '["모든 요청에 대해 라우트 핸들러보다 먼저 실행되도록 예약된 전처리 전용 미들웨어다.", "응답 본문을 스트리밍으로 전송하기 위한 전용 미들웨어다.", "다음 미들웨어 호출을 생략하고 요청을 즉시 종료시키는 미들웨어다.", "앞선 미들웨어나 라우트에서 발생한 오류를 처리하는 오류 처리 미들웨어다."]', answer_key = '{"correct":3}' WHERE id = 1118 AND md5(content) = '38d1d7d7f54c209bad17e4ecfc01b600';
UPDATE question_bank SET content = 'Express의 일반 미들웨어가 받는 3개 인자 `(req, res, next)`는 각각 어떤 역할을 하는가?', options = '["요청 객체, 응답 객체, 오류를 던지기 위한 전용 함수", "응답 객체, 요청 객체, 프로세스를 종료하는 함수", "라우트 정보 객체, 세션 객체, 로깅을 위한 콜백 함수", "요청 객체, 응답 객체, 다음 미들웨어로 제어를 넘기는 함수"]', answer_key = '{"correct":3}' WHERE id = 1124 AND md5(content) = 'b38f4fa7a5eeeb2c40eaac7ad2b5fae6';
UPDATE question_bank SET content = 'Node.js의 프로세스 모델에 대한 설명 중 올바른 것은 무엇인가?', options = '["자바스크립트 코드는 기본적으로 단일 스레드 이벤트 루프에서 실행된다.", "HTTP 요청이 들어올 때마다 새 스레드를 생성해 각 요청을 병렬로 처리한다.", "worker_threads 모듈을 사용하면 작업이 동기적으로 순차 수행된다.", "이벤트 루프는 CPU 집약 작업도 블로킹 없이 자동으로 처리한다."]', answer_key = '{"correct":0}' WHERE id = 1128 AND md5(content) = '3c448e41e03e31aeb22bfb9d96558c8b';
UPDATE question_bank SET content = '다음 커스텀 타입을 `User`에 적용한 `Nullable<User>`와 결과가 동일한 내장 유틸리티 타입은 무엇인가?
type Nullable<T> = { [P in keyof T]?: T[P]; }', options = '["Partial<User>", "Pick<User, keyof User>", "Required<User>", "Readonly<User>"]', answer_key = '{"correct":0}' WHERE id = 1130 AND md5(content) = '3413df21fc51280e125d27fa6ab54dc4';
UPDATE question_bank SET content = 'Node.js에서 `process.nextTick` 콜백과 `Promise.then` 콜백의 실행 순서 차이를 올바르게 설명한 것은?', options = '["nextTick은 매크로태스크이고 Promise.then은 마이크로태스크라서 then이 항상 먼저 실행된다.", "둘은 같은 큐를 공유하므로 등록한 순서대로 실행된다.", "nextTick 큐가 프로미스 마이크로태스크 큐보다 먼저 비워지므로 nextTick 콜백이 먼저 실행된다.", "Promise.then 콜백은 타이머 단계에서 실행되므로 setTimeout과 우선순위가 같다."]', answer_key = '{"correct":2}' WHERE id = 1135 AND md5(content) = '816c71e20d5a2d12224e601193bbe86d';
UPDATE question_bank SET content = 'TypeScript에서 객체 프로퍼티에 `readonly`를 붙였을 때 컴파일 오류가 되는 동작은 무엇인가?', options = '["해당 프로퍼티의 값을 읽어 다른 변수에 대입하는 것", "초기화 이후 해당 프로퍼티에 새 값을 재할당하는 것", "객체 리터럴을 생성하면서 해당 프로퍼티를 초기화하는 것", "프로퍼티 값이 객체일 때 그 내부의 중첩 프로퍼티를 수정하는 것"]', answer_key = '{"correct":1}' WHERE id = 1137 AND md5(content) = 'e72c4b9674b92fbee73d8a34db8b8109';
UPDATE question_bank SET content = '다음 코드에서 `example()` 내부에서 `throw new Error(''error'')`가 발생하면 그 오류는 어디에서 처리되는가?
async function example() {
  throw new Error(''error'');
}

example().then(() => console.log(''resolved''))
.catch((err) => { 
    console.error(err);
});', options = '[".then의 첫 번째 콜백이 성공 값 대신 오류 객체를 인자로 받아 처리한다.", ".finally() 콜백이 오류 객체를 전달받아 처리한다.", "체인에 연결된 .catch() 콜백이 거부된 프로미스의 오류를 받아 처리한다.", "어디에서도 처리되지 않아 unhandledRejection으로 이어진다."]', answer_key = '{"correct":2}' WHERE id = 1138 AND md5(content) = 'afc8018350cbcd89b02fbb91b62e0b3f';
UPDATE question_bank SET content = 'Express에서 `app.get(''/users/:id'', ...)`가 `app.get(''/users/list'', ...)`보다 먼저 등록되어 있을 때, `GET /users/list` 요청은 어떻게 처리되는가?', options = '["먼저 등록된 `/users/:id` 핸들러가 매칭되어 `req.params.id`가 ''list''가 된다.", "Express가 경로 구체성을 계산해 더 구체적인 `/users/list` 핸들러를 우선 매칭한다.", "두 핸들러가 모두 실행되어 응답이 두 번 전송된다.", "경로가 모호하다는 라우팅 오류가 발생한다."]', answer_key = '{"correct":0}' WHERE id = 1141 AND md5(content) = 'ca00e8a05cbafae0ee64f34b084e8e12';
UPDATE question_bank SET content = 'Node.js에서 여러 프로미스를 실행하고, 일부가 거부되더라도 전부 완료될 때까지 기다려 각각의 성공/실패 결과를 배열로 받는 메서드는 무엇인가?', options = '["Promise.race", "Promise.any", "Promise.allSettled", "Promise.all"]', answer_key = '{"correct":2}' WHERE id = 1143 AND md5(content) = '7da329248b6916f910309aa9a638d813';
UPDATE question_bank SET content = 'Node.js 프로세스가 `SIGTERM` 시그널을 받았을 때 graceful shutdown을 구현하는 올바른 방법은 무엇인가?', options = '["process.on(''SIGTERM'', ...) 핸들러에서 서버 연결 등 자원을 정리한 뒤 종료한다.", "시그널 처리와 무관하게 코드 곳곳에서 process.exit()를 즉시 호출해 종료를 앞당긴다.", "process.on(''SIGTERM'', () => process.abort())로 코어 덤프와 함께 즉시 중단한다.", "throw new Error(''shutdown'')로 예외를 던져 프로세스를 종료시킨다."]', answer_key = '{"correct":0}' WHERE id = 1145 AND md5(content) = '57fbe5ec8ab03a5dbeb3dfe00917f701';
UPDATE question_bank SET content = '다음 코드에서 `console.log`의 출력 순서는?

```typescript
setTimeout(() => console.log(''timeout''), 0);
process.nextTick(() => console.log(''tick''));
console.log(''sync'');
```', options = '["''sync'', ''tick'', ''timeout''", "''tick'', ''sync'', ''timeout''", "''sync'', ''timeout'', ''tick''", "''timeout'', ''sync'', ''tick''"]', answer_key = '{"correct":0}' WHERE id = 1150 AND md5(content) = 'f270791e6012c5ca32530678a1d7b4f4';
UPDATE question_bank SET content = 'Node.js 프로세스 모델에 대한 설명으로 옳은 것은?', options = '["Node.js는 단일 스레드이므로 파일 I/O 같은 비동기 작업도 내부적으로 한 번에 하나씩만 진행된다.", "worker_threads로 만든 각 워커는 완전히 독립된 별개의 프로세스로 실행되어 메모리를 일절 공유할 수 없다.", "기본 설정에서 처리되지 않은 Promise rejection이 발생하면 프로세스는 오류를 내며 종료된다.", "process.on(''SIGKILL'', handler)로 핸들러를 등록하면 강제 종료 신호를 가로채 무시할 수 있다."]', answer_key = '{"correct":2}' WHERE id = 1151 AND md5(content) = '5e87a1abc33e5b393ab5d7f8cd0078ee';
UPDATE question_bank SET content = '다음 TypeScript 코드에 대한 설명으로 옳은 것은?
```ts
interface UserDetails {
  name?: string;
  age: number | null;
}
const u: UserDetails = { age: null };
```', options = '["`age: null` 대입은 타입 오류다 — null을 허용하려면 `age?: number`로 선언해야 한다.", "`name?: string`은 `name: string | null`과 완전히 동일한 선언이다.", "`const u: UserDetails = {}`로 초기화해도 컴파일된다 — 인터페이스의 모든 속성은 기본적으로 옵셔널이기 때문이다.", "`name`은 옵셔널 속성이라 생략할 수 있고, `u.name`의 타입은 `string | undefined`로 읽힌다."]', answer_key = '{"correct":3}' WHERE id = 1154 AND md5(content) = 'e88d4de54988bbb0861fe62591b310e5';
UPDATE question_bank SET content = '다음 코드에서 프로세스 모델이 어떻게 동작하는지 설명하십시오.

```typescript
const spawn = require(''child_process'').spawn;

function startServer() {
  const childProcess = spawn(''node'', [''app.js''], {stdio: ''inherit''});
}
```
- 위 코드에서 `startServer` 함수가 실행되면서 발생하는 프로세스 상태는?', options = '["자식과 부모 프로세스가 동일한 메모리 공간을 공유하며 서로의 변수에 직접 접근할 수 있다.", "부모 프로세스가 종료되면 자식 프로세스도 기본적으로 즉시 함께 종료된다.", "자식 프로세스가 부모 프로세스의 표준 입력·출력·오류 스트림을 그대로 물려받아 사용한다.", "부모 프로세스는 spawn된 `app.js` 실행이 끝날 때까지 블로킹되어 다음 코드를 실행하지 못한다."]', answer_key = '{"correct":2}' WHERE id = 1155 AND md5(content) = '94aacb90a934b85ee48c7059f7cc9f93';
UPDATE question_bank SET content = '다음 코드 조각은 어떤 문제를 나타내나?
```typescript
import { Pool } from ''pg'';
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

export async function getUsers(): Promise<object[]> {
  const client = await pool.connect();
  const result = await client.query(''SELECT * FROM users'');
  return result.rows;
}
```
- 위 코드는 pg의 커넥션 풀을 이용한 비동기 데이터베이스 조회입니다.', options = '["`pool.connect()`는 동기 함수이므로 `await`를 붙이면 컴파일 오류가 발생한다.", "`result.rows`는 `any[]` 타입이라 `object[]`로 선언된 반환 타입과 충돌해 컴파일 오류가 난다.", "`client.release()`를 호출하지 않아 연결이 풀로 반환되지 않고, 반복 호출 시 풀이 고갈되어 이후 `connect()`가 대기 상태에 빠진다.", "모든 쿼리가 하나의 Pool 인스턴스를 공유하고 있어, 요청마다 새 Pool을 만들지 않으면 쿼리가 직렬화되어 성능이 크게 저하된다."]', answer_key = '{"correct":2}' WHERE id = 1165 AND md5(content) = 'f7536dbf8466cfeb88dadfb225ae939d';
UPDATE question_bank SET content = '다음 코드 스니펫에서 실행을 가장 직접적으로 깨뜨리는 결함은 무엇인가?
```typescript
import { Pool } from ''pg'';
class DBConnection {
  pool: Pool;
  constructor(connectionString) {
    this.pool = new Pool({ connectionString });
  }
}
class UserManagementDB extends DBConnection {
  async getUserProfile(userId): Promise<UserProfile> {
    const result = await this.query(`SELECT * FROM users WHERE user_id=$1`, [userId]);
    return { userId: result.rows[0].user_id, name: result.rows[0].name };
  }
}
class AuthDB extends DBConnection {
  async authenticate(username, password): Promise<JwtToken> {
    // 여기서 JWT 토큰 발급 로직이 있음
  }
}```
- 위 코드 스니펫은 여러 데이터베이스 연결을 위해 클래스와 확장 클래스를 이용한 설계입니다.', options = '["`getUserProfile`이 `DBConnection`에 존재하지 않는 `this.query`를 호출한다 — `this.pool.query`를 사용해야 한다.", "`new Pool({ connectionString })`은 생성자에서 즉시 DB 연결을 시도하는 동기 블로킹 호출이라, 연결이 끝날 때까지 애플리케이션 기동이 멈춘다.", "파라미터 바인딩(`$1`)을 사용하고 있어 SQL 인젝션 공격에 그대로 노출된다.", "클래스 상속으로 풀을 공유하면 두 하위 클래스가 서로의 쿼리 결과를 덮어쓴다."]', answer_key = '{"correct":0}' WHERE id = 1167 AND md5(content) = 'a71c1c9bc0113242aca5890acabbc3c0';
UPDATE question_bank SET content = '다음 코드의 설정 검증에 있는 결함은 무엇인가?
```typescript
import { strict as assert } from ''assert'';
type Config = {
  port: number;
  dbUrl: string;
}
const configFromEnv: Partial<Config> = process.env.NODE_ENV === ''test''
  ? { port: 4001 }
  : { port: Number(process.env.PORT), dbUrl: process.env.DATABASE_URL };
assert.ok(configFromEnv.port !== undefined || configFromEnv.dbUrl !== undefined);```
- `process.env`는 환경 변수 객체입니다.', options = '["Partial 타입은 런타임 검증을 자동으로 수행하므로 assert 라인은 불필요한 중복이다.", "조건이 `||`로 연결되어 두 값 중 하나만 있어도 검증을 통과한다 — 둘 다 필수라면 `&&`로 검사해야 한다.", "`Number(process.env.PORT)`는 환경 변수가 정의되어 있지 않으면 형변환 시점에 TypeError를 던지므로 assert에 도달하기 전에 프로세스가 종료된다.", "test 분기에서 `dbUrl`을 생략한 것은 `Partial<Config>` 타입에 대한 컴파일 오류다."]', answer_key = '{"correct":1}' WHERE id = 1169 AND md5(content) = 'b3ff8a81604c3eaa50ce636c42c06ffe';
UPDATE question_bank SET content = '다음 코드는 async/await로 파일을 읽고 오류를 처리합니다.

async function readData() {
    try{
        const data = await fs.promises.readFile(''file.txt'');
        console.log(data.toString());
    } catch (error) {
        console.error(`Error reading file: ${error.message}`);
    }
}
readData();

''file.txt''가 존재하지 않을 때 이 코드는 어떻게 동작하나요?', options = '["catch 블록이 오류를 잡아 ''Error reading file: ...'' 메시지를 출력하고 함수는 정상 종료된다.", "rejection이 처리되지 않아 unhandled rejection 경고와 함께 프로세스가 종료된다.", "readFile이 동기 예외를 던져 try/catch 밖의 호출부까지 예외가 그대로 전파된다.", "data가 undefined인 상태로 toString()이 호출되어 TypeError가 발생한다."]', answer_key = '{"correct":0}' WHERE id = 1176 AND md5(content) = 'e8d0f32dd0462dc6370f6cb95b861fc3';
UPDATE question_bank SET content = '다음 코드에서 `fetchData` 함수가 호출될 때 HTTP 요청과 Promise가 정상적으로 동작하는지 분석하십시오.

```typescript
function fetchData(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = require(''https'').request(url, (res: any) => {
      let data = '''';
      res.on(''data'', chunk => { data += chunk; });
      res.once(''end'', () => resolve(data));
    }).on(''error'', err => reject(err));
  });
}
```', options = '["''data'' 이벤트 핸들러가 등록되어 있지 않아 응답 본문이 조립되지 않고 유실된다.", "`req.end()`를 호출하지 않아 요청이 실제로 전송되지 않고, 반환된 Promise는 영원히 pending 상태로 남는다.", "`res.once(''end'', ...)`를 사용했기 때문에 ''end'' 이벤트가 두 번째 발생하는 시점부터 응답 데이터가 유실된다.", "https 모듈의 콜백 API는 Promise로 감쌀 수 없으므로 이 패턴 자체가 동작하지 않는다."]', answer_key = '{"correct":1}' WHERE id = 1189 AND md5(content) = '82ab7eef96f7a7e90c7a9f4bdca8bceb';
UPDATE question_bank SET content = '다음 코드 스니펫의 동작에 대한 설명으로 옳은 것을 선택하세요.

const readFile = () => {
 fs.readFile(''data.json'', ''utf8'', (err, data) => { // 주석 부착 위치
 if (err) throw err;
 console.log(JSON.parse(data));
 });
};', options = '["파일이 UTF-8로 읽히며, 파일 부재나 잘못된 JSON 형식 등 어떤 상황에서도 항상 정상적으로 콘솔에 출력된다.", "JSON.parse는 비동기로 동작하므로 파싱이 끝나기 전에 console.log가 먼저 실행된다.", "콜백 안에서 `throw err`로 던진 에러는 바깥 try/catch로 잡을 수 없어 uncaught exception으로 프로세스가 중단될 위험이 있다.", "fs.readFile은 이 형태로 호출하면 동기적으로 실행되어 파일 읽기가 끝날 때까지 이후 코드를 블로킹한다."]', answer_key = '{"correct":2}' WHERE id = 1190 AND md5(content) = '784a4b7178c2dfd7f6359d58a2791eb1';
UPDATE question_bank SET content = '다음 코드에서 비동기 호출의 실행 순서와 종료 조건이 어떻게 되는지 분석하십시오.

```typescript
const processQueue = async () => {
  let remainingTasks: number;
  while (remainingTasks--) await performTask();
};
```
`processQueue` 함수에서 발생하는 가장 중요한 문제를 지목하십시오.', options = '["`await performTask()`는 다음 반복으로 넘어가기 전에 완료를 기다리지 않으므로 모든 태스크가 동시에 병렬로 실행되어 순서가 보장되지 않는다.", "`remainingTasks`가 초기화되지 않아 TypeScript에서는 컴파일 오류이고, 검사를 우회해 실행해도 `undefined--`는 NaN이라 루프 본문이 한 번도 실행되지 않는다.", "async 함수 안의 while 루프에서는 await 키워드를 사용할 수 없다.", "`remainingTasks--`는 후위 연산자이므로 값이 감소하지 않아 루프가 무한 반복된다."]', answer_key = '{"correct":1}' WHERE id = 1191 AND md5(content) = '58a0eba4520470017e0f1915b731a590';
UPDATE question_bank SET content = '다음 코드를 분석하여 주석이 부착된 catch 블록의 문제점을 선택하세요.

const fetchUser = async (userId: string) => {
 try {
 const response = await axios.get(`/users/${userId}`);
 if (!response.data.user) throw new Error(''No user found'');
 return response.data.user;
 } catch (error) { // 주석 부착 위치
 console.error(error);
 }
};', options = '["catch가 에러를 콘솔에만 기록하고 다시 던지거나 반환하지 않아, 호출자는 실패를 감지하지 못한 채 `undefined`를 돌려받는다.", "async 함수의 catch 블록은 await에서 발생한 rejection을 잡을 수 없으므로 이 catch 코드는 실행되지 않는다.", "try 블록 안에서 직접 던진 `throw new Error(''No user found'')`는 같은 함수의 catch에 잡히지 않고 곧바로 상위로 전파된다.", "axios.get이 실패하면 catch 대신 전역 unhandled rejection 핸들러로 에러가 전달된다."]', answer_key = '{"correct":0}' WHERE id = 1192 AND md5(content) = 'f6bc7e146695d28b0eac5b5750eb46d6';
UPDATE question_bank SET content = '다음 코드에서 `AbortController`를 사용한 취소 메커니즘이 실제로 동작하는지 분석하십시오.

```typescript
const controller = new AbortController();
function longRunningTask(signal: any) {
  return new Promise((resolve, reject) => setTimeout(() => resolve(''done''), 5000));
}
longRunningTask(controller.signal).then(result => console.log(result)).catch(error => console.error(error));
setImmediate(() => controller.abort());```
위 코드에서 abort() 호출이 비동기 작업에 어떤 영향을 주는지 고르십시오.', options = '["setImmediate 단계에서 abort()가 호출되는 즉시 pending 상태의 Promise가 AbortError로 reject되고 catch 핸들러가 오류를 출력한다.", "signal을 인자로 넘겼으므로 내부의 setTimeout이 자동으로 취소되어 아무것도 출력되지 않는다.", "controller.abort()는 이미 시작된 태스크에 대해 호출하면 예외를 던진다.", "`longRunningTask`가 전달받은 signal을 사용하지 않으므로 abort()가 호출돼도 태스크는 취소되지 않고 5초 뒤 ''done''이 출력된다."]', answer_key = '{"correct":3}' WHERE id = 1194 AND md5(content) = '9f01a71359643c0bec4a01be54acaf6b';
UPDATE question_bank SET content = '다음 코드를 실행하면 어떤 일이 일어나는지 설명하세요.

const p1 = Promise.resolve(42);
const p2 = new Promise((resolve, reject) => {
  setTimeout(() => resolve(''resolved''), 500);
});
const p3 = new Promise((resolve, reject) => {
  console.log(''P3 start'');
  process.nextTick(() => {
    throw new Error(''Error in promise P3'')
  });
});
const promisesArray = [p1, p2, p3];
Promise.all(promisesArray).then(values => {console.log(`Promise all result: ${values}`)}).
catch(error => console.error(''Uncaught error:'', error));', options = '["세 프로미스가 모두 resolve되어 ''Promise all result: 42,resolved,...''가 출력된다.", "p3의 예외는 Promise.all 내부에서 rejection으로 변환되므로 catch 블록이 실행되어 ''Uncaught error: Error in promise P3''가 출력된다.", "`process.nextTick` 콜백에서 던진 예외는 Promise 생성자가 잡지 못하므로 p3는 영원히 pending이고, 예외는 uncaught exception으로 프로세스를 중단시킨다.", "Promise.all은 가장 먼저 완료된 p1의 값 42만 반환하고 나머지 프로미스는 무시한다."]', answer_key = '{"correct":2}' WHERE id = 1198 AND md5(content) = 'f9fd31d09a9e7bcaf8720ef6e675b5f4';
UPDATE question_bank SET content = '다음 코드에서 워커가 종료되는 시점과 원인에 대해 설명하세요.

const { Worker, isMainThread } = require(''worker_threads'');

if (isMainThread) {
  const worker = new Worker(__filename);
  worker.on(''exit'', code => console.log(`worker exited with code ${code}`));
  setTimeout(() => worker.terminate(), 500);
} else {
  setInterval(() => {}, 1000); // 워커의 이벤트 루프를 계속 살려 둔다
}', options = '["워커의 setInterval이 첫 실행을 마치는 즉시 이벤트 루프가 비어 워커가 스스로 종료된다.", "워커 스레드는 별도의 프로세스이므로 `process.kill`로 SIGTERM 신호를 보내기 전에는 종료시킬 수 없다.", "약 500ms 뒤 메인 스레드의 `worker.terminate()` 호출로 워커가 강제 종료되고 ''exit'' 이벤트 핸들러가 실행된다.", "terminate()를 호출해도 setInterval이 이벤트 루프를 붙잡고 있는 동안에는 워커가 종료되지 않는다."]', answer_key = '{"correct":2}' WHERE id = 1199 AND md5(content) = '68af0a045e18060c29232c314596f210';
UPDATE question_bank SET content = 'SQL에서 어떤 열의 값이 NULL인 행을 WHERE 절로 선택할 때 사용하는 연산자는 무엇입니까?', options = '["IS NULL", "COALESCE(NULL, 값)", "NULLIF(값, NULL)", "NVL(값, 대체값)"]', answer_key = '{"correct":0}' WHERE id = 1203 AND md5(content) = 'dd7a1632a370feff033f0cee7497dcf4';
UPDATE question_bank SET content = 'pandas Series에서 인덱스 레이블(이름)을 사용해 단일 값뿐 아니라 슬라이스나 리스트로 여러 값까지 선택할 수 있는 인덱서는 무엇인가?', options = '["loc", "iloc", "at", "iat"]', answer_key = '{"correct":0}' WHERE id = 1204 AND md5(content) = '026d22831f507aacf82dcad8da16c838';
UPDATE question_bank SET content = 'pandas의 DataFrame에서 결측치가 포함된 행을 삭제하는 방법은?', options = '["dropna() 메서드를 호출한다", "fillna(0) 메서드로 결측값을 0으로 대체한다", "isnull().sum() 메서드로 결측치의 개수를 집계한다", "drop_duplicates() 메서드로 중복 행을 제거한다"]', answer_key = '{"correct":0}' WHERE id = 1208 AND md5(content) = '28d9eebfeb81170adfd71855dabbb364';
UPDATE question_bank SET content = '분산과 표준편차에 대한 설명으로 옳은 것은?', options = '["분산은 중앙값으로부터 각 값들의 거리제곱합을 데이터 개수로 나눈 것이다.", "표준편차는 원자료와 같은 단위를 가지므로 분산보다 해석이 쉽다.", "데이터의 범위(최대-최소)가 0보다 크더라도 표준편차는 0이 될 수 있다.", "중앙값과 최빈값이 동일한 위치에 있으면 분산은 0으로 계산된다."]', answer_key = '{"correct":1}' WHERE id = 1211 AND md5(content) = '4d9bf5c097d31201b6cd0c5ab4b050fb';
UPDATE question_bank SET content = 'numpy 배열의 크기·형태 변경에 대한 설명으로 옳은 것은?', options = '["np.shape()은 배열의 형태를 변경한 새로운 배열을 반환한다.", "reshape는 호출한 원본 배열의 shape 속성을 그 자리에서 바꾼다.", "np.resize() 함수는 크기를 늘리거나 줄일 때 완전히 새로운 배열을 반환한다.", "reshape로는 전체 원소 개수가 다른 형태로도 자유롭게 변경할 수 있다."]', answer_key = '{"correct":2}' WHERE id = 1217 AND md5(content) = 'e80d063308cbefe6a3d2be0191864afa';
UPDATE question_bank SET content = '데이터 누수(leakage)에 대한 설명으로 옳은 것은?', options = '["트레이닝 데이터에서 계산한 결측치 대체 기준을 테스트 세트에도 동일하게 적용해야 한다.", "상관관계가 높은 두 변수를 모델에 함께 넣는 것 자체가 데이터 누수에 해당한다.", "시계열 데이터에서는 미래 레코드의 정보를 학습에 사용해도 누수가 되지 않는다.", "데이터셋 분리 전에 전체 데이터로 스케일링을 적용해도 데이터 누수는 발생하지 않는다."]', answer_key = '{"correct":0}' WHERE id = 1225 AND md5(content) = '94fcea45eed053718731e8881b8accac';
UPDATE question_bank SET content = '데이터프레임에서 결측치 처리에 pandas의 fillna 메서드가 사용됩니다. fillna로 칼럼마다 서로 다른 대체값을 지정하는 방법은?', options = '["매개변수 method=''ffill'' 또는 ''bfill''을 주면 칼럼마다 원하는 대체값을 지정할 수 있다.", "칼럼 이름을 키로, 대체값을 값으로 하는 딕셔너리를 fillna()에 전달하면 된다.", "parameter axis=1을 설정하면 칼럼별 대체값이 자동으로 결정된다.", "fillna 한 번의 호출로는 칼럼마다 다른 값을 지정할 수 없다."]', answer_key = '{"correct":1}' WHERE id = 1227 AND md5(content) = '4dfeebf8e42a25b7aab29944569090e1';
UPDATE question_bank SET content = 'numpy의 브로드캐스팅(broadcasting)은 어떤 경우에 발생하는가?', options = '["두 배열의 전체 원소 개수가 같기만 하면 어떤 shape이든 항상 브로드캐스팅된다.", "두 배열의 형태가 달라도 규칙에 따라 크기 1인 차원을 늘려 맞출 수 있는 경우.", "모든 배열이 동일한 크기여야 하는 경우.", "shape과 무관하게 임의의 두 배열 사이에서 항상 발생한다."]', answer_key = '{"correct":1}' WHERE id = 1239 AND md5(content) = '34527ef3d9fe869797258b3e895ee5dc';
UPDATE question_bank SET content = '시계열 센서 데이터에서 중간중간 비어 있는 수치 측정값을 앞뒤 값의 추세를 반영해 채우려고 한다. 가장 적절한 방법은?', options = '["dropna(axis=0)을 이용하여 해당 시점의 행을 모두 삭제한다.", "fillna(value=''Unknown'')로 문자열 값으로 일괄 대체한다.", "interpolate() 메서드를 사용해 앞뒤 값으로 보간한다.", "value_counts(normalize=True)로 빈도 분포를 확인한다."]', answer_key = '{"correct":2}' WHERE id = 1242 AND md5(content) = 'ff76ec8d4896fff26ef7f5abb087d3ff';
UPDATE question_bank SET content = '데이터프레임(df)에서 groupby를 사용하여 계산한 그룹별 평균은 어떤 형태로 반환되나요?
예시 코드:
```python
result = df.groupby(''category'').mean()
```', options = '["각 카테고리에 대한 각 컬럼의 평균이 딕셔너리 형식으로 나타난다.", "카테고리 값을 인덱스로 하여 그룹당 한 행씩, 수치형 열별 평균을 담은 DataFrame이 반환된다.", "전체 데이터의 평균 하나만 스칼라 값으로 반환된다.", "각 카테고리를 키로 하고 모든 수치형 열의 평균을 하나로 합산한 값을 갖는 pandas.Series 객체가 반환된다."]', answer_key = '{"correct":1}' WHERE id = 1248 AND md5(content) = '525d1bc031f896ef49d86903c66cbbd3';
UPDATE question_bank SET content = '데이터 누수가 발생할 수 있는 경우는 어떤 상황인가요?', options = '["훈련 데이터에서 특성 엔지니어링을 수행한 후, 테스트 세트에서도 같은 전처리를 적용하지 않음.", "훈련 세트와 테스트 세트를 무작위로 분할한 뒤 서로 섞지 않고 사용함.", "훈련이 끝난 뒤 별도로 보관해 둔 테스트 세트로 최종 성능을 한 번만 평가함.", "데이터 분할 시, 시간 순서 상관 관계를 고려하지 않아 미래 데이터가 학습에 사용됨."]', answer_key = '{"correct":3}' WHERE id = 1250 AND md5(content) = '5e4c88bf3eb73de97e2537b18c6130d6';
UPDATE question_bank SET content = '다음 코드 스니펫에서 데이터 누수가 발생하는 이유는 무엇인가요?
```python
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_all)
x_train, x_test = train_test_split(X_scaled)
```', options = '["분할 전에 전체 데이터로 스케일러를 fit하여 테스트 데이터의 통계량이 훈련 데이터 변환에 반영된다.", "StandardScaler는 레이블(정답) 정보를 사용하므로 항상 누수를 일으킨다.", "train_test_split이 데이터를 복사하지 않아 두 세트가 같은 메모리를 참조하게 된다.", "fit_transform이 원본 배열을 제자리에서 수정하여 원본 데이터가 오염되기 때문이다."]', answer_key = '{"correct":0}' WHERE id = 1253 AND md5(content) = 'fd00309b3658824428170ba6064a4a42';
UPDATE question_bank SET content = '다음 코드 조각에서 데이터 누수를 일으키는 부분은?
```python
scaled_all = scaler.fit_transform(X_all)
X_train, X_test, y_train, y_test = train_test_split(scaled_all, y_all)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
```', options = '["train_test_split() 이전에 전체 데이터에 스케일러를 fit_transform 했다.", "스케일링 직후 곧바로 모델을 학습시켰다.", "훈련 데이터와 테스트 데이터를 분리해서 사용했다.", "학습에 사용하지 않은 X_test로 예측을 수행했다."]', answer_key = '{"correct":0}' WHERE id = 1254 AND md5(content) = '4058b70305afd82f983a6a73f7bfe92b';
UPDATE question_bank SET content = '데이터 누수가 발생하는 한 가지 예시를 고르세요.', options = '["훈련 데이터만으로 계산한 통계량을 사용해 특성을 스케일링함", "학습에 쓰지 않는 별도 검증 세트를 두어 하이퍼파라미터를 선택함", "테스트 세트에서 얻은 성능 지표를 보고 반복적으로 하이퍼파라미터를 조정함", "훈련 데이터와 테스트 데이터 사이에 특성 분포 불일치가 존재함"]', answer_key = '{"correct":2}' WHERE id = 1255 AND md5(content) = '475418a7ced5d53675eea1bec0ece736';
UPDATE question_bank SET content = '교차 검증에서 전처리를 Pipeline으로 묶어 사용하는 이유로 옳은 것은?
```python
from sklearn.pipeline import make_pipeline
pipeline = make_pipeline(scaler, estimator)
scores = cross_val_score(pipeline, X, y, cv=5)
```', options = '["각 폴드에서 훈련 폴드에만 전처리가 fit되어 검증 폴드 정보의 누수를 막는다.", "전처리가 전체 데이터에 한 번만 fit되므로 반복 계산이 줄어 속도가 빨라진다.", "Pipeline을 쓰면 교차 검증 없이도 모델의 일반화 성능이 자동으로 보장된다.", "검증 폴드에는 전처리가 아예 적용되지 않아 원본 분포가 그대로 유지된다."]', answer_key = '{"correct":0}' WHERE id = 1263 AND md5(content) = '2cfc10bde4dde12eefe1a6d8c5c90b27';
UPDATE question_bank SET content = '학습-테스트 데이터 간 특성 분포 불일치와 데이터 누수(leakage)의 관계에 대한 설명으로 옳은 것은?', options = '["특성 분포 불일치는 그 자체로 데이터 누수의 한 형태로 분류된다.", "누수는 평가 시점에 쓸 수 없는 정보가 학습에 쓰인 것이고, 분포 불일치는 일반화의 문제로 서로 다른 개념이다.", "데이터 누수가 있으면 테스트 성능이 항상 실제 성능보다 낮게 측정된다.", "분포 불일치는 테스트 세트의 크기를 충분히 늘리기만 하면 별도 조치 없이 자동으로 해소되는 문제다."]', answer_key = '{"correct":1}' WHERE id = 1265 AND md5(content) = 'f99b0901e2707cac7906a99aeb80fa59';
UPDATE question_bank SET content = '데이터 누수를 방지하는 데 효과적이지 않은 조치는?', options = '["시계열 데이터에서 훈련 데이터와 테스트 데이터를 시간 순서로 격리하기", "타깃(정답) 값을 이용해 만든 피처를 그대로 훈련에 사용하기", "각 피처가 예측 시점에 실제로 알 수 있는 정보인지 비즈니스 로직으로 검토하기", "데이터 수집 시점을 주의 깊게 고려하여 누수 가능성을 최소화하기"]', answer_key = '{"correct":1}' WHERE id = 1268 AND md5(content) = 'b52d05d96cae8b1b0b0729d32b3510a9';
UPDATE question_bank SET content = '시계열 데이터를 낮은 빈도로 리샘플링(다운샘플링)하여 예측용 피처를 만들 때, 미래 정보 누수(look-ahead bias)를 막기 위한 올바른 방법은?', options = '["리샘플링 전에 전체 기간에 대해 계산한 평균값으로 각 구간의 결측치를 미리 채워 둔다", "각 구간의 집계에 그 구간 종료 시점까지의 데이터만 포함되도록 구간 경계와 라벨을 설정한다", "데이터를 무작위로 셔플한 뒤 시간 구간별로 다시 정렬해 사용한다", "구간 값이 비어 있으면 다음 구간의 첫 값으로 채운다(backfill)"]', answer_key = '{"correct":1}' WHERE id = 1269 AND md5(content) = 'd57c158c53f6a0b0040ebc48fe043a62';
UPDATE question_bank SET content = '다음 코드에서 데이터 누수(data leakage) 관점의 문제점은 무엇인가요?

```python
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

X_train, X_test = train_test_split(X, test_size=0.2, random_state=42)
scaler = StandardScaler().fit(X)  # 전체 데이터 X에 fit
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)
```', options = '["테스트 세트의 통계량이 스케일러 학습에 포함되어 평가 결과가 낙관적으로 왜곡될 수 있다", "train_test_split이 클래스 비율을 유지하지 않아 모델 학습 자체가 불가능해진다", "StandardScaler는 음수 값을 처리하지 못해 fit 단계에서 예외가 발생한다", "훈련 세트와 테스트 세트에 같은 scaler 객체로 transform을 호출했기 때문에 서로 다른 스케일이 적용된다"]', answer_key = '{"correct":0}' WHERE id = 1278 AND md5(content) = '530e8bb6202cc28a5060d2e3b3d68e95';
UPDATE question_bank SET content = '다음 코드에서 동작으로 옳은 것은?

import pandas as pd

def handle_data_leakage(df):
    df[''target''] = (df[''date''] > ''2023-01-01'').astype(int)
    train, test = train_test_split(df, test_size=0.2, random_state=42)
    return train,test', options = '["target이 ''date'' 칼럼에서 직접 파생되므로 date를 피처로 쓰면 정답 정보가 누출된다.", "훈련 세트는 전체의 20%, 테스트 세트는 80%를 차지한다.", "''date'' 칼럼은 target 생성 직후 자동으로 삭제되므로 누수 위험이 없다.", "테스트 세트에서 target 값은 항상 1이다."]', answer_key = '{"correct":0}' WHERE id = 1283 AND md5(content) = 'f3c5fdf9261064eb936c32fb7a7ac97c';
UPDATE question_bank SET content = '다음 코드에서 동작으로 옳은 것은?

import pandas as pd
from sklearn.preprocessing import StandardScaler

def scale_data(df):
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[[''feature1'', ''feature2'']])
    df[''scaled_feature1''] = scaled_features[:, 0]
    df[''scaled_feature2''] = scaled_features[:, 1]
    return df', options = '["스케일링된 피처의 평균은 이제 0이다.", "기존 feature1, feature2 컬럼 값이 스케일링된 값으로 덮어써진다.", "새로운 데이터가 들어올 때마다 스케일러를 새로 fit하는 것이 올바른 사용법이다.", "결측값(NaN)이 있어도 StandardScaler가 자동으로 평균값으로 대체해 준다."]', answer_key = '{"correct":0}' WHERE id = 1284 AND md5(content) = '6c89ad454d651f8c8c075fe0477c7a18';
UPDATE question_bank SET content = '다음 Python 코드가 수행할 때 어떤 문제가 생길까요?

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = pd.read_csv(''data.csv'') # 가상의 데이터 세트
X = df[[''feature1'', ''feature2'']]
y = df[''target'']
scaler = StandardScaler()
scaler.fit(X)
x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)', options = '["스케일러가 훈련 세트의 통계량만으로 학습되어 테스트 세트 정보는 전혀 반영되지 않는다.", "train-test 분할 전에 전체 데이터로 스케일러를 fit하여 테스트 세트 정보가 누수된다.", "scaler.fit(X)가 별도의 테스트 세트를 자동으로 생성한다.", "모든 전처리 과정이 올바른 순서로 수행되었다."]', answer_key = '{"correct":1}' WHERE id = 1291 AND md5(content) = '1278c4e9f4220ed1ff982e9bcf40157c';
UPDATE question_bank SET content = '다음 SQL 코드가 수행할 때 어떤 효과가 있을까요?

WITH cumulative_sales AS (
    SELECT order_date,
           product_id,
           SUM(quantity) OVER (PARTITION BY product_id ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumul_sum
    FROM orders)
SELECT * 
FROM cumulative_sales', options = '["각 상품별로 주문 날짜 순서에 따른 누적 판매량을 주문 행 단위로 나타낸다.", "일정 기간 내에서 최대 순위를 가진 상품만 뽑아 낸다.", "주문 날짜 별로 가장 많이 팔린 제품을 정렬한다.", "상품별로 여러 행이 하나로 집계되어 상품당 한 행만 출력된다."]', answer_key = '{"correct":0}' WHERE id = 1294 AND md5(content) = '20522abbb9373e135734e7a2286ccf15';
UPDATE question_bank SET content = '다음 SQL에서 ROW_NUMBER() 함수는 어떤 역할을 할까요?

WITH ranked_sales AS (
    SELECT product_id,
           order_date,
           SUM(quantity) AS total_quantity,
           ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY SUM(quantity) DESC) AS rn
    FROM orders
    GROUP BY product_id, order_date
)
SELECT * FROM ranked_sales', options = '["product_id와 무관하게 전체 결과에 하나의 연속된 순번을 부여한다.", "각 product_id 안에서 날짜별 판매량 합계가 큰 순서대로 1부터 순번을 매긴다.", "판매량 합계가 같은 날짜에는 같은 순번을 부여하고 다음 순번을 건너뛴다.", "각 product_id의 판매량을 날짜 순서대로 누적 합산한다."]', answer_key = '{"correct":1}' WHERE id = 1295 AND md5(content) = 'f8d03600af832e648069b7f85a37db3c';
UPDATE question_bank SET content = '다음 코드의 동작으로 옳은 것은?

import pandas as pd

df = pd.read_csv(''data.csv'')
grouped_df = df.groupby(''category'').agg(
    total_sales=(''sales'', ''sum''),
    min_price=(''price'', ''min''),
)', options = '["카테고리별로 sales의 합계와 price의 최솟값이 각각 total_sales, min_price 컬럼으로 계산된다.", "total_sales와 min_price 모두 sales 컬럼 하나만을 대상으로 계산된다.", "결과 컬럼 이름은 (''sales'', ''sum'') 형태의 다중 인덱스(MultiIndex)가 된다.", "결과는 원본 df와 같은 행 수를 유지한 채 각 행에 그룹 집계값이 붙는다."]', answer_key = '{"correct":0}' WHERE id = 1298 AND md5(content) = '31f1aa409f4622f87bff544a46831072';
UPDATE question_bank SET content = '다음 코드의 동작으로 옳은 것은?

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
X, y = make_classification(random_state=42)
x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
scores = cross_val_score(LogisticRegression(), X, y, cv=5)', options = '["각 폴드마다 데이터를 훈련용과 검증용으로 나누어 총 5개의 점수를 계산한다.", "앞서 만든 x_train만 사용되므로 test_size=0.3 분할이 교차검증 점수에 영향을 준다.", "각 폴드에서 전체 샘플이 모두 검증 세트로 동시에 사용된다.", "모델을 한 번만 학습한 뒤 5개 폴드에서 같은 학습 결과를 재사용한다."]', answer_key = '{"correct":0}' WHERE id = 1299 AND md5(content) = 'a8137b383e8ce59d9e835f5dd725cc63';
UPDATE question_bank SET content = '다음 코드의 동작으로 옳은 것은?

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pandas as pd

df = pd.read_csv(''data.csv'')
x, x_val, y, y_val = train_test_split(df.drop(columns=[''target'']), df[''target''], test_size=0.2)
scaler = StandardScaler()
x_scaled = scaler.fit_transform(pd.concat([x, x_val]))', options = '["스케일러 학습(fit)에 검증 데이터까지 포함되어 데이터 누수가 발생한다.", "검증 데이터에는 새로운 스케일러를 별도로 fit해서 적용하는 것이 올바른 방법이다.", "이 방식은 검증 점수를 실제 성능보다 비관적으로(낮게) 측정하게 만든다.", "훈련 데이터와 검증 데이터에 서로 다른 기준의 스케일이 적용되어 비교가 불가능해진다."]', answer_key = '{"correct":0}' WHERE id = 1300 AND md5(content) = '02d1030b9000c251b42cb6093783c204';
COMMIT;
-- 후속(2026-08-22, 사실 검증 게이트 도입이 적발): 재작성 811 의 보기 집합이
-- 기존 823 과 동일해진 충돌 교정(Summary -> Untyped). 운영 적용 완료(UPDATE 1).
BEGIN;
UPDATE question_bank SET options = '["Counter","Gauge","Histogram","Untyped"]' WHERE id = 811 AND md5(content) = 'faccd9ed45fc72344ee9f1f61268e33d' AND options = '["Counter","Gauge","Histogram","Summary"]';
COMMIT;
