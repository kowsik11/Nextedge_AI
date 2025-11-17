export async function fetchHubSpotBlogs(userId: string, accessToken?: string, options?: { signal?: AbortSignal }) {
  const response = await fetch("/api/hubspot/blogs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({ user_id: userId }),
    signal: options?.signal,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Unable to fetch HubSpot blogs.");
  }

  return response.json() as Promise<{
    total?: number;
    results?: Array<{ id: string; name?: string; slug?: string }>;
  }>;
}
