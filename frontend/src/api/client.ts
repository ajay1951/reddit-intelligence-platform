import axios from "axios";

// Create a centralized Axios instance
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  // Add 5 minute timeout for long running operations like indexing
  timeout: 300000,
});

// Optional: Add request interceptors (e.g., for auth tokens later)
apiClient.interceptors.request.use(
  (config) => {
    // You can attach tokens here
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Optional: Add response interceptors (e.g., for global error handling)
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // We can add global error toasts here later
    console.error("API Client Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);
