const ALLOWED_EMAILS = [
  "kowsikperumalla@gmail.com",
  "kowsikperumalla123@gmail.com",
  "domakondasaisharan@gmail.com",
  "abhinavstavarub7@gmail.com",
] as const;

const NORMALIZED = new Set(ALLOWED_EMAILS.map((email) => email.trim().toLowerCase()));
export const ACCESS_DENIED_MESSAGE = "Access denied — not an approved tester.";

/**
 * Returns true if the email is whitelisted.
 */
export function isAllowedEmail(email: string): boolean {
  return NORMALIZED.has(email.trim().toLowerCase());
}

/**
 * Throws with a normalized error message when the email is not allowed.
 * Use this in front of auth flows to block unsupported accounts early.
 */
export function verifyAllowedEmail(email: string): void {
  if (!isAllowedEmail(email)) {
    const error = new Error(ACCESS_DENIED_MESSAGE);
    error.name = "AccessDeniedError";
    throw error;
  }
}
