import api from "./axios";

export const login = (email, password) =>
  api.post("/api/auth/login", { email, password });

export const register = (email, password, display_name, business_name, consent = false, plan = "free", referral_code = null) =>
  api.post("/api/auth/register", { email, password, display_name, business_name, consent, plan, referral_code });

export const exportMyData = () => api.get("/api/auth/me/export");

export const deleteMyAccount = () => api.delete("/api/auth/me");

export const logout = () => api.post("/api/auth/logout");

export const me = () => api.get("/api/auth/me");

export const getGoogleAuthUrl = (plan = "free") => api.get(`/api/auth/google?plan=${plan}`);

export const forgotPassword = (email) =>
  api.post("/api/auth/forgot-password", { email });

export const resetPassword = (token, new_password) =>
  api.post("/api/auth/reset-password", { token, new_password });

export const resendVerification = (email) =>
  api.post("/api/auth/resend-verification", { email });

export const verifyEmail = (token) =>
  api.get(`/api/auth/verify-email?token=${token}`);

// ── Two-factor authentication ────────────────────────────────────────────────
export const twoFactorStatus = () => api.get("/api/auth/2fa/status");
export const twoFactorSetup = () => api.post("/api/auth/2fa/setup");
export const twoFactorEnable = (code) => api.post("/api/auth/2fa/enable", { code });
export const twoFactorDisable = (password, code = null) =>
  api.post("/api/auth/2fa/disable", { password, code });
// Completes a login that returned mfa_required — no auth header, the mfa_token
// is the credential.
export const twoFactorVerifyLogin = (mfa_token, code) =>
  api.post("/api/auth/2fa/verify-login", { mfa_token, code });
