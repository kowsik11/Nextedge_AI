type CmsTestResponse = {
  status: string;
  payload: Record<string, unknown>;
  hubspot_response: Record<string, unknown>;
};

export async function triggerCmsBlogPostTest(userId: string, options?: { signal?: AbortSignal }) {
  const response = await fetch("/api/hubspot/cms/test-blog-post", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
    signal: options?.signal,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Unable to trigger CMS blog post test.");
  }

  return (await response.json()) as CmsTestResponse;
}
