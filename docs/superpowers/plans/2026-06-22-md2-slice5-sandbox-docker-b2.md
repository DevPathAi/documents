# 슬라이스 #5 빌드 B2 — DockerRunnerBackend (Docker 격리 실행 구현 + CI Docker 통합 테스트) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `RunnerBackend` 인터페이스(빌드 B1 Task 5에서 확정된 시그니처)를 Docker로 구현한 `DockerRunnerBackend`를 추가한다. 언어별 온디맨드 컨테이너(Java21/Node20/Python3.12)에 코드를 주입·실행하고 stdout/stderr를 실시간 logCallback으로 전달한다. 30s 타임아웃 초과 시 컨테이너를 SIGKILL하고 `exitCode=-1`을 반환한다. 보안 옵션(`--network none`, `--memory 512m`, `--cpus 1`, `--pids-limit 128`, `--user nobody`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, tmpfs `/tmp`)을 docker-java HostConfig API로 적용한다. `@Tag("docker")` 통합 테스트 4개(언어별 hello·무한루프·exit≠0·네트워크 차단)를 작성하고 CI `build` job 안에서 `@Tag("docker")` 태그 필터로 함께 실행한다. **단위 테스트(B1, Docker 불요)는 항상 녹색 유지.**

**Architecture:**
```
DockerRunnerBackend implements RunnerBackend (B1 인터페이스 그대로)
   1. 임시 디렉터리(Files.createTempDirectory) → 코드 파일 기록
   2. createContainerCmd(image)
        .withCmd(언어별 실행 커맨드)
        .withHostConfig(HostConfig: 보안 옵션 전체)
        .exec()
   3. startContainerCmd(id).exec()
   4. logContainerCmd(id) → ResultCallback.Adapter<Frame> → logCallback 호출
      (awaitCompletion(30, SECONDS) 병행 — 타임아웃 시 kill)
   5. waitContainerCmd(id).exec(WaitContainerResultCallback).awaitStatusCode(30, SECONDS)
      → exitCode 수집(-1 if timeout)
   6. removeContainerCmd(id).withForce(true).exec()  ← finally
   7. 임시 디렉터리 삭제  ← finally
```

**Tech Stack:** Spring Boot 4.0.7 · Java 21 · docker-java 3.5.1(`docker-java-core` + `docker-java-transport-httpclient5`) · JUnit 5 · `@Tag("docker")` · GitHub Actions ubuntu-latest(Docker 기본 제공).

**Global Constraints:**
- 대상 레포: **devpath-sandbox-svc 단독**. B1/C/D에 손대지 않는다.
- B1이 develop에 머지·CI 녹색 완료된 이후 이 빌드 브랜치를 분기한다.
- `RunnerBackend` 시그니처 변경 금지: `RunResult run(RunSpec spec, Consumer<String> logCallback)` 그대로.
- `RunResult(int exitCode, String stdout, String stderr, Long cpuMsUsed, Integer memoryMbPeak)` — 타임아웃 kill 시 `exitCode=-1`을 사용한다(`SandboxRunService`가 `-1`을 `KILLED`로 매핑).
- docker-java 확인된 API만 코드에 사용:
  - `HostConfig.newHostConfig()` + `.withMemory(long)`, `.withCpuCount(long)`, `.withPidsLimit(long)`, `.withNetworkMode(String)`, `.withReadonlyRootfs(Boolean)`, `.withCapDrop(Capability...)`, `.withSecurityOpts(List<String>)`, `.withTmpFs(Map<String, String>)`, `.withBinds(Bind...)`.
  - `CreateContainerCmd.withUser(String)` — 컨테이너 레벨 user 설정.
  - `logContainerCmd(id).withStdOut(true).withStdErr(true).withFollowStream(true).exec(new ResultCallback.Adapter<Frame>() { onNext(Frame f){...} })`.
  - `Frame.getPayload()` → `new String(frame.getPayload(), StandardCharsets.UTF_8).stripTrailing()` 로 라인 추출.
  - `waitContainerCmd(id).exec(new WaitContainerResultCallback()).awaitStatusCode(30, TimeUnit.SECONDS)` — 타임아웃 시 `DockerClientException` throw.
  - `killContainerCmd(id).exec()` — 타임아웃 강제 종료.
  - `removeContainerCmd(id).withForce(true).exec()`.
- 단위 테스트(`@SpringBootTest` 비Docker)는 `@Tag("docker")` 제외 — `./gradlew test -x test` 구분 없이 기본 실행 시 DockerRunnerBackendIT만 Docker 필요.
- 모든 `@SpringBootTest`에 `@ActiveProfiles("test")` 필수.
- `@MockitoBean` import: `org.springframework.test.context.bean.override.mockito.MockitoBean`(Boot 4; `@MockBean` 금지).
- Jackson: `tools.jackson.databind.json.JsonMapper`(Boot 4 패키지; `com.fasterxml` 금지).
- `@AutoConfigureMockMvc` import: `org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc`.
- CI: sandbox-svc `.github/workflows/ci.yml` `build` job에 `@Tag("docker")` 태그 포함 실행 추가(GitHub Actions ubuntu-latest는 Docker 기본 제공). **단위 테스트(B1 산출물)는 별도 job 또는 태그 제외 step으로 항상 녹색 보장.**
- 신규 작업 브랜치: `develop`에서 `feat/sandbox-docker-b2` 분기(CLAUDE.md 규칙 4). B1 머지 후 분기.

---

## File Structure

