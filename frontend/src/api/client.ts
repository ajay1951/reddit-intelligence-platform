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

import { getAuthToken } from "../lib/auth";

// Attach bearer token to all outgoing API requests
apiClient.interceptors.request.use(
  async (config) => {
    const token = await getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
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
