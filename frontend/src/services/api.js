import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("rms_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem("rms_token")) {
      localStorage.removeItem("rms_token");
      window.dispatchEvent(new Event("rms:auth-expired"));
    }
    return Promise.reject(error);
  },
);
export default api;
