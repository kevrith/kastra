import api from "./axios";

export const getRecurring = () => api.get("/api/recurring");
export const createRecurring = (data) => api.post("/api/recurring", data);
export const toggleRecurring = (id) => api.patch(`/api/recurring/${id}/toggle`);
export const deleteRecurring = (id) => api.delete(`/api/recurring/${id}`);
