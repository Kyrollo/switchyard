# Switchyard API Reference

The Switchyard Gateway provides an **OpenAI-compatible** API alongside administration and telemetry endpoints.

- **Base URL**: `http://localhost:8001/api/v1`
- **Interactive Swagger UI**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **OpenAPI JSON**: [http://localhost:8001/openapi.json](http://localhost:8001/openapi.json)

---

## 1. Chat Completions (OpenAI Compatible)

`POST /api/v1/chat/completions`

Dispatches inference through dynamic routing, rate limit checks, and semantic caching.

### Request Headers
- `Authorization`: `Bearer <VIRTUAL_API_KEY>` (e.g. `Bearer sk_live_switchyard_enterprise_2026`)
- `Content-Type`: `application/json`

### Request Body
```json
{
  "model": "company-default",
  "messages": [
    {"role": "system", "content": "You are a concise enterprise assistant."},
    {"role": "user", "content": "Summarize the primary benefits of private model gateways."}
  ],
  "temperature": 0.2,
  "max_tokens": 150,
  "stream": false
}
```

### Response Body
```json
{
  "id": "chatcmpl-9b8a21f8",
  "object": "chat.completion",
  "created": 1791709059,
  "model": "qwen2.5:0.5b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Private model gateways provide centralized governance, rate limiting, and data privacy."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 28,
    "completion_tokens": 14,
    "total_tokens": 42
  },
  "backend_id": "node-local-gpu",
  "cached": false,
  "latency_ms": 214.6
}
```

### Python (OpenAI SDK) Example
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8001/api/v1",
    api_key="sk_live_switchyard_enterprise_2026",
)

response = client.chat.completions.create(
    model="company-default",
    messages=[{"role": "user", "content": "Hello via Switchyard!"}],
)

print(response.choices[0].message.content)
```

---

## 2. Models Catalog

`GET /api/v1/models`

Lists available models, including model routing aliases (`company-default`) and physical upstream backends.

```bash
curl -X GET http://localhost:8001/api/v1/models \
  -H "Authorization: Bearer sk_live_switchyard_enterprise_2026"
```

---

## 3. Administration & Telemetry

### Dashboard Telemetry Summary
`GET /api/v1/admin/dashboard`

Returns composite metrics: p95 latency, SLA uptime, token bucket gauges, NVML GPU metrics, and upstream backend health.

### Virtual API Key Management
- `GET /api/v1/admin/keys`: List all provisioned virtual keys with live sliding-window RPM and TPM consumption.
- `POST /api/v1/admin/keys`: Provision a new virtual key with custom token-bucket quotas.
- `DELETE /api/v1/admin/keys/{key_id}`: Revoke a virtual key.

### Hardware & GPU Telemetry
`GET /api/v1/admin/gpu`

Returns real-time VRAM allocation, utilization percentage, and temperature from NVML for NVIDIA RTX A5000 Laptop GPU.

### Audit Logs
`GET /api/v1/admin/logs?limit=50`

Returns detailed per-request audit logs with model requested, model resolved, backend used, latency in ms, token usage, and cost in USD.
