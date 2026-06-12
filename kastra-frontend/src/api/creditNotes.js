import api from "./axios";

export const listCreditNotes = (params) => api.get("/api/credit-notes", { params });
export const getCreditNote = (id) => api.get(`/api/credit-notes/${id}`);
export const createCreditNote = (payload) => api.post("/api/credit-notes", payload);
export const voidCreditNote = (id) => api.delete(`/api/credit-notes/${id}`);
export const submitCreditNoteEtims = (id) => api.post(`/api/credit-notes/${id}/etims`);
export const downloadCreditNotePdf = (id) =>
  api.get(`/api/credit-notes/${id}/pdf`, { responseType: "blob" });
