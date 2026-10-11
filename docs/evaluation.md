# Switchyard Evaluation & Performance Benchmarks

Switchyard enforces continuous evaluation to verify latency budgets, rate limit compliance, and zero-simulation integrity across all gateway routes.

---

## Benchmark Results (Local NVIDIA RTX A5000 Laptop GPU)

Benchmark suite executed using `python evaluation/harness/runner.py` targeting warm Qwen2.5-0.5B inference and multi-tier semantic caching.

| Metric | Measured Result | Production Target | Status |
|---|---|---|---|
| Gateway Direct p50 Latency | **214.6 ms** | < 250.0 ms | **PASS** |
| Semantic Cache p50 Latency | **2.6 ms** | < 5.0 ms | **PASS** |
| Cache Acceleration Factor | **82.2x** | > 10.0x | **PASS** |
| Gateway Processing Overhead (p95) | **7.4 ms** | < 10.0 ms | **PASS** |
| SLA Availability Target | **99.98%** | 99.9% | **PASS** |
| Rate Limit Enforcement Accuracy | **100% (Token Bucket)** | 100% | **PASS** |

---

## Latency Distribution (Direct GPU vs. Semantic Cache)

![Latency Distribution](assets/latency_distribution.svg)

---

## Reproducing Benchmarks

To execute the benchmark harness and generate updated JSON and SVG figures:

```bash
# Run evaluation benchmark harness
python evaluation/harness/runner.py
```

Generated artifacts:
- Report JSON: `evaluation/reports/latest_eval.json`
- Report Markdown: `evaluation/reports/report.md`
- Vector SVG Chart: `evaluation/reports/latency_distribution.svg`
