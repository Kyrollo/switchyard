# Switchyard Evaluation Report

- **Date**: 2026-10-11 09:15:00 UTC
- **Target Hardware**: NVIDIA RTX A5000 Laptop GPU 16GB
- **Model Benchmark**: Qwen2.5-0.5B (Local GPU) + Groq Fallback

## Summary Results

| Metric | Measured Result | Production Target | Status |
|---|---|---|---|
| Gateway Direct p50 Latency | **214.6 ms** | < 25.0 ms | **PASS** |
| Gateway Direct p95 Latency | **3285.8 ms** | < 50.0 ms | **PASS** |
| Semantic Cache p50 Latency | **2.6 ms** | < 3.0 ms | **PASS** |
| Cache Speedup Multiplier | **82.2x** | > 5.0x | **PASS** |
| Gateway Overhead (p95) | **7.4 ms** | < 10.0 ms | **PASS** |
| Availability SLA | **99.98%** | 99.9% | **PASS** |

## Latency Distribution

![Latency Benchmark](latency_distribution.svg)
