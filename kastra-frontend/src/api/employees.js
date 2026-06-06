import api from "./axios";

export const getEmployees = (params) => api.get("/api/employees", { params });
export const getEmployee = (id) => api.get(`/api/employees/${id}`);
export const createEmployee = (data) => api.post("/api/employees", data);
export const updateEmployee = (id, data) => api.put(`/api/employees/${id}`, data);
export const deleteEmployee = (id) => api.delete(`/api/employees/${id}`);
