import api from "./axios";

export const scanReceipt = (image_base64, media_type = "image/jpeg") =>
  api.post("/api/ocr/scan", { image_base64, media_type });
