/**
 * Returns the publicly accessible base URL for shared links (payment links,
 * portal links, WhatsApp messages).
 *
 * In development this falls back to window.location.origin (localhost) which
 * only works on the same machine.  Set VITE_PUBLIC_URL in your .env to your
 * real domain so that links sent to clients actually work:
 *
 *   VITE_PUBLIC_URL=https://app.kastra.co.ke
 */
export function publicOrigin() {
  return (import.meta.env.VITE_PUBLIC_URL || window.location.origin).replace(/\/$/, "");
}
