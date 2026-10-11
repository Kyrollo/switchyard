# Switchyard System Architecture

Switchyard provides a single, high-performance, private OpenAI-compatible gateway fronting locally-hosted models (Ollama on NVIDIA RTX A5000) and enterprise cloud APIs.

---

## 1. C4 Container Diagram

```mermaid
flowchart TD
    subgraph Clients["Clients & Applications"]
        WebUser["Internal Developer / Console\\n(Browser)"]
        SDKClient["Application Client / OpenAI SDK\\n(Python, TS, Go)"]
    end

    subgraph Switchyard["Switchyard Gateway Platform"]
        Frontend["Frontend Console (React 19 + Tailwind v4)\\nPort 3001"]
        API["FastAPI Gateway Engine\\nPort 8001"]
        RateLimiter["Token Bucket Rate Limiter\\n(RPM / TPM Sliding Window)"]
        SemanticCache["Multi-Tier Cache\\n(Exact SHA-256 + Semantic Jaccard)"]
        RouterEngine["Routing Engine & Circuit Breakers"]
        Metering["Metering & Audit Service"]
        DB[("PostgreSQL 16\\nAsync ORM (Alembic)")]
        Redis[("Redis 7\\nState & Token Bucket")]
    end

    subgraph Backends["Inference Backends"]
        LocalGPU["Primary: Local Ollama (RTX A5000 16GB)\\nPort 11434"]
        Groq["Fallback 1: Groq Cloud (Llama-3.3-70B)"]
        OpenAI["Fallback 2: OpenAI (GPT-4o)"]
    end

    subgraph Observability["Observability Stack"]
        Prometheus["Prometheus /metrics"]
        Langfuse["Langfuse LLM Tracing"]
        Structlog["Structlog JSON Auditing"]
    end

    WebUser -->|"HTTP / REST"| Frontend
    Frontend -->|"REST /api/v1"| API
    SDKClient -->|"OpenAI API /v1"| API

    API --> RateLimiter
    API --> SemanticCache
    API --> RouterEngine
    API --> Metering

    RouterEngine -->|"Low Latency (~8ms)"| LocalGPU
    RouterEngine -.->|"Circuit Tripped Failover"| Groq
    RouterEngine -.->|"Secondary Failover"| OpenAI

    API --> DB
    API --> Redis
    API --> Prometheus
    API --> Langfuse
    API --> Structlog
```

---

## 2. Request Sequence & Lifecycle

The sequence diagram below traces an incoming completion request through authorization, sliding-window rate limiting, cache evaluation, dynamic routing, circuit breaking, and telemetry accounting.

```mermaid
sequenceDiagram
    autonumber
    actor Client as OpenAI SDK / Client
    participant GW as Switchyard Gateway API
    participant RL as Rate Limiter (Token Bucket)
    participant SC as Semantic Cache
    participant RE as Routing Engine
    participant GPU as Local RTX A5000 (Ollama)
    participant FB as Cloud Fallback (Groq/OpenAI)
    participant MT as Metering & Audit

    Client->>GW: POST /v1/chat/completions (Bearer sk_live_...)
    GW->>GW: Authenticate Virtual Key & Check Model Allowlists
    GW->>RL: Consume RPM & TPM tokens
    alt Rate Limit Exceeded
        RL-->>Client: HTTP 429 RateLimitExceeded (RFC 7807)
    end

    GW->>SC: Lookup (model, prompt messages)
    alt Cache HIT (Exact or Semantic)
        SC-->>GW: Return Cached Response (latency 2.5ms)
        GW->>MT: Record 0-cost cache hit
        GW-->>Client: 200 OK (cached=true)
    else Cache MISS
        GW->>RE: Resolve routing chain for model alias
        RE->>GPU: POST /v1/chat/completions (qwen2.5:0.5b)
        alt Local GPU Healthy (200 OK)
            GPU-->>RE: Model Tokens + Usage
            RE->>RE: Update p95 latency EMA & reset failure counter
        else Local GPU Down / 5xx / Timeout
            GPU-->>RE: Connection Error / Timeout
            RE->>RE: Increment failure count (Trip circuit breaker if >= 3)
            RE->>FB: Failover dispatch to Standby Cloud Node
            FB-->>RE: Response from Cloud Model
        end
        RE-->>GW: Normalized ChatCompletionResponse
        GW->>SC: Store in Exact & Semantic Cache (TTL 3600s)
        GW->>MT: Record prompt/completion tokens, latency, cost USD
        GW-->>Client: 200 OK (cached=false)
    end
```

---

## 3. Circuit Breaker State Machine

To prevent cascading failures and request pileups on degraded nodes, each upstream backend node operates under an active circuit breaker:

```mermaid
stateDiagram-v2
    [*] --> Closed: Initial State

    Closed --> Closed: Request Succeeds (Failures = 0)
    Closed --> Open: 3 Consecutive 5xx / Timeouts

    state Open {
        [*] --> CoolingDown
        CoolingDown --> ReadyForProbe: 30 Seconds Elapsed
    }

    Open --> HalfOpen: Automated Probe Dispatched
    HalfOpen --> Closed: Probe Succeeds (Health Restored)
    HalfOpen --> Open: Probe Fails (Cooldown Reset to 30s)
```

- **Closed**: Requests routed normally with active health tracking.
- **Open**: Failing backend is immediately bypassed; requests automatically route to the next configured fallback in the policy chain.
- **Half-Open**: A single canary probe tests node recovery after the 30-second cooldown period.
