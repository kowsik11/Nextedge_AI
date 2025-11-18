import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button-enhanced";
import { toast } from "@/hooks/use-toast";
import { triggerCmsBlogPostTest } from "@/lib/hubspotCmsTest";
import { useSupabaseAuth } from "@/providers/AuthProvider";

const TestsPage = () => {
  const { user, loading } = useSupabaseAuth();
  const navigate = useNavigate();
  const userId = user?.id;
  const [cmsTestRunning, setCmsTestRunning] = useState(false);
  const [runningKey, setRunningKey] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState("");
  const [lastLabel, setLastLabel] = useState("");
  const [latestContactId, setLatestContactId] = useState<string | null>(null);

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

  const callTestEndpoint = async (label: string, path: string) => {
    setRunningKey(label);
    setLastLabel(label);
    setLastResponse("");
    try {
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const text = await res.text();
      if (!res.ok) {
        throw new Error(text || `Request failed: ${res.status}`);
      }
      try {
        const json = JSON.parse(text || "{}");
        setLastResponse(JSON.stringify(json, null, 2));
        if (label === "Create contact" && json?.id) {
          setLatestContactId(String(json.id));
        }
      } catch {
        setLastResponse(text || "Request completed with no body.");
      }
      toast({ title: "Request sent", description: label });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleGetContact = async () => {
    const chosenId = latestContactId || window.prompt("Enter a HubSpot contact ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get contact");
    setLastLabel("Get contact");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/contacts/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        console.log("Get contact 404 payload:", text);
        setLastResponse("Contact not found. Check id or re-create.");
        toast({ title: "Contact not found", description: "Check id or re-create.", variant: "destructive" });
        return;
      }
      if (!res.ok) {
        throw new Error(text || `Request failed: ${res.status}`);
      }
      try {
        const json = JSON.parse(text || "{}");
        setLastResponse(JSON.stringify(json, null, 2));
      } catch {
        setLastResponse(text || "Request completed with no body.");
      }
      toast({ title: "Request sent", description: "Get contact" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleCmsTest = async () => {
    setCmsTestRunning(true);
    setLastLabel("Test CMS POST");
    try {
      const result = await triggerCmsBlogPostTest(userId);
      const pretty = JSON.stringify(result, null, 2);
      setLastResponse(pretty || "Request completed with no body.");
      toast({
        title: "CMS sample payload sent",
        description: result.hubspot_response?.id
          ? `HubSpot created blog post ${String(result.hubspot_response.id)}.`
          : "HubSpot accepted the sample payload.",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "CMS test failed", description: message, variant: "destructive" });
    } finally {
      setCmsTestRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-background px-6 py-8">
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">Test utilities</p>
            <h1 className="text-3xl font-semibold text-foreground">HubSpot API playground</h1>
            <p className="text-sm text-muted-foreground">
              Buttons send predefined dummy payloads using your HubSpot connection. No placeholders required.
            </p>
          </div>
          <Button variant="hero-outline" size="sm" onClick={() => navigate("/home")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to home
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button
            variant="hero"
            onClick={handleCmsTest}
            disabled={cmsTestRunning || !!runningKey}
          >
            {cmsTestRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending payload...
              </>
            ) : (
              "Test CMS POST"
            )}
          </Button>
          <Button variant="hero-outline" onClick={() => navigate("/blogs")} disabled={!!runningKey || cmsTestRunning}>
            View blog IDs
          </Button>
          <Button variant="hero-outline" onClick={() => navigate("/blog-authors")} disabled={!!runningKey || cmsTestRunning}>
            View blog authors
          </Button>
        </div>

        <div className="space-y-2 rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Contacts</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Create contact", path: "/api/hubspot/test/contacts/create" },
              { label: "Update contact", path: "/api/hubspot/test/contacts/update" },
              { label: "Get contact", path: "/api/hubspot/test/contacts/get" },
              { label: "Search contacts", path: "/api/hubspot/test/contacts/search" },
              { label: "List contacts", path: "/api/hubspot/test/contacts/list" },
              { label: "Batch read contacts", path: "/api/hubspot/test/contacts/batch-read" },
              { label: "Batch create contacts", path: "/api/hubspot/test/contacts/batch-create" },
              { label: "Batch update contacts", path: "/api/hubspot/test/contacts/batch-update" },
              { label: "Batch upsert contacts", path: "/api/hubspot/test/contacts/batch-upsert" },
              { label: "Associate contact → company", path: "/api/hubspot/test/contacts/associate" },
            ].map((item) => {
              const isRunning = runningKey === item.label;
              const clickHandler =
                item.label === "Get contact"
                  ? () => handleGetContact()
                  : () => callTestEndpoint(item.label, item.path);
              return (
                <Button
                  key={item.label}
                  variant="outline"
                  className="justify-between text-left"
                  disabled={!!runningKey || cmsTestRunning}
                  onClick={clickHandler}
                >
                  <span>{item.label}</span>
                  {isRunning && <Loader2 className="h-4 w-4 animate-spin" />}
                </Button>
              );
            })}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Latest response</p>
          {lastLabel && <p className="text-xs text-muted-foreground">{lastLabel}</p>}
          <pre className="mt-3 max-h-96 overflow-y-auto rounded-xl border border-border bg-background px-4 py-3 text-xs text-muted-foreground">
            {lastResponse || "Click a button above to send a request."}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default TestsPage;
