import api from "./axios";

export const getMyPlan = () => api.get("/api/subscriptions/me");
export const listPlans = () => api.get("/api/subscriptions/plans");
export const upgradePlan = (plan) => api.post("/api/subscriptions/upgrade", { plan });

// Super admin
export const superadminLogin = (username, password) =>
  api.post("/api/superadmin/login", { username, password });

export const superadminStats = (token) =>
  api.get("/api/superadmin/stats", { headers: { Authorization: `Bearer ${token}` } });

export const superadminOrgs = (token, params = {}) =>
  api.get("/api/superadmin/organizations", { headers: { Authorization: `Bearer ${token}` }, params });

export const superadminOrgDetail = (token, orgId) =>
  api.get(`/api/superadmin/organizations/${orgId}`, { headers: { Authorization: `Bearer ${token}` } });

export const superadminChangePlan = (token, orgId, plan, plan_status = "active") =>
  api.patch(`/api/superadmin/organizations/${orgId}/plan`, { plan, plan_status }, { headers: { Authorization: `Bearer ${token}` } });

export const superadminSuspendOrg = (token, orgId) =>
  api.delete(`/api/superadmin/organizations/${orgId}/suspend`, { headers: { Authorization: `Bearer ${token}` } });
