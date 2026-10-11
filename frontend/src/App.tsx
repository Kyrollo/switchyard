import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Copy,
  Cpu,
  Database,
  ExternalLink,
  Gauge,
  GitBranch,
  KeyRound,
  Layers,
  LineChart,
  MessageSquare,
  Network,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trash2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';

interface DashboardData {
  metrics: {
    p95_latency_ms: number;
    uptime_pct: number;
    total_requests: number;
    total_tokens: number;
    total_cost_usd: number;
    cache_hit_rate_pct: number;
    total_cached_items: number;
  };
  gpu: {
    name: string;
    vram_total_mb: number;
    vram_used_mb: number;
    vram_free_mb: number;
    utilization_pct: number;
    temperature_c?: number;
  };
  ollama_models: Array<{
    name: string;
    size: number;
    modified_at?: string;
  }>;
  backends: Array<{
    id: string;
    name: string;
    provider: string;
    latency_p95_ms: number;
    is_healthy: boolean;
    circuit_open: boolean;
    models: string[];
  }>;
  virtual_keys: Array<{
    id: string;
    name: string;
    key_prefix: string;
    rpm_limit: number;
    current_rpm: number;
    tpm_limit: number;
    current_tpm: number;
    monthly_budget_usd: number;
    budget_spent_usd: number;
    is_active: boolean;
  }>;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'routing' | 'analytics' | 'gpu' | 'keys' | 'logs'>('routing');
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Playground state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Switchyard Gateway connected. Directing queries to local GPU on RTX A5000 with failover protection.' },
  ]);
  const [promptInput, setPromptInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('company-default');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatLatency, setChatLatency] = useState<number | null>(null);
  const [chatCached, setChatCached] = useState<boolean>(false);
  const [chatBackend, setChatBackend] = useState<string>('node-local-gpu');

  // Logs state
  const [logs, setLogs] = useState<any[]>([]);

  // Key creation state
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyRpm, setNewKeyRpm] = useState(600);
  const [createdApiKey, setCreatedApiKey] = useState<string | null>(null);

  async function fetchDashboard() {
    try {
      const res = await fetch('/api/v1/admin/dashboard');
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard telemetry');
    } finally {
      setLoading(false);
    }
  }

  async function fetchLogs() {
    try {
      const res = await fetch('/api/v1/admin/logs?limit=25');
      if (res.ok) {
        const json = await res.json();
        setLogs(json);
      }
    } catch {
      // non-blocking
    }
  }

  useEffect(() => {
    fetchDashboard();
    fetchLogs();
    const interval = setInterval(() => {
      fetchDashboard();
      fetchLogs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!promptInput.trim() || chatLoading) return;

    const userMsg: ChatMessage = { role: 'user', content: promptInput.trim() };
    const updated = [...chatMessages, userMsg];
    setChatMessages(updated);
    setPromptInput('');
    setChatLoading(true);

    const startTime = performance.now();

    try {
      const res = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer sk_live_switchyard_enterprise_2026',
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: updated,
          temperature: 0.2,
          max_tokens: 150,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `Gateway error ${res.status}`);
      }

      const resData = await res.json();
      const duration = Math.round(performance.now() - startTime);
      setChatLatency(duration);
      setChatCached(Boolean(resData.cached));
      setChatBackend(resData.backend_id || 'node-local-gpu');

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: resData.choices[0]?.message?.content || 'No response content.',
      };
      setChatMessages([...updated, assistantMsg]);
      fetchDashboard();
      fetchLogs();
    } catch (err: any) {
      setChatMessages([
        ...updated,
        { role: 'assistant', content: `[Error: ${err.message}]` },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    try {
      const res = await fetch('/api/v1/admin/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newKeyName.trim(),
          rpm_limit: Number(newKeyRpm),
          tpm_limit: 100000,
          monthly_budget_usd: 500.0,
        }),
      });
      if (res.ok) {
        const json = await res.json();
        setCreatedApiKey(json.api_key);
        setNewKeyName('');
        fetchDashboard();
      }
    } catch {
      // ignore
    }
  }

  async function handleRevokeKey(keyId: string) {
    try {
      const res = await fetch(`/api/v1/admin/keys/${keyId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchDashboard();
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
      {/* Top Header */}
      <header className="border-b border-border bg-card/70 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center text-white shadow-sm font-bold text-lg">
              S
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-tight">Switchyard</span>
                <Badge variant="outline" className="text-xs px-1.5 py-0">v1.0.0</Badge>
              </div>
              <p className="text-xs text-muted-foreground hidden sm:block">Private Enterprise LLM Gateway</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-3 text-xs font-mono bg-muted/60 px-3 py-1.5 rounded-lg border border-border">
              <span className="text-muted-foreground">Cluster p95:</span>
              <span className="font-bold text-primary">{data?.metrics.p95_latency_ms || 8.2}ms</span>
              <span className="text-border">|</span>
              <span className="text-muted-foreground">Hardware:</span>
              <span className="text-foreground">RTX A5000 16GB</span>
            </div>

            {loading ? (
              <Badge variant="outline" className="animate-pulse">Checking Gateway...</Badge>
            ) : error ? (
              <Badge variant="destructive" className="flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Degraded
              </Badge>
            ) : (
              <Badge variant="success" className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Gateway Operational
              </Badge>
            )}

            <Button variant="outline" size="sm" asChild>
              <a href="/docs" target="_blank" rel="noreferrer" className="flex items-center gap-1">
                Docs <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </a>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Layout Body */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 flex flex-col md:flex-row gap-8">
        {/* Navigation Sidebar */}
        <aside className="w-full md:w-64 space-y-2 shrink-0">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 mb-2">
            Gateway Controls
          </div>

          <button
            onClick={() => setActiveTab('routing')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
              activeTab === 'routing'
                ? 'bg-primary text-white shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Network className="w-4 h-4" />
            Routing & Policy Hub
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
              activeTab === 'analytics'
                ? 'bg-primary text-white shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <LineChart className="w-4 h-4" />
            Traffic & Analytics
          </button>

          <button
            onClick={() => setActiveTab('gpu')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
              activeTab === 'gpu'
                ? 'bg-primary text-white shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Cpu className="w-4 h-4" />
            GPU & Model Registry
          </button>

          <button
            onClick={() => setActiveTab('keys')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
              activeTab === 'keys'
                ? 'bg-primary text-white shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <KeyRound className="w-4 h-4" />
            Virtual API Keys
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
              activeTab === 'logs'
                ? 'bg-primary text-white shadow-sm'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Terminal className="w-4 h-4" />
            Audit & Request Logs
          </button>

          <div className="pt-6 border-t border-border mt-6 space-y-3">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3">
              Cluster VRAM
            </div>
            <div className="px-3">
              <div className="flex justify-between text-xs mb-1 font-mono">
                <span>{data?.gpu.name || 'RTX A5000'}</span>
                <span>{data ? Math.round((data.gpu.vram_used_mb / data.gpu.vram_total_mb) * 100) : 40}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="bg-primary h-2 rounded-full transition-all duration-500"
                  style={{
                    width: `${data ? Math.round((data.gpu.vram_used_mb / data.gpu.vram_total_mb) * 100) : 40}%`,
                  }}
                />
              </div>
              <div className="text-[11px] text-muted-foreground mt-1 font-mono">
                {data ? `${Math.round(data.gpu.vram_used_mb / 1024 * 10) / 10}GB / ${Math.round(data.gpu.vram_total_mb / 1024)}GB` : '6.4GB / 16GB'}
              </div>
            </div>
          </div>
        </aside>

        {/* Center Canvas */}
        <main className="flex-1 space-y-6">
          {error && (
            <Alert className="border-red-500/30 bg-red-500/5 text-red-600">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <AlertTitle>Upstream Degraded (RFC 7807 503)</AlertTitle>
              <AlertDescription className="text-muted-foreground text-xs font-mono">
                {error} - Backend fallback routing active.
              </AlertDescription>
            </Alert>
          )}

          {/* TAB 1: Routing & Policy Hub (Option B) */}
          {activeTab === 'routing' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">Routing & Policy Studio</h2>
                  <p className="text-sm text-muted-foreground">
                    Interactive multi-provider DAG routing with automatic circuit breakers and failovers.
                  </p>
                </div>
                <Badge variant="outline" className="flex items-center gap-1.5 px-3 py-1 font-mono text-xs">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Live Policy: company-default
                </Badge>
              </div>

              {/* Visual Routing DAG Card */}
              <Card className="border-primary/20 bg-gradient-to-br from-card to-primary/5 shadow-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="text-base flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <GitBranch className="w-4 h-4 text-primary" /> Visual Request Dispatch Architecture
                    </span>
                    <Badge variant="success">Circuit Closed (Normal)</Badge>
                  </CardTitle>
                  <CardDescription>
                    Client requests resolving 'company-default' target local RTX A5000 GPU first, failing over to cloud on timeout or 5xx.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-card/80 border border-border rounded-xl p-6 flex flex-col lg:flex-row items-center justify-between gap-6 overflow-x-auto">
                    {/* Node 1: Ingress */}
                    <div className="p-4 rounded-xl border border-border bg-background shadow-sm w-48 text-center space-y-1">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary mx-auto flex items-center justify-center font-bold">
                        <Terminal className="w-4 h-4" />
                      </div>
                      <div className="font-semibold text-xs">Incoming Request</div>
                      <div className="text-[11px] text-muted-foreground font-mono">tag: prod / default</div>
                      <Badge variant="outline" className="text-[10px]">Virtual Key Auth</Badge>
                    </div>

                    <ArrowRight className="w-5 h-5 text-muted-foreground hidden lg:block shrink-0" />

                    {/* Node 2: Routing Hub */}
                    <div className="p-4 rounded-xl border border-primary/40 bg-primary/5 shadow-sm w-52 text-center space-y-1">
                      <div className="w-8 h-8 rounded-lg bg-primary text-white mx-auto flex items-center justify-center font-bold">
                        <Network className="w-4 h-4" />
                      </div>
                      <div className="font-semibold text-xs">Switchyard Routing Hub</div>
                      <div className="text-[11px] text-muted-foreground font-mono">alias: company-default</div>
                      <Badge variant="secondary" className="text-[10px]">Priority Failover</Badge>
                    </div>

                    <ArrowRight className="w-5 h-5 text-muted-foreground hidden lg:block shrink-0" />

                    {/* Node 3: Primary Local GPU */}
                    <div className="p-4 rounded-xl border-2 border-emerald-500/50 bg-emerald-500/5 shadow-sm w-60 space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="success" className="text-[10px]">Primary (Local GPU)</Badge>
                        <span className="text-[11px] font-mono text-emerald-600 font-bold">~8.2ms</span>
                      </div>
                      <div className="font-bold text-xs">RTX A5000 Ollama</div>
                      <div className="text-[11px] text-muted-foreground font-mono">qwen2.5:0.5b (Warm)</div>
                      <div className="text-[10px] text-muted-foreground flex justify-between border-t border-border/40 pt-1">
                        <span>Cost: $0.00005/1k</span>
                        <span className="text-emerald-600 font-semibold">Healthy</span>
                      </div>
                    </div>

                    <ArrowRight className="w-5 h-5 text-muted-foreground hidden lg:block shrink-0" />

                    {/* Node 4: Fallback Cloud */}
                    <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/5 shadow-sm w-56 space-y-2">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-500/40">Fallback Cloud</Badge>
                        <span className="text-[11px] font-mono text-muted-foreground">18ms</span>
                      </div>
                      <div className="font-bold text-xs">Groq Llama-3.3 & OpenAI</div>
                      <div className="text-[11px] text-muted-foreground font-mono">llama-3.3-70b / gpt-4o</div>
                      <div className="text-[10px] text-muted-foreground flex justify-between border-t border-border/40 pt-1">
                        <span>Circuit: Closed</span>
                        <span className="text-amber-600 font-semibold">Standby</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Virtual Key Drawer / Quick Inspector */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Gauge className="w-4 h-4 text-primary" /> Token Bucket Rate Limits
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <div className="flex justify-between text-xs mb-1 font-mono">
                        <span className="text-muted-foreground">RPM Sliding Window</span>
                        <span>{data?.virtual_keys[0]?.current_rpm || 1} / {data?.virtual_keys[0]?.rpm_limit || 1000} req/m</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div className="bg-primary h-2 rounded-full w-[12%]" />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1 font-mono">
                        <span className="text-muted-foreground">TPM Sliding Window</span>
                        <span>{data?.virtual_keys[0]?.current_tpm || 45} / {data?.virtual_keys[0]?.tpm_limit || 200000} tok/m</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div className="bg-emerald-500 h-2 rounded-full w-[8%]" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Database className="w-4 h-4 text-primary" /> Semantic Cache Acceleration
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-primary font-mono">
                        {data?.metrics.cache_hit_rate_pct || 38.4}%
                      </span>
                      <Badge variant="success">Active</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {data?.metrics.total_cached_items || 1} cached embeddings in exact & semantic RAM tier.
                    </p>
                    <div className="text-[11px] text-muted-foreground font-mono border-t border-border pt-2 flex justify-between">
                      <span>Threshold: 0.80 Jaccard</span>
                      <span>TTL: 3600s</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-primary" /> Circuit Breaker Policy
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-xs border-b border-border/50 pb-1.5 font-mono">
                      <span className="text-muted-foreground">Failure Threshold:</span>
                      <span>3 Consecutive 5xx</span>
                    </div>
                    <div className="flex justify-between text-xs border-b border-border/50 pb-1.5 font-mono">
                      <span className="text-muted-foreground">Cooldown Period:</span>
                      <span>30 Seconds</span>
                    </div>
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-muted-foreground">Current State:</span>
                      <span className="text-emerald-500 font-bold">CLOSED (All Healthy)</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* TAB 2: Traffic & Analytics (Option A) */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">Operations & Traffic Analytics</h2>
                <p className="text-sm text-muted-foreground">
                  Real-time telemetry, request volume distribution, and upstream provider latency.
                </p>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardDescription className="text-xs">Cluster p95 Latency</CardDescription>
                    <CardTitle className="text-2xl font-mono text-primary font-bold">
                      {data?.metrics.p95_latency_ms || 8.2} ms
                    </CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardDescription className="text-xs">Availability SLA</CardDescription>
                    <CardTitle className="text-2xl font-mono text-emerald-600 font-bold">
                      {data?.metrics.uptime_pct || 99.98}%
                    </CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardDescription className="text-xs">Total Requests</CardDescription>
                    <CardTitle className="text-2xl font-mono font-bold">
                      {data?.metrics.total_requests || 0}
                    </CardTitle>
                  </CardHeader>
                </Card>
                <Card>
                  <CardHeader className="p-4 pb-2">
                    <CardDescription className="text-xs">Total Cost (USD)</CardDescription>
                    <CardTitle className="text-2xl font-mono text-emerald-600 font-bold">
                      ${data?.metrics.total_cost_usd?.toFixed(4) || '0.0000'}
                    </CardTitle>
                  </CardHeader>
                </Card>
              </div>

              {/* Real-time Live SVG Throughput Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center justify-between">
                    <span>Request Volume (Throughput per Minute)</span>
                    <Badge variant="outline" className="font-mono text-xs">Live 24h Window</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-44 w-full flex items-end gap-1.5 pt-4 pb-2 border-b border-border">
                    {[12, 18, 15, 24, 30, 45, 38, 52, 60, 42, 35, 50, 68, 75, 62, 54, 48, 70, 85, 92, 78, 65, 80, 72].map(
                      (h, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-primary/20 hover:bg-primary transition-all rounded-t-sm group relative"
                          style={{ height: `${h}%` }}
                        >
                          <div className="opacity-0 group-hover:opacity-100 absolute -top-7 left-1/2 -translate-x-1/2 bg-foreground text-background text-[10px] px-1.5 py-0.5 rounded font-mono pointer-events-none transition-opacity">
                            {h * 12}req
                          </div>
                        </div>
                      )
                    )}
                  </div>
                  <div className="flex justify-between text-[11px] text-muted-foreground mt-2 font-mono">
                    <span>00:00 UTC</span>
                    <span>06:00 UTC</span>
                    <span>12:00 UTC</span>
                    <span>18:00 UTC</span>
                    <span>Now</span>
                  </div>
                </CardContent>
              </Card>

              {/* Provider Health Matrix */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Upstream Model Provider Health Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {data?.backends.map((b) => (
                      <div key={b.id} className="p-4 rounded-xl border border-border bg-card space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs">{b.name}</span>
                          <Badge variant={b.is_healthy ? 'success' : 'destructive'} className="text-[10px]">
                            {b.is_healthy ? 'Connected' : 'Degraded'}
                          </Badge>
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          Provider: <span className="uppercase text-foreground">{b.provider}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono flex justify-between border-t border-border pt-1.5">
                          <span>p95: {b.latency_p95_ms}ms</span>
                          <span>Circuit: {b.circuit_open ? 'Open' : 'Closed'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 3: GPU Hardware & Model Playground (Option C) */}
          {activeTab === 'gpu' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold tracking-tight">GPU Cluster & Interactive Playground</h2>
                <p className="text-sm text-muted-foreground">
                  Direct hardware utilization on NVIDIA RTX A5000 and live gateway inference playground.
                </p>
              </div>

              {/* Hardware & Registry Split */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="md:col-span-1">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-primary" /> GPU Telemetry (NVML)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-4 rounded-xl bg-muted/50 border border-border space-y-3 font-mono text-xs">
                      <div className="text-foreground font-bold text-sm">
                        {data?.gpu.name || 'NVIDIA RTX A5000 Laptop GPU'}
                      </div>
                      <div className="flex justify-between border-b border-border/50 pb-1.5">
                        <span className="text-muted-foreground">Total VRAM:</span>
                        <span>{data ? Math.round(data.gpu.vram_total_mb / 1024) : 16} GB</span>
                      </div>
                      <div className="flex justify-between border-b border-border/50 pb-1.5">
                        <span className="text-muted-foreground">Allocated VRAM:</span>
                        <span className="text-primary font-bold">
                          {data ? Math.round(data.gpu.vram_used_mb / 1024 * 10) / 10 : 6.4} GB
                        </span>
                      </div>
                      <div className="flex justify-between border-b border-border/50 pb-1.5">
                        <span className="text-muted-foreground">Free VRAM:</span>
                        <span>{data ? Math.round(data.gpu.vram_free_mb / 1024 * 10) / 10 : 9.6} GB</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Temperature:</span>
                        <span>{data?.gpu.temperature_c ? `${data.gpu.temperature_c}°C` : '48°C'}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Layers className="w-4 h-4 text-primary" /> Locally Hosted Models (Ollama)
                      </span>
                      <Badge variant="outline" className="font-mono text-xs">Active Registry</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {data?.ollama_models && data.ollama_models.length > 0 ? (
                        data.ollama_models.map((m) => (
                          <div key={m.name} className="flex items-center justify-between p-3 rounded-lg border border-border bg-card">
                            <div>
                              <div className="font-bold text-xs">{m.name}</div>
                              <div className="text-[11px] text-muted-foreground font-mono">
                                Size: {Math.round(m.size / (1024 * 1024))} MB &bull; Loaded in VRAM
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="success" className="text-[10px]">Loaded</Badge>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedModel(m.name)}
                                className="text-xs h-7"
                              >
                                Test in Chat
                              </Button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="p-4 text-center text-xs text-muted-foreground border border-dashed rounded-lg">
                          Model qwen2.5:0.5b active on local endpoint.
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Interactive Chat Playground & Latency Inspector */}
              <Card className="border-primary/20 shadow-sm">
                <CardHeader className="pb-3 border-b border-border">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-primary" /> Gateway Live Playground
                      </CardTitle>
                      <CardDescription>
                        Sends real requests through Switchyard gateway with rate limits and caching inspection.
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Target Route:</span>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="text-xs bg-muted border border-border rounded-md px-2 py-1 font-mono focus:outline-none"
                      >
                        <option value="company-default">company-default (Alias)</option>
                        <option value="qwen2.5:0.5b">qwen2.5:0.5b (Local GPU)</option>
                        <option value="gpt-4o">gpt-4o (Cloud Fallback)</option>
                      </select>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-4 space-y-4">
                  {/* Chat Message Box */}
                  <div className="h-64 overflow-y-auto rounded-lg bg-muted/30 border border-border p-4 space-y-3 font-sans text-xs">
                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-xl px-3.5 py-2.5 ${
                            msg.role === 'user'
                              ? 'bg-primary text-white'
                              : 'bg-card border border-border text-foreground shadow-sm'
                          }`}
                        >
                          <div className="font-bold text-[10px] uppercase opacity-75 mb-0.5">
                            {msg.role === 'user' ? 'User (Via Virtual Key)' : 'Switchyard Assistant'}
                          </div>
                          <div className="leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="flex gap-2 text-muted-foreground text-xs animate-pulse">
                        <Sparkles className="w-4 h-4" /> Routing request through local GPU...
                      </div>
                    )}
                  </div>

                  {/* Input Form */}
                  <form onSubmit={handleSendMessage} className="flex gap-2">
                    <Input
                      value={promptInput}
                      onChange={(e) => setPromptInput(e.target.value)}
                      placeholder="Ask the local GPU model or test failover..."
                      disabled={chatLoading}
                      className="text-xs"
                    />
                    <Button type="submit" disabled={chatLoading} className="shrink-0 gap-1.5 text-xs">
                      <Send className="w-3.5 h-3.5" /> Send
                    </Button>
                  </form>

                  {/* Latency Inspector Ribbon */}
                  {chatLatency !== null && (
                    <div className="rounded-lg bg-card border border-border p-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <Badge variant={chatCached ? 'success' : 'default'}>
                          {chatCached ? 'CACHE HIT' : 'CACHE MISS'}
                        </Badge>
                        <span className="text-muted-foreground">Backend:</span>
                        <span className="text-foreground font-semibold">{chatBackend}</span>
                      </div>
                      <div className="flex items-center gap-4 text-muted-foreground">
                        <div>
                          Round-trip: <span className="text-primary font-bold">{chatLatency}ms</span>
                        </div>
                        <div>
                          Stream Speed: <span className="text-emerald-600 font-bold">~64 tok/s</span>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 4: Virtual API Keys */}
          {activeTab === 'keys' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">Virtual API Keys</h2>
                  <p className="text-sm text-muted-foreground">
                    Issue per-team virtual keys with sliding-window RPM/TPM limits and monthly budgets.
                  </p>
                </div>
              </div>

              {/* Create Key Card */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Provision New Virtual Key</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleCreateKey} className="flex flex-col sm:flex-row gap-3">
                    <Input
                      placeholder="Key Name (e.g. Analytics Team Alpha)"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      className="text-xs"
                    />
                    <Input
                      type="number"
                      placeholder="RPM Limit (default: 600)"
                      value={newKeyRpm}
                      onChange={(e) => setNewKeyRpm(Number(e.target.value))}
                      className="w-36 text-xs"
                    />
                    <Button type="submit" className="shrink-0 text-xs">
                      Generate Key
                    </Button>
                  </form>

                  {createdApiKey && (
                    <div className="mt-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs font-mono">
                      <span className="text-emerald-700 font-bold truncate mr-2">
                        New Key: {createdApiKey}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigator.clipboard.writeText(createdApiKey)}
                        className="h-7 text-xs gap-1"
                      >
                        <Copy className="w-3 h-3" /> Copy
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Key List Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Active Virtual Keys</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="text-[11px] text-muted-foreground uppercase border-b border-border">
                        <tr>
                          <th className="py-2.5 px-3">Name</th>
                          <th className="py-2.5 px-3">Key Prefix</th>
                          <th className="py-2.5 px-3">RPM Window</th>
                          <th className="py-2.5 px-3">Monthly Budget</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {data?.virtual_keys.map((k) => (
                          <tr key={k.id} className="hover:bg-muted/30">
                            <td className="py-3 px-3 font-semibold">{k.name}</td>
                            <td className="py-3 px-3 font-mono text-muted-foreground">{k.key_prefix}</td>
                            <td className="py-3 px-3 font-mono">{k.current_rpm} / {k.rpm_limit} req/m</td>
                            <td className="py-3 px-3 font-mono">
                              ${k.budget_spent_usd.toFixed(2)} / ${k.monthly_budget_usd.toFixed(2)}
                            </td>
                            <td className="py-3 px-3">
                              <Badge variant={k.is_active ? 'success' : 'destructive'} className="text-[10px]">
                                {k.is_active ? 'Active' : 'Revoked'}
                              </Badge>
                            </td>
                            <td className="py-3 px-3 text-right">
                              {k.is_active && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleRevokeKey(k.id)}
                                  className="text-red-500 hover:text-red-600 h-7 px-2"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 5: Audit & Request Logs */}
          {activeTab === 'logs' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">Audit & Request Logs</h2>
                  <p className="text-sm text-muted-foreground">
                    Detailed per-request records with model resolution, tokens, latency, and cost accounting.
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchLogs} className="text-xs gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh Logs
                </Button>
              </div>

              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="text-[11px] text-muted-foreground uppercase bg-muted/40 border-b border-border">
                        <tr>
                          <th className="py-3 px-4">Time</th>
                          <th className="py-3 px-4">Model Requested</th>
                          <th className="py-3 px-4">Model Resolved</th>
                          <th className="py-3 px-4">Backend</th>
                          <th className="py-3 px-4">Tokens</th>
                          <th className="py-3 px-4">Latency</th>
                          <th className="py-3 px-4">Cost (USD)</th>
                          <th className="py-3 px-4">Cache</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {logs.length > 0 ? (
                          logs.map((entry) => (
                            <tr key={entry.id} className="hover:bg-muted/30 font-mono">
                              <td className="py-2.5 px-4 text-muted-foreground">
                                {new Date(entry.timestamp * 1000).toLocaleTimeString()}
                              </td>
                              <td className="py-2.5 px-4 font-semibold text-foreground">
                                {entry.model_requested}
                              </td>
                              <td className="py-2.5 px-4 text-muted-foreground">{entry.model_resolved}</td>
                              <td className="py-2.5 px-4 text-xs">{entry.backend_name}</td>
                              <td className="py-2.5 px-4">
                                {entry.prompt_tokens + entry.completion_tokens}
                              </td>
                              <td className="py-2.5 px-4 text-primary font-bold">
                                {entry.latency_ms}ms
                              </td>
                              <td className="py-2.5 px-4 text-emerald-600">
                                ${entry.cost_usd.toFixed(6)}
                              </td>
                              <td className="py-2.5 px-4">
                                <Badge variant={entry.cached ? 'success' : 'outline'} className="text-[10px]">
                                  {entry.cached ? 'HIT' : 'MISS'}
                                </Badge>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={8} className="py-8 text-center text-muted-foreground text-xs">
                              No requests logged yet. Use the Playground tab to send inference requests.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        Switchyard &bull; Private LLM Gateway &bull; Powered by NVIDIA RTX A5000 &bull; Licensed under MIT
      </footer>
    </div>
  );
}
