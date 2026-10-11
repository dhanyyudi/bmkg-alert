import { atom, map } from 'nanostores';
import { api, setAdminToken, clearAdminToken, getAdminToken } from '@/lib/api';

// Types (mirrored from backend models)
export type EngineStatus = {
  running: boolean;
  last_poll: string | null;
  last_poll_result: string | null;
  demo_mode: boolean;
};

export type Area = {
  name: string;
  polygon: number[][] | null;
};

// Matches the Warning model returned by GET /api/v1/nowcast/active
export type Alert = {
  identifier: string;
  event: string;
  severity: string;
  urgency: string;
  certainty: string;
  effective: string;
  expires: string;
  headline: string;
  description: string;
  sender: string;
  infographic_url: string | null;
  areas: Area[];
  is_expired: boolean;
};

export type LoadState = 'loading' | 'ready' | 'error';

// Stores
export const engineStatus = map<EngineStatus>({
  running: false,
  last_poll: null,
  last_poll_result: null,
  demo_mode: false,
});

export const engineState = atom<LoadState>('loading');

export const activeAlerts = atom<Alert[]>([]);

export const alertsState = atom<LoadState>('loading');

// Admin auth state
export const isAdmin = atom<boolean>(!!getAdminToken());

export async function adminLogin(password: string): Promise<boolean> {
  try {
    const res = await api.post<{ authenticated: boolean }>('/auth/login', { password });
    if (res.authenticated) {
      setAdminToken(password);
      isAdmin.set(true);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

export function adminLogout(): void {
  clearAdminToken();
  isAdmin.set(false);
}

// Actions
export async function fetchEngineStatus() {
  try {
    const res = await api.get<{ running: boolean; last_poll: string | null; last_poll_result: string | null; demo_mode?: boolean }>('/engine/status');
    engineStatus.set({
      running: res.running === true,
      last_poll: res.last_poll,
      last_poll_result: res.last_poll_result,
      demo_mode: res.demo_mode === true,
    });
    engineState.set('ready');
  } catch (e) {
    console.error('Failed to fetch engine status', e);
    engineState.set('error');
  }
}

export async function fetchActiveAlerts() {
  try {
    const res = await api.get<{ data: Alert[] }>('/nowcast/active');
    activeAlerts.set(res.data ?? []);
    alertsState.set('ready');
  } catch (e) {
    console.error('Failed to fetch active alerts', e);
    // Keep the last good list on screen during a refresh failure
    alertsState.set('error');
  }
}
