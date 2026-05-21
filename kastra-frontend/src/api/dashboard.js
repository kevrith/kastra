import api from "./axios";

export const getDashboardStats = () => api.get("/api/dashboard/stats");
