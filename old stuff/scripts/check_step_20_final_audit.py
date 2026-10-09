"""
Consistency checker for Step 20 final reproducibility audit.

Run from repository root after Step 20:

    python scripts/check_step_20_final_audit.py

Exit code:
    0 = final audit package is complete
    1 = one or more checks failed
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "metadata"
LOGS = ROOT / "logs"

FINAL_MANIFEST = META / "final_reproducibility_manifest.csv"
STEP_STATUS = META / "final_step_status.csv"
CLAIMS = META / "paper_claim_support_matrix.csv"
AUDIT_REPORT = LOGS / "final_reproducibility_audit_report.md"
READINESS = LOGS / "final_paper_readiness_summary.md"
SCRIPT = ROOT / "scripts" / "21_final_reproducibility_audit.py"
PROTOCOL = ROOT / "docs" / "final_reproducibility_audit_protocol.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    required = [FINAL_MANIFEST, STEP_STATUS, CLAIMS, AUDIT_REPORT, READINESS, SCRIPT, PROTOCOL]
    for path in required:
        check(path.exists(), f"missing Step 20 file: {path.relative_to(ROOT)}", failures)
        if path.exists():
            check(path.stat().st_size > 0, f"empty Step 20 file: {path.relative_to(ROOT)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    manifest = read_csv(FINAL_MANIFEST)
    steps = read_csv(STEP_STATUS)
    claims = read_csv(CLAIMS)
    check(len(manifest) >= 30, f"final manifest too small: {len(manifest)}", failures)
    check(len(steps) == 14, f"final step status expected 14 rows, found {len(steps)}", failures)
    check(len(claims) >= 7, f"claim support matrix expected at least 7 rows, found {len(claims)}", failures)

    missing_manifest = [row for row in manifest if row.get("exists") != "1"]
    check(not missing_manifest, f"manifest has missing files: {missing_manifest[:5]}", failures)
    bad_steps = [row for row in steps if row.get("status") != "complete"]
    check(not bad_steps, f"non-complete steps: {bad_steps}", failures)
    bad_claims = [row for row in claims if row.get("status") != "supported"]
    check(not bad_claims, f"unsupported claims: {bad_claims}", failures)

    audit_text = AUDIT_REPORT.read_text(encoding="utf-8")
    readiness_text = READINESS.read_text(encoding="utf-8")
    check("## Status" in audit_text and "PASS" in audit_text, "audit report does not show PASS", failures)
    check("Final Paper-Readiness Summary" in readiness_text, "readiness summary title missing", failures)
    check("1440 master text rows" in readiness_text, "readiness summary missing master-row statement", failures)
    check("205 stylometric features" in readiness_text, "readiness summary missing feature statement", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: Step 20 final reproducibility audit package is complete and internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
