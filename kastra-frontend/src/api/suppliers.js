import api from "./axios";

// Suppliers CRUD
export const getSuppliers = (q) => api.get("/api/suppliers", { params: q ? { q } : {} });
export const createSupplier = (data) => api.post("/api/suppliers", data);
export const updateSupplier = (id, data) => api.put(`/api/suppliers/${id}`, data);
export const deleteSupplier = (id) => api.delete(`/api/suppliers/${id}`);

// Price requests (RFQs)
export const getSupplierRequests = (params) => api.get("/api/suppliers/requests", { params });
export const createSupplierRequest = (data) => api.post("/api/suppliers/requests", data);
export const getSupplierRequest = (id) => api.get(`/api/suppliers/requests/${id}`);
export const updateSupplierRequest = (id, data) => api.put(`/api/suppliers/requests/${id}`, data);
export const closeSupplierRequest = (id) => api.patch(`/api/suppliers/requests/${id}/close`);
export const deleteSupplierRequest = (id) => api.delete(`/api/suppliers/requests/${id}`);

// Invites
export const addInvite = (requestId, supplierId) =>
  api.post(`/api/suppliers/requests/${requestId}/invites`, { supplier_id: supplierId });
export const removeInvite = (requestId, inviteId) =>
  api.delete(`/api/suppliers/requests/${requestId}/invites/${inviteId}`);

// Comparison
export const getComparison = (requestId) =>
  api.get(`/api/suppliers/requests/${requestId}/comparison`);

// Public portal (no auth)
export const getSupplierPortal = (token) => api.get(`/api/supplier-portal/${token}`);
export const submitSupplierPrices = (token, data) => api.post(`/api/supplier-portal/${token}/submit`, data);
