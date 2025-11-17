type BlogAuthor = {
  id: number | string;
  name?: string;
  email?: string;
  display_name?: string;
  bio?: string;
};

export type BlogAuthorsResponse = {
  total?: number;
  results?: BlogAuthor[];
} & Record<string, unknown>;

export async function fetchHubSpotBlogAuthors(userId: string, accessToken?: string, options?: { signal?: AbortSignal }) {
  const response = await fetch("/api/hubspot/blog-authors", {
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
    throw new Error(detail || "Unable to fetch HubSpot blog authors.");
  }

  return (await response.json()) as BlogAuthorsResponse;
}
