"""8단계 seal 수집 — sealed 매니페스트가 3차 validate 런의 아티팩트를 가리키는지 확인하고 coords.json 의 validate 를 채운다."""
import hashlib
import json
import pathlib

OUT = pathlib.Path("D:/workspace/dpa/.release-artifacts/ms-20261003-ai-fallback-retry-budget")
RID = "ms-20261003-ai-fallback-retry-budget"
RUN = 37418150783
SEALED = "c8ee341d395539544ec62abad21efb406555c1d9"
ART = {"sealed_validation": 11392034571, "activation": 11391794827, "contextual": 11392305189, "home_visual_a11y": 11391447950}

raw = (OUT / "sealed-release-manifest-budget.json").read_bytes()
digest = hashlib.sha256(raw).hexdigest()
manifest = json.loads(raw.decode("utf-8"))
assert manifest["release_id"] == RID, manifest["release_id"]


def ids(node, found):
    """매니페스트 안의 모든 정수 artifact/run 식별자를 (경로, 값)으로 모은다."""
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, int) and not isinstance(o, bool) and o > 10_000_000:
            found.append((path, o))
    walk(node, "")
    return found


journey_ids = ids(manifest["journeys"], [])
print("journeys ids:")
for path, value in journey_ids:
    print("  ", path, value)
values = {v for _, v in journey_ids}
assert ART["activation"] in values and ART["contextual"] in values, "manifest does not bind this run's journey artifacts"
stale = {11272935112, 11271964766, 11272117634} & {v for _, v in ids(manifest, [])}
assert not stale, f"manifest references artifacts of the failed 10/03 run: {stale}"
print("validation_attestation:", json.dumps(manifest["validation_attestation"], ensure_ascii=False)[:600])
print("candidate_spec:", json.dumps(manifest["candidate_spec"], ensure_ascii=False)[:300])

coords_path = OUT / "coords.json"
coords = json.loads(coords_path.read_text(encoding="utf-8"))
assert coords.get("validate") is None, "validate already collected"
coords["validate"] = {
    "dispatcher_branch": f"automation/dispatch-{RID}",
    "dispatcher_commit": "40ba8b64388b17704ea311562e3ef99993f831bf",
    "dispatcher_run": 37418140991,
    "validate_run_id": RUN,
    "staging_gate_1": "deployment 6876363247 (AI)",
    "staging_gate_2": "deployment 6876442324 (AI)",
    "sealed_sha": SEALED,
    "sealed_manifest_sha256": digest,
    "sealed_validation_artifact_id": ART["sealed_validation"],
    "journey_activation_artifact": ART["activation"],
    "journey_contextual_artifact": ART["contextual"],
    "home_visual_a11y_artifact": ART["home_visual_a11y"],
    "conclusion": "success",
    "seal_commit_subject": f"release(manifest): seal {RID} validation attestation",
    "prior_attempts": [
        {"run": 37118424720, "at": "2026-10-03T11:03:34Z", "dispatcher_commit": "390a702b7e5d30d4642e0a96aae200677f7f64f8",
         "failure": "seal: exactly one frontend producer run is required (journeys success)"},
        {"run": 37417289045, "at": "2026-10-06T05:11:17Z", "dispatcher_commit": "57c3dd3f2432c2d71b8945bed9576e7e69066611",
         "failure": "activation journey: required-consent-claim-replay — waitForRequest POST /consents 30s timeout (first occurrence, cause not determined; contextual journey passed)"},
    ],
}
coords_path.write_text(json.dumps(coords, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("coords.validate written | sealed_manifest_sha256 =", digest)
