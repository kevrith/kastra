import { afterEach, describe, expect, it, vi } from "vitest";
import { publicOrigin } from "./publicUrl";

/**
 * publicOrigin() decides the base URL used in links we hand to clients —
 * payment links, portal links, WhatsApp messages. A trailing slash or a
 * localhost fallback leaking into production produces links that 404 for the
 * recipient, so both branches are worth pinning.
 */

function withWindowOrigin(origin) {
  vi.stubGlobal("window", { location: { origin } });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("publicOrigin", () => {
  it("prefers VITE_PUBLIC_URL over the browser origin", () => {
    vi.stubEnv("VITE_PUBLIC_URL", "https://app.kastra.co.ke");
    withWindowOrigin("http://localhost:5200");
    expect(publicOrigin()).toBe("https://app.kastra.co.ke");
  });

  it("strips a trailing slash so paths don't double up", () => {
    vi.stubEnv("VITE_PUBLIC_URL", "https://app.kastra.co.ke/");
    withWindowOrigin("http://localhost:5200");
    expect(publicOrigin()).toBe("https://app.kastra.co.ke");
    expect(`${publicOrigin()}/pay/INV-1`).toBe("https://app.kastra.co.ke/pay/INV-1");
  });

  it("falls back to the browser origin when the env var is unset", () => {
    vi.stubEnv("VITE_PUBLIC_URL", "");
    withWindowOrigin("http://localhost:5200");
    expect(publicOrigin()).toBe("http://localhost:5200");
  });

  it("strips a trailing slash from the browser origin too", () => {
    vi.stubEnv("VITE_PUBLIC_URL", "");
    withWindowOrigin("https://kastra-ten.vercel.app/");
    expect(publicOrigin()).toBe("https://kastra-ten.vercel.app");
  });
});
