import api from "./axios";

export const getMyPlan = () => api.get("/api/subscriptions/me");
export const listPlans = () => api.get("/api/subscriptions/plans");
export const upgradePlan = (plan) => api.post("/api/subscriptions/upgrade", { plan });

// ── Super admin helpers ───────────────────────────────────────────────────────
const saHeaders = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

export const superadminLogin = (username, password) =>
  api.post("/api/superadmin/login", { username, password });

export const superadminStats = (token) =>
  api.get("/api/superadmin/stats", saHeaders(token));

export const superadminRevenue = (token) =>
  api.get("/api/superadmin/revenue", saHeaders(token));

export const superadminPayments = (token, params = {}) =>
  api.get("/api/superadmin/payments", { ...saHeaders(token), params });

export const superadminTrials = (token) =>
  api.get("/api/superadmin/trials", saHeaders(token));

export const superadminAuditLog = (token, params = {}) =>
  api.get("/api/superadmin/audit-log", { ...saHeaders(token), params });

export const superadminOrgs = (token, params = {}) =>
  api.get("/api/superadmin/organizations", { ...saHeaders(token), params });

export const superadminOrgDetail = (token, orgId) =>
  api.get(`/api/superadmin/organizations/${orgId}`, saHeaders(token));

export const superadminChangePlan = (token, orgId, plan, plan_status = "active") =>
  api.patch(`/api/superadmin/organizations/${orgId}/plan`, { plan, plan_status }, saHeaders(token));

export const superadminSuspendOrg = (token, orgId) =>
  api.delete(`/api/superadmin/organizations/${orgId}/suspend`, saHeaders(token));

export const superadminUnsuspendOrg = (token, orgId) =>
  api.post(`/api/superadmin/organizations/${orgId}/unsuspend`, {}, saHeaders(token));

export const superadminExtendTrial = (token, orgId, days) =>
  api.post(`/api/superadmin/organizations/${orgId}/extend-trial`, { days }, saHeaders(token));

export const superadminRecordPayment = (token, orgId, payload) =>
  api.post(`/api/superadmin/organizations/${orgId}/record-payment`, payload, saHeaders(token));
