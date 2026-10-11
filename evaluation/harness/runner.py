#!/usr/bin/env python3
"""
Evaluation Runner for Switchyard
Executes reproducible benchmarks against live product endpoints and outputs JSON metrics.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
import httpx

API_BASE = "http://localhost:8001/api/v1"


def run_benchmark() -> int:
    print("--> Starting benchmark for Switchyard...")
    start_time = time.perf_counter()

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{API_BASE}/info")
            if resp.status_code != 200:
                print(f"[ERROR] API returned {resp.status_code}: {resp.text}", file=sys.stderr)
                return 1
            info = resp.json()
    except Exception as exc:
        print(f"[ERROR] Could not connect to Switchyard API at {API_BASE}: {exc}", file=sys.stderr)
        return 1

    duration = time.perf_counter() - start_time
    report = {
        "product": "switchyard",
        "timestamp": time.time(),
        "latency_seconds": duration,
        "status": "passed",
        "system_info": info,
    }

    report_path = Path("evaluation/reports/latest_eval.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"--> [PASS] Benchmark completed in {duration:.3f}s. Report written to {report_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark())
