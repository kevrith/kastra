import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true, // sends HttpOnly refresh cookie
});

api.interceptors.request.use((config) => {
  if (!config.headers.Authorization) {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Endpoints where a 401 is a normal answer rather than an expired session:
// signing in, and answering a two-factor challenge. Running the refresh-and-
// redirect dance on these throws the user back to a blank login form instead of
// showing "that code is not valid".
const AUTH_CHALLENGE_PATHS = ["/api/auth/login", "/api/auth/2fa/verify-login"];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isChallenge = AUTH_CHALLENGE_PATHS.some((p) => original?.url?.includes(p));
    if (error.response?.status === 401 && !original._retry && !isChallenge) {
      original._retry = true;
      try {
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/auth/refresh`,
          {},
          { withCredentials: true }
        );
        localStorage.setItem("access_token", data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
