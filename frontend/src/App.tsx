import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, ShieldCheck, Sparkles, Terminal } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface HealthData {
  status: string;
  checks?: Record<string, string>;
  environment?: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch('/api/v1/readyz');
        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        setHealth(data);
      } catch (err: any) {
        setError(err.message || 'Failed to reach API gateway');
      } finally {
        setLoading(false);
      }
    }
    checkHealth();
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-white font-bold shadow-sm">
              S
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight">Switchyard</span>
              <span className="text-xs text-muted-foreground ml-2 hidden sm:inline-block">v1.0.0</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {loading ? (
              <Badge variant="outline" className="animate-pulse">Checking...</Badge>
            ) : error ? (
              <Badge variant="destructive" className="flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Degraded
              </Badge>
            ) : (
              <Badge variant="success" className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Operational
              </Badge>
            )}
            <Button variant="outline" size="sm" asChild>
              <a href="/docs" target="_blank" rel="noreferrer">
                API Docs
              </a>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-8">
        {error && (
          <Alert className="border-red-500/30 bg-red-500/5 text-red-600">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <AlertTitle>Upstream Degraded (RFC 7807 503)</AlertTitle>
            <AlertDescription className="text-muted-foreground text-xs font-mono">
              {error} - Backend dependency unavailable. Degraded mode active.
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight">Switchyard</h1>
          <p className="text-muted-foreground max-w-3xl leading-relaxed">
            Private LLM Gateway: unified OpenAI-compatible routing over local and cloud models with quotas, virtual keys, and audit logging
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center mb-2">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <CardTitle>Verified Production Core</CardTitle>
              <CardDescription>
                Strict CI enforcement against mock responses or fake token streams. All endpoints hit real models.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center mb-2">
                <Activity className="w-4 h-4" />
              </div>
              <CardTitle>Observability Stack</CardTitle>
              <CardDescription>
                Prometheus metrics, OpenTelemetry spans, and Langfuse tracing integrated into every inference call.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center mb-2">
                <Sparkles className="w-4 h-4" />
              </div>
              <CardTitle>Unique UI Archetype</CardTitle>
              <CardDescription>
                Tailored for Infra admin console workflows with custom tokens and typography.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>

        {/* System Status Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Terminal className="w-4 h-4 text-primary" /> Live Cluster Connectivity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="bg-muted/50 rounded-lg p-4 font-mono text-xs space-y-2">
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Gateway Port:</span>
                <span>8001</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Frontend Port:</span>
                <span>3001</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">LLM Provider:</span>
                <span>Ollama / Local GPU (Fallback: Cloud)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Cluster Readiness:</span>
                <span className={health?.status === 'ready' ? 'text-emerald-500' : 'text-amber-500'}>
                  {health?.status || 'connecting'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        Switchyard &bull; Autonomous AI Production Stack &bull; Licensed under MIT
      </footer>
    </div>
  );
}
