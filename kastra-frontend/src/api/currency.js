import api from "./axios";

export const getCurrencies = () =>
  api.get("/api/currency/currencies");

export const getExchangeRate = (code) =>
  api.get("/api/currency/rate", { params: { code } });
