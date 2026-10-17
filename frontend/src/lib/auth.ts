// Authentication & Token Management Service

const TOKEN_STORAGE_KEY = 'reddit_intel_jwt_token';
const USER_STORAGE_KEY = 'reddit_intel_user';

let memoryToken: string | null = null;

export interface AuthUser {
  username: string;
  role: string;
}

export function isAuthenticated(): boolean {
  if (memoryToken) return true;
  try {
    return Boolean(sessionStorage.getItem(TOKEN_STORAGE_KEY));
  } catch {
    return false;
  }
}

export function getStoredUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(USER_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

export async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const res = await fetch(`${apiUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      return {
        success: false,
        error: errData.detail || 'Invalid username or password.',
      };
    }

    const data = await res.json();
    const token = data.access_token;
    if (token) {
      memoryToken = token;
      try {
        sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
        sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ username, role: 'admin' }));
      } catch {}
      return { success: true };
    }
    return { success: false, error: 'Token missing in response.' };
  } catch (err: any) {
    return { success: false, error: err.message || 'Network connection failed.' };
  }
}

export function logout(): void {
  memoryToken = null;
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(USER_STORAGE_KEY);
  } catch {}
}

export async function getAuthToken(): Promise<string | null> {
  if (memoryToken) return memoryToken;
  try {
    const stored = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      memoryToken = stored;
      return stored;
    }
  } catch {}
  return null;
}

export function clearAuthToken(): void {
  logout();
}
