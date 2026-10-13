import { atom, map } from 'nanostores';
import { api, setAdminToken, clearAdminToken, getAdminToken } from '@/lib/api';

// Types (mirrored from backend models)
export type EngineStatus = {
  running: boolean;
  last_poll: string | null;
  last_poll_result: string | null;
  demo_mode: boolean;
  // Settings changes need the admin password (public demo, or ADMIN_PASSWORD is set)
  write_locked: boolean;
  // False while ADMIN_PASSWORD is still the default: nobody can log in
  admin_login_available: boolean;
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
  write_locked: false,
  admin_login_available: false,
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
    const res = await api.get<Partial<EngineStatus>>('/engine/status');
    engineStatus.set({
      running: res.running === true,
      last_poll: res.last_poll ?? null,
      last_poll_result: res.last_poll_result ?? null,
      demo_mode: res.demo_mode === true,
      write_locked: res.write_locked === true,
      admin_login_available: res.admin_login_available === true,
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

/** Why a settings control is disabled, for its tooltip. */
export function lockReason(): string {
  return engineStatus.get().demo_mode
    ? 'Mode demo: pasang instance sendiri untuk mengubah konfigurasi'
    : 'Terkunci: masuk sebagai admin untuk mengubah pengaturan';
}
