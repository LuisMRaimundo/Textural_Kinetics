import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compare_reference_script():
    r = subprocess.run(
        [sys.executable, str(ROOT / "corpus" / "scripts" / "compare_all.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
