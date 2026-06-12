import api from "./axios";

export const getDashboardStats = () => api.get("/api/dashboard/stats");
export const getOnboarding = () => api.get("/api/dashboard/onboarding");
