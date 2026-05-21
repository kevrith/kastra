import api from "./axios";

export const globalSearch = (q) => api.get("/api/search", { params: { q } });