```
devpath-sandbox-svc/
├── build.gradle.kts                                         Modify: docker-java deps 추가
├── .github/workflows/ci.yml                                 Modify: docker 통합 테스트 step 추가
└── src/
    ├── main/java/ai/devpath/sandbox/
    │   └── run/
    │       └── DockerRunnerBackend.java                      Create: RunnerBackend Docker 구현
    └── test/java/ai/devpath/sandbox/
        └── run/
            └── DockerRunnerBackendIT.java                    Create: @Tag("docker") 통합 테스트
```

> 본보기(B1 산출물): `run/RunnerBackend.java`(인터페이스), `run/RunSpec.java`, `run/RunResult.java`, `run/SandboxUnavailableException.java`, `run/FakeRunnerBackend.java`(테스트 패키지).

---

## Task 0: 작업 브랜치

- [ ] **Step 1: B1 develop 머지 확인 후 브랜치 분기**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
git switch develop
git pull
# B1 PR이 develop에 머지·CI 녹색인지 확인
git log --oneline -5
git switch -c feat/sandbox-docker-b2
```

Expected: 브랜치가 B1 커밋(feat/sandbox-core-b1 머지)을 포함한 develop 위에서 시작됨.

---

## Task 1: build.gradle.kts — docker-java deps 추가

**Files:**
- Modify: `build.gradle.kts`

**Interfaces:**
- Produces: `docker-java-core:3.5.1` + `docker-java-transport-httpclient5:3.5.1` 의존성이 추가된 빌드 설정.

**Context7/GitHub 확인된 artifact:**
- groupId: `com.github.docker-java`
- docker-java-core: `3.5.1` (Maven Central 최신 릴리스)
- docker-java-transport-httpclient5: `3.5.1` (httpclient5 기반 transport — unix socket 지원, CI linux 호환)

- [ ] **Step 1: 현재 빌드 기준점 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
.\gradlew.bat compileJava
```

Expected: B1 산출물로 SUCCESS.

- [ ] **Step 2: docker-java deps 추가** — `build.gradle.kts`의 `dependencies` 블록에 다음을 추가한다.

현재 `build.gradle.kts`(B1 완료 상태):
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
    runtimeOnly("org.postgresql:postgresql")
    // implementation("org.springframework.boot:spring-boot-starter-data-redis")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
    testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
    testImplementation("org.springframework.security:spring-security-test")
    testCompileOnly("org.projectlombok:lombok")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testAnnotationProcessor("org.projectlombok:lombok")
}
```

추가할 두 줄 (docker-java deps):
```kotlin
    implementation("com.github.docker-java:docker-java-core:3.5.1")
    implementation("com.github.docker-java:docker-java-transport-httpclient5:3.5.1")
```

최종 `dependencies` 블록:
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("ai.devpath:devpath-shared:0.0.1-SNAPSHOT")
    implementation("com.github.docker-java:docker-java-core:3.5.1")
    implementation("com.github.docker-java:docker-java-transport-httpclient5:3.5.1")
    runtimeOnly("org.postgresql:postgresql")
    // implementation("org.springframework.boot:spring-boot-starter-data-redis")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
    testImplementation("org.springframework.boot:spring-boot-starter-validation-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
    testImplementation("org.springframework.security:spring-security-test")
    testCompileOnly("org.projectlombok:lombok")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testAnnotationProcessor("org.projectlombok:lombok")
}
```

- [ ] **Step 3: 의존성 해소 확인**

```powershell
.\gradlew.bat dependencies --configuration runtimeClasspath | Select-String "docker-java"
```

Expected: `com.github.docker-java:docker-java-core:3.5.1`, `com.github.docker-java:docker-java-transport-httpclient5:3.5.1` 출력.

- [ ] **Step 4: 기존 단위 테스트 회귀 없음 확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups='!docker'
```

Expected: B1 전 단위 테스트 PASS(DockerRunnerBackendIT 없으므로 필터 없어도 동일).

- [ ] **Step 5: 커밋**

```powershell
git add build.gradle.kts
git commit -m "build(deps): add docker-java-core + transport-httpclient5 3.5.1 (slice5 B2)"
```

---

## Task 2: DockerRunnerBackend 구현

**Files:**
- Create: `src/main/java/ai/devpath/sandbox/run/DockerRunnerBackend.java`

**Interfaces:**
- `DockerRunnerBackend implements RunnerBackend`:
  - `RunResult run(RunSpec spec, Consumer<String> logCallback)` — B1 인터페이스 시그니처 그대로.
  - Docker 미가동·컨테이너 생성 실패 시 `SandboxUnavailableException` throw.
  - 타임아웃(30s) 초과 시 `killContainerCmd(id).exec()` 후 `exitCode=-1` 반환.
  - finally 블록에서 컨테이너 삭제 + 임시 디렉터리 삭제.

**언어별 이미지 및 실행 커맨드:**

| language | image | 실행 커맨드 | 소스 파일명 |
|---|---|---|---|
| `JAVA` | `eclipse-temurin:21-jdk` | `java Main.java` (JEP 445 single-file source launcher, Java 21 지원) | `Main.java` |
| `NODE` | `node:20-alpine` | `node solution.js` | `solution.js` |
| `PYTHON` | `python:3.12-slim` | `python solution.py` | `solution.py` |

> **Java 실행 커맨드 결정 근거**: Java 11+부터 `java FileName.java`로 single-file source 직접 실행 가능(컴파일 없음). Java 21은 JEP 445로 unnamed class 지원 추가. `javac+java` 2단계보다 30s 제한 내에서 유리하고, 단일 public class `Main`을 파일명 `Main.java`로 저장하면 동작. 단, 멀티 클래스 분리 불가 — 이는 MVP 수준 제약으로 수용.

**보안 옵션 (§7 전체 적용 — docker-java 확인된 API):**

```
--network none           → .withNetworkMode("none")
--memory 512m            → .withMemory(512 * 1024 * 1024L)
--cpus 1                 → .withCpuCount(1L)
--pids-limit 128         → .withPidsLimit(128L)
--user nobody            → createContainerCmd.withUser("nobody")
--read-only              → .withReadonlyRootfs(true)
--cap-drop ALL           → .withCapDrop(Capability.ALL)
--security-opt no-new-privileges → .withSecurityOpts(List.of("no-new-privileges:true"))
tmpfs /tmp               → .withTmpFs(Map.of("/tmp", "size=64m"))
```

- [ ] **Step 1: 실패 테스트 작성** — 통합 테스트(Task 3)보다 먼저 컴파일 실패를 확인하기 위한 플레이스홀더 테스트. 이후 Task 3에서 본격 테스트로 교체.

```powershell
# 먼저 DockerRunnerBackend.java가 없는 상태에서 컴파일 실패를 유도하는 임시 테스트 작성
# (Task 3 DockerRunnerBackendIT.java가 DockerRunnerBackend를 참조하므로 Task 3과 함께 처리)
```

Task 2와 Task 3은 순서대로 진행한다 — DockerRunnerBackend 구현 후 통합 테스트 작성·확인.

- [ ] **Step 2: DockerRunnerBackend 구현** — `src/main/java/ai/devpath/sandbox/run/DockerRunnerBackend.java`:

```java
package ai.devpath.sandbox.run;

