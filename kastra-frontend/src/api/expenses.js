import api from "./axios";

export const getExpenses = (params) => api.get("/api/expenses", { params });
export const createExpense = (data) => api.post("/api/expenses", data);
export const updateExpense = (id, data) => api.put(`/api/expenses/${id}`, data);
export const deleteExpense = (id) => api.delete(`/api/expenses/${id}`);
export const getMonthlyExpenseSummary = () => api.get("/api/expenses/summary/monthly");

// Invoice-scoped job expenses
export const getInvoiceExpenses = (invoiceId) => api.get(`/api/invoices/${invoiceId}/expenses`);
export const createInvoiceExpense = (invoiceId, data) => api.post(`/api/invoices/${invoiceId}/expenses`, data);
export const updateInvoiceExpense = (invoiceId, expenseId, data) => api.put(`/api/invoices/${invoiceId}/expenses/${expenseId}`, data);
export const deleteInvoiceExpense = (invoiceId, expenseId) => api.delete(`/api/invoices/${invoiceId}/expenses/${expenseId}`);
