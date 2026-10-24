"""Run Level 3 validation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from level3.validation import build_validation_artifact


def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "level3/tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    passed = output.count("PASSED")
    failed = output.count("FAILED")
    return {
        "command": "pytest level3/tests -v",
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "all_passed": result.returncode == 0 and failed == 0,
        "tail": output.splitlines()[-30:],
    }


def main():
    test_results = run_tests()
    artifact = build_validation_artifact(ROOT, test_results)
    out = ROOT / "level3_validation.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "tests_passed": test_results["passed"],
        "tests_failed": test_results["failed"],
        "all_passed": test_results["all_passed"],
        "predictive_validity_validated": artifact["predictive_validity_validated"],
    }, ensure_ascii=False, indent=2))
    return 0 if test_results["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