import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.async.ResultCallback;
import com.github.dockerjava.api.command.CreateContainerResponse;
import com.github.dockerjava.api.command.WaitContainerResultCallback;
import com.github.dockerjava.api.exception.DockerException;
import com.github.dockerjava.api.model.Bind;
import com.github.dockerjava.api.model.Capability;
import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.HostConfig;
import com.github.dockerjava.api.model.Volume;
import com.github.dockerjava.core.DockerClientBuilder;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import java.util.stream.Stream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * RunnerBackend Docker 구현.
 *
 * <p>요청마다 온디맨드 컨테이너를 생성→실행→삭제한다(D-4: 온디맨드).
 * 보안 옵션(§7): --network none, --memory 512m, --cpus 1, --pids-limit 128,
 * --user nobody, --read-only, --cap-drop ALL, --security-opt no-new-privileges, tmpfs /tmp.
 * 30s wall-clock 타임아웃 초과 시 SIGKILL → exitCode=-1(KILLED).
 *
 * <p>Docker 데몬 미가동 또는 컨테이너 생성 실패 시 SandboxUnavailableException throw.
 */
@Component
public class DockerRunnerBackend implements RunnerBackend {

  private static final Logger log = LoggerFactory.getLogger(DockerRunnerBackend.class);

  private static final long TIMEOUT_SECONDS = 30L;
  private static final long MEMORY_BYTES = 512L * 1024 * 1024;  // 512 MB
  private static final long CPU_COUNT = 1L;
  private static final long PIDS_LIMIT = 128L;

  /** 언어별 Docker 이미지. */
  private static String imageFor(String language) {
    return switch (language) {
      case "JAVA"   -> "eclipse-temurin:21-jdk";
      case "NODE"   -> "node:20-alpine";
      case "PYTHON" -> "python:3.12-slim";
      default -> throw new IllegalArgumentException("지원하지 않는 language: " + language);
    };
  }

  /** 언어별 소스 파일명. */
  private static String sourceFileNameFor(String language) {
    return switch (language) {
      case "JAVA"   -> "Main.java";
      case "NODE"   -> "solution.js";
      case "PYTHON" -> "solution.py";
      default -> throw new IllegalArgumentException("지원하지 않는 language: " + language);
    };
  }

  /** 컨테이너 내 실행 커맨드. 코드는 /workspace/<파일명> 에 마운트됨. */
  private static String[] cmdFor(String language, String fileName) {
    return switch (language) {
      case "JAVA"   -> new String[]{"java", "/workspace/" + fileName};
      case "NODE"   -> new String[]{"node", "/workspace/" + fileName};
      case "PYTHON" -> new String[]{"python", "/workspace/" + fileName};
      default -> throw new IllegalArgumentException("지원하지 않는 language: " + language);
    };
  }

