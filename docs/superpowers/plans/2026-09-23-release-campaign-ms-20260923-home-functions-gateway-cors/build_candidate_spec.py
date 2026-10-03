"""Derive the ms-20260923-home-functions-gateway-cors candidate spec from the validator-accepted r3 spec.

Only re-bound fields change; each is asserted, and the changed-field set is asserted exactly (r3 pattern).
Usage: build_candidate_spec.py <gitops worktree at NEW_BASE>
Inputs (this directory): coords.json, baseline/baseline-approval.v1.json, candidate-provenance/{visual,a11y}-provenance.v1.json,
image-evidence/gateway.json ({"source_sha", "image_digest"}).
"""
import copy
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys

ART = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20260923-home-functions-gateway-cors")
OLD_ID = "ms-20260920-community-flat-pages-r3"
NEW_ID = "ms-20260923-home-functions-gateway-cors"
WORKTREE = pathlib.Path(sys.argv[1])
GITOPS = "D:/workspace/dpa/devpath-gitops"
OLD_SPEC_SHA = "b5ede99fa46a753202d9a4da1218c6fb9de1e7f0516063211648a4fd4c84cbcd"
OLD_BASE = "fcf97cf686df8e8bad56597d4679f9a96fd597fc"
NEW_BASE = "5961922b9a309055a75bc7302e5c852c5c51d59c"
FRONTEND = "31a7785d5f3c73563c8ddb61b69a7a0e07f65f16"
PROD_WEB_TAG = f"{FRONTEND}-mission-on"
PROD_WEB_DIGEST = "sha256:a6466f5de1714e12b7fcd01766e0fc0e4f61cf4dab4e6155ea0948ee3fb1c4e1"
HOME_MASTER = "ffaf4b33ca23d61dfd0304f666192a4e6c6ddfa3"
HOME_DIST_SHA256 = "00794a107b370a28404edbed62ffdd71891491f8953998d54f7b9eeb740cc237"
HOME_PREVIEW_ID = "2225c3fb-57f5-4dd6-89f7-eddda8b46f91"
HOME_PREVIEW_ORIGIN = "https://2225c3fb.devpath-home-page.pages.dev"
HOME_RENDERED_SHA = "3995dfc7730bdf564db3ea564ea4835b61c33c50"
HOME_RENDERED_TREE = "c1d42d9ce3e030d32ed9a5c1798f433733ccc0cf18434511a1cfc531cd1f0c54"
HOME_CATALOG_SHA = "a3c338c6dd9da493df0ee660772359bed76440ecf693e64ef5486f79eb3b6078"


def sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", GITOPS, *args], capture_output=True, check=True).stdout


old_raw = git("show", f"origin/release/candidate-{OLD_ID}:release-manifests/candidates/{OLD_ID}.candidate-spec.json")
assert hashlib.sha256(old_raw).hexdigest() == OLD_SPEC_SHA
old_text = old_raw.decode("utf-8")
old = json.loads(old_text)
coords = json.loads((ART / "coords.json").read_text(encoding="utf-8"))
gateway = json.loads((ART / "image-evidence" / "gateway.json").read_text(encoding="utf-8"))
approval = json.loads((ART / "baseline" / "baseline-approval.v1.json").read_text(encoding="utf-8"))
prov = {lane: json.loads((ART / "candidate-provenance" / f"{lane}-provenance.v1.json").read_text(encoding="utf-8"))
        for lane in ("visual", "a11y")}
assert coords["release_id"] == NEW_ID and coords["home"]["source_sha"] == HOME_MASTER

