import api from "./axios";

export const getInvoicePayments = (invoiceId) => api.get(`/api/invoices/${invoiceId}/payments`);
export const recordPayment = (invoiceId, data) => api.post(`/api/invoices/${invoiceId}/payments`, data);
export const deletePayment = (invoiceId, paymentId) => api.delete(`/api/invoices/${invoiceId}/payments/${paymentId}`);
