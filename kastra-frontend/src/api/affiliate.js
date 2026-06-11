import axios from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const api = axios.create({ baseURL: BASE });

const _auth = () => {
  const t = localStorage.getItem("affiliate_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
};

export const affiliateRegister = (data) =>
  api.post("/api/affiliate/register", data);

export const affiliateLogin = (email, password) =>
  api.post("/api/affiliate/login", { email, password });

export const checkReferralCode = (code) =>
  api.get(`/api/affiliate/check/${code}`);

export const affiliateMe = () =>
  api.get("/api/affiliate/me", { headers: _auth() });

export const affiliateReferrals = () =>
  api.get("/api/affiliate/referrals", { headers: _auth() });

export const affiliateCommissions = () =>
  api.get("/api/affiliate/commissions", { headers: _auth() });

export const affiliatePayouts = () =>
  api.get("/api/affiliate/payouts", { headers: _auth() });

export const requestPayout = (amount_ksh) =>
  api.post("/api/affiliate/payout", { amount_ksh }, { headers: _auth() });
