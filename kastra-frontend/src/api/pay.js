import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8080";
const payApi = axios.create({ baseURL });

export const getPublicInvoice = (id) => payApi.get(`/api/pay/${id}`);
export const publicMpesaPay = (id, phone_number, amount = null) =>
  payApi.post(`/api/pay/${id}/mpesa`, { phone_number, ...(amount ? { amount } : {}) });
