# Copyright 2025-2026 Sri Surya Sameer Vaddhiparthy.
#
# All rights reserved.
#
# Non-commercial use is permitted for review and research only.

from __future__ import annotations

import subprocess
import sys


def test_benchmark_load_script_runs_small_case():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_load.py",
            "--aircraft-count",
            "12",
            "--duration-s",
            "1",
            "--dt-s",
            "1.0",
            "--spacing-m",
            "12000",
            "--max-ms-per-frame",
            "1200",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "[benchmark]" in result.stdout
