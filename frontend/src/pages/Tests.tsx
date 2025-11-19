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
  const [latestCompanyId, setLatestCompanyId] = useState<string | null>(null);
  const [latestDealId, setLatestDealId] = useState<string | null>(null);
  const [latestTicketId, setLatestTicketId] = useState<string | null>(null);
  const [latestOrderId, setLatestOrderId] = useState<string | null>(null);
  const [latestPaymentId, setLatestPaymentId] = useState<string | null>(null);

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
        if (label === "Create company" && json?.id) {
          setLatestCompanyId(String(json.id));
        }
        if (label === "Create deal" && json?.id) {
          setLatestDealId(String(json.id));
        }
        if (label === "Create ticket" && json?.id) {
          setLatestTicketId(String(json.id));
        }
        if (label === "Create order" && json?.id) {
          setLatestOrderId(String(json.id));
        }
        if (label === "Create payment" && json?.id) {
          setLatestPaymentId(String(json.id));
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

  const handleGetCompany = async () => {
    const chosenId = latestCompanyId || window.prompt("Enter a HubSpot company ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get company");
    setLastLabel("Get company");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/companies/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        console.log("Get company 404 payload:", text);
        setLastResponse("Company not found. Check id or re-create.");
        toast({ title: "Company not found", description: "Check id or re-create.", variant: "destructive" });
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
      toast({ title: "Request sent", description: "Get company" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleGetDeal = async () => {
    const chosenId = latestDealId || window.prompt("Enter a HubSpot deal ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get deal");
    setLastLabel("Get deal");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/deals/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        console.log("Get deal 404 payload:", text);
        setLastResponse("Deal not found. Check id or re-create.");
        toast({ title: "Deal not found", description: "Check id or re-create.", variant: "destructive" });
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
      toast({ title: "Request sent", description: "Get deal" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleGetTicket = async () => {
    const chosenId = latestTicketId || window.prompt("Enter a HubSpot ticket ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get ticket");
    setLastLabel("Get ticket");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/tickets/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        console.log("Get ticket 404 payload:", text);
        setLastResponse("Ticket not found. Check id or re-create.");
        toast({ title: "Ticket not found", description: "Check id or re-create.", variant: "destructive" });
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
      toast({ title: "Request sent", description: "Get ticket" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleGetOrder = async () => {
    const chosenId = latestOrderId || window.prompt("Enter a HubSpot order ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get order");
    setLastLabel("Get order");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/orders/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        setLastResponse("Order not found. Check id or re-create.");
        toast({ title: "Order not found", description: "Check id or re-create.", variant: "destructive" });
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
      toast({ title: "Request sent", description: "Get order" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error occurred.";
      setLastResponse(`Error: ${message}`);
      toast({ title: "Test failed", description: message, variant: "destructive" });
    } finally {
      setRunningKey(null);
    }
  };

  const handleGetPayment = async () => {
    const chosenId = latestPaymentId || window.prompt("Enter a HubSpot payment ID to fetch")?.trim();
    if (!chosenId) return;
    setRunningKey("Get payment");
    setLastLabel("Get payment");
    setLastResponse("");
    try {
      const res = await fetch("/api/hubspot/test/payments/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, id: chosenId }),
      });
      const text = await res.text();
      if (res.status === 404) {
        setLastResponse("Payment not found. Check id or re-create.");
        toast({ title: "Payment not found", description: "Check id or re-create.", variant: "destructive" });
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
      toast({ title: "Request sent", description: "Get payment" });
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

        <div className="space-y-2 rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Companies</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Create company", path: "/api/hubspot/test/companies/create" },
              { label: "Update company", path: "/api/hubspot/test/companies/update" },
              { label: "Get company", path: "/api/hubspot/test/companies/get" },
              { label: "Search companies", path: "/api/hubspot/test/companies/search" },
              { label: "List companies", path: "/api/hubspot/test/companies/list" },
              { label: "Batch read companies", path: "/api/hubspot/test/companies/batch-read" },
              { label: "Batch create companies", path: "/api/hubspot/test/companies/batch-create" },
              { label: "Batch update companies", path: "/api/hubspot/test/companies/batch-update" },
              { label: "Batch upsert companies", path: "/api/hubspot/test/companies/batch-upsert" },
              { label: "Associate company -> contact", path: "/api/hubspot/test/companies/associate" },
            ].map((item) => {
              const isRunning = runningKey === item.label;
              const clickHandler =
                item.label === "Get company"
                  ? () => handleGetCompany()
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

        <div className="space-y-2 rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Deals</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Create deal", path: "/api/hubspot/test/deals/create" },
              { label: "Update deal", path: "/api/hubspot/test/deals/update" },
              { label: "Get deal", path: "/api/hubspot/test/deals/get" },
              { label: "Search deals", path: "/api/hubspot/test/deals/search" },
              { label: "List deals", path: "/api/hubspot/test/deals/list" },
              { label: "Batch read deals", path: "/api/hubspot/test/deals/batch-read" },
              { label: "Batch create deals", path: "/api/hubspot/test/deals/batch-create" },
              { label: "Batch update deals", path: "/api/hubspot/test/deals/batch-update" },
              { label: "Associate deal -> contact", path: "/api/hubspot/test/deals/associate" },
              { label: "Batch delete deals", path: "/api/hubspot/test/deals/batch-archive" },
            ].map((item) => {
              const isRunning = runningKey === item.label;
              const clickHandler =
                item.label === "Get deal"
                  ? () => handleGetDeal()
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

        <div className="space-y-2 rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Tickets</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Create ticket", path: "/api/hubspot/test/tickets/create" },
              { label: "Update ticket", path: "/api/hubspot/test/tickets/update" },
              { label: "Get ticket", path: "/api/hubspot/test/tickets/get" },
              { label: "Search tickets", path: "/api/hubspot/test/tickets/search" },
              { label: "List tickets", path: "/api/hubspot/test/tickets/list" },
              { label: "Batch read tickets", path: "/api/hubspot/test/tickets/batch-read" },
              { label: "Batch update tickets", path: "/api/hubspot/test/tickets/batch-update" },
              { label: "Associate ticket -> contact", path: "/api/hubspot/test/tickets/associate" },
              { label: "Pin ticket activity", path: "/api/hubspot/test/tickets/pin-activity" },
              { label: "Delete ticket", path: "/api/hubspot/test/tickets/delete" },
              { label: "Batch delete tickets", path: "/api/hubspot/test/tickets/batch-archive" },
            ].map((item) => {
              const isRunning = runningKey === item.label;
              const clickHandler =
                item.label === "Get ticket"
                  ? () => handleGetTicket()
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

        <div className="space-y-2 rounded-2xl border border-border bg-card/70 p-5 shadow-card">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Orders</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Create order", path: "/api/hubspot/test/orders/create" },
              { label: "Update order", path: "/api/hubspot/test/orders/update" },
              { label: "Get order", path: "/api/hubspot/test/orders/get" },
              { label: "Search orders", path: "/api/hubspot/test/orders/search" },
              { label: "List orders", path: "/api/hubspot/test/orders/list" },
              { label: "Batch read orders", path: "/api/hubspot/test/orders/batch-read" },
              { label: "Batch create orders", path: "/api/hubspot/test/orders/batch-create" },
              { label: "Batch update orders", path: "/api/hubspot/test/orders/batch-update" },
              { label: "Batch archive orders", path: "/api/hubspot/test/orders/batch-archive" },
              { label: "Create payment", path: "/api/hubspot/test/payments/create" },
              { label: "Update payment", path: "/api/hubspot/test/payments/update" },
              { label: "Get payment", path: "/api/hubspot/test/payments/get" },
              { label: "Search payments", path: "/api/hubspot/test/payments/search" },
              { label: "List payments", path: "/api/hubspot/test/payments/list" },
              { label: "Delete payment", path: "/api/hubspot/test/payments/delete" },
            ].map((item) => {
              const isRunning = runningKey === item.label;
              const clickHandler =
                item.label === "Get order"
                  ? () => handleGetOrder()
                  : item.label === "Get payment"
                    ? () => handleGetPayment()
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
