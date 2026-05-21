import api from "./axios";

export const getInvoices = (params) => api.get("/api/invoices", { params });
export const getInvoice = (id) => api.get(`/api/invoices/${id}`);
export const markPaid = (id, data) => api.patch(`/api/invoices/${id}/mark-paid`, data);
export const mpesaPay = (id, phone_number) =>
  api.post(`/api/invoices/${id}/mpesa-pay`, { phone_number });
export const sendReminder = (id) => api.post(`/api/invoices/${id}/remind`);
export const submitEtims = (id) => api.post(`/api/invoices/${id}/etims-submit`, {});
export const testEtimsConnection = () => api.post("/api/organization/etims-test");
export const sendInvoiceEmail = (id) => api.post(`/api/invoices/${id}/email`);
