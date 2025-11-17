import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button-enhanced";
import { toast } from "@/hooks/use-toast";
import { fetchHubSpotTestCatalog, runHubSpotTest, type HubSpotTestEntry } from "@/lib/hubspotTests";
import { useSupabaseAuth } from "@/providers/AuthProvider";

const TestsPage = () => {
  const { user, session, loading } = useSupabaseAuth();
  const navigate = useNavigate();
  const userId = user?.id;
  const accessToken = session?.access_token;

  const [catalog, setCatalog] = useState<HubSpotTestEntry[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [runningKey, setRunningKey] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState("");
  const [lastEntry, setLastEntry] = useState<HubSpotTestEntry | null>(null);

  useEffect(() => {
    if (loading) return;
    setCatalogLoading(true);
    fetchHubSpotTestCatalog(accessToken)
      .then((data) => setCatalog(data))
      .catch((error: Error) => setCatalogError(error.message))
      .finally(() => setCatalogLoading(false));
  }, [accessToken, loading]);

  const groupedTests = useMemo(() => {
    const map = new Map<string, HubSpotTestEntry[]>();
    catalog.forEach((entry) => {
      if (!map.has(entry.section)) {
        map.set(entry.section, []);
      }
      map.get(entry.section)!.push(entry);
    });
    return Array.from(map.entries());
  }, [catalog]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-lg text-muted-foreground">
        Please sign in to use the test utilities.
      </div>
    );
  }

  const handleRun = async (entry: HubSpotTestEntry) => {
    setRunningKey(entry.key);
    setLastEntry(entry);
    setLastResponse("");
    try {
      const response = await runHubSpotTest({ userId, key: entry.key, accessToken });
      const pretty = JSON.stringify(response.result, null, 2);
      setLastResponse(pretty || "Request completed with no body.");
      toast({ title: "Request sent", description: `${entry.method} ${entry.path}` });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      toast({ title: "Test failed", description: message, variant: "destructive" });
      setLastResponse(`Error: ${message}`);
    } finally {
      setRunningKey(null);
    }
  };

  return (
    <div className="min-h-screen bg-background px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">Test utilities</p>
            <h1 className="text-3xl font-semibold text-foreground">HubSpot API playground</h1>
            <p className="text-sm text-muted-foreground">
              Each button below sends a predefined sample payload for that endpoint using your connected HubSpot portal.
            </p>
          </div>
          <Button variant="hero-outline" size="sm" onClick={() => navigate("/home")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to home
          </Button>
        </div>

        {catalogLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-card/80 p-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading endpoints...
          </div>
        )}

        {!catalogLoading && catalogError && (
          <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-6 text-destructive">{catalogError}</div>
        )}

        {!catalogLoading && !catalogError && (
          <div className="space-y-6">
            {groupedTests.map(([section, entries]) => (
              <div key={section} className="rounded-2xl border border-border bg-card/70 p-5 shadow-card">
                <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{section}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {entries.map((entry) => {
                    const isRunning = runningKey === entry.key;
                    return (
                      <Button
                        key={entry.key}
                        variant="outline"
                        className="flex justify-between gap-3 text-left"
                        disabled={!!runningKey && !isRunning}
                        onClick={() => handleRun(entry)}
                      >
                        <span className="text-sm font-semibold text-foreground">{entry.title}</span>
                        <span className="text-xs font-mono text-muted-foreground">
                          {isRunning ? <Loader2 className="h-3 w-3 animate-spin" /> : entry.method}
                        </span>
                      </Button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Latest response</p>
          {lastEntry && (
            <p className="mt-2 text-xs font-mono text-muted-foreground">
              {lastEntry.method} {lastEntry.path}
            </p>
          )}
          <pre className="mt-3 max-h-96 overflow-y-auto rounded-xl border border-border bg-background px-4 py-3 text-xs text-muted-foreground">
            {lastResponse || "Select an endpoint above to send a sample request."}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default TestsPage;
