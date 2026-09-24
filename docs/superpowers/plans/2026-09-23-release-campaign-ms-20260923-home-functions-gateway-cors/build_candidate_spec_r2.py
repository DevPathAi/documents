"""Derive the ms-20260923-home-functions-gateway-cors-r2 candidate spec from the validator-accepted r3 spec.

The frontend was rebuilt (README-only commit) so that the candidate web images differ from production, as the
release contract requires. Only re-bound fields change; each is asserted, and the changed-field set is asserted exactly.
Usage: build_candidate_spec_r2.py <coords-r2.json> <gitops worktree at NEW_BASE>
"""
import copy
import datetime as dt
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile

coords = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
WORKTREE = pathlib.Path(sys.argv[2])
ART = pathlib.Path(coords["out_dir"])
OLD_ID = "ms-20260920-community-flat-pages-r3"
NEW_ID = coords["release_id"]
GITOPS = "D:/workspace/dpa/devpath-gitops"
FRONTEND_REPO = "D:/workspace/dpa/devpath-frontend"
OLD_SPEC_SHA = "b5ede99fa46a753202d9a4da1218c6fb9de1e7f0516063211648a4fd4c84cbcd"
OLD_BASE = "fcf97cf686df8e8bad56597d4679f9a96fd597fc"
NEW_BASE = coords["gitops_base_sha"]
OLD_FE = "31a7785d5f3c73563c8ddb61b69a7a0e07f65f16"
NEW_FE = coords["frontend_sha"]
PROD_WEB_TAG = f"{OLD_FE}-mission-on"
PROD_WEB_DIGEST = "sha256:a6466f5de1714e12b7fcd01766e0fc0e4f61cf4dab4e6155ea0948ee3fb1c4e1"
WEB_OFF, WEB_ON, ADMIN = coords["web_off_digest"], coords["web_on_digest"], coords["admin_digest"]
home_c = coords["home"]


def sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def git(repo: str, *args: str) -> bytes:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout


def frontend_blob_sha(path: str) -> str:
    return hashlib.sha256(git(FRONTEND_REPO, "show", f"{NEW_FE}:{path}")).hexdigest()


old_raw = git(GITOPS, "show", f"origin/release/candidate-{OLD_ID}:release-manifests/candidates/{OLD_ID}.candidate-spec.json")
assert hashlib.sha256(old_raw).hexdigest() == OLD_SPEC_SHA
old_text = old_raw.decode("utf-8")
old = json.loads(old_text)
gateway = json.loads((ART / "image-evidence" / "gateway.json").read_text(encoding="utf-8"))
approval = json.loads((pathlib.Path(coords["baseline"]["dir"]) / "baseline-approval.v1.json").read_text(encoding="utf-8"))
prov_dir = ART / "candidate-provenance"
prov = {lane: json.loads((prov_dir / f"{lane}-provenance.v1.json").read_text(encoding="utf-8")) for lane in ("visual", "a11y")}
for digest in (WEB_OFF, WEB_ON, ADMIN):
    assert digest.startswith("sha256:") and len(digest) == 71, digest
assert len({WEB_OFF, WEB_ON, ADMIN, PROD_WEB_DIGEST}) == 4, "digests must be distinct"
assert git(FRONTEND_REPO, "rev-parse", "origin/main").decode().strip() == NEW_FE, "frontend main moved"
assert git(FRONTEND_REPO, "rev-parse", f"{NEW_FE}^{{tree}}") != git(FRONTEND_REPO, "rev-parse", f"{OLD_FE}^{{tree}}")

