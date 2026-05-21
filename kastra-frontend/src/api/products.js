import api from "./axios";

export const getProducts = (q, clientId) =>
  api.get("/api/products", { params: { ...(q ? { q } : {}), ...(clientId ? { client_id: clientId } : {}) } });
export const createProduct = (data) => api.post("/api/products", data);
export const updateProduct = (id, data) => api.put(`/api/products/${id}`, data);
export const deleteProduct = (id) => api.delete(`/api/products/${id}`);
