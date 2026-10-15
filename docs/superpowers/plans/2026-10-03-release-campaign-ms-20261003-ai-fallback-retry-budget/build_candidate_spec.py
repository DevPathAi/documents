"""6단계 — ms-20261003-ai-fallback-retry-budget candidate spec 을 10/02 spec 에서 파생.

재바인딩되는 필드만 바뀐다. 각 필드는 바꾸기 전에 옛 값을 단언하고,
마지막에 **바뀐 필드 집합을 정확히** 단언한다(r3·9/23·10/02 캠페인과 같은 패턴).

10/02 대비 변경 집합:
  · 같다 — gitops base·frontend(off/on/admin)·ai-svc·홈 preview·frontend 카탈로그 재바인딩.
  · ★넓다 — 두 필드가 새로 바뀐다★
    - `analytics_privacy.approval_source_sha`: documents main 이 #208 로 움직였다(7f732ac5 → f52b4a9a).
      10/02 에는 documents main 이 r3 와 같아서 이 필드가 변경 집합에 없었다.
    - `ai_release_eval_config.rendered_config_sha256`: gitops base 가 a97a1754(폴백 publisher)로 바뀌어
      apps/devpath-ai-svc/base 렌더가 달라졌다(리뷰 M3). compute_ai_rendered_config.py 로 계산한 값이며,
      방법 증명(eb413814 → bfa0126d…)을 먼저 통과했다.
  · 홈은 무변경(master abdf57a7·dist 51e8ef83 재계산 일치).

Usage: build_candidate_spec.py <gitops worktree at NEW_BASE>
"""

import copy
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

ART = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget")
GITOPS = "D:/workspace/dpa/devpath-gitops"
DOCUMENTS = "D:/workspace/dpa/documents"
WORKTREE = pathlib.Path(sys.argv[1])

OLD_ID = "ms-20261002-ai-provider-fallback-gpu7b"
OLD_SPEC_SHA = "3423b8be5cde26420ed34f040447ce8db1ef516c7057ab76db7b57e5891a58a2"
OLD_BASE = "eb413814c9a813d84b8e1b2c7f5d69979b18bb02"
# 10/02 spec 의 prior_identity 가 가리키던 릴리스(= 10/02 의 직전). 이번에는 10/02 자신이 prior 가 된다.
OLDER_ID = "ms-20260930-s3-web-redesign-r3"
OLDER_SPEC_SHA = "ef51e3ef8f71decfdebfbe5b4dbb1e3b7d7edc989265b9ce7c5595bee0407e0f"
OLD_WEB_BASE_DIGEST = "sha256:3a6ab8dbca5d362632c22c5cf2a01afe6430db33802608bb3f5bcf5e606a211a"
OLD_WEB_BASE_TAG_SHA = "9c7efee38a83e250848ee023da46e6fe1fafe438"
OLD_APPROVAL_SOURCE = "7f732ac5ba31a91e81ea4e557cb7f67c8ee5ca36"
OLD_RENDERED_CONFIG = "bfa0126d2cd8f97245ead1ab9d4c3c0fb2b20e3c29025055fa4f743554dbd41e"

coords = json.loads((ART / "coords.json").read_text(encoding="utf-8"))
NEW_ID = coords["release_id"]

NEW_BASE = coords["gitops"]["base_sha"]
PROD_WEB_DIGEST = coords["gitops"]["base_web_digest"]       # 현재 운영 웹 = 10/02 mission-on
RENDERED_CONFIG = coords["gitops"]["ai_rendered_config_sha256"]
OLD_FRONTEND = coords["frontend"]["main_before_release"]     # 10/02 의 frontend main
FRONTEND = coords["frontend"]["main"]
WEB_OFF = coords["frontend"]["web_mission_off"]
WEB_ON = coords["frontend"]["web_mission_on"]
ADMIN = coords["frontend"]["admin"]
AI_SVC_SHA = coords["ai_svc"]["main"]
AI_SVC_DIGEST = coords["ai_svc"]["image_digest"]
AI_SVC_PRIOR_DIGEST = coords["ai_svc"]["prior_image_digest"]
DOCUMENTS_MAIN = coords["documents"]["main"]
HOME_MASTER = coords["home"]["master"]
HOME_DIST = coords["home"]["dist_sha256"]
HOME_PREVIEW_ID = coords["home"]["candidate_deployment_id"]
HOME_PREVIEW_ORIGIN = coords["home"]["candidate_preview_url"]
HOME_PRIOR_PROD = coords["home"]["prior_production_deployment_id"]
BASE = coords["et13_baseline"]
PROV = coords["frontend"]["provenance"]


def sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def git(*args: str, repo: str = GITOPS) -> bytes:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout


