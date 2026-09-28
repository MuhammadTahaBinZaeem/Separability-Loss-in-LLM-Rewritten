"""Current, fail-closed v3 progress and local delivery checks; no review impersonation."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

from .expanded_study import BASE, effective_plan, now, verify
from .io import ROOT, file_hash, read_json, write_json


def current_analysis(folder, expected_inputs=None):
    result = {"current": False, "running": (folder / "RUNNING.lock").exists()}
    if result["running"] or not (folder / "manifest.json").exists():
        return result
    try:
        manifest = read_json(folder / "manifest.json")
        if expected_inputs is not None and manifest["inputs"] != expected_inputs:
            result["reason"] = "input_set_changed"
            return result
        for relative, expected in manifest["inputs"].items():
            path = ROOT / relative
            if not path.resolve().is_relative_to(ROOT.resolve()) or file_hash(path) != expected:
                result["reason"] = "input_changed"
                return result
        for relative, expected in manifest["output_hashes"].items():
            path = folder / relative
            if not path.resolve().is_relative_to(folder.resolve()) or file_hash(path) != expected:
                result["reason"] = "output_changed"
                return result
        replay = read_json(folder / "replay_verification.json")
        result["current"] = bool(replay.get("passed") and replay.get("manifest_sha256") == file_hash(folder / "manifest.json"))
        result["replay_verified"] = result["current"]
    except (FileNotFoundError, KeyError, ValueError):
        result["reason"] = "missing_or_invalid_evidence"
    return result


def site_check():
    from .review_app import ReviewStore
    root = ReviewStore()
    url = "http://127.0.0.1:8765"
    report = {"checked_utc": now(), "url": url, "accounts": [], "passed": False}
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            report["homepage_http"] = response.status
        for account in root.sessions():
            if account["kind"] not in {"source", "semantic_A", "semantic_B"} or account["mode"] != "human":
                continue
            token = root.assignment(account["id"])["token"]
            request = urllib.request.Request(url + "/api/me", headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(request, timeout=5) as response:
                principal = json.load(response)
            request = urllib.request.Request(url + "/api/sessions/" + principal["session_id"], headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(request, timeout=5) as response:
                status = json.load(response)
            report["accounts"].append({"kind": account["kind"], "assignments": len(principal["assignments"]),
                                       "total": status["total"], "saved": status["saved"], "status": status["status"]})
        report["passed"] = report["homepage_http"] == 200 and len(report["accounts"]) == 3
    except Exception as exc:
        # Do not dump request objects, headers, private tokens or database rows.
        report["error_class"] = type(exc).__name__
    write_json(BASE / "verification/local_delivery.json", report)
    return report


def test_suite():
    from .release import check_environment, code_fingerprint
    directory = BASE / "verification"
    directory.mkdir(parents=True, exist_ok=True)
    xml = directory / "tests_current.xml"
    before = code_fingerprint()
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests", "--junitxml", str(xml)],
                            cwd=ROOT, capture_output=True, text=True)
    report = {"passed": result.returncode == 0 and code_fingerprint() == before,
              "return_code": result.returncode, "code_fingerprint": before,
              "environment": check_environment(), "completed_utc": now(), "output": result.stdout + result.stderr}
    if xml.exists():
        suites = ET.parse(xml).getroot()
        report["test_count"] = sum(int(s.get("tests", 0)) for s in suites.iter("testsuite"))
        report["failures"] = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites.iter("testsuite"))
        report["receipt_sha256"] = file_hash(xml)
    write_json(directory / "tests_current.json", report)
    return report


def check():
    from .expanded_generation import Budget
    from .expanded_primary import DESTINATION, inputs as primary_inputs
    from .expanded_review import semantic_validation, source_validation
    from .release import code_fingerprint
    from .session_workers import audit
    from .transfer_extension import fingerprints
    verify()
    plan = effective_plan()
    models, analyses = {}, {}
    extension = BASE / "extensions/jql_v1"
    for model in plan["active_models"]:
        folder = BASE / f"generation/{model}"
        status = read_json(folder / "completion.json")
        models[model] = {k: status[k] for k in ("expected", "accounted", "missing", "valid_outputs", "fail", "accounting_complete")}
        models[model]["running"] = (folder / "RUNNING.lock").exists()
        if status["accounting_complete"] and not models[model]["running"]:
            analyses[model] = {"primary": current_analysis(DESTINATION / model, primary_inputs(model)),
                               "transfer": current_analysis(extension / model, fingerprints(model, BASE, extension)),
                               "shift_contraction": current_analysis(extension / model / "explanatory_model")}
        else:
            analyses[model] = {"primary": {"current": False}, "transfer": {"current": False}, "shift_contraction": {"current": False}}
    session = audit()
    session.pop("evidence_sha256", None)
    source, semantic = source_validation(), semantic_validation()
    test_path = BASE / "verification/tests_current.json"
    test = read_json(test_path) if test_path.exists() else {"passed": False}
    tests_current = bool(test.get("passed") and test.get("environment", {}).get("passed") and test.get("code_fingerprint") == code_fingerprint())
    packets = BASE / "annotations/issued_manifest.json"
    computational = all(m["accounting_complete"] and not m["running"] for m in models.values()) and all(v["current"] for a in analyses.values() for v in a.values()) and tests_current
    combined = DESTINATION / "status.json"
    archive = BASE / "archive/candidate.json"
    result = {"checked_utc": now(), "models": models, "analyses": analyses, "astra_provenance_audit": session,
              "budget": Budget(BASE / "private/budget.sqlite3", plan["budget"]).status(),
              "source_review": source, "semantic_review": semantic,
              "tests": {"current": tests_current, "passed": test.get("passed", False), "test_count": test.get("test_count", 0)},
              "semantic_packets_issued": packets.exists(),
              "all_model_multiplicity_table_exists": combined.exists(), "local_archive_exists": archive.exists(),
              "computational_checks_complete": computational,
              "reviews_only_remaining": False, "submission_ready": False,
              "mandatory_later_steps": ["Actual source follow-up and independent semantic reviews", "Review-gated sensitivity and any independence/adjudication follow-up",
                                       "Final validated release package and investigator rights/ethics/authorship/AI-use disclosures", "Actual archival deposit/DOI and journal submission checks", "Manuscript writing"]}
    write_json(BASE / "checkpoint.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "test", "site"))
    args = parser.parse_args()
    result = {"check": check, "test": test_suite, "site": site_check}[args.action]()
    print(json.dumps({k: v for k, v in result.items() if k != "output"}, indent=2))
    if args.action in {"test", "site"} and not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
