# Switchyard Data Model & Schemas

Switchyard models virtual keys, upstream routing nodes, dynamic policies, and request audit accounting.

---

## 1. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    VIRTUAL_KEY ||--o{ AUDIT_LOG_ENTRY : "authorizes"
    ROUTING_POLICY ||--|{ BACKEND_NODE : "primary nodes"
    ROUTING_POLICY ||--o{ BACKEND_NODE : "fallback nodes"
    USER ||--o{ VIRTUAL_KEY : "owns"

    USER {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        boolean is_superuser
        datetime created_at
        datetime updated_at
    }

    VIRTUAL_KEY {
        string id PK
        string name
        string key_prefix
        string key_hash UK
        int rpm_limit
        int tpm_limit
        float monthly_budget_usd
        float budget_spent_usd
        string_array allowed_models
        boolean is_active
        float created_at
        float expires_at
    }

    BACKEND_NODE {
        string id PK
        string name
        enum provider
        string base_url
        string api_key
        string_array models
        int weight
        float latency_p95_ms
        boolean is_healthy
        int consecutive_failures
        boolean circuit_open
        float last_checked
    }

    ROUTING_POLICY {
        string id PK
        string name
        string model_alias UK
        enum strategy
        string_array primary_backend_ids
        string_array fallback_backend_ids
        boolean is_active
    }

    AUDIT_LOG_ENTRY {
        string id PK
        float timestamp
        string virtual_key_id FK
        string model_requested
        string model_resolved
        string backend_name
        int prompt_tokens
        int completion_tokens
        float latency_ms
        float cost_usd
        boolean cached
        int status_code
    }
```

---

## 2. Core Schemas

### Virtual Key Schema
```json
{
  "id": "key_default_admin",
  "name": "Primary Admin Virtual Key",
  "key_prefix": "sk_live_switchyard...",
  "rpm_limit": 1000,
  "tpm_limit": 200000,
  "monthly_budget_usd": 1000.0,
  "budget_spent_usd": 42.50,
  "allowed_models": ["*"],
  "is_active": true
}
```

### Routing Policy Schema
```json
{
  "id": "pol-company-default",
  "name": "Enterprise Default Route",
  "model_alias": "company-default",
  "strategy": "priority_failover",
  "primary_backend_ids": ["node-local-gpu"],
  "fallback_backend_ids": ["node-cloud-groq", "node-cloud-openai"],
  "is_active": true
}
```
