import api from "./axios";

export const getPayrollRuns = () => api.get("/api/payroll/runs");
export const getPayrollRun = (id) => api.get(`/api/payroll/runs/${id}`);
export const createPayrollRun = (data) => api.post("/api/payroll/runs", data);
export const finalizePayrollRun = (id) => api.post(`/api/payroll/runs/${id}/finalize`);
export const deletePayrollRun = (id) => api.delete(`/api/payroll/runs/${id}`);

export const exportPayrollRunCsv = (id) =>
  api.get(`/api/payroll/runs/${id}/export/csv`, { responseType: "blob" });

export const downloadPayslipPdf = (runId, payslipId) =>
  api.get(`/api/payroll/runs/${runId}/payslips/${payslipId}/pdf`, { responseType: "blob" });
