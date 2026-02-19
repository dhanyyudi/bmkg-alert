const API_BASE = '/api/v1';

// ── Admin token (sessionStorage) ─────────────────────────────────────────────

const ADMIN_TOKEN_KEY = 'bmkg_admin_token';

export function getAdminToken(): string | null {
  try { return sessionStorage.getItem(ADMIN_TOKEN_KEY); } catch { return null; }
}

export function setAdminToken(token: string): void {
  try { sessionStorage.setItem(ADMIN_TOKEN_KEY, token); } catch { /* noop */ }
}

export function clearAdminToken(): void {
  try { sessionStorage.removeItem(ADMIN_TOKEN_KEY); } catch { /* noop */ }
}

// ── API client ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  };

  // Inject admin token if available
  const token = getAdminToken();
  if (token) {
    headers['X-Admin-Token'] = token;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `API Error: ${response.statusText}`;
    let errorData;
    try {
      errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (e) {
      // ignore JSON parse error
    }
    throw new ApiError(response.status, errorMessage, errorData);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, body: any) => request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(endpoint: string, body: any) => request<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(endpoint: string, body: any) => request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};
