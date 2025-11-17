export type Provider = "hubspot" | "gmail";

export type TokenInfo = {
  access_token: string;
  refresh_token?: string | null;
  expires_at?: string | null;
  scope?: string[] | null;
  email?: string | null;
  external_user_id?: string | null;
};

export async function disconnect(provider: Provider, accessToken?: string): Promise<void> {
  const res = await fetch(`/api/oauth/disconnect/${provider}`, {
    method: "POST",
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });
  if (!res.ok) {
    throw new Error((await res.text()) || "Failed to disconnect provider");
  }
}