  @Override
  public RunResult run(RunSpec spec, Consumer<String> logCallback) {
    Path tempDir = null;
    String containerId = null;
    DockerClient docker = null;

    try {
      // Docker 클라이언트 생성 (호스트 소켓 자동 감지 — unix:///var/run/docker.sock 또는 npipe)
      docker = DockerClientBuilder.getInstance().build();

      // 1. 임시 워크스페이스 생성 + 코드 파일 기록
      tempDir = Files.createTempDirectory("sandbox-" + spec.sandboxSessionId() + "-");
      String fileName = sourceFileNameFor(spec.language());
      Path codeFile = tempDir.resolve(fileName);
      Files.writeString(codeFile, spec.code(), StandardCharsets.UTF_8);

      // 2. 컨테이너 볼륨·바인드 설정 (코드 디렉터리 read-only 마운트)
      Volume workspaceVol = new Volume("/workspace");
      Bind workspaceBind = new Bind(tempDir.toAbsolutePath().toString(), workspaceVol, true /* ro */);

      // 3. HostConfig 보안 옵션 (§7 전체 적용)
      HostConfig hostConfig = HostConfig.newHostConfig()
          .withNetworkMode("none")                              // --network none
          .withMemory(MEMORY_BYTES)                            // --memory 512m
          .withCpuCount(CPU_COUNT)                             // --cpus 1
          .withPidsLimit(PIDS_LIMIT)                           // --pids-limit 128
          .withReadonlyRootfs(true)                            // --read-only
          .withCapDrop(Capability.ALL)                         // --cap-drop ALL
          .withSecurityOpts(List.of("no-new-privileges:true")) // --security-opt no-new-privileges
          .withTmpFs(Map.of("/tmp", "size=64m"))               // tmpfs /tmp (쓰기 가능 임시 영역)
          .withBinds(workspaceBind);                           // /workspace ro 마운트

      // 4. 컨테이너 생성
      String image = imageFor(spec.language());
      String[] cmd = cmdFor(spec.language(), fileName);

      CreateContainerResponse container;
      try {
        container = docker.createContainerCmd(image)
            .withCmd(cmd)
            .withUser("nobody")                                 // --user nobody (비root)
            .withHostConfig(hostConfig)
            .exec();
      } catch (DockerException e) {
        throw new SandboxUnavailableException(
            "컨테이너 생성 실패 (Docker 데몬 미가동 또는 이미지 pull 불가): " + e.getMessage(), e);
      }
      containerId = container.getId();

      // 5. 컨테이너 시작
      docker.startContainerCmd(containerId).exec();

      // 6. 로그 스트리밍 (stdout + stderr → logCallback 실시간 전달)
      StringBuilder stdoutBuf = new StringBuilder();
      StringBuilder stderrBuf = new StringBuilder();
      boolean[] timedOut = {false};

      ResultCallback.Adapter<Frame> logCallback2 = new ResultCallback.Adapter<>() {
        @Override
        public void onNext(Frame frame) {
          if (frame == null || frame.getPayload() == null) return;
          String line = new String(frame.getPayload(), StandardCharsets.UTF_8).stripTrailing();
          if (line.isEmpty()) return;
          switch (frame.getStreamType()) {
            case STDOUT -> { stdoutBuf.append(line).append('\n'); logCallback.accept(line); }
            case STDERR -> { stderrBuf.append(line).append('\n'); logCallback.accept(line); }
            default -> { /* RAW/STDIN 무시 */ }
          }
        }
      };

      try {
        docker.logContainerCmd(containerId)
            .withStdOut(true)
            .withStdErr(true)
            .withFollowStream(true)
            .exec(logCallback2)
            .awaitCompletion(TIMEOUT_SECONDS, TimeUnit.SECONDS);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        timedOut[0] = true;
      }

      // 7. exit code 수집 (WaitContainerResultCallback)
      int exitCode;
      try {
        Integer status = docker.waitContainerCmd(containerId)
            .exec(new WaitContainerResultCallback())
            .awaitStatusCode(TIMEOUT_SECONDS, TimeUnit.SECONDS);
        exitCode = (status != null) ? status : -1;
      } catch (Exception e) {
        // 타임아웃 또는 강제 종료 신호
        timedOut[0] = true;
        exitCode = -1;
      }

      // 8. 타임아웃 처리
      if (timedOut[0] || exitCode == -1) {
        String timeoutMsg = "실행 시간 초과(30s) — 컨테이너를 강제 종료합니다.";
        logCallback.accept(timeoutMsg);
        stderrBuf.append(timeoutMsg).append('\n');
        try {
          docker.killContainerCmd(containerId).exec();
        } catch (Exception killEx) {
          log.warn("컨테이너 kill 실패 (이미 종료됐을 수 있음): {}", killEx.getMessage());
        }
        return new RunResult(-1, stdoutBuf.toString(), stderrBuf.toString(), null, null);
      }

      return new RunResult(exitCode, stdoutBuf.toString(), stderrBuf.toString(), null, null);

    } catch (SandboxUnavailableException e) {
      throw e;  // 그대로 전파 → GlobalExceptionHandler 503
    } catch (IOException e) {
      throw new SandboxUnavailableException("임시 워크스페이스 생성/파일 쓰기 실패: " + e.getMessage(), e);
    } catch (Exception e) {
      throw new SandboxUnavailableException("DockerRunnerBackend 실행 오류: " + e.getMessage(), e);
    } finally {
      // 컨테이너 삭제 (forceRemove=true: 실행 중이어도 삭제)
      if (containerId != null && docker != null) {
        try {
          docker.removeContainerCmd(containerId).withForce(true).exec();
        } catch (Exception e) {
          log.warn("컨테이너 삭제 실패 (이미 삭제됐을 수 있음): {}", e.getMessage());
        }
      }
      // 임시 디렉터리 삭제
      if (tempDir != null) {
        deleteQuietly(tempDir);
      }
      // DockerClient 닫기
      if (docker != null) {
        try { docker.close(); } catch (Exception e) { /* 무시 */ }
      }
    }
  }

  private static void deleteQuietly(Path dir) {
    try (Stream<Path> walk = Files.walk(dir)) {
      walk.sorted(Comparator.reverseOrder())
          .forEach(p -> {
            try { Files.delete(p); } catch (IOException e) { /* 무시 */ }
          });
    } catch (IOException e) {
      log.warn("임시 디렉터리 삭제 실패: {}", e.getMessage());
    }
  }
}
```

- [ ] **Step 3: 컴파일 확인**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
.\gradlew.bat compileJava
```

Expected: BUILD SUCCESS(`DockerRunnerBackend.java` 컴파일 성공).

- [ ] **Step 4: 기존 단위 테스트 회귀 없음 확인**