spec = copy.deepcopy(old)
spec["release_id"] = NEW_ID
spec["created_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# gitops base and the web image production runs now (r3 mission-on)
assert spec["gitops"]["base_sha"] == OLD_BASE
assert git(GITOPS, "rev-parse", "origin/main").decode().strip() == NEW_BASE
kustomization = git(GITOPS, "show", f"{NEW_BASE}:{spec['gitops']['web_kustomization']}")
assert PROD_WEB_DIGEST.encode() in kustomization and OLD_ID.encode() in kustomization
assert spec["frontend"]["mission_on"]["image_digest"] == PROD_WEB_DIGEST
spec["gitops"]["base_sha"] = NEW_BASE
spec["gitops"]["base_web_tag"] = PROD_WEB_TAG
spec["gitops"]["base_web_digest"] = PROD_WEB_DIGEST

# ai release eval: the AI kustomize render changes with the base (5961922b adds a startupProbe), and the ai-svc
# validator + the gitops seal re-render apps/devpath-ai-svc/base at base_sha and compare the sha256 (r2 lesson).
KUSTOMIZE = coords["kustomize_exe"]


def render_ai(sha: str) -> str:
    with tempfile.TemporaryDirectory(prefix="ai-render-") as td:
        src = pathlib.Path(td) / "src"
        src.mkdir()
        archive = git(GITOPS, "archive", sha, "apps/devpath-ai-svc/base")
        with tarfile.open(fileobj=io.BytesIO(archive)) as tf:
            tf.extractall(src, filter="data")
        out = subprocess.run([KUSTOMIZE, "build", "apps/devpath-ai-svc/base"], cwd=src, capture_output=True, check=True).stdout
    assert out and b"\r" not in out and out.endswith(b"\n") and out.decode("utf-8").encode("utf-8") == out
    return hashlib.sha256(out).hexdigest()


assert subprocess.run([KUSTOMIZE, "version"], capture_output=True, check=True).stdout.strip() == b"v5.4.3"
ai_cfg = spec["ai_release_eval_config"]
assert ai_cfg["rendered_config_sha256"] == render_ai(OLD_BASE) == "bb9f18df1edaa01580079905c912e9ce3394b79e3d41a8987adf8d88eacf0c90"
new_rendered = render_ai(NEW_BASE)
assert new_rendered == coords["ai_rendered_config_sha256"] != ai_cfg["rendered_config_sha256"], new_rendered
ai_cfg["rendered_config_sha256"] = new_rendered

# frontend: rebuilt source and images
fe = spec["frontend"]
assert fe["source_sha"] == OLD_FE and fe["app_version"] == OLD_ID
fe["source_sha"], fe["app_version"] = NEW_FE, NEW_ID
fe["mission_off"] = {"tag": f"{NEW_FE}-mission-off", "image_digest": WEB_OFF}
fe["mission_on"] = {"tag": f"{NEW_FE}-mission-on", "image_digest": WEB_ON}
fe["selected_on_digest"] = WEB_ON
rb = fe["rollback"]
assert rb["prior_identity"]["release_id"] == "ms-20260916-community-ia" and rb["final_target"] == "prior"
rb["mission_off_digest"] = WEB_OFF
rb["prior_digest"] = PROD_WEB_DIGEST
rb["prior_identity"] = {"ready": True, "release_id": OLD_ID, "candidate_spec_sha256": OLD_SPEC_SHA, "image_digest": PROD_WEB_DIGEST}

# services: admin (rebuilt with the frontend) and gateway (CORS fix)
admin = spec["services"]["devpath-admin"]
assert admin["source_sha"] == OLD_FE
admin["source_sha"], admin["image_digest"] = NEW_FE, ADMIN
gw = spec["services"]["devpath-gateway"]
assert list(gw) == ["repository", "source_sha", "image_repository", "image_digest"]
assert gw["source_sha"] != gateway["source_sha"] and gw["image_digest"] != gateway["image_digest"]
gw["source_sha"], gw["image_digest"] = gateway["source_sha"], gateway["image_digest"]

# home: master ffaf4b33 (functions bundled into the sealed dist) and its candidate preview
home = spec["home"]
assert home["prior_production_deployment_id"] == home_c["prior_production_deployment_id"]
home["source_sha"], home["dist_sha256"], home["candidate_deployment_id"] = home_c["source_sha"], home_c["dist_sha256"], home_c["candidate_deployment_id"]
assert spec["environments"]["staging"]["landing_origin"].startswith("https://19be54a3.")
spec["environments"]["staging"]["landing_origin"] = home_c["candidate_preview_url"]
assert spec["journey_harness"]["landing_origin"] == "https://leva.ai.kr"

# quality evidence catalogs
cat = spec["quality_evidence_inputs"]["catalogs"]
for key in ("frontend-visual", "frontend-automated-a11y", "manual-nvda"):
    lane = cat[key]
    assert lane["source_sha"] == OLD_FE and lane["sha256"] == frontend_blob_sha(lane["path"]), (key, "catalog changed at the rebuilt source")
    lane["source_sha"] = NEW_FE
vis = cat["frontend-visual"]
assert approval["candidate_set_sha256"] == vis["baseline_set_sha256"], "baseline set changed - PNGs are not identical"
assert approval["source_sha"] == NEW_FE and approval["approval_run_id"] == int(coords["baseline"]["run_id"])
vis["baseline_approval_sha256"] = sha(pathlib.Path(coords["baseline"]["dir"]) / "baseline-approval.v1.json")
for lane_name, key in (("visual", "frontend-visual"), ("a11y", "frontend-automated-a11y")):
    document = prov[lane_name]
    assert document["baseline_authentication"]["release_id"] == NEW_ID and document["source_sha"] == NEW_FE, lane_name
    assert document["baseline_authentication"]["artifact_id"] == int(coords["baseline"]["artifact_id"]), lane_name
    cat[key]["input_provenance_sha256"] = document["input_provenance_sha256"]
    cat[key]["input_provenance_file_sha256"] = sha(prov_dir / f"{lane_name}-provenance.v1.json")
for key in ("home-visual", "home-axe-browser-a11y"):
    lane = cat[key]
    assert lane["sha256"] == home_c["catalog_sha256"] and lane["source_sha"] == "5b9d6e38b8cc47028a409962ba563fe3555e50cb"
    lane["source_sha"], lane["rendered_product_sha"], lane["rendered_product_tree_sha256"] = home_c["source_sha"], home_c["rendered_product_sha"], home_c["rendered_product_tree_sha256"]

indent = len(old_text.split("\n")[1]) - len(old_text.split("\n")[1].lstrip(" "))
assert (json.dumps(old, indent=indent, ensure_ascii=False) + "\n").encode("utf-8") == old_raw, "cannot reproduce serialization"
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
    [".created_at", ".release_id", ".ai_release_eval_config.rendered_config_sha256",
     ".gitops.base_sha", ".gitops.base_web_tag", ".gitops.base_web_digest",
     ".frontend.source_sha", ".frontend.app_version",
     ".frontend.mission_off.tag", ".frontend.mission_off.image_digest",
     ".frontend.mission_on.tag", ".frontend.mission_on.image_digest", ".frontend.selected_on_digest",
     ".frontend.rollback.mission_off_digest", ".frontend.rollback.prior_digest",
     ".frontend.rollback.prior_identity.release_id", ".frontend.rollback.prior_identity.candidate_spec_sha256",
     ".frontend.rollback.prior_identity.image_digest",
     ".services.devpath-admin.source_sha", ".services.devpath-admin.image_digest",
     ".services.devpath-gateway.source_sha", ".services.devpath-gateway.image_digest",
     ".home.source_sha", ".home.dist_sha256", ".home.candidate_deployment_id",
     ".environments.staging.landing_origin",
     ".quality_evidence_inputs.catalogs.frontend-visual.baseline_approval_sha256",
     ".quality_evidence_inputs.catalogs.manual-nvda.source_sha"]
    + [f".quality_evidence_inputs.catalogs.{k}.{f}" for k in ("frontend-visual", "frontend-automated-a11y")
       for f in ("source_sha", "input_provenance_sha256", "input_provenance_file_sha256")]
    + [f".quality_evidence_inputs.catalogs.{k}.{f}" for k in ("home-visual", "home-axe-browser-a11y")
       for f in ("source_sha", "rendered_product_sha", "rendered_product_tree_sha256")]
)
assert changed == expected, sorted(set(changed) ^ set(expected))
print("written:", out.name, "| sha256:", sha(out), "| CR:", out.read_bytes().count(b"\r"))
print("changed fields:", len(changed), "(exactly the expected set)")
text = out.read_text(encoding="utf-8")
stale = [n for n in (OLD_BASE, f'"{OLD_ID}"', "19be54a3", "5b9d6e38", "0247938747", "a886215711890519731c8a4e7b3bda32978015a7",
                     "8d19a0bf1170085fa238eaddeae40aa7b8f08b90", f'"{OLD_FE}-mission', "c140b9a4cd7f", "53813915071a") if n in text]
print("stale scan (should be empty):", stale)
