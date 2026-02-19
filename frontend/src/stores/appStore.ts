import { atom, map } from 'nanostores';
import { persistentMap } from '@nanostores/persistent';
import { api, setAdminToken, clearAdminToken, getAdminToken } from '@/lib/api';

// Types (mirrored from backend models)
export type EngineStatus = {
  running: boolean;
  last_poll: string | null;
  last_poll_result: string | null;
  demo_mode: boolean;
};

export type SystemConfig = {
  bmkg_api_url: string;
  setup_completed: boolean;
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

// Stores
export const engineStatus = map<EngineStatus>({
  running: false,
  last_poll: null,
  last_poll_result: null,
  demo_mode: false,
});

export const systemConfig = map<SystemConfig>({
  bmkg_api_url: '',
  setup_completed: false,
});

export const activeAlerts = atom<Alert[]>([]);

export const isLoading = atom<boolean>(false);

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
    // Alert engine returns { running: boolean, last_poll: string|null, last_poll_result: string|null }
    const res = await api.get<{ running: boolean; last_poll: string | null; last_poll_result: string | null; demo_mode?: boolean }>('/engine/status');
    engineStatus.set({
      running: res.running === true,
      last_poll: res.last_poll,
      last_poll_result: res.last_poll_result,
      demo_mode: res.demo_mode === true,
    });
  } catch (e) {
    console.error('Failed to fetch engine status', e);
  }
}

export async function fetchActiveAlerts() {
  try {
    const res = await api.get<{ data: Alert[] }>('/nowcast/active');
    activeAlerts.set(res.data ?? []);
  } catch (e) {
    console.error('Failed to fetch active alerts', e);
  }
}

export async function fetchConfig() {
  try {
    const res = await api.get<{ data: any }>('/config');
    systemConfig.set(res.data);
  } catch (e) {
    console.error('Failed to fetch config', e);
  }
}

export type UserSettings = {
  locations: string; // JSON string of string[]
  telegram_bot_token: string;
  telegram_chat_id: string;
};

export const settingsStore = persistentMap<UserSettings>('bmkg_settings:', {
  locations: '["Jakarta", "Yogyakarta"]',
  telegram_bot_token: '',
  telegram_chat_id: '',
});
