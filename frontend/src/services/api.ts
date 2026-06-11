/** Typed REST client. Base URL always from VITE_API_BASE_URL — never localhost. */

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

if (!BASE_URL) {
  console.error('VITE_API_BASE_URL is not set — see frontend/.env.example');
}

export interface CreateSessionResponse {
  session_id: string;
  state: string;
  created_at: string;
  ws_path: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`API ${path} failed: ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export const api = {
  createSession: () =>
    request<CreateSessionResponse>('/sessions', { method: 'POST' }),
  getSession: (id: string) => request<unknown>(`/sessions/${id}`),
  getProducts: () => request<unknown>('/products'),
};

export function wsUrl(wsPath: string): string {
  // FIX ISSUE-14: server returns a relative ws_path; client builds the full URL.
  const httpBase = new URL(BASE_URL);
  const proto = httpBase.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${httpBase.host}${wsPath}`;
}
