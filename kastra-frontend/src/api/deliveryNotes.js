import api from "./axios";

export const listDeliveryNotes = (params) => api.get("/api/delivery-notes", { params });
export const getDeliveryNote = (id) => api.get(`/api/delivery-notes/${id}`);
export const createDeliveryNote = (payload) => api.post("/api/delivery-notes", payload);
export const updateDeliveryNote = (id, payload) => api.patch(`/api/delivery-notes/${id}`, payload);
export const deleteDeliveryNote = (id) => api.delete(`/api/delivery-notes/${id}`);
export const downloadDeliveryNotePdf = (id) =>
  api.get(`/api/delivery-notes/${id}/pdf`, { responseType: "blob" });
