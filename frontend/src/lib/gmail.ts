export async function startGmailOAuth(): Promise<void> {
  window.location.href = "/api/oauth/gmail/start";
}

export async function pollGmail(accessToken?: string) {
  const res = await fetch("/api/gmail/poll", {
    method: "POST",
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });
  if (!res.ok) {
    throw new Error((await res.text()) || "Unable to poll Gmail");
  }
  return res.json();
}

export type MessageRecord = {
  id: string;
  user_id: string;
  message_id: string;
  thread_id: string | null;
  subject: string | null;
  sender: string | null;
  snippet: string | null;
  preview: string | null;
  status: string;
  has_attachments: boolean;
  has_images: boolean;
  has_links: boolean;
  gmail_url: string | null;
  crm_record_url: string | null;
  error: string | null;
  received_at: string | null;
};

export async function listMessages(options?: { status?: string; limit?: number; accessToken?: string }) {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.limit) params.set("limit", String(options.limit));
  const res = await fetch(`/api/messages/list?${params.toString()}`, {
    headers: {
      ...(options?.accessToken ? { Authorization: `Bearer ${options.accessToken}` } : {}),
    },
  });
  if (!res.ok) {
    throw new Error((await res.text()) || "Unable to load messages");
  }
  const data = await res.json();
  return (data.messages || []) as MessageRecord[];
}
