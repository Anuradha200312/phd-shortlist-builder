import os
import subprocess
from pathlib import Path


def test_full_pipeline_runs_and_writes_output():
    """Run the E2E smoke script and assert final JSON is written."""
    repo_root = Path(__file__).parent.parent.parent
    script = repo_root / "scripts" / "run_e2e_smoke.py"
    # Run the script
    res = subprocess.run(["python", str(script)], cwd=repo_root, capture_output=True, text=True)
    assert res.returncode == 0, f"E2E script failed: {res.stdout}\n{res.stderr}"

    # Check output file
    out_file = repo_root / "sample_output" / "e2e_test-student.json"
    assert out_file.exists(), "Expected output file not found"
    # Basic sanity check: file non-empty
    assert out_file.stat().st_size > 0