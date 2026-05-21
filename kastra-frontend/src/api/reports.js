import api from "./axios";

export const getIncomeReport = (params) => api.get("/api/reports/income", { params });
export const getClientReport = () => api.get("/api/reports/clients");
export const exportCsv = (year) =>
  api.get("/api/reports/export/csv", { params: { year }, responseType: "blob" });
