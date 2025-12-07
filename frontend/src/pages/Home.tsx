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
type InboxFilter =
  | "new"
  | "processed"
  | "error"
  | "pending_ai_analysis"
  | "ai_analyzed"
  | "routed"
  | "accepted"
  | "rejected"
  | "needs_review";

type HubSpotStatus = {
  connected: boolean;
  email?: string;
};

type SheetsStatus = {
  status: string;
  spreadsheet_name?: string;
  last_sync_at?: string | null;
};

type SalesforceStatus = {
  connected: boolean;
  email?: string;
  instance_url?: string;
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
  message_id?: string; // Gmail message id (external)
  thread_id?: string | null;
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
  ai_routing_decision?: any;
  ai_confidence?: number | null;
  hubspot_object_type?: string | null;
  salesforce_object_type?: string | null;
  salesforce_contact_id?: string | null;
  synced_to_gsheets?: boolean | null;
  ai_summary?: string | null;
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
    counts: {
      new: 0,
      processed: 0,
      error: 0,
      pending_ai_analysis: 0,
      ai_analyzed: 0,
      routed: 0,
      accepted: 0,
      rejected: 0,
      needs_review: 0,
    },
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
  const [sheetsState, setSheetsState] = useState<ConnectionState>("connecting");
  const [sheetsStatus, setSheetsStatus] = useState<SheetsStatus | null>(null);
  const [sheetsError, setSheetsError] = useState<string | null>(null);
  const [sheetsDisconnecting, setSheetsDisconnecting] = useState(false);
  const [salesforceState, setSalesforceState] =
    useState<ConnectionState>("connecting");
  const [salesforceStatus, setSalesforceStatus] =
    useState<SalesforceStatus | null>(null);
  const [salesforceError, setSalesforceError] = useState<string | null>(null);
  const [salesforceDisconnecting, setSalesforceDisconnecting] = useState(false);

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
  const [noteOverride, setNoteOverride] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [routingSalesforce, setRoutingSalesforce] = useState(false);
  const [sheetsSyncingId, setSheetsSyncingId] = useState<string | null>(null);
  const [sheetsSynced, setSheetsSynced] = useState<Record<string, boolean>>({});
  const [autoSynced, setAutoSynced] = useState(false);

  const bannerParam = searchParams.get("connected");
  const showBanner = bannerParam === "google" || bannerParam === "hubspot" || bannerParam === "salesforce" || bannerParam === "sheets";
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
        counts: {
          new: 0,
          processed: 0,
          error: 0,
          pending_ai_analysis: 0,
          ai_analyzed: 0,
          routed: 0,
          accepted: 0,
          rejected: 0,
          needs_review: 0,
        },
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

  const fetchSheetsStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`/api/google-sheets/status?user_id=${encodeURIComponent(userId)}`, {
        headers: buildHeaders(),
      });
      if (!res.ok) throw new Error(`Status request failed: ${res.status}`);
      const payload = (await res.json()) as SheetsStatus | { status: string };
      setSheetsStatus(payload as SheetsStatus);
      setSheetsState(payload.status && payload.status !== "disconnected" ? "connected" : "disconnected");
      setSheetsError(null);
    } catch (error) {
      console.error(error);
      setSheetsError("Unable to load Google Sheets status.");
      setSheetsState("disconnected");
    }
  }, [buildHeaders, userId]);

  const fetchSalesforceStatus = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await fetch(`/api/salesforce/status?user_id=${encodeURIComponent(userId)}`, {
        headers: buildHeaders(),
      });
      if (!res.ok) throw new Error(`Status request failed: ${res.status}`);
      const payload = (await res.json()) as SalesforceStatus;
      setSalesforceStatus(payload);
      setSalesforceState(payload.connected ? "connected" : "disconnected");
      setSalesforceError(null);
    } catch (error) {
      console.error(error);
      setSalesforceError("Unable to load Salesforce status.");
      setSalesforceState("disconnected");
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
      fetchSheetsStatus();
      fetchSalesforceStatus();
    }
  }, [fetchGmailStatus, fetchHubSpotStatus, fetchSheetsStatus, fetchSalesforceStatus, userId]);

  useEffect(() => {
    setAutoSynced(false);
  }, [userId]);

  useEffect(() => {
    if (
      gmailState === "connected" &&
      (hubspotState === "connected" || salesforceState === "connected") &&
      userId &&
      !autoSynced
    ) {
      setAutoSynced(true);
      triggerSync();
    }
  }, [autoSynced, gmailState, hubspotState, salesforceState, triggerSync, userId]);

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

  // Ensure a message is selected when messages load/change
  useEffect(() => {
    if (!messages.length) {
      setSelectedMessage(null);
      return;
    }
    const stillExists = selectedMessage && messages.find((m) => m.id === selectedMessage.id);
    if (!stillExists) {
      setSelectedMessage(messages[0]);
    }
  }, [messages, selectedMessage, filter]);

  const activeMessage = selectedMessage ?? (messages.length ? messages[0] : null);

  useEffect(() => {
    if (!showInbox || !userId) return;
    // When opening the inbox preview, hide the live feed drawer.
    setShowInsights(false);
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
        setSelectedMessage(payload[0] ?? null);
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

  const analyzeSelected = async () => {
    if (!selectedMessage || !userId) return;
    setAnalyzing(true);
    try {
      const res = await fetch("/api/pipeline/analyze", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          user_id: userId,
          message_id: selectedMessage.message_id || selectedMessage.id,
          note_override: noteOverride || undefined,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Analyze failed");
      }
      const payload = await res.json();
      // optimistic update of selected message and list
      setSelectedMessage((prev) =>
        prev && prev.id === selectedMessage.id
          ? {
            ...prev,
            ai_routing_decision: payload.routing,
            ai_confidence: payload.routing?.confidence ?? prev.ai_confidence,
            ai_summary: payload.ai_summary ?? prev.ai_summary,
            status: "pending_ai_analysis",
          }
          : prev
      );
      setMessages((prev) =>
        prev.map((m) =>
          m.id === selectedMessage.id
            ? {
              ...m,
              ai_routing_decision: payload.routing,
              ai_confidence: payload.routing?.confidence ?? m.ai_confidence,
              ai_summary: payload.ai_summary ?? m.ai_summary,
              status: "pending_ai_analysis",
            }
            : m
        )
      );
      await fetchGmailStatus();
    } catch (error) {
      console.error(error);
      setMessagesError("AI analyze failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  const acceptSelected = async () => {
    if (!selectedMessage || !userId) return;
    setAccepting(true);
    try {
      const res = await fetch("/api/pipeline/accept", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          user_id: userId,
          message_id: selectedMessage.message_id || selectedMessage.id,
          note_override: noteOverride || undefined,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Accept failed");
      }
      const payload = await res.json();
      setSelectedMessage((prev) =>
        prev && prev.id === selectedMessage.id
          ? {
            ...prev,
            ai_routing_decision: payload.routing,
            ai_confidence: payload.routing?.confidence ?? prev.ai_confidence,
            ai_summary: payload.ai_summary ?? prev.ai_summary,
            status: "ai_analyzed",
          }
          : prev
      );
      setMessages((prev) =>
        prev.map((m) =>
          m.id === selectedMessage.id
            ? {
              ...m,
              ai_routing_decision: payload.routing,
              ai_confidence: payload.routing?.confidence ?? m.ai_confidence,
              ai_summary: payload.ai_summary ?? m.ai_summary,
              status: "ai_analyzed",
            }
            : m
        )
      );
      await fetchGmailStatus();
    } catch (error) {
      console.error(error);
      setMessagesError("Accept failed.");
    } finally {
      setAccepting(false);
    }
  };

  const routeToSalesforce = async () => {
    if (!selectedMessage || !userId) return;
    setRoutingSalesforce(true);
    try {
      const res = await fetch("/api/salesforce/route-email", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          user_id: userId,
          message_id: selectedMessage.message_id || selectedMessage.id,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Salesforce route failed");
      }
      const payload = await res.json();
      setSelectedMessage((prev) =>
        prev && prev.id === selectedMessage.id
          ? {
            ...prev,
            salesforce_object_type: "contacts",
            salesforce_contact_id: payload.contact_id || prev.salesforce_contact_id,
            crm_record_url: payload.crm_record_url || prev.crm_record_url,
            status: "routed",
          }
          : prev
      );
      setMessages((prev) =>
        prev.map((m) =>
          m.id === selectedMessage.id
            ? {
              ...m,
              salesforce_object_type: "contacts",
              salesforce_contact_id: payload.contact_id || m.salesforce_contact_id,
              crm_record_url: payload.crm_record_url || m.crm_record_url,
              status: "routed",
            }
            : m
        )
      );
    } catch (error) {
      console.error(error);
      setMessagesError("Salesforce route failed.");
    } finally {
      setRoutingSalesforce(false);
    }
  };

  const sendToSheets = async () => {
    if (!selectedMessage || !userId) return;
    const targetId = selectedMessage.id;
    setSheetsSyncingId(targetId);
    try {
      const res = await fetch("/api/google-sheets/sync-email", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          user_id: userId,
          email_id: targetId,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Sheets sync failed");
      }
      const payload = await res.json();
      setSheetsSynced((prev) => ({ ...prev, [targetId]: true }));
      setSelectedMessage((prev) =>
        prev && prev.id === targetId
          ? {
            ...prev,
            synced_to_gsheets: true,
            crm_record_url: prev.crm_record_url,
          }
          : prev
      );
      setMessages((prev) =>
        prev.map((m) =>
          m.id === targetId
            ? { ...m, synced_to_gsheets: true }
            : m
        )
      );
      if (payload?.spreadsheet_url) {
        setSyncMessage(`Synced to Sheets row ${payload.row_number || ""}`);
      }
    } catch (error) {
      console.error(error);
      setMessagesError("Google Sheets sync failed.");
    } finally {
      setSheetsSyncingId(null);
    }
  };

  const rejectSelected = async () => {
    if (!selectedMessage || !userId) return;
    setAnalyzing(true);
    try {
      const res = await fetch("/api/pipeline/reject", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ user_id: userId, message_id: selectedMessage.message_id || selectedMessage.id }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Reject failed");
      }
      await fetchGmailStatus();
      const params = new URLSearchParams({
        user_id: userId,
        status: filter,
        limit: "50",
      });
      if (debouncedSearch) params.set("query", debouncedSearch);
      const refreshed = await fetch(`/api/inbox/messages?${params.toString()}`, { headers: buildHeaders() }).then((r) => r.json());
      setMessages(refreshed.messages);
      const updated = refreshed.messages.find((m: InboxMessage) => m.id === selectedMessage.id);
      setSelectedMessage(updated || null);
    } catch (error) {
      console.error(error);
      setMessagesError("Reject failed.");
    } finally {
      setAnalyzing(false);
    }
  };

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
    gmailState === "connected" &&
    (hubspotState === "connected" || salesforceState === "connected" || sheetsState === "connected");

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

  const handleConnectSheets = async () => {
    if (!userId) return;
    setSheetsState("connecting");
    try {
      const res = await fetch(`/api/google-sheets/auth?user_id=${encodeURIComponent(userId)}`, {
        headers: buildHeaders(),
      });
      if (!res.ok) throw new Error("Sheets auth init failed");
      const payload = await res.json();
      if (payload?.auth_url) {
        window.location.href = payload.auth_url;
      } else {
        throw new Error("Missing auth_url");
      }
    } catch (error) {
      console.error(error);
      setSheetsError("Unable to start Google Sheets connect.");
      setSheetsState("disconnected");
    }
  };

  const handleDisconnectSheets = async () => {
    if (!userId) return;
    setSheetsDisconnecting(true);
    try {
      const res = await fetch(`/api/google-sheets/disconnect?user_id=${encodeURIComponent(userId)}`, {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
      });
      if (!res.ok) throw new Error("Disconnect failed");
      await fetchSheetsStatus();
      setSheetsState("disconnected");
    } catch (error) {
      console.error(error);
    } finally {
      setSheetsDisconnecting(false);
    }
  };

  const handleConnectSalesforce = () => {
    if (!userId) return;
    setSalesforceState("connecting");
    window.location.href = `/api/salesforce/connect?user_id=${encodeURIComponent(
      userId
    )}`;
  };

  const handleDisconnectSalesforce = async () => {
    if (!userId) return;
    setSalesforceDisconnecting(true);
    try {
      const res = await fetch("/api/salesforce/disconnect", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ user_id: userId }),
      });
      if (!res.ok) throw new Error("Disconnect failed");
      await fetchSalesforceStatus();
      setSalesforceState("disconnected");
    } catch (error) {
      console.error(error);
    } finally {
      setSalesforceDisconnecting(false);
    }
  };

  const handleDisconnectHubSpotButton = async () => {
    if (!userId) return;
    try {
      const res = await fetch("/api/hubspot/disconnect", {
        method: "POST",
        headers: buildHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ user_id: userId }),
      });
      if (res.ok) {
        setHubspotStatus(null);
        setHubspotState("disconnected");
        console.log("HubSpot disconnected");
        navigate("/");
      }
    } catch (error) {
      console.error(error);
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
        }).catch(() => { });
        await fetch("/api/hubspot/disconnect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        }).catch(() => { });
        await fetch("/api/google-sheets/disconnect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        }).catch(() => { });
        await fetch("/api/salesforce/disconnect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: uid }),
        }).catch(() => { });
      }
    } finally {
      await signOut();
      // Reset local UI state
      setGmailState("disconnected");
      setHubspotState("disconnected");
      setSheetsState("disconnected");
      setSalesforceState("disconnected");
      setGmailStatus({
        connected: false,
        counts: {
          new: 0,
          processed: 0,
          error: 0,
          pending_ai_analysis: 0,
          ai_analyzed: 0,
          routed: 0,
          accepted: 0,
          rejected: 0,
          needs_review: 0,
        },
        baseline_ready: false,
      });
      setHubspotStatus(null);
      setSheetsStatus(null);
      setSalesforceStatus(null);
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
  const sheetsCardStatus = sheetsStatus ?? {
    status: "disconnected",
    spreadsheet_name: "",
  };
  const salesforceCardStatus = salesforceStatus ?? {
    connected: false,
    instance_url: "",
  };

  return (
    <div className="min-h-screen bg-background px-6 py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">
            Hi {greeting}
          </h1>
          <p className="text-muted-foreground">
            Let&apos;s secure your automations in two quick steps.
          </p>
        </div>

        {showBanner && (
          <div className="flex items-center gap-2 rounded-xl border border-success/30 bg-success/10 px-4 py-3 text-sm font-medium text-success">
            <CheckCircle2 className="h-4 w-4" />
            Connected successfully!
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
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
          <ConnectionCard
            title="Connect Google Sheets"
            description={
              sheetsCardStatus.status !== "disconnected"
                ? sheetsCardStatus.spreadsheet_name
                  ? `Using ${sheetsCardStatus.spreadsheet_name}`
                  : "Connected. Select a spreadsheet."
                : "Authorize Google Sheets to sync records."
            }
            state={sheetsState}
            onConnect={handleConnectSheets}
            detail={
              sheetsCardStatus.status !== "disconnected"
                ? sheetsCardStatus.last_sync_at
                  ? `Last sync ${formatRelativeTime(sheetsCardStatus.last_sync_at)}`
                  : "Ready"
                : undefined
            }
            error={sheetsError || undefined}
            onDisconnect={sheetsState === "connected" ? handleDisconnectSheets : undefined}
            disconnecting={sheetsDisconnecting}
          />
          <ConnectionCard
            title="Connect Salesforce"
            description={
              salesforceCardStatus.connected
                ? `Instance ${salesforceCardStatus.instance_url || ""}`
                : "Authorize Salesforce to route AI-enriched records."
            }
            state={salesforceState}
            onConnect={handleConnectSalesforce}
            detail={salesforceCardStatus.connected ? "Ready" : undefined}
            error={salesforceError || undefined}
            onDisconnect={
              salesforceCardStatus.connected ? handleDisconnectSalesforce : undefined
            }
            disconnecting={salesforceDisconnecting}
          />
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-dashed border-border bg-muted/20 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-base font-semibold text-foreground">
              All set? Jump into your live inbox.
            </p>
            <p className="text-sm text-muted-foreground">
              We&apos;ll keep polling Gmail once both integrations are active.
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
                  Syncing...
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
                  {(summary?.counts.processed ?? 0).toLocaleString()} processed &middot;{" "}
                  {(summary?.counts.error ?? 0).toLocaleString()} with errors
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
        <div className="fixed inset-0 z-40 bg-background">
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
                  Filter, search, and open any record in Gmail or your CRM.
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
                {(
                  [
                    "new",
                    "pending_ai_analysis",
                    "ai_analyzed",
                    "needs_review",
                    "routed",
                    "accepted",
                    "rejected",
                  ] as InboxFilter[]
                ).map((item) => (
                  <Button
                    key={item}
                    variant={filter === item ? "hero" : "outline"}
                    size="sm"
                    onClick={() => setFilter(item)}
                  >
                    {item.replace(/_/g, " ")}
                  </Button>
                ))}
              </div>
              <div className="flex w-full gap-2 lg:max-w-xs">
                <Input
                  placeholder="Search subject, sender, or content..."
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                />
              </div>
            </div>

            <div className="mt-6 grid flex-1 gap-4 overflow-hidden" style={{ gridTemplateColumns: '1.2fr 0.8fr' }}>
              <div className="flex min-h-0 flex-col rounded-2xl border border-border bg-card/60" style={{ minWidth: 0 }}>
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
                          activeMessage?.id === message.id &&
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

              <div className="flex min-h-0 flex-col rounded-2xl border border-border bg-card/60 p-4" style={{ minWidth: 0 }}>
                {activeMessage ? (
                  <>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="uppercase">
                          {activeMessage.status}
                        </Badge>
                        {sheetsState === "connected" && (
                          <Badge
                            variant={
                              activeMessage.synced_to_gsheets ||
                                sheetsSynced[activeMessage.id]
                                ? "secondary"
                                : "outline"
                            }
                            className="uppercase"
                          >
                            {activeMessage.synced_to_gsheets ||
                              sheetsSynced[activeMessage.id]
                              ? "Sheets synced"
                              : "Sheets ready"}
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        Updated{" "}
                        {formatRelativeTime(
                          activeMessage.updated_at ||
                          activeMessage.created_at
                        )}
                      </span>
                    </div>
                    <div className="mt-4 space-y-1">
                      <p className="text-lg font-semibold text-foreground">
                        {activeMessage.subject}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {activeMessage.sender || "Unknown sender"}
                      </p>
                    </div>
                    <div className="mt-4 flex-1 overflow-y-auto rounded-lg bg-background/60 p-4">
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs font-semibold uppercase text-muted-foreground">
                            Email preview
                          </p>
                          <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
                            {activeMessage.preview ||
                              activeMessage.snippet ||
                              "No preview available yet."}
                          </p>
                        </div>
                        {activeMessage.ai_summary && (
                          <div className="rounded-lg border border-border bg-background/70 p-3">
                            <p className="text-xs font-semibold uppercase text-muted-foreground">
                              AI summary
                            </p>
                            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                              {activeMessage.ai_summary}
                            </p>
                          </div>
                        )}
                      </div>
                      {activeMessage.error && (
                        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                          {activeMessage.error}
                        </p>
                      )}
                      {(filter === "pending_ai_analysis" || filter === "ai_analyzed") && (
                        <div className="mt-4 rounded-lg border border-border bg-card/70 p-3 space-y-2">
                          <p className="text-xs font-semibold uppercase text-muted-foreground">
                            AI Analysis
                          </p>
                          {activeMessage.ai_routing_decision ? (
                            <>
                              <p className="text-sm text-foreground">
                                Object:{" "}
                                <strong>
                                  {activeMessage.hubspot_object_type ||
                                    activeMessage.ai_routing_decision
                                      ?.primary_object ||
                                    "N/A"}
                                </strong>
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Confidence:{" "}
                                {Math.round((activeMessage.ai_confidence || 0) * 100)}
                                %
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Intent:{" "}
                                {activeMessage.ai_routing_decision.intent ||
                                  "N/A"}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Reasoning:{" "}
                                {activeMessage.ai_routing_decision.reasoning ||
                                  "N/A"}
                              </p>
                              {(activeMessage.salesforce_object_type ||
                                activeMessage.hubspot_object_type) && (
                                  <p className="text-sm text-muted-foreground">
                                    CRM targets:{" "}
                                    {[
                                      activeMessage.hubspot_object_type
                                        ? `HubSpot (${activeMessage.hubspot_object_type})`
                                        : null,
                                      activeMessage.salesforce_object_type
                                        ? `Salesforce (${activeMessage.salesforce_object_type})`
                                        : null,
                                    ]
                                      .filter(Boolean)
                                      .join(" • ")}
                                  </p>
                                )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              Not analyzed yet. Run AI to classify and summarize.
                            </p>
                          )}
                          <label className="text-xs text-muted-foreground">
                            Note (editable before accepting)
                          </label>
                          <textarea
                            className="w-full rounded-md border border-border bg-background p-2 text-sm text-foreground"
                            rows={4}
                            value={noteOverride}
                            onChange={(e) => setNoteOverride(e.target.value)}
                            placeholder="Edit the note text before sending to CRM..."
                          />
                          <div className="flex flex-wrap gap-2">
                            <Button
                              variant="hero-outline"
                              size="sm"
                              disabled={analyzing || accepting}
                              onClick={() => analyzeSelected()}
                            >
                              {analyzing ? (
                                <>
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                  Analyzing...
                                </>
                              ) : (
                                "Analyze with AI"
                              )}
                            </Button>
                            <Button
                              variant="hero"
                              size="sm"
                              disabled={accepting || analyzing}
                              onClick={() => acceptSelected()}
                            >
                              {accepting ? (
                                <>
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                  Sending...
                                </>
                              ) : (
                                "Accept & send to HubSpot"
                              )}
                            </Button>
                            <Button
                              variant="hero-outline"
                              size="sm"
                              disabled={routingSalesforce || analyzing || salesforceState !== "connected"}
                              onClick={() => routeToSalesforce()}
                            >
                              {routingSalesforce ? (
                                <>
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                  Routing...
                                </>
                              ) : (
                                "Send to Salesforce"
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={
                                analyzing ||
                                sheetsState !== "connected" ||
                                sheetsSyncingId === selectedMessage.id
                              }
                              onClick={() => sendToSheets()}
                            >
                              {sheetsSyncingId === selectedMessage.id ? (
                                <>
                                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                  Sending to Sheets...
                                </>
                              ) : (
                                "Send to Sheets"
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={analyzing}
                              onClick={rejectSelected}
                            >
                              Reject
                            </Button>
                          </div>
                        </div>
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
                  <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-border bg-card/60 p-6 text-center text-muted-foreground">
                    <Mail className="mb-4 h-8 w-8 text-muted-foreground" />
                    <p className="text-sm font-medium text-foreground">Select a message to view the enriched preview.</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      AI Analysis, HubSpot/Salesforce/Sheets actions will appear here once an email is selected.
                    </p>
                    <div className="mt-4 w-full max-w-xs space-y-2 text-left">
                      <div className="rounded-lg border border-border bg-background/80 p-3">
                        <p className="text-xs font-semibold uppercase text-muted-foreground">AI Analysis</p>
                        <p className="mt-1 text-xs text-muted-foreground">Run AI to classify, summarize, then route.</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Button variant="hero-outline" size="sm" disabled>
                            Analyze with AI
                          </Button>
                          <Button variant="hero" size="sm" disabled>
                            Accept &amp; send to HubSpot
                          </Button>
                          <Button variant="hero-outline" size="sm" disabled>
                            Send to Salesforce
                          </Button>
                          <Button variant="outline" size="sm" disabled>
                            Send to Sheets
                          </Button>
                          <Button variant="outline" size="sm" disabled>
                            Reject
                          </Button>
                        </div>
                      </div>
                    </div>
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
            className="mb-3 shadow-xl"
            onClick={handleDisconnectHubSpotButton}
          >
            Disconnect HubSpot
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
