import { useState, useCallback, useRef } from 'react';

export function useSSE<T = any>(endpoint: string) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startStream = useCallback(async (
    payload: any,
    onData: (data: T) => void,
    onComplete?: () => void
  ) => {
    setIsStreaming(true);
    setError(null);
    
    abortControllerRef.current = new AbortController();

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error('Stream request failed');
      if (!response.body) throw new Error('ReadableStream not yet supported in this browser');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataStr = line.substring(6);
              const data = JSON.parse(dataStr);
              onData(data);
            } catch (e) {
              console.error('Failed to parse SSE JSON:', e);
            }
          }
        }
      }
      
      onComplete?.();
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted');
      } else {
        setError(err.message || 'Stream failed');
      }
    } finally {
      setIsStreaming(false);
    }
  }, [endpoint]);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  return { isStreaming, error, startStream, stopStream };
}
