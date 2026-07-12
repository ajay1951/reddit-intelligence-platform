import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';

export function useApi<T = any>() {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (
    method: 'get' | 'post' | 'put' | 'delete',
    url: string,
    payload?: any
  ) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient[method](url, payload);
      setData(response.data);
      return response.data;
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'An unexpected error occurred';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, execute };
}
