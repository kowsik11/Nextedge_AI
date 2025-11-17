export async function startHubSpotOAuth(): Promise<void> {
  window.location.href = "/api/oauth/hubspot/start";
}

export async function contactSync(email: string, accessToken?: string) {
  const res = await fetch("/api/hubspot/contact-sync", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    throw new Error((await res.text()) || "Unable to sync contact");
  }
  return res.json();
}
