import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8080";
const portalApi = axios.create({ baseURL });

export const getClientPortal = (token, sessionToken) =>
  portalApi.get(`/api/portal/c/${token}`, sessionToken ? { headers: { Authorization: `Bearer ${sessionToken}` } } : undefined);

export const verifyPortalPin = (token, pin) =>
  portalApi.post(`/api/portal/c/${token}/verify`, { pin });

export const getPublicQuotation = (id) => portalApi.get(`/api/portal/q/${id}`);
export const respondToQuotation = (id, action, decline_reason = "") =>
  portalApi.post(`/api/portal/q/${id}/respond`, { action, decline_reason: decline_reason || null });

export const initializePaystack = (invoice_id, email, amount = null) =>
  portalApi.post("/api/paystack/initialize", { invoice_id, email, ...(amount ? { amount } : {}) });

export const verifyPaystackPayment = (reference) =>
  portalApi.get(`/api/paystack/verify/${reference}`);
