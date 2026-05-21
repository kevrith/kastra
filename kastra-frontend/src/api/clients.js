import api from "./axios";

export const getClients = (params) => api.get("/api/clients", { params });
export const getClient = (id) => api.get(`/api/clients/${id}`);
export const createClient = (data) => api.post("/api/clients", data);
export const updateClient = (id, data) => api.put(`/api/clients/${id}`, data);
export const deleteClient = (id) => api.delete(`/api/clients/${id}`);
export const getClientHistory = (id) => api.get(`/api/clients/${id}/history`);