> **주의**: B1 `SandboxRunServiceTest`는 `@MockitoBean RunnerBackend runnerBackend`를 사용하므로 `DockerRunnerBackend`가 `@Component`로 등록되어도 mock으로 대체됨. 하지만 Docker 미가동 시 `@SpringBootTest` 컨텍스트 로딩에서 `DockerRunnerBackend` Bean 초기화가 Docker를 호출하지 않아야 한다 — `DockerClientBuilder.getInstance().build()`는 `run()` 메서드 내부에서만 호출하므로 Bean 생성 시 Docker 연결 시도 없음. 단위 테스트는 Docker 없이 통과해야 한다.

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups='!docker'
```

Expected: B1 전 단위 테스트 PASS, Docker 미가동 무관.

- [ ] **Step 5: 커밋**

```powershell
git add src/main/java/ai/devpath/sandbox/run/DockerRunnerBackend.java
git commit -m "feat(docker): add DockerRunnerBackend — multilang, security options, 30s timeout (slice5 B2)"
```

---

## Task 3: DockerRunnerBackendIT — @Tag("docker") 통합 테스트

**Files:**
- Create: `src/test/java/ai/devpath/sandbox/run/DockerRunnerBackendIT.java`

**Interfaces:**
- `@Tag("docker")` 4개 테스트: 언어별 hello(JAVA/NODE/PYTHON 정상 exit 0), 무한루프(타임아웃→KILLED, exitCode=-1), exit≠0(FAILED), 네트워크 차단 확인.
- Docker 데몬이 없는 환경에서는 `assumeTrue(isDockerAvailable())`으로 skip.
- `@SpringBootTest` + `@ActiveProfiles("test")` 사용 시 full context 로딩 비용이 크므로, 이 테스트는 `@SpringBootTest` 없이 `DockerRunnerBackend`를 직접 인스턴스화해 사용한다(의존성 없음 — `@Component`지만 직접 생성 가능).

> **설계 이유**: 통합 테스트는 실제 Docker 소켓과 컨테이너를 사용하므로 Spring 컨텍스트 불필요. 직접 인스턴스화로 테스트 속도를 높이고 DB·Kafka 의존을 배제한다.

- [ ] **Step 1: 실패 테스트 작성** — `src/test/java/ai/devpath/sandbox/run/DockerRunnerBackendIT.java`:

```java
package ai.devpath.sandbox.run;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

import com.github.dockerjava.core.DockerClientBuilder;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * DockerRunnerBackend 통합 테스트.
 *
 * <p>실제 Docker 데몬 + 컨테이너가 필요한다. Docker 미가동 환경(로컬 Windows dev 등)에서는
 * assumeTrue(isDockerAvailable())로 자동 skip.
 *
 * <p>CI(GitHub Actions ubuntu-latest)에서는 Docker가 기본 제공되어 항상 실행됨.
 * @Tag("docker")로 분리 → 단위 테스트(B1)는 -Dgroups='!docker'로 항상 Docker 없이 녹색 보장.
 */
@Tag("docker")
class DockerRunnerBackendIT {

  private DockerRunnerBackend backend;

  @BeforeEach
  void setUp() {
    assumeTrue(isDockerAvailable(),
        "Docker 데몬이 가동 중이 아님 — 통합 테스트 skip (로컬 환경에서 Docker 실행 후 재시도)");
    backend = new DockerRunnerBackend();
  }

  /** Docker 데몬 가용성 확인. ping 실패 시 false 반환. */
  private static boolean isDockerAvailable() {
    try {
      DockerClientBuilder.getInstance().build().pingCmd().exec();
      return true;
    } catch (Exception e) {
      return false;
    }
  }

  // ─── Python: 정상 hello-world ────────────────────────────────────────

  @Test
  void pythonHelloWorldExits0AndLogsOutput() {
    List<String> logs = new ArrayList<>();
    String code = "print('Hello, DevPath!')";
    RunSpec spec = new RunSpec(code, "PYTHON", 1L);

    RunResult result = backend.run(spec, logs::add);

    assertEquals(0, result.exitCode(), "정상 실행은 exit 0");
    assertTrue(logs.stream().anyMatch(l -> l.contains("Hello, DevPath!")),
        "Hello, DevPath! 로그 출력 필요. 실제 logs: " + logs);
  }

  // ─── Node: 정상 hello-world ──────────────────────────────────────────

  @Test
  void nodeHelloWorldExits0AndLogsOutput() {
    List<String> logs = new ArrayList<>();
    String code = "console.log('Hello, DevPath from Node!');";
    RunSpec spec = new RunSpec(code, "NODE", 2L);

    RunResult result = backend.run(spec, logs::add);

    assertEquals(0, result.exitCode(), "정상 실행은 exit 0");
    assertTrue(logs.stream().anyMatch(l -> l.contains("Hello, DevPath from Node!")),
        "Node 출력 로그 필요. 실제 logs: " + logs);
  }

  // ─── Java: 정상 hello-world ──────────────────────────────────────────

  @Test
  void javaHelloWorldExits0AndLogsOutput() {
    List<String> logs = new ArrayList<>();
    // Java 21 single-file source launcher — unnamed class (JEP 445) 또는 public class Main
    String code = """
        void main() {
            System.out.println("Hello, DevPath from Java!");
        }
        """;
    RunSpec spec = new RunSpec(code, "JAVA", 3L);

    RunResult result = backend.run(spec, logs::add);

    assertEquals(0, result.exitCode(),
        "정상 실행은 exit 0. stderr: " + result.stderr() + " logs: " + logs);
    assertTrue(logs.stream().anyMatch(l -> l.contains("Hello, DevPath from Java!")),
        "Java 출력 로그 필요. 실제 logs: " + logs);
  }

  // ─── 타임아웃: 무한루프 → KILLED (exitCode=-1) ────────────────────────

