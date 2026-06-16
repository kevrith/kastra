import api from "./axios";

// Purchase orders
export const getPurchaseOrders = (params) => api.get("/api/purchase-orders", { params });
export const getPurchaseOrder = (id) => api.get(`/api/purchase-orders/${id}`);
export const createPurchaseOrder = (data) => api.post("/api/purchase-orders", data);
export const createPOFromQuote = (requestId, inviteId) =>
  api.post(`/api/purchase-orders/from-request/${requestId}`, { invite_id: inviteId });
export const updatePurchaseOrder = (id, data) => api.put(`/api/purchase-orders/${id}`, data);
export const deletePurchaseOrder = (id) => api.delete(`/api/purchase-orders/${id}`);

// Workflow
export const sendPurchaseOrder = (id) => api.post(`/api/purchase-orders/${id}/send`);
export const acceptPurchaseOrder = (id) => api.post(`/api/purchase-orders/${id}/accept`);
export const rejectPurchaseOrder = (id, reason) => api.post(`/api/purchase-orders/${id}/reject`, { reason });
export const cancelPurchaseOrder = (id) => api.post(`/api/purchase-orders/${id}/cancel`);
export const addPONote = (id, body) => api.post(`/api/purchase-orders/${id}/notes`, { body });
export const receiveGoods = (id, data) => api.post(`/api/purchase-orders/${id}/receipts`, data);

// Public supplier order portal (no auth)
export const getSupplierOrder = (token) => api.get(`/api/supplier-portal/order/${token}`);
export const respondSupplierOrder = (token, data) =>
  api.post(`/api/supplier-portal/order/${token}/respond`, data);
