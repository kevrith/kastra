import api from "./axios";

export const getOrganization = () => api.get("/api/organization");
export const updateOrganization = (data) => api.put("/api/organization", data);