  @Test
  void infiniteLoopIsKilledAfterTimeout() {
    List<String> logs = new ArrayList<>();
    // Python 무한루프 — 30s 타임아웃 초과 → DockerRunnerBackend가 kill → exitCode=-1
    String code = "while True: pass";
    RunSpec spec = new RunSpec(code, "PYTHON", 4L);

    RunResult result = backend.run(spec, logs::add);

    assertEquals(-1, result.exitCode(),
        "타임아웃 kill은 exitCode=-1이어야 함. 실제: " + result.exitCode());
    assertTrue(logs.stream().anyMatch(l -> l.contains("시간 초과") || l.contains("timeout")),
        "타임아웃 메시지 로그 필요. 실제 logs: " + logs);
  }

  // ─── exit≠0: 런타임 에러 → FAILED ────────────────────────────────────

  @Test
  void runtimeErrorResultsInNonZeroExitCode() {
    List<String> logs = new ArrayList<>();
    String code = "print(undefined_variable)";  // NameError → exit 1
    RunSpec spec = new RunSpec(code, "PYTHON", 5L);

    RunResult result = backend.run(spec, logs::add);

    assertNotEquals(0, result.exitCode(),
        "런타임 에러는 exit 0이 아니어야 함. 실제: " + result.exitCode());
    assertTrue(result.exitCode() > 0,
        "Python NameError는 exit 1 이상. 실제: " + result.exitCode());
    assertTrue(logs.stream().anyMatch(l -> l.contains("NameError") || l.contains("Error")),
        "에러 메시지 로그 필요. 실제 logs: " + logs);
  }

  // ─── 네트워크 차단 확인 ─────────────────────────────────────────────────

  @Test
  void networkIsBlockedByNoneMode() {
    List<String> logs = new ArrayList<>();
    // curl 없음(alpine pip install도 차단됨). Python으로 네트워크 시도 → 연결 실패 exit≠0
    String code = """
        import socket
        try:
            socket.create_connection(('8.8.8.8', 53), timeout=3)
            print('NETWORK_REACHABLE')  # 이 라인이 출력되면 테스트 실패
        except OSError as e:
            print('NETWORK_BLOCKED: ' + str(e))
        """;
    RunSpec spec = new RunSpec(code, "PYTHON", 6L);

    RunResult result = backend.run(spec, logs::add);

    // --network none 이면 OS 레벨에서 연결 거부 → NETWORK_BLOCKED 출력, exit 0
    // (예외를 catch해 exit 0으로 종료하는 코드이므로 exit 0도 허용)
    assertTrue(logs.stream().noneMatch(l -> l.contains("NETWORK_REACHABLE")),
        "네트워크가 차단되어야 함(NETWORK_REACHABLE 출력 금지). logs: " + logs);
    assertTrue(logs.stream().anyMatch(l -> l.contains("NETWORK_BLOCKED")),
        "NETWORK_BLOCKED 메시지 출력 필요. logs: " + logs);
  }
}
```

- [ ] **Step 2: 실패 확인 (Docker 가동 시)**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups="docker"
```

Expected: 컴파일 성공 → Docker가 가동 중이면 테스트 실행됨. 이미지 미pull 상태면 `SandboxUnavailableException`(pull 필요 시 수동 pull) 또는 pull 자동 수행. 로컬 Docker 미가동 시 모든 테스트 `assumeTrue` skip(SKIPPED) — 이것도 정상.

> **로컬 이미지 선행 pull (Docker 가동 시 권장):**
> ```powershell
> docker pull eclipse-temurin:21-jdk
> docker pull node:20-alpine
> docker pull python:3.12-slim
> ```

- [ ] **Step 3: 통합 테스트 통과 확인 (Docker 가동 환경)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups="docker" --info 2>&1 | Select-String "PASSED|FAILED|SKIPPED|ERROR"
```

Expected (Docker 가동 시): 6개 테스트 PASSED.
Expected (Docker 미가동 시): 6개 테스트 SKIPPED — 단위 테스트에는 영향 없음.

- [ ] **Step 4: 단위 테스트 회귀 없음 재확인**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups='!docker'
```

Expected: B1 전 단위 테스트 PASS(DockerRunnerBackendIT 제외).

- [ ] **Step 5: 커밋**

```powershell
git add src/test/java/ai/devpath/sandbox/run/DockerRunnerBackendIT.java
git commit -m "test(docker): add DockerRunnerBackendIT integration tests @Tag(docker) (slice5 B2)"
```

---

## Task 4: ci.yml — docker 통합 테스트 step 추가

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- `build` job에 단계를 추가: 기존 `./gradlew build`(단위 테스트 포함)는 그대로 유지 + 별도 step으로 `./gradlew test -Dgroups=docker`를 추가.
- GitHub Actions `ubuntu-latest`는 Docker 데몬이 기본 제공되므로 별도 서비스 설정 불필요.
- `build` job은 두 단계: (a) `./gradlew build`(단위 테스트 포함) → (b) `./gradlew test -Dgroups=docker`(Docker 통합 테스트).
- **이미지 pull 최적화**: `docker pull` step을 통합 테스트 전에 추가해 타임아웃 시간 내에 컨테이너 실행 시간을 보장한다.
- `continue-on-error: false` — 통합 테스트 실패 시 CI 전체 실패.

- [ ] **Step 1: 현재 ci.yml 확인 (이미 읽음)**

