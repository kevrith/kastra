import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";
import api from "./axios";

/**
 * The response interceptor is what keeps a session alive: on a 401 it silently
 * refreshes the access token and replays the original request once. Getting it
 * wrong either logs everyone out mid-session or loops forever, and neither
 * shows up in a page test — so it is exercised here directly.
 *
 * Requests are driven through a stub adapter so the real interceptors run
 * against a controllable transport.
 */

let adapter;
let originalLocation;

const ok = (config, data = { ok: true }) => Promise.resolve({
  data, status: 200, statusText: "OK", headers: {}, config,
});

const unauthorized = (config) => Promise.reject({
  config, response: { status: 401, data: { detail: "Invalid or expired token" } },
});

const serverError = (config) => Promise.reject({
  config, response: { status: 500, data: { detail: "boom" } },
});

beforeEach(() => {
  adapter = vi.fn(ok);
  api.defaults.adapter = adapter;
  localStorage.clear();

  originalLocation = window.location;
  Object.defineProperty(window, "location", {
    configurable: true, writable: true, value: { href: "/dashboard" },
  });
});

afterEach(() => {
  Object.defineProperty(window, "location", {
    configurable: true, writable: true, value: originalLocation,
  });
  vi.restoreAllMocks();
});

describe("request interceptor", () => {
  it("attaches the stored token as a bearer header", async () => {
    localStorage.setItem("access_token", "tok-123");
    await api.get("/api/clients");
    expect(adapter.mock.calls[0][0].headers.Authorization).toBe("Bearer tok-123");
  });

  it("sends no Authorization header when signed out", async () => {
    await api.get("/api/clients");
    expect(adapter.mock.calls[0][0].headers.Authorization).toBeUndefined();
  });

  it("does not clobber an explicitly supplied header", async () => {
    localStorage.setItem("access_token", "tok-123");
    await api.get("/api/portal/x", { headers: { Authorization: "Bearer portal-token" } });
    expect(adapter.mock.calls[0][0].headers.Authorization).toBe("Bearer portal-token");
  });

  it("sends cookies so the refresh cookie reaches the API", () => {
    expect(api.defaults.withCredentials).toBe(true);
  });
});

describe("401 handling", () => {
  it("refreshes the token and replays the request", async () => {
    localStorage.setItem("access_token", "stale");
    vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "fresh" } });
    adapter.mockImplementationOnce(unauthorized).mockImplementation((c) => ok(c, { data: [] }));

    const res = await api.get("/api/clients");

    expect(axios.post).toHaveBeenCalledOnce();
    expect(localStorage.getItem("access_token")).toBe("fresh");
    expect(adapter).toHaveBeenCalledTimes(2);
    expect(adapter.mock.calls[1][0].headers.Authorization).toBe("Bearer fresh");
    expect(res.data).toEqual({ data: [] });
  });

  it("calls the refresh endpoint with credentials", async () => {
    vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "fresh" } });
    adapter.mockImplementationOnce(unauthorized).mockImplementation(ok);

    await api.get("/api/clients");

    const [url, body, config] = axios.post.mock.calls[0];
    expect(url).toMatch(/\/api\/auth\/refresh$/);
    expect(body).toEqual({});
    expect(config).toEqual({ withCredentials: true });
  });

  it("retries only once, so an expired session cannot loop", async () => {
    vi.spyOn(axios, "post").mockResolvedValue({ data: { access_token: "fresh" } });
    adapter.mockImplementation(unauthorized);

    await expect(api.get("/api/clients")).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(axios.post).toHaveBeenCalledOnce();
    expect(adapter).toHaveBeenCalledTimes(2);
  });

  it("clears the token and redirects to login when refresh fails", async () => {
    localStorage.setItem("access_token", "stale");
    vi.spyOn(axios, "post").mockRejectedValue(new Error("refresh rejected"));
    adapter.mockImplementation(unauthorized);

    await api.get("/api/clients").catch(() => {});

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(window.location.href).toBe("/login");
  });

  it("leaves the session alone on a non-401 error", async () => {
    localStorage.setItem("access_token", "tok-123");
    vi.spyOn(axios, "post");
    adapter.mockImplementation(serverError);

    await expect(api.get("/api/clients")).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(axios.post).not.toHaveBeenCalled();
    expect(localStorage.getItem("access_token")).toBe("tok-123");
    expect(window.location.href).toBe("/dashboard");
  });

  it("passes a successful response straight through", async () => {
    adapter.mockImplementation((c) => ok(c, { data: { id: "c1" } }));
    const res = await api.get("/api/clients/c1");
    expect(res.data).toEqual({ data: { id: "c1" } });
  });
});
