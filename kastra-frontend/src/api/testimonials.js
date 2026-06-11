import api from "./axios";

export const requestTestimonial = (data) =>
  api.post("/api/testimonials/request", data);