현재 `build` job은:
```yaml
- run: ./gradlew build
  env:
    DB_URL: jdbc:postgresql://localhost:5432/devpath
    DB_USER: devpath
    DB_PASSWORD: localdev
    GITHUB_ACTOR: ${{ github.actor }}
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: ci.yml 수정** — `.github/workflows/ci.yml`의 `build` job `steps`에 다음 두 step을 추가한다(기존 `./gradlew build` step 뒤에 순서대로):

추가할 step (기존 `./gradlew build` step 뒤에 삽입):
```yaml
      - name: Pull sandbox images for integration tests
        run: |
          docker pull eclipse-temurin:21-jdk
          docker pull node:20-alpine
          docker pull python:3.12-slim

      - name: Run Docker integration tests
        run: ./gradlew test -Dgroups=docker
        env:
          DB_URL: jdbc:postgresql://localhost:5432/devpath
          DB_USER: devpath
          DB_PASSWORD: localdev
          GITHUB_ACTOR: ${{ github.actor }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

최종 `build` job `steps`:
```yaml
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: 21
      - uses: gradle/actions/setup-gradle@v6
      - run: ./gradlew build
        env:
          DB_URL: jdbc:postgresql://localhost:5432/devpath
          DB_USER: devpath
          DB_PASSWORD: localdev
          GITHUB_ACTOR: ${{ github.actor }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Pull sandbox images for integration tests
        run: |
          docker pull eclipse-temurin:21-jdk
          docker pull node:20-alpine
          docker pull python:3.12-slim
      - name: Run Docker integration tests
        run: ./gradlew test -Dgroups=docker
        env:
          DB_URL: jdbc:postgresql://localhost:5432/devpath
          DB_USER: devpath
          DB_PASSWORD: localdev
          GITHUB_ACTOR: ${{ github.actor }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> **설계 근거**: 단위 테스트(`./gradlew build`)와 Docker 통합 테스트(`-Dgroups=docker`)를 분리해, 단위 테스트가 먼저 녹색인지 확인한 뒤 Docker 통합 테스트를 실행한다. `./gradlew build`는 `-Dgroups='!docker'` 없이 실행하지만, `DockerRunnerBackendIT`는 `assumeTrue(isDockerAvailable())`로 Docker 미가동 시 skip — 실제 GitHub Actions에선 Docker가 가동되므로 두 번째 step(`-Dgroups=docker`)에서 실행됨.
>
> **교훈 반영(슬라이스 #2/#3)**: "로컬 Docker가 CI를 가린다" — Docker 통합 테스트를 CI에서 실증하고, 단위 테스트(B1)는 Docker 없이도 항상 녹색임을 보장한다.

- [ ] **Step 3: YAML 문법 확인**

```powershell
# ci.yml을 읽어 들여쓰기가 올바른지 확인
cat D:\workspace\dev-path-ai\devpath-sandbox-svc\.github\workflows\ci.yml
```

Expected: `steps` 하위에 총 6개 step이 올바른 들여쓰기로 존재.

- [ ] **Step 4: 커밋**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: add docker image pull + integration test step for DockerRunnerBackend (slice5 B2)"
```

---

## Task 5: 전체 검증 + develop PR

**Files:**
- No new files — 전체 검증 + PR 생성.

- [ ] **Step 1: 단위 테스트 전체 회귀 (Docker 불요)**

```powershell
cd D:\workspace\dev-path-ai\devpath-sandbox-svc
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat clean test -Dgroups='!docker'
```

Expected: BUILD SUCCESSFUL. B1 전 단위 테스트 PASS. DockerRunnerBackendIT는 제외.

- [ ] **Step 2: Docker 통합 테스트 (Docker 가동 시 로컬 검증)**

```powershell
$env:DB_URL="jdbc:postgresql://localhost:5432/devpath_citest"
.\gradlew.bat test -Dgroups="docker" --info 2>&1 | Select-String "PASSED|FAILED|SKIPPED|ERROR"
```

Expected (Docker 가동 시):
```
DockerRunnerBackendIT > pythonHelloWorldExits0AndLogsOutput() PASSED
DockerRunnerBackendIT > nodeHelloWorldExits0AndLogsOutput() PASSED
DockerRunnerBackendIT > javaHelloWorldExits0AndLogsOutput() PASSED
DockerRunnerBackendIT > infiniteLoopIsKilledAfterTimeout() PASSED
DockerRunnerBackendIT > runtimeErrorResultsInNonZeroExitCode() PASSED
DockerRunnerBackendIT > networkIsBlockedByNoneMode() PASSED
```

Expected (Docker 미가동 시): 전부 SKIPPED — CI에서 실증할 것.

- [ ] **Step 3: 컴파일 경고 없음 확인**

```powershell
.\gradlew.bat compileJava compileTestJava 2>&1 | Select-String "warning|error" | Select-String -NotMatch "^Note:"
```

Expected: 출력 없음.

- [ ] **Step 4: develop PR 생성**

```powershell
git push -u origin feat/sandbox-docker-b2
gh pr create --base develop --title "feat(sandbox-svc): DockerRunnerBackend multilang isolation + CI docker integration tests (slice5 B2)" --body "MD2 슬라이스 #5 빌드 B2.

## 변경 내용
- build.gradle.kts: docker-java-core + docker-java-transport-httpclient5 3.5.1 추가
- DockerRunnerBackend: RunnerBackend 구현 — Java21/Node20/Python3.12 온디맨드 컨테이너
  - 보안 옵션(§7): --network none, --memory 512m, --cpus 1, --pids-limit 128, --user nobody, --read-only, --cap-drop ALL, --security-opt no-new-privileges, tmpfs /tmp
  - 30s 타임아웃 → SIGKILL → exitCode=-1(KILLED)
  - finally: 컨테이너 삭제 + 임시 디렉터리 삭제
- DockerRunnerBackendIT: @Tag(docker) 통합 테스트 6개
  - Python/Node/Java hello-world(exit 0), 무한루프(KILLED), exit≠0(FAILED), 네트워크 차단
- ci.yml: docker pull + ./gradlew test -Dgroups=docker step 추가 (ubuntu-latest Docker 활용)

## 선행 관계
- 빌드 A(devpath-shared): sandbox_sessions + SandboxRunSubmittedEvent (develop 머지 완료)
- 빌드 B1(sandbox-svc 코어): RunnerBackend 인터페이스 + SandboxRunService + outbox (develop 머지 완료)

## 테스트
- 단위 테스트(B1): Docker 없이 항상 PASS (./gradlew build)
- Docker 통합 테스트: CI ubuntu-latest에서 ./gradlew test -Dgroups=docker 실증

설계서: docs/superpowers/specs/2026-06-22-md2-slice5-sandbox-design.md
플랜: docs/superpowers/plans/2026-06-22-md2-slice5-sandbox-docker-b2.md"
gh pr checks --watch
```

Expected: CI `build` job — (1) 단위 테스트 PASS → (2) docker pull → (3) Docker 통합 테스트 PASS. 전체 녹색 확인 후 머지(컨트롤러 직접 검증: `git log`, 파일 구조, CI 로그).

---

## Self-Review 메모 (작성자)

### Spec 커버리지
- §3 DockerRunnerBackend: 이미지·온디맨드·코드 주입·마운트(ro)·언어별 실행·로그 콜백·컨테이너 삭제 — Task 2 커버.
- §7 보안 다층격리: `--network none`, `--memory 512m`, `--cpus 1`, `--pids-limit`, `--user nobody`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, tmpfs `/tmp` — Task 2 HostConfig에 전부 적용.
- §8 테스트 전략: 통합(`@Tag("docker")`·CI Docker) — hello(정상)·타임아웃(30s→KILLED)·exit≠0(FAILED)·네트워크 차단 — Task 3 커버. "로컬 Docker가 CI를 가린다" 교훈 반영(assumeTrue skip + CI step 분리). 단위 테스트 항상 녹색 보장.

### docker-java API — 확인된 것만 사용 (NEEDS_CONTEXT 없음)
- `HostConfig.newHostConfig().withMemory(Long)` — GitHub 소스 확인.
- `HostConfig.withCpuCount(Long)` — GitHub 소스 확인.
- `HostConfig.withPidsLimit(Long)` — GitHub 소스 확인.
- `HostConfig.withNetworkMode(String)` — GitHub 소스 확인.
- `HostConfig.withReadonlyRootfs(Boolean)` — GitHub 소스 확인.
- `HostConfig.withCapDrop(Capability...)` — GitHub 소스 확인.
- `HostConfig.withSecurityOpts(List<String>)` — GitHub 소스 확인.
- `HostConfig.withTmpFs(Map<String,String>)` — GitHub 소스 확인.
- `HostConfig.withBinds(Bind...)` — GitHub 소스 확인.
- `CreateContainerCmd.withUser(String)` — GitHub 소스 확인(컨테이너 레벨, HostConfig.withUsernsMode와 다름).
- `ResultCallback.Adapter<Frame>.onNext(Frame)` — GitHub 소스 확인.
- `Frame.getPayload()` → `byte[]`, `Frame.getStreamType()` → `StreamType(STDOUT/STDERR)` — GitHub 소스 확인.
- `WaitContainerResultCallback.awaitStatusCode(long, TimeUnit)` → `Integer` — GitHub 소스 확인.
- `killContainerCmd(id).exec()` — docker-java wiki 확인.
- `removeContainerCmd(id).withForce(true).exec()` — docker-java wiki 확인.
- Artifact: `com.github.docker-java:docker-java-core:3.5.1` + `com.github.docker-java:docker-java-transport-httpclient5:3.5.1` — Maven Central 확인(latestVersion 3.5.1).

### Java single-file launcher (java Main.java) 결정 근거
- Java 11+: `java FileName.java`로 single-file source 직접 실행. Java 21 JEP 445: unnamed class(void main() 지원). `public class Main { public static void main(String[] args){} }` 형식도 동작. 30s 제한 내 javac 없이 실행 가능 — javac+java 2단계 대비 유리.
- 제약: 단일 파일, 멀티 public class 분리 불가 — MVP 수준에서 수용(학습 실습 코드는 단일 파일).
- 통합 테스트에서 `void main()` unnamed class 형식으로 검증.

### No placeholder
- 모든 Task에 실코드(패키지명·클래스명·메서드 시그니처·어노테이션 포함). "TBD"/"적절히" 없음.

### 교훈 반영
- "로컬 Docker가 CI를 가린다"(슬라이스 #2/#3): `assumeTrue(isDockerAvailable())`로 로컬 skip 허용 + CI(ubuntu-latest) docker 통합 테스트 실증 필수.
- 단위 테스트(B1)는 `-Dgroups='!docker'` 또는 `assumeTrue` skip으로 항상 Docker 없이 녹색.
- DockerClient를 `run()` 메서드 내부에서 생성·닫기 → Bean 생성 시 Docker 연결 없음 → 단위 테스트 컨텍스트 로딩 시 Docker 소켓 접근 없음.

### 타임아웃 설계
- `logContainerCmd.awaitCompletion(30, SECONDS)`: 로그 스트림이 30s 내 완료되지 않으면 InterruptedException → `timedOut[0]=true`.
- `waitContainerCmd.awaitStatusCode(30, SECONDS)`: exit code를 30s 내 수집 못하면 예외 → `timedOut[0]=true`.
- 타임아웃 감지 시 `killContainerCmd(id).exec()` → `exitCode=-1` 반환 → `SandboxRunService`가 `KILLED` 상태로 기록.
- finally에서 `removeContainerCmd(id).withForce(true).exec()` — kill 여부 무관 컨테이너 항상 삭제.
