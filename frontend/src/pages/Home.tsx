import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Image as ImageIcon,
  Inbox,
  Link2,
  Loader2,
  Mail,
  Paperclip,
  RefreshCw,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button-enhanced";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useSupabaseAuth } from "@/providers/AuthProvider";

type ConnectionState = "connecting" | "disconnected" | "connected";
type InboxFilter = "new" | "processed" | "error";

type HubSpotStatus = {
  connected: boolean;
  email?: string;
};

type GmailStatus = {
  connected: boolean;
  email?: string;
  last_checked_at?: string | null;
  counts?: Record<InboxFilter, number>;
  baseline_at?: string | null;
  baseline_ready?: boolean | null;
};

type InboxSummary = {
  last_checked_at: string | null;
  counts: Record<InboxFilter, number>;
  total: number;
};

type InboxMessage = {
  id: string;
  subject: string;
  sender: string | null;
  preview: string;
  snippet?: string | null;
  status: InboxFilter | "error";
  has_attachments: boolean;
  has_links: boolean;
  has_images: boolean;
  received_at?: string | null;
  created_at?: string;
  updated_at?: string;
  gmail_url?: string;
  crm_record_url?: string | null;
  error?: string | null;
};

const formatRelativeTime = (iso?: string | null) => {
  if (!iso) return "never";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "unknown";
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

const Home = () => {
  const { user, session, loading, signOut } = useSupabaseAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const userId = user?.id;

  const [gmailStatus, setGmailStatus] = useState<GmailStatus>({
    connected: false,
    counts: { new: 0, processed: 0, error: 0 },
    baseline_ready: false,
  });
  const [gmailState, setGmailState] = useState<ConnectionState>("connecting");
  const [gmailDisconnecting, setGmailDisconnecting] = useState(false);
  const [hubspotState, setHubspotState] =
    useState<ConnectionState>("connecting");
  const [hubspotStatus, setHubspotStatus] = useState<HubSpotStatus | null>(
    null
  );
  const [hubspotError, setHubspotError] = useState<string | null>(null);
  const [hubspotDisconnecting, setHubspotDisconnecting] = useState(false);

  const [showInsights, setShowInsights] = useState(false);
  const [showInbox, setShowInbox] = useState(false);

  const [summary, setSummary] = useState<InboxSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [filter, setFilter] = useState<InboxFilter>("new");
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedMessage, setSelectedMessage] = useState<InboxMessage | null>(
    null
  );

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [autoSynced, setAutoSynced] = useState(false);

  const bannerParam = searchParams.get("connected");
  const showBanner = bannerParam === "google" || bannerParam === "hubspot";
  const buildHeaders = useCallback(
    (extra: HeadersInit = {}) => ({
      ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
      ...extra,
    }),
    [session?.access_token],
  );

  const fetchGmailStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`/api/gmail/status?user_id=${encodeURIComponent(userId)}`, {
        headers: buildHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load Gmail status");
      const payload = (await res.json()) as GmailStatus;
      setGmailStatus(payload);
      setGmailState(payload.connected ? "connected" : "disconnected");
    } catch (error) {
      console.error(error);
      setGmailStatus({
        connected: false,
        counts: { new: 0, processed: 0, error: 0 },
        baseline_ready: false,
      });
      setGmailState("disconnected");
    }
  }, [buildHeaders, userId]);

  const fetchHubSpotStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`/api/hubspot/status?user_id=${encodeURIComponent(userId)}`, {
        headers: buildHeaders(),
      });
      if (!res.ok) throw new Error(`Status request failed: ${res.status}`);
      const payload = (await res.json()) as HubSpotStatus;
      setHubspotStatus(payload);
      setHubspotState(payload.connected ? "connected" : "disconnected");
      setHubspotError(null);
    } catch (error) {
      console.error(error);
      setHubspotError("Unable to load HubSpot status.");
      setHubspotState("disconnected");
    }
  }, [buildHeaders, userId]);

  const triggerSync = useCallback(
    async (opts?: { openInsights?: boolean }) => {
      if (!userId) return;
      setIsSyncing(true);
      setSyncMessage(
        !gmailStatus.baseline_ready ? "Preparing Gmail baseline..." : null
      );
      try {
        const res = await fetch("/api/gmail/sync/start", {
          method: "POST",
          headers: buildHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ user_id: userId, max_messages: 200 }),
        });
        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || "Failed to start Gmail sync");
        }
        const payload = await res.json();
        setSyncMessage(`Captured ${payload.processed} messages`);
        if (opts?.openInsights) setShowInsights(true);
        await fetchGmailStatus();
      } catch (error) {
        console.error(error);
        setSyncMessage("Sync failed. Try again.");
      } finally {
        setIsSyncing(false);
      }
    },
    [buildHeaders, fetchGmailStatus, gmailStatus.baseline_ready, userId]
  );

  useEffect(() => {
    if (userId) {
      fetchGmailStatus();
      fetchHubSpotStatus();
    }
  }, [fetchGmailStatus, fetchHubSpotStatus, userId]);

  useEffect(() => {
    setAutoSynced(false);
  }, [userId]);

  useEffect(() => {
    if (
      gmailState === "connected" &&
      hubspotState === "connected" &&
      userId &&
      !autoSynced
    ) {
      setAutoSynced(true);
      triggerSync();
    }
  }, [autoSynced, gmailState, hubspotState, triggerSync, userId]);

  useEffect(() => {
    if (!showInsights || !userId) return;
    let active = true;
    const fetchSummary = async () => {
      try {
        const res = await fetch(
          `/api/inbox/summary?user_id=${encodeURIComponent(userId)}`,
          { headers: buildHeaders() }
        );
        if (!res.ok) throw new Error("Unable to fetch inbox summary");
        const data = (await res.json()) as InboxSummary;
        if (active) {
          setSummary(data);
          setSummaryError(null);
        }
      } catch (error) {
        console.error(error);
        if (active) setSummaryError("Unable to refresh inbox summary.");
      }
    };
    fetchSummary();
    const interval = window.setInterval(fetchSummary, 15000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [buildHeaders, showInsights, userId]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
    }, 400);
    return () => window.clearTimeout(handle);
  }, [searchTerm]);

  useEffect(() => {
    if (!showInbox || !userId) return;
    let active = true;
    setMessagesLoading(true);
    setMessagesError(null);
    const params = new URLSearchParams({
      user_id: userId,
      status: filter,
      limit: "50",
    });
    if (debouncedSearch) params.set("query", debouncedSearch);
    fetch(`/api/inbox/messages?${params.toString()}`, { headers: buildHeaders() })
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load inbox messages");
        return (await res.json()).messages as InboxMessage[];
      })
      .then((payload) => {
        if (!active) return;
        setMessages(payload);
        setSelectedMessage((previous) => {
          if (!payload.length) return null;
          if (previous) {
            const stillExists = payload.find((item) => item.id === previous.id);
            if (stillExists) return stillExists;
          }
          return payload[0];
        });
      })
      .catch((error) => {
        console.error(error);
        if (active) {
          setMessagesError("Unable to load inbox preview.");
          setMessages([]);
          setSelectedMessage(null);
        }
      })
      .finally(() => {
        if (active) setMessagesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [buildHeaders, showInbox, filter, debouncedSearch, userId]);

  const summaryStats = useMemo(
    () => [
      {
        label: "New",
        value: summary?.counts.new ?? gmailStatus.counts?.new ?? 0,
        accent: "text-primary",
      },
      {
        label: "Processed",
        value: summary?.counts.processed ?? gmailStatus.counts?.processed ?? 0,
        accent: "text-success",
      },
      {
        label: "Errors",
        value: summary?.counts.error ?? gmailStatus.counts?.error ?? 0,
        accent: "text-destructive",
      },
    ],
    [summary, gmailStatus]
  );

  const greeting =
    (user?.user_metadata as Record<string, string | undefined>)?.full_name ||
    user?.email ||
    "there";
  const baselineReady = gmailStatus.baseline_ready ?? true;
  const canProceed =
    gmailState === "connected" && hubspotState === "connected";

  const handleConnectGmail = () => {
    if (!userId) return;
    setGmailState("connecting");
    window.location.href = `/api/google/connect?user_id=${encodeURIComponent(
      userId
    )}`;
  };

  const handleDisconnectGmail = async () => {
    if (!userId) return;
    setGmailDisconnecting(true);
    try {
      const res = await fetch("/api/google/disconnect", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error("Disconnect failed");
      await fetchGmailStatus();
      setGmailState("disconnected");
    } catch (error) {
      console.error(error);
    } finally {
      setGmailDisconnecting(false);
    }
  };

  const handleConnectHubSpot = () => {
    if (!userId) return;
    setHubspotState("connecting");
    window.location.href = `/api/hubspot/connect?user_id=${encodeURIComponent(
      userId
    )}`;
  };

  const handleDisconnectHubSpot = async () => {
    if (!userId) return;
    setHubspotDisconnecting(true);
    try {
      const res = await fetch("/api/hubspot/disconnect", { // Assuming a similar disconnect endpoint for HubSpot
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error("Disconnect failed");
      await fetchHubSpotStatus();
      setHubspotState("disconnected");
    } catch (error) {
      console.error(error);
    } finally {
      setHubspotDisconnecting(false);
    }
  };


  const handleOpenTests = () => {
    navigate("/tests");
  };

  const handleSignOut = async () => {
    try {
      const uid = user?.id;
      if (uid) {
        // Best-effort backend disconnects; ignore failures
        await fetch("/api/google/disconnect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        }).catch(() => {});
        await fetch("/api/hubspot/disconnect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        }).catch(() => {});
      }
    } finally {
      await signOut();
      // Reset local UI state
      setGmailState("disconnected");
      setHubspotState("disconnected");
      setGmailStatus({
        connected: false,
        counts: { new: 0, processed: 0, error: 0 },
        baseline_ready: false,
      });
      setHubspotStatus(null);
      setShowInbox(false);
      setShowInsights(false);
      navigate("/");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-lg text-muted-foreground">
        Please sign in to continue.
      </div>
    );
  }

  // Null-safe wrapper for hubspotStatus
  const hubspotCardStatus = hubspotStatus ?? {
    connected: false,
    email: "",
  };

  return (
    <div className="min-h-screen bg-background px-6 py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">
            Hi {greeting}
          </h1>
          <p className="text-muted-foreground">
            Let's secure your automations in two quick steps.
          </p>
        </div>

        {showBanner && (
          <div className="flex items-center gap-2 rounded-xl border border-success/30 bg-success/10 px-4 py-3 text-sm font-medium text-success">
            <CheckCircle2 className="h-4 w-4" />
            Connected successfully!
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2">
          <ConnectionCard
            title="Connect Gmail"
            description={
              gmailStatus.email
                ? `Connected as ${gmailStatus.email}`
                : "Authorize NextEdge to read new emails and attachments securely."
            }
            state={gmailState}
            onConnect={handleConnectGmail}
            detail={
              gmailStatus.baseline_at
                ? `Watching new mail since ${formatRelativeTime(
                    gmailStatus.baseline_at
                  )}`
                : gmailStatus.last_checked_at
                ? `Last sync ${formatRelativeTime(gmailStatus.last_checked_at)}`
                : undefined
            }
            onDisconnect={
              gmailStatus.connected ? handleDisconnectGmail : undefined
            }
            disconnecting={gmailDisconnecting}
          />
          <ConnectionCard
            title="Connect HubSpot"
            description={
              hubspotCardStatus.connected
                ? `Connected as ${hubspotCardStatus.email || "HubSpot user"}`
                : "Allow us to write AI-enriched insights back to your CRM."
            }
            state={hubspotState}
            onConnect={handleConnectHubSpot}
            detail={hubspotCardStatus.connected ? "Synced" : undefined}
            error={hubspotError || undefined}
            onDisconnect={hubspotCardStatus.connected ? handleDisconnectHubSpot : undefined}
            disconnecting={hubspotDisconnecting}
          />
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-dashed border-border bg-muted/20 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-base font-semibold text-foreground">
              All set? Jump into your live inbox.
            </p>
            <p className="text-sm text-muted-foreground">
              We'll keep polling Gmail once both integrations are active.
              You can re-run sync anytime.
            </p>
            {gmailStatus.connected && !baselineReady && (
              <p className="text-xs text-muted-foreground">
                Waiting for the first baseline sync to finish? hang tight.
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Button
              variant="hero"
              size="lg"
              disabled={!canProceed || isSyncing}
              onClick={() => triggerSync({ openInsights: true })}
            >
              {isSyncing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Syncing…
                </>
              ) : (
                <>
                  Next
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
            <Button
              variant="hero-outline"
              size="lg"
              disabled={!gmailStatus.connected || !baselineReady || isSyncing}
              onClick={() => triggerSync()}
            >
              <RefreshCw className="h-4 w-4" />
              Sync again
            </Button>
          </div>
        </div>
        {syncMessage && (
          <p className="text-sm font-medium text-muted-foreground">
            {syncMessage}
          </p>
        )}
      </div>

      {showInsights && (
        <div className="fixed inset-y-0 right-0 z-30 w-full max-w-md border-l border-border bg-background shadow-2xl">
          <div className="flex h-full flex-col p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-primary">
                  Live feed
                </p>
                <h2 className="text-2xl font-semibold text-foreground">
                  New emails detected
                </h2>
                <p className="text-sm text-muted-foreground">
                  Last checked{" "}
                  {summary?.last_checked_at
                    ? formatRelativeTime(summary.last_checked_at)
                    : "never"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowInsights(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="mt-8 grid grid-cols-3 gap-3">
              {summaryStats.map((item) => (
                <div
                  key={item.label}
                  className="rounded-xl border border-border bg-muted/40 p-4 text-center"
                >
                  <p className={cn("text-2xl font-bold", item.accent)}>
                    {item.value}
                  </p>
                  <p className="text-xs uppercase text-muted-foreground">
                    {item.label}
                  </p>
                </div>
              ))}
            </div>
            {summaryError && (
              <p className="mt-3 text-sm text-destructive">{summaryError}</p>
            )}

            <div className="mt-auto space-y-4">
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="text-sm text-muted-foreground">Inbox health</p>
                <p className="text-3xl font-semibold text-foreground">
                  {summary?.counts.new ?? 0} new emails
                </p>
                <p className="text-xs text-muted-foreground">
                  {(summary?.counts.processed ?? 0).toLocaleString()} processed
                  · {(summary?.counts.error ?? 0).toLocaleString()} with errors
                </p>
              </div>
              <Button
                variant="hero-outline"
                size="lg"
                onClick={() => setShowInbox(true)}
              >
                View list
              </Button>
            </div>
          </div>
        </div>
      )}

      {showInbox && (
        <div className="fixed inset-y-0 left-0 z-40 w-full max-w-5xl border-r border-border bg-background shadow-2xl">
          <div className="flex h-full flex-col p-6 overflow-hidden">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-primary">
                  Inbox preview
                </p>
                <h2 className="text-2xl font-semibold text-foreground">
                  Latest Gmail activity
                </h2>
                <p className="text-sm text-muted-foreground">
                  Filter, search, and open any record in Gmail or HubSpot.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowInbox(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="mt-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex gap-2">
                {(["new", "processed", "error"] as InboxFilter[]).map(
                  (item) => (
                    <Button
                      key={item}
                      variant={filter === item ? "hero" : "outline"}
                      size="sm"
                      onClick={() => setFilter(item)}
                    >
                      {item.charAt(0).toUpperCase() + item.slice(1)}
                    </Button>
                  )
                )}
              </div>
              <div className="flex w-full gap-2 lg:max-w-xs">
                <Input
                  placeholder="Search subject, sender, or content..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                />
              </div>
            </div>

            <div className="mt-6 grid flex-1 gap-6 overflow-hidden lg:grid-cols-[1.2fr,0.8fr]">
              <div className="flex min-h-0 flex-col rounded-2xl border border-border bg-card/60">
                <div className="flex items-center gap-2 border-b border-border px-4 py-3 text-sm text-muted-foreground">
                  <Inbox className="h-4 w-4" />
                  <span>{messages.length} conversations</span>
                </div>
                <div className="flex-1 overflow-y-auto px-2 py-3">
                  {messagesLoading && (
                    <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Loading emails...
                    </div>
                  )}
                  {!messagesLoading && !messages.length && (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                      {messagesError || "Nothing to show just yet."}
                    </div>
                  )}
                  <div className="space-y-2">
                    {messages.map((message) => (
                      <button
                        key={message.id}
                        className={cn(
                          "w-full rounded-xl border border-transparent bg-background/80 p-4 text-left transition hover:border-primary/40 hover:bg-primary/5",
                          selectedMessage?.id === message.id &&
                            "border-primary bg-primary/5"
                        )}
                        onClick={() => setSelectedMessage(message)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-foreground">
                              {message.subject}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {message.sender || "Unknown sender"}
                            </p>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(
                              message.received_at || message.created_at
                            )}
                          </span>
                        </div>
                        <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                          {message.preview || "No preview"}
                        </p>
                        <div className="mt-3 flex items-center gap-3 text-muted-foreground">
                          {message.has_attachments && (
                            <Paperclip className="h-4 w-4" />
                          )}
                          {message.has_links && <Link2 className="h-4 w-4" />}
                          {message.has_images && (
                            <ImageIcon className="h-4 w-4" />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex min-h-0 flex-col rounded-2xl border border-border bg-card/60 p-4">
                {selectedMessage ? (
                  <>
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="secondary" className="uppercase">
                        {selectedMessage.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Updated{" "}
                        {formatRelativeTime(
                          selectedMessage.updated_at ||
                            selectedMessage.created_at
                        )}
                      </span>
                    </div>
                    <div className="mt-4 space-y-1">
                      <p className="text-lg font-semibold text-foreground">
                        {selectedMessage.subject}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {selectedMessage.sender || "Unknown sender"}
                      </p>
                    </div>
                    <div className="mt-4 flex-1 overflow-y-auto rounded-lg bg-background/60 p-4">
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                        {selectedMessage.preview ||
                          selectedMessage.snippet ||
                          "No preview available yet."}
                      </p>
                      {selectedMessage.error && (
                        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                          {selectedMessage.error}
                        </p>
                      )}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3">
                      {selectedMessage.gmail_url && (
                        <Button variant="hero-outline" size="sm" asChild>
                          <a
                            href={selectedMessage.gmail_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open in Gmail
                          </a>
                        </Button>
                      )}
                      {selectedMessage.crm_record_url && (
                        <Button variant="hero" size="sm" asChild>
                          <a
                            href={selectedMessage.crm_record_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open in CRM note
                          </a>
                        </Button>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-center text-muted-foreground">
                    <Mail className="mb-4 h-8 w-8 text-muted-foreground" />
                    <p className="text-sm">
                      Select a message to view the enriched preview.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {!showInbox && (
        <div className="fixed bottom-6 left-6 z-50">
          <Button
            variant="hero-outline"
            size="lg"
            className="mb-3 shadow-xl"
            onClick={handleSignOut}
          >
            Sign Out
          </Button>
          <Button
            variant="hero"
            size="lg"
            className="shadow-xl"
            onClick={handleOpenTests}
            disabled={hubspotState !== "connected"}
          >
            Open tests
          </Button>
        </div>
      )}
    </div>
  );
};

type ConnectionCardProps = {
  title: string;
  description: string;
  state: ConnectionState;
  onConnect: () => void;
  detail?: string;
  error?: string;
  onDisconnect?: () => void;
  disconnecting?: boolean;
};

const ConnectionCard = ({
  title,
  description,
  state,
  onConnect,
  detail,
  error,
  onDisconnect,
  disconnecting,
}: ConnectionCardProps) => {
  const isConnected = state === "connected";
  const isConnecting = state === "connecting";

  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card/70 p-6 shadow-card transition",
        isConnected && "border-success/40 bg-success/5"
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-xl font-semibold text-foreground">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
          {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
        </div>
        <Badge
          variant={isConnected ? "secondary" : "outline"}
          className="flex items-center gap-1 text-xs uppercase"
        >
          {isConnecting && <Loader2 className="h-3 w-3 animate-spin" />}
          {isConnected && <CheckCircle2 className="h-3 w-3 text-success" />}
          {isConnecting
            ? "Connecting"
            : isConnected
            ? "Connected"
            : "Not Connected"}
        </Badge>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <div>
          {isConnected ? (
            <p className="text-sm font-medium text-success">Connected.</p>
          ) : (
            <p className="text-sm text-muted-foreground">
              {isConnecting
                ? "Waiting for authorization…"
                : "Click connect to continue."}
            </p>
          )}
        </div>
        {!isConnected && (
          <Button
            variant="hero"
            size="sm"
            onClick={onConnect}
            disabled={isConnecting}
          >
            Connect
          </Button>
        )}
        {isConnected && onDisconnect && (
          <Button
            variant="hero-outline"
            size="sm"
            onClick={onDisconnect}
            disabled={disconnecting}
          >
            {disconnecting ? "Disconnecting…" : "Disconnect"}
          </Button>
        )}
      </div>
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
    </div>
  );
};

export default Home;
