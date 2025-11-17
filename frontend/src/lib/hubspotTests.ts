export type HubSpotTestEntry = {
  key: string;
  method: string;
  path: string;
  section: string;
  title: string;
};

export async function fetchHubSpotTestCatalog(accessToken?: string) {
  const response = await fetch("/api/hubspot/tests/catalog", {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Unable to load HubSpot tests catalog.");
  }
  const payload = (await response.json()) as { results: HubSpotTestEntry[] };
  return payload.results;
}

type RunOptions = {
  userId: string;
  key: string;
  accessToken?: string;
};

export async function runHubSpotTest({ userId, key, accessToken }: RunOptions) {
  const response = await fetch("/api/hubspot/tests/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({
      user_id: userId,
      key,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Unable to run HubSpot test.");
  }
  return response.json() as Promise<{ result: unknown; test: HubSpotTestEntry }>;
}
