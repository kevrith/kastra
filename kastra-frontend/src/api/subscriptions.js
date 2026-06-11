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

export const superadminGrantComplimentary = (token, orgId, payload) =>
  api.post(`/api/superadmin/organizations/${orgId}/grant-complimentary`, payload, saHeaders(token));

export const superadminRevokeComplimentary = (token, orgId) =>
  api.post(`/api/superadmin/organizations/${orgId}/revoke-complimentary`, {}, saHeaders(token));

export const superadminResetUserPassword = (token, userId) =>
  api.post(`/api/superadmin/users/${userId}/reset-password`, {}, saHeaders(token));

export const superadminDeactivateUser = (token, userId) =>
  api.post(`/api/superadmin/users/${userId}/deactivate`, {}, saHeaders(token));

export const superadminReactivateUser = (token, userId) =>
  api.post(`/api/superadmin/users/${userId}/reactivate`, {}, saHeaders(token));

export const superadminChangeUserRole = (token, userId, role) =>
  api.patch(`/api/superadmin/users/${userId}/role`, { role }, saHeaders(token));

export const superadminInvoices = (token, params = {}) =>
  api.get("/api/superadmin/invoices", { ...saHeaders(token), params });

export const superadminQuotations = (token, params = {}) =>
  api.get("/api/superadmin/quotations", { ...saHeaders(token), params });

export const superadminSuppliers = (token, params = {}) =>
  api.get("/api/superadmin/suppliers", { ...saHeaders(token), params });

export const superadminSupplierRequests = (token, params = {}) =>
  api.get("/api/superadmin/supplier-requests", { ...saHeaders(token), params });

// Document access
export const superadminInvoiceDetail = (token, invoiceId) =>
  api.get(`/api/superadmin/invoices/${invoiceId}/detail`, saHeaders(token));

const _baseUrl = () => import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const superadminInvoicePdfBlob = async (token, invoiceId) => {
  const res = await fetch(`${_baseUrl()}/api/superadmin/invoices/${invoiceId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("PDF failed");
  return res.blob();
};
export const superadminQuotationPdfBlob = async (token, quotationId) => {
  const res = await fetch(`${_baseUrl()}/api/superadmin/quotations/${quotationId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("PDF failed");
  return res.blob();
};
export const superadminSupplierRequestDetail = (token, requestId) =>
  api.get(`/api/superadmin/supplier-requests/${requestId}/detail`, saHeaders(token));

// Testimonials CRUD
export const superadminGetTestimonials = (token, status = null) =>
  api.get("/api/superadmin/testimonials", { ...saHeaders(token), params: status ? { status } : {} });

export const superadminCreateTestimonial = (token, payload) =>
  api.post("/api/superadmin/testimonials", payload, saHeaders(token));

export const superadminUpdateTestimonial = (token, id, payload) =>
  api.put(`/api/superadmin/testimonials/${id}`, payload, saHeaders(token));

export const superadminDeleteTestimonial = (token, id) =>
  api.delete(`/api/superadmin/testimonials/${id}`, saHeaders(token));

export const superadminRequestTestimonial = (token, payload) =>
  api.post("/api/superadmin/testimonials/request", payload, saHeaders(token));

export const superadminResendTestimonial = (token, id) =>
  api.post(`/api/superadmin/testimonials/${id}/resend`, {}, saHeaders(token));

export const superadminApproveTestimonial = (token, id) =>
  api.post(`/api/superadmin/testimonials/${id}/approve`, {}, saHeaders(token));

export const superadminRejectTestimonial = (token, id, reason = "") =>
  api.post(`/api/superadmin/testimonials/${id}/reject`, { reason }, saHeaders(token));

export const superadminListAffiliates = (token) =>
  api.get("/api/superadmin/affiliates", saHeaders(token));

export const superadminGetAffiliate = (token, id) =>
  api.get(`/api/superadmin/affiliates/${id}`, saHeaders(token));

export const superadminUpdateAffiliateStatus = (token, id, status) =>
  api.patch(`/api/superadmin/affiliates/${id}/status`, { status }, saHeaders(token));