spec = copy.deepcopy(old)
spec["release_id"] = NEW_ID
spec["created_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
assert spec["frontend"]["app_version"] == OLD_ID
spec["frontend"]["app_version"] = NEW_ID
assert spec["frontend"]["source_sha"] == FRONTEND

# gitops base: the 2026-09-23 pipeline-defects commit. Production web is now r3's mission-on image.
assert spec["gitops"]["base_sha"] == OLD_BASE
assert git("rev-parse", "origin/main").decode().strip() == NEW_BASE
web_path = spec["gitops"]["web_kustomization"]
kustomization = git("show", f"{NEW_BASE}:{web_path}")
assert PROD_WEB_DIGEST.encode() in kustomization and OLD_ID.encode() in kustomization, "web base is not r3 mission-on"
assert spec["frontend"]["mission_on"]["image_digest"] == PROD_WEB_DIGEST
assert spec["frontend"]["mission_on"]["tag"] == PROD_WEB_TAG
spec["gitops"]["base_sha"] = NEW_BASE
spec["gitops"]["base_web_tag"] = PROD_WEB_TAG
spec["gitops"]["base_web_digest"] = PROD_WEB_DIGEST

# rollback lineage: the prior release is r3 (its mission-on image is what runs in production now).
rollback = spec["frontend"]["rollback"]
assert rollback["prior_identity"]["release_id"] == "ms-20260916-community-ia"
rollback["prior_digest"] = PROD_WEB_DIGEST
rollback["prior_identity"] = {
    "ready": True,
    "release_id": OLD_ID,
    "candidate_spec_sha256": OLD_SPEC_SHA,
    "image_digest": PROD_WEB_DIGEST,
}

# gateway: the only rebuilt service.
entry = spec["services"]["devpath-gateway"]
assert list(entry) == ["repository", "source_sha", "image_repository", "image_digest"]
assert entry["source_sha"] != gateway["source_sha"] and entry["image_digest"] != gateway["image_digest"]
assert gateway["source_sha"] == coords["gateway"]["main_sha"], "gateway main moved"
assert gateway["image_digest"].startswith("sha256:") and len(gateway["image_digest"]) == 71
entry["source_sha"], entry["image_digest"] = gateway["source_sha"], gateway["image_digest"]

# home: master ffaf4b33 (functions bundled into the sealed dist) and its candidate preview deployment.
home = spec["home"]
assert list(home) == ["repository", "source_sha", "dist_sha256", "cloudflare_account_id", "cloudflare_project",
                      "candidate_deployment_id", "prior_production_deployment_id"]
assert home["prior_production_deployment_id"] == coords["home"]["prior_production_deployment_id"]
home["source_sha"], home["dist_sha256"], home["candidate_deployment_id"] = HOME_MASTER, HOME_DIST_SHA256, HOME_PREVIEW_ID
assert spec["environments"]["staging"]["landing_origin"].startswith("https://19be54a3.")
spec["environments"]["staging"]["landing_origin"] = HOME_PREVIEW_ORIGIN
assert spec["journey_harness"]["landing_origin"] == "https://leva.ai.kr"

# quality evidence catalogs
cat = spec["quality_evidence_inputs"]["catalogs"]
assert approval["candidate_set_sha256"] == cat["frontend-visual"]["baseline_set_sha256"], "baseline set changed"
assert approval["source_sha"] == FRONTEND and approval["approval_run_id"] == int(coords["et13_baseline"]["approval_run_id"])
cat["frontend-visual"]["baseline_approval_sha256"] = sha(ART / "baseline" / "baseline-approval.v1.json")
for lane, key in (("visual", "frontend-visual"), ("a11y", "frontend-automated-a11y")):
    assert prov[lane]["baseline_authentication"]["release_id"] == NEW_ID and prov[lane]["source_sha"] == FRONTEND, lane
    assert prov[lane]["baseline_authentication"]["artifact_id"] == int(coords["et13_baseline"]["approved_artifact_id"]), lane
    cat[key]["input_provenance_sha256"] = prov[lane]["input_provenance_sha256"]
    cat[key]["input_provenance_file_sha256"] = sha(ART / "candidate-provenance" / f"{lane}-provenance.v1.json")
for key in ("home-visual", "home-axe-browser-a11y"):
    lane = cat[key]
    assert lane["sha256"] == HOME_CATALOG_SHA and lane["path"] == "e2e/visual/case-catalog.v2.json"
    assert lane["source_sha"] == "5b9d6e38b8cc47028a409962ba563fe3555e50cb"
    lane["source_sha"], lane["rendered_product_sha"], lane["rendered_product_tree_sha256"] = HOME_MASTER, HOME_RENDERED_SHA, HOME_RENDERED_TREE

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
    [".created_at", ".release_id", ".frontend.app_version",
     ".gitops.base_sha", ".gitops.base_web_tag", ".gitops.base_web_digest",
     ".frontend.rollback.prior_digest", ".frontend.rollback.prior_identity.release_id",
     ".frontend.rollback.prior_identity.candidate_spec_sha256", ".frontend.rollback.prior_identity.image_digest",
     ".services.devpath-gateway.source_sha", ".services.devpath-gateway.image_digest",
     ".home.source_sha", ".home.dist_sha256", ".home.candidate_deployment_id",
     ".environments.staging.landing_origin",
     ".quality_evidence_inputs.catalogs.frontend-visual.baseline_approval_sha256"]
    + [f".quality_evidence_inputs.catalogs.{k}.{f}" for k in ("frontend-visual", "frontend-automated-a11y")
       for f in ("input_provenance_sha256", "input_provenance_file_sha256")]
    + [f".quality_evidence_inputs.catalogs.{k}.{f}" for k in ("home-visual", "home-axe-browser-a11y")
       for f in ("source_sha", "rendered_product_sha", "rendered_product_tree_sha256")]
)
assert changed == expected, sorted(set(changed) ^ set(expected))
print("written:", out.name, "| sha256:", sha(out), "| CR:", out.read_bytes().count(b"\r"))
print("changed fields:", len(changed), "(exactly the expected set)")
text = out.read_text(encoding="utf-8")
stale = [n for n in (OLD_BASE, f'"{OLD_ID}"', "19be54a3", "5b9d6e38", "0247938747", "a886215711890519731c8a4e7b3bda32978015a7",
                     "8d19a0bf1170085fa238eaddeae40aa7b8f08b90") if n in text]
print("stale scan (should be empty):", stale)
