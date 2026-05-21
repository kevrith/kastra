import api from "./axios";

export const login = (email, password) =>
  api.post("/api/auth/login", { email, password });

export const register = (email, password, display_name, business_name, consent = false, plan = "free") =>
  api.post("/api/auth/register", { email, password, display_name, business_name, consent, plan });

export const exportMyData = () => api.get("/api/auth/me/export");

export const deleteMyAccount = () => api.delete("/api/auth/me");

export const logout = () => api.post("/api/auth/logout");

export const me = () => api.get("/api/auth/me");

export const getGoogleAuthUrl = (plan = "free") => api.get(`/api/auth/google?plan=${plan}`);

export const forgotPassword = (email) =>
  api.post("/api/auth/forgot-password", { email });

export const resetPassword = (token, new_password) =>
  api.post("/api/auth/reset-password", { token, new_password });
