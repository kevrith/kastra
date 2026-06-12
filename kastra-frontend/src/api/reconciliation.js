import api from "./axios";

export const parseStatement = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/reconciliation/parse", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const confirmMatches = (matches) =>
  api.post("/api/reconciliation/confirm", { matches });
