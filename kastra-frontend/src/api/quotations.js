import api from "./axios";

export const getQuotations = (params) => api.get("/api/quotations", { params });
export const getQuotation = (id) => api.get(`/api/quotations/${id}`);
export const createQuotation = (data) => api.post("/api/quotations", data);
export const updateQuotation = (id, data) => api.put(`/api/quotations/${id}`, data);
export const updateQuotationStatus = (id, status) =>
  api.patch(`/api/quotations/${id}/status`, { status });
export const convertToInvoice = (id) =>
  api.post(`/api/quotations/${id}/convert`);
export const deleteQuotation = (id) => api.delete(`/api/quotations/${id}`);
export const emailQuotation = (id) => api.post(`/api/quotations/${id}/email`);
