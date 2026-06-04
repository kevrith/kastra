import api from "./axios";

export const suggestItems = (clientId, count = 5) =>
  api.post("/api/ai/suggest-items", { client_id: clientId, count });

export const categorizeExpense = (imageBase64, mediaType = "image/jpeg") =>
  api.post("/api/ai/categorize-expense", { image_base64: imageBase64, media_type: mediaType });

export const getCashFlowForecast = () =>
  api.get("/api/ai/cash-flow-forecast");

export const generateDescription = (bullets, context = "") =>
  api.post("/api/ai/generate-description", { bullets, context });

export const getClientRisk = (clientId) =>
  api.get(`/api/ai/client-risk/${clientId}`);
