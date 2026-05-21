import api from "./axios";

export const getAuditLogs = (params) => api.get("/api/audit-logs", { params });
export const exportAuditCsv = (params) =>
  api.get("/api/audit-logs/export/csv", { params, responseType: "blob" });