old_raw = git(
    "show",
    f"origin/release/candidate-{OLD_ID}:release-manifests/candidates/{OLD_ID}.candidate-spec.json",
)
assert hashlib.sha256(old_raw).hexdigest() == OLD_SPEC_SHA
old_text = old_raw.decode("utf-8")
old = json.loads(old_text)

spec = copy.deepcopy(old)
spec["release_id"] = NEW_ID
spec["created_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---- gitops base: 10/02 가 승격시킨 상태 + 폴백 publisher(a97a1754)가 지금 운영이다 ------
assert spec["gitops"]["base_sha"] == OLD_BASE
assert git("rev-parse", "origin/main").decode().strip() == NEW_BASE
kustomization = git("show", f"{NEW_BASE}:{spec['gitops']['web_kustomization']}")
assert PROD_WEB_DIGEST.encode() in kustomization and OLD_ID.encode() in kustomization, (
    "web base is not 10/02 mission-on"
)
assert spec["gitops"]["base_web_digest"] == OLD_WEB_BASE_DIGEST
assert spec["gitops"]["base_web_tag"] == f"{OLD_WEB_BASE_TAG_SHA}-mission-on"
assert spec["frontend"]["mission_on"]["image_digest"] == PROD_WEB_DIGEST
assert spec["frontend"]["mission_on"]["tag"] == f"{OLD_FRONTEND}-mission-on"
spec["gitops"]["base_sha"] = NEW_BASE
spec["gitops"]["base_web_tag"] = f"{OLD_FRONTEND}-mission-on"
spec["gitops"]["base_web_digest"] = PROD_WEB_DIGEST

# ---- frontend: web off/on·admin 이 전부 새 이미지다 --------------------------------
fe = spec["frontend"]
assert fe["source_sha"] == OLD_FRONTEND
assert fe["app_version"] == OLD_ID
fe["source_sha"] = FRONTEND
fe["app_version"] = NEW_ID
fe["mission_off"]["tag"] = f"{FRONTEND}-mission-off"
fe["mission_off"]["image_digest"] = WEB_OFF
fe["mission_on"]["tag"] = f"{FRONTEND}-mission-on"
fe["mission_on"]["image_digest"] = WEB_ON
fe["selected_on_digest"] = WEB_ON

rollback = fe["rollback"]
assert rollback["prior_identity"]["release_id"] == OLDER_ID
assert rollback["prior_identity"]["candidate_spec_sha256"] == OLDER_SPEC_SHA
rollback["mission_off_digest"] = WEB_OFF
rollback["prior_digest"] = PROD_WEB_DIGEST
rollback["prior_identity"] = {
    "ready": True,
    "release_id": OLD_ID,
    "candidate_spec_sha256": OLD_SPEC_SHA,
    "image_digest": PROD_WEB_DIGEST,
}
# validate_release_manifest.py:993-996 — prior 는 base 웹과 같고 두 후보와는 달라야 한다.
assert rollback["prior_digest"] == PROD_WEB_DIGEST
assert len({WEB_OFF, WEB_ON, ADMIN, PROD_WEB_DIGEST}) == 4

# ---- services: admin + ★ai-svc★. 나머지 7곳은 그대로 ------------------------------
svc = spec["services"]
admin = svc["devpath-admin"]
assert list(admin) == ["repository", "source_sha", "image_repository", "image_digest"]
assert admin["source_sha"] == OLD_FRONTEND and admin["image_digest"] != ADMIN
admin["source_sha"], admin["image_digest"] = FRONTEND, ADMIN

ai = svc["devpath-ai-svc"]
assert list(ai) == ["repository", "source_sha", "image_repository", "image_digest"]
assert ai["source_sha"] == coords["ai_svc"]["main_before_release"], "ai-svc base moved"
assert ai["image_digest"] == AI_SVC_PRIOR_DIGEST, "ai-svc prior digest mismatch"
assert AI_SVC_DIGEST != AI_SVC_PRIOR_DIGEST
ai["source_sha"], ai["image_digest"] = AI_SVC_SHA, AI_SVC_DIGEST

untouched = {k: v for k, v in svc.items() if k not in ("devpath-admin", "devpath-ai-svc")}
assert len(untouched) == 7
for name, value in untouched.items():
    assert value == old["services"][name], name

# ---- ★analytics_privacy: documents main 이 움직였다★ -------------------------------
privacy = spec["analytics_privacy"]
assert privacy["approval_source_sha"] == OLD_APPROVAL_SOURCE
assert git("rev-parse", "origin/main", repo=DOCUMENTS).decode().strip() == DOCUMENTS_MAIN, "documents main moved"
privacy["approval_source_sha"] = DOCUMENTS_MAIN

# ---- ★ai_release_eval_config: gitops base 의 AI 렌더 해시★ --------------------------
evaluation = spec["ai_release_eval_config"]
assert evaluation["rendered_config_sha256"] == OLD_RENDERED_CONFIG
assert RENDERED_CONFIG != OLD_RENDERED_CONFIG
evaluation["rendered_config_sha256"] = RENDERED_CONFIG

# ---- home: ★무변경★. preview 배포 id 와 직전 운영 배포만 새로 가리킨다 --------------
home = spec["home"]
assert list(home) == [
    "repository", "source_sha", "dist_sha256", "cloudflare_account_id",
    "cloudflare_project", "candidate_deployment_id", "prior_production_deployment_id",
]
assert home["cloudflare_account_id"] == coords["home"]["cloudflare_account_id"]
assert home["source_sha"] == HOME_MASTER, "home master moved — 이번 릴리스는 홈 무변경이다"
assert home["dist_sha256"] == HOME_DIST, "home dist moved — 재현 실측과 어긋난다"
home["candidate_deployment_id"] = HOME_PREVIEW_ID
assert home["prior_production_deployment_id"] == "d09631a6-fb7b-4999-99a5-d94632132261"
home["prior_production_deployment_id"] = HOME_PRIOR_PROD

assert spec["environments"]["staging"]["landing_origin"].startswith("https://f563bd8d.")
spec["environments"]["staging"]["landing_origin"] = HOME_PREVIEW_ORIGIN
assert spec["journey_harness"]["landing_origin"] == "https://leva.ai.kr"

# ---- quality evidence catalogs ---------------------------------------------------
cat = spec["quality_evidence_inputs"]["catalogs"]

BASELINE_DIR = pathlib.Path(BASE["dir"])
approval = json.loads((BASELINE_DIR / "baseline-approval.v1.json").read_text(encoding="utf-8"))
assert approval["source_sha"] == FRONTEND
assert approval["approval_run_id"] == int(BASE["approval_run_id"])
assert approval["case_catalog_sha256"] == cat["frontend-visual"]["sha256"], "case catalog moved"

prov = {
    lane: json.loads(
        (ART / "candidate-provenance" / f"{lane}-provenance.v1.json").read_text(encoding="utf-8")
    )
    for lane in ("visual", "a11y")
}

# frontend 카탈로그 3종은 source_sha 가 candidate producer 를 정확히 물어야 한다
# (validate_release_manifest.py:727-728).
for key in ("frontend-visual", "frontend-automated-a11y", "manual-nvda"):
    assert cat[key]["source_sha"] == OLD_FRONTEND, key
    cat[key]["source_sha"] = FRONTEND

cat["frontend-visual"]["baseline_set_sha256"] = approval["candidate_set_sha256"]
cat["frontend-visual"]["baseline_approval_sha256"] = sha(BASELINE_DIR / "baseline-approval.v1.json")

for lane, key in (("visual", "frontend-visual"), ("a11y", "frontend-automated-a11y")):
    assert prov[lane]["baseline_authentication"]["release_id"] == NEW_ID, lane
    assert prov[lane]["source_sha"] == FRONTEND, lane
    assert prov[lane]["baseline_authentication"]["artifact_id"] == int(
        BASE["approved_artifact_id"]
    ), lane
    cat[key]["input_provenance_sha256"] = prov[lane]["input_provenance_sha256"]
    cat[key]["input_provenance_file_sha256"] = sha(
        ART / "candidate-provenance" / f"{lane}-provenance.v1.json"
    )
    assert cat[key]["input_provenance_sha256"] == PROV[lane]["input_provenance_sha256"], lane
    assert cat[key]["input_provenance_file_sha256"] == PROV[lane]["input_provenance_file_sha256"], lane

# 홈 카탈로그는 손대지 않는다 — master 가 10/02 와 동일한 커밋이고 dist 재계산으로 실증했다.
for key in ("home-visual", "home-axe-browser-a11y"):
    lane = cat[key]
    assert lane["sha256"] == coords["home"]["catalog_sha256"], "home catalog moved"
    assert lane["path"] == "e2e/visual/case-catalog.v2.json"
    assert lane["source_sha"] == HOME_MASTER, "home catalog source moved"
    assert lane["rendered_product_sha"] == coords["home"]["rendered_product_sha"]
    assert lane["rendered_product_tree_sha256"] == coords["home"]["rendered_product_tree_sha256"]

# ---- 직렬화 --------------------------------------------------------------------
indent = len(old_text.split("\n")[1]) - len(old_text.split("\n")[1].lstrip(" "))
assert (json.dumps(old, indent=indent, ensure_ascii=False) + "\n").encode("utf-8") == old_raw, (
    "cannot reproduce serialization"
)
out = WORKTREE / "release-manifests/candidates" / f"{NEW_ID}.candidate-spec.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes((json.dumps(spec, indent=indent, ensure_ascii=False) + "\n").encode("utf-8"))


def flat(obj, prefix=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from flat(value, f"{prefix}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from flat(value, f"{prefix}[{index}]")
    else:
        yield prefix, obj


before, after = dict(flat(old)), dict(flat(spec))
assert before.keys() == after.keys(), "key set changed"
changed = sorted(key for key in before if before[key] != after[key])
expected = sorted(
    [
        ".created_at", ".release_id",
        ".gitops.base_sha", ".gitops.base_web_tag", ".gitops.base_web_digest",
        ".frontend.app_version", ".frontend.source_sha",
        ".frontend.mission_off.tag", ".frontend.mission_off.image_digest",
        ".frontend.mission_on.tag", ".frontend.mission_on.image_digest",
        ".frontend.selected_on_digest",
        ".frontend.rollback.mission_off_digest",
        ".frontend.rollback.prior_digest",
        ".frontend.rollback.prior_identity.release_id",
        ".frontend.rollback.prior_identity.candidate_spec_sha256",
        ".frontend.rollback.prior_identity.image_digest",
        ".services.devpath-admin.source_sha", ".services.devpath-admin.image_digest",
        # ★이번 릴리스의 주 목적★
        ".services.devpath-ai-svc.source_sha", ".services.devpath-ai-svc.image_digest",
        # ★10/02 에 없던 두 필드★
        ".analytics_privacy.approval_source_sha",
        ".ai_release_eval_config.rendered_config_sha256",
        # 홈은 무변경이므로 source_sha·dist_sha256 는 여기 없다.
        ".home.candidate_deployment_id", ".home.prior_production_deployment_id",
        ".environments.staging.landing_origin",
        # baseline_set_sha256 는 바뀌지 않는다 — 기준선 104/104 무변경이라 승인 PNG 세트가 바이트 동일하다.
        ".quality_evidence_inputs.catalogs.frontend-visual.baseline_approval_sha256",
        ".quality_evidence_inputs.catalogs.manual-nvda.source_sha",
    ]
    + [
        f".quality_evidence_inputs.catalogs.{k}.{f}"
        for k in ("frontend-visual", "frontend-automated-a11y")
        for f in ("source_sha", "input_provenance_sha256", "input_provenance_file_sha256")
    ]
)
assert changed == expected, sorted(set(changed) ^ set(expected))

print("written:", out.name, "| sha256:", sha(out), "| CR:", out.read_bytes().count(b"\r"))
print("changed fields:", len(changed), "(exactly the expected set)")
text = out.read_text(encoding="utf-8")

# 아예 남아 있으면 안 되는 값들. OLD_ID 와 OLD_FRONTEND 는 여기 넣지 않는다 —
# 각각 rollback.prior_identity.release_id 와 gitops.base_web_tag 로 **정당하게** 남는다.
stale = [
    n
    for n in (
        OLD_BASE,                       # 10/02 의 gitops base
        OLDER_ID, OLDER_SPEC_SHA,       # 10/02 의 prior_identity(r3)
        OLD_WEB_BASE_DIGEST, OLD_WEB_BASE_TAG_SHA,   # 10/02 의 base 웹(r3)
        "ed8ce273",                     # 10/02 mission_off digest
        "4c93a285",                     # 10/02 admin digest
        "107fd20a",                     # 직전 ai-svc digest
        "83cfe792",                     # 직전 ai-svc main
        "f563bd8d",                     # 10/02 홈 preview
        "d09631a6",                     # 그 전 운영 배포
        "9d6674b2", "592a9174",         # 10/02 input provenance
        "d7fdac8b", "5dc1badf",         # 10/02 input provenance file
        OLD_APPROVAL_SOURCE[:8],        # 옛 documents main
        OLD_RENDERED_CONFIG[:8],        # 옛 AI 렌더 해시
    )
    if n in text
]
print("stale scan (should be empty):", stale)

assert text.count(f'"{OLD_ID}"') == 1, ("OLD_ID occurrences", text.count(f'"{OLD_ID}"'))
assert text.count(OLD_FRONTEND) == 1, ("OLD_FRONTEND occurrences", text.count(OLD_FRONTEND))
print(f"expected survivors: prior_identity.release_id={OLD_ID} · base_web_tag={OLD_FRONTEND[:8]}…-mission-on")
assert not stale
print("ai-svc:", AI_SVC_PRIOR_DIGEST[:20], "->", AI_SVC_DIGEST[:20])
print("privacy approval source:", OLD_APPROVAL_SOURCE[:8], "->", DOCUMENTS_MAIN[:8])
print("ai rendered config:", OLD_RENDERED_CONFIG[:8], "->", RENDERED_CONFIG[:8])
print("home: unchanged (master", HOME_MASTER[:8], "dist", HOME_DIST[:12], ")")
