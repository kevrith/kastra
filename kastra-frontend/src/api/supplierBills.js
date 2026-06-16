import api from "./axios";

export const getSupplierBills = (params) => api.get("/api/supplier-bills", { params });
export const getSupplierBill = (id) => api.get(`/api/supplier-bills/${id}`);
export const getPayablesSummary = () => api.get("/api/supplier-bills/summary");
export const createBillFromPO = (poId, data) => api.post(`/api/supplier-bills/from-po/${poId}`, data);
export const recordBillPayment = (id, data) => api.post(`/api/supplier-bills/${id}/payments`, data);
