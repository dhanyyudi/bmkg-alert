import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trash2, Plus, Save, RefreshCw, Send, Download, Upload, Info } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { engineStatus, isAdmin, fetchEngineStatus } from '@/stores/appStore';

const DEMO_TOOLTIP = 'Demo mode — deploy instance sendiri untuk mengkonfigurasi';

// ─── Types ────────────────────────────────────────────────────────────────────

type Location = {
    id: number;
    label: string | null;
    province_name: string;
    district_name: string;
    subdistrict_name: string;
    subdistrict_code: string;
    district_code: string;
    province_code: string;
    enabled: boolean;
};

type WilayahResult = {
    code: string;
    name: string;
    level: string;
    province?: string;
    district?: string;
    subdistrict?: string;
};

type Channel = {
    id: number;
    channel_type: string;
    enabled: boolean;
    config: Record<string, string>;
    last_success_at: string | null;
};

type AppConfig = Record<string, string>;

// ─── Locations Tab ────────────────────────────────────────────────────────────

const LocationsTab: React.FC<{ demoMode: boolean }> = ({ demoMode }) => {
    const [locations, setLocations] = useState<Location[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<WilayahResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [adding, setAdding] = useState(false);

    const fetchLocations = async () => {
        try {
            const res = await api.get<{ data: Location[] }>('/locations');
            setLocations(res.data ?? []);
        } catch { toast.error('Gagal memuat lokasi'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchLocations(); }, []);

    const searchWilayah = useCallback(async (q: string) => {
        if (q.length < 2) { setSearchResults([]); return; }
        setSearching(true);
        try {
            const res = await api.get<{ data: WilayahResult[] }>(`/wilayah/search?q=${encodeURIComponent(q)}`);
            // Only show kecamatan (subdistrict) level results
            const sub = (res.data ?? []).filter(r => r.level === 'kecamatan' || r.level === 'subdistrict');
            setSearchResults(sub.length > 0 ? sub : (res.data ?? []).slice(0, 8));
        } catch { setSearchResults([]); }
        finally { setSearching(false); }
    }, []);

    useEffect(() => {
        const t = setTimeout(() => searchWilayah(searchQuery), 400);
        return () => clearTimeout(t);
    }, [searchQuery, searchWilayah]);

    const addLocation = async (result: WilayahResult) => {
        setAdding(true);
        try {
            await api.post('/locations', {
                label: result.name,
                province_code: result.code.substring(0, 2) + '.00.00.0000',
                province_name: result.province ?? '',
                district_code: result.code.substring(0, 5) + '.00.0000',
                district_name: result.district ?? '',
                subdistrict_code: result.code,
                subdistrict_name: result.name,
            });
            toast.success(`Lokasi "${result.name}" ditambahkan`);
            setSearchQuery('');
            setSearchResults([]);
            await fetchLocations();
        } catch (e: any) {
            const msg = e?.message ?? 'Gagal menambahkan lokasi';
            toast.error(msg.includes('409') ? 'Lokasi sudah ada' : msg);
        } finally { setAdding(false); }
    };

    const deleteLocation = async (id: number, name: string) => {
        try {
            await api.delete(`/locations/${id}`);
            toast.success(`Lokasi "${name}" dihapus`);
            setLocations(locs => locs.filter(l => l.id !== id));
        } catch { toast.error('Gagal menghapus lokasi'); }
    };

    const toggleLocation = async (id: number, enabled: boolean) => {
        try {
            await api.patch(`/locations/${id}`, { enabled: !enabled });
            setLocations(locs => locs.map(l => l.id === id ? { ...l, enabled: !enabled } : l));
        } catch { toast.error('Gagal mengubah status lokasi'); }
    };

    return (
        <div className="space-y-4">
            {/* Search & add */}
            <div className="relative">
                <Input
                    placeholder={demoMode ? 'Pencarian dinonaktifkan dalam demo mode' : 'Cari kecamatan / kabupaten (min. 2 karakter)...'}
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    disabled={demoMode}
                />
                {(searching || searchResults.length > 0) && (
                    <div className="absolute z-20 top-full mt-1 w-full bg-white dark:bg-slate-900 border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                        {searching && <div className="p-3 text-sm text-muted-foreground">Mencari...</div>}
                        {!searching && searchResults.map(r => (
                            <button
                                key={r.code}
                                className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 flex justify-between items-center gap-2"
                                onClick={() => addLocation(r)}
                                disabled={adding}
                            >
                                <div>
                                    <div className="font-medium">{r.name}</div>
                                    <div className="text-xs text-muted-foreground">
                                        {[r.district, r.province].filter(Boolean).join(', ')}
                                    </div>
                                </div>
                                <Plus className="w-4 h-4 shrink-0 text-green-500" />
                            </button>
                        ))}
                        {!searching && searchResults.length === 0 && searchQuery.length >= 2 && (
                            <div className="p-3 text-sm text-muted-foreground">Tidak ada hasil</div>
                        )}
                    </div>
                )}
            </div>

            {/* Location list */}
            {loading ? (
                <div className="py-6 text-center text-muted-foreground text-sm">Memuat lokasi...</div>
            ) : locations.length === 0 ? (
                <div className="py-6 text-center text-muted-foreground text-sm italic">
                    Belum ada lokasi yang dipantau.
                </div>
            ) : (
                <div className="space-y-2">
                    {locations.map(loc => (
                        <div
                            key={loc.id}
                            className={`flex justify-between items-center p-3 border rounded-lg ${
                                loc.enabled ? 'bg-white dark:bg-slate-900' : 'bg-slate-50 dark:bg-slate-950 opacity-60'
                            }`}
                        >
                            <div>
                                <div className="font-medium text-sm">{loc.label ?? loc.subdistrict_name}</div>
                                <div className="text-xs text-muted-foreground">
                                    {[loc.district_name, loc.province_name].filter(Boolean).join(', ')}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => toggleLocation(loc.id, loc.enabled)}
                                    disabled={demoMode}
                                    title={demoMode ? DEMO_TOOLTIP : undefined}
                                    className={`text-xs px-2 py-0.5 rounded-full border ${
                                        loc.enabled
                                            ? 'border-green-500 text-green-600'
                                            : 'border-slate-400 text-slate-500'
                                    } ${demoMode ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    {loc.enabled ? 'Aktif' : 'Nonaktif'}
                                </button>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => deleteLocation(loc.id, loc.label ?? loc.subdistrict_name)}
                                    disabled={demoMode}
                                    title={demoMode ? DEMO_TOOLTIP : undefined}
                                >
                                    <Trash2 className="w-4 h-4 text-red-500" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// ─── Channels Tab ─────────────────────────────────────────────────────────────

const CHANNEL_FIELDS: Record<string, { key: string; label: string; type?: string; placeholder: string }[]> = {
    telegram: [
        { key: 'bot_token', label: 'Bot Token', type: 'password', placeholder: '123456789:ABCdef...' },
        { key: 'chat_id', label: 'Chat ID', placeholder: '-987654321' },
    ],
    discord: [
        { key: 'webhook_url', label: 'Webhook URL', type: 'password', placeholder: 'https://discord.com/api/webhooks/...' },
    ],
    slack: [
        { key: 'webhook_url', label: 'Webhook URL', type: 'password', placeholder: 'https://hooks.slack.com/services/...' },
    ],
    email: [
        { key: 'smtp_host', label: 'SMTP Host', placeholder: 'smtp.gmail.com' },
        { key: 'smtp_port', label: 'SMTP Port', placeholder: '587' },
        { key: 'smtp_user', label: 'SMTP User', placeholder: 'you@gmail.com' },
        { key: 'smtp_password', label: 'SMTP Password', type: 'password', placeholder: 'app password' },
        { key: 'to_email', label: 'Recipient Email', placeholder: 'recipient@example.com' },
    ],
    webhook: [
        { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://your-server.com/webhook' },
        { key: 'secret', label: 'Secret Header (optional)', type: 'password', placeholder: 'Bearer your-token' },
    ],
};

const ChannelsTab: React.FC<{ demoMode: boolean }> = ({ demoMode }) => {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [loading, setLoading] = useState(true);
    const [addType, setAddType] = useState<string>('telegram');
    const [addConfig, setAddConfig] = useState<Record<string, string>>({});
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState<number | null>(null);

    const fetchChannels = async () => {
        try {
            const res = await api.get<{ data: Channel[] }>('/channels');
            setChannels(res.data ?? []);
        } catch { toast.error('Gagal memuat channel'); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchChannels(); }, []);

    const addChannel = async () => {
        setSaving(true);
        try {
            await api.post('/channels', { channel_type: addType, enabled: true, config: addConfig });
            toast.success(`Channel ${addType} ditambahkan`);
            setAddConfig({});
            await fetchChannels();
        } catch { toast.error('Gagal menambahkan channel'); }
        finally { setSaving(false); }
    };

    const deleteChannel = async (id: number) => {
        try {
            await api.delete(`/channels/${id}`);
            toast.success('Channel dihapus');
            setChannels(ch => ch.filter(c => c.id !== id));
        } catch { toast.error('Gagal menghapus channel'); }
    };

    const toggleChannel = async (id: number, enabled: boolean) => {
        try {
            await api.patch(`/channels/${id}`, { enabled: !enabled });
            setChannels(ch => ch.map(c => c.id === id ? { ...c, enabled: !enabled } : c));
        } catch { toast.error('Gagal mengubah status channel'); }
    };

    const testChannel = async (id: number) => {
        setTesting(id);
        try {
            await api.post(`/channels/${id}/test`, {});
            toast.success('Notifikasi test berhasil dikirim!');
        } catch { toast.error('Gagal mengirim notifikasi test'); }
        finally { setTesting(null); }
    };

    const fields = CHANNEL_FIELDS[addType] ?? [];

    return (
        <div className="space-y-6">
            {/* Existing channels */}
            {loading ? (
                <div className="py-4 text-center text-sm text-muted-foreground">Memuat channel...</div>
            ) : channels.length === 0 ? (
                <div className="py-4 text-center text-sm text-muted-foreground italic">
                    Belum ada channel notifikasi.
                </div>
            ) : (
                <div className="space-y-2">
                    {channels.map(ch => (
                        <div key={ch.id} className={`flex items-center justify-between p-3 border rounded-lg ${
                            ch.enabled ? 'bg-white dark:bg-slate-900' : 'bg-slate-50 dark:bg-slate-950 opacity-60'
                        }`}>
                            <div>
                                <div className="font-medium text-sm capitalize">{ch.channel_type}</div>
                                <div className="text-xs text-muted-foreground">
                                    {ch.last_success_at ? `Terakhir sukses: ${new Date(ch.last_success_at).toLocaleString('id-ID')}` : 'Belum pernah terkirim'}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => toggleChannel(ch.id, ch.enabled)}
                                    disabled={demoMode}
                                    title={demoMode ? DEMO_TOOLTIP : undefined}
                                    className={`text-xs px-2 py-0.5 rounded-full border ${
                                        ch.enabled ? 'border-green-500 text-green-600' : 'border-slate-400 text-slate-500'
                                    } ${demoMode ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    {ch.enabled ? 'Aktif' : 'Nonaktif'}
                                </button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => testChannel(ch.id)}
                                    disabled={demoMode || testing === ch.id}
                                    title={demoMode ? DEMO_TOOLTIP : undefined}
                                >
                                    <Send className="w-3 h-3 mr-1" />
                                    {testing === ch.id ? 'Kirim...' : 'Test'}
                                </Button>
                                <Button variant="ghost" size="sm" onClick={() => deleteChannel(ch.id)} disabled={demoMode} title={demoMode ? DEMO_TOOLTIP : undefined}>
                                    <Trash2 className="w-4 h-4 text-red-500" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add new channel */}
            <div className="border rounded-lg p-4 space-y-3 bg-slate-50 dark:bg-slate-950">
                <h3 className="font-medium text-sm">Tambah Channel Baru</h3>
                <div className="flex gap-2 flex-wrap">
                    {Object.keys(CHANNEL_FIELDS).map(type => (
                        <button
                            key={type}
                            onClick={() => { setAddType(type); setAddConfig({}); }}
                            className={`text-xs px-3 py-1 rounded-full border capitalize ${
                                addType === type
                                    ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900'
                                    : 'border-slate-300 text-slate-600 hover:border-slate-500'
                            }`}
                        >
                            {type}
                        </button>
                    ))}
                </div>
                <div className="space-y-2">
                    {fields.map(f => (
                        <div key={f.key}>
                            <label className="text-xs font-medium text-muted-foreground">{f.label}</label>
                            <Input
                                type={f.type ?? 'text'}
                                placeholder={f.placeholder}
                                value={addConfig[f.key] ?? ''}
                                onChange={e => setAddConfig(c => ({ ...c, [f.key]: e.target.value }))}
                            />
                        </div>
                    ))}
                </div>
                <Button onClick={addChannel} disabled={demoMode || saving} className="w-full" title={demoMode ? DEMO_TOOLTIP : undefined}>
                    <Plus className="w-4 h-4 mr-2" />
                    {saving ? 'Menyimpan...' : `Tambah ${addType}`}
                </Button>
            </div>
        </div>
    );
};

// ─── Config Tab ───────────────────────────────────────────────────────────────

const CONFIG_FIELDS = [
    { key: 'poll_interval', label: 'Polling Interval (detik)', placeholder: '300', type: 'number' },
    { key: 'severity_threshold', label: 'Severity Threshold', placeholder: 'all | minor | moderate | severe | extreme' },
    { key: 'quiet_hours_enabled', label: 'Quiet Hours (true/false)', placeholder: 'false' },
    { key: 'quiet_hours_start', label: 'Quiet Hours Mulai', placeholder: '22:00' },
    { key: 'quiet_hours_end', label: 'Quiet Hours Selesai', placeholder: '06:00' },
    { key: 'quiet_hours_override_severe', label: 'Override untuk Severe/Extreme (true/false)', placeholder: 'true' },
    { key: 'bmkg_api_url', label: 'BMKG API URL', placeholder: 'https://bmkg-restapi.vercel.app', readOnly: true },
    { key: 'notification_language', label: 'Bahasa Notifikasi (id/en)', placeholder: 'id' },
];

const ConfigTab: React.FC<{ demoMode: boolean }> = ({ demoMode }) => {
    const [config, setConfig] = useState<AppConfig>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.get<{ data: AppConfig }>('/config')
            .then(res => setConfig(res.data ?? {}))
            .catch(() => toast.error('Gagal memuat konfigurasi'))
            .finally(() => setLoading(false));
    }, []);

    const save = async () => {
        setSaving(true);
        try {
            await api.put('/config', { settings: config });
            toast.success('Konfigurasi disimpan');
        } catch { toast.error('Gagal menyimpan konfigurasi'); }
        finally { setSaving(false); }
    };

    const exportConfig = async () => {
        try {
            const data = await api.post<object>('/config/export', {});
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bmkg-alert-config-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Konfigurasi diekspor');
        } catch { toast.error('Gagal mengekspor konfigurasi'); }
    };

    const importConfig = async () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = async () => {
            const file = input.files?.[0];
            if (!file) return;
            try {
                const text = await file.text();
                const data = JSON.parse(text);
                await api.post('/config/import', data);
                toast.success('Konfigurasi diimport');
                window.location.reload();
            } catch { toast.error('Gagal mengimport konfigurasi'); }
        };
        input.click();
    };

    if (loading) return <div className="py-4 text-center text-sm text-muted-foreground">Memuat konfigurasi...</div>;

    return (
        <div className="space-y-4">
            {CONFIG_FIELDS.map(f => (
                <div key={f.key} className="space-y-1">
                    <label className="text-sm font-medium">{f.label}</label>
                    {f.readOnly ? (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-md border bg-slate-50 dark:bg-slate-900 text-sm font-mono text-slate-600 dark:text-slate-400 select-all">
                            {config[f.key] ?? f.placeholder}
                            <span className="ml-auto text-[10px] font-sans uppercase tracking-wide text-slate-400 shrink-0">Server</span>
                        </div>
                    ) : (
                        <Input
                            type={f.type ?? 'text'}
                            placeholder={f.placeholder}
                            value={config[f.key] ?? ''}
                            onChange={e => setConfig(c => ({ ...c, [f.key]: e.target.value }))}
                            disabled={demoMode}
                        />
                    )}
                </div>
            ))}
            <Button onClick={save} disabled={demoMode || saving} className="w-full mt-2" title={demoMode ? DEMO_TOOLTIP : undefined}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Menyimpan...' : 'Simpan Konfigurasi'}
            </Button>
            <div className="flex gap-2 pt-4 border-t">
                <Button variant="outline" onClick={exportConfig} className="flex-1">
                    <Download className="w-4 h-4 mr-2" /> Export JSON
                </Button>
                <Button variant="outline" onClick={importConfig} className="flex-1" disabled={demoMode} title={demoMode ? DEMO_TOOLTIP : undefined}>
                    <Upload className="w-4 h-4 mr-2" /> Import JSON
                </Button>
            </div>
        </div>
    );
};

// ─── System Tab ───────────────────────────────────────────────────────────────

const SystemTab: React.FC = () => {
    const [engStatus, setEngStatus] = useState<any>(null);
    const [alertStats, setAlertStats] = useState<any>(null);
    const [version, setVersion] = useState<string>('1.0.0');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            api.get<any>('/engine/status'),
            api.get<any>('/alerts/stats'),
            api.get<{ data: Record<string, string> }>('/config'),
        ]).then(([eng, stats, cfg]) => {
            setEngStatus(eng);
            setAlertStats(stats);
            setVersion(cfg.data?.app_version ?? '1.0.0');
        }).catch(() => {})
          .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="py-4 text-center text-sm text-muted-foreground">Memuat info sistem...</div>;

    const rows = [
        { label: 'Versi Aplikasi', value: version },
        { label: 'Mode', value: engStatus?.demo_mode ? 'Demo' : 'Production' },
        { label: 'Status Engine', value: engStatus?.running ? 'Berjalan' : 'Berhenti' },
        { label: 'Poll Terakhir', value: engStatus?.last_poll ? new Date(engStatus.last_poll).toLocaleString('id-ID') : '-' },
        { label: 'Hasil Poll Terakhir', value: engStatus?.last_poll_result ?? '-' },
        { label: 'Total Alert Tersimpan', value: alertStats?.total_alerts ?? '-' },
        { label: 'Alert Bulan Ini', value: alertStats?.alerts_this_month ?? '-' },
        { label: 'Lokasi Dipantau', value: alertStats?.monitored_locations ?? '-' },
        { label: 'Channel Aktif', value: alertStats?.active_channels ?? '-' },
    ];

    return (
        <div className="space-y-2">
            {rows.map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-2 border-b last:border-0 text-sm">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-medium">{String(value)}</span>
                </div>
            ))}
        </div>
    );
};

// ─── Main SettingsForm ────────────────────────────────────────────────────────

export const SettingsForm: React.FC = () => {
    const status = useStore(engineStatus);
    const admin = useStore(isAdmin);
    const demoMode = status.demo_mode && !admin;

    useEffect(() => { fetchEngineStatus(); }, []);

    return (
        <div className="max-w-4xl mx-auto pb-10 space-y-6">
            {/* Demo Mode Banner */}
            {demoMode && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-700 text-amber-800 dark:text-amber-200 text-sm">
                    <Info className="w-4 h-4 shrink-0" />
                    <span>
                        <strong>Demo Mode</strong> — Konfigurasi dinonaktifkan. Deploy instance sendiri untuk mengaktifkan semua fitur.
                    </span>
                </div>
            )}

            <Tabs defaultValue="locations" className="w-full">
                <TabsList className="grid w-full grid-cols-4 mb-6">
                    <TabsTrigger value="locations">Lokasi</TabsTrigger>
                    <TabsTrigger value="channels">Notifikasi</TabsTrigger>
                    <TabsTrigger value="config">Konfigurasi</TabsTrigger>
                    <TabsTrigger value="system">Sistem</TabsTrigger>
                </TabsList>

                <TabsContent value="locations">
                    <Card>
                        <CardHeader>
                            <CardTitle>Lokasi yang Dipantau</CardTitle>
                            <CardDescription>
                                Tambah kecamatan yang ingin dipantau. Engine akan mencocokkan peringatan BMKG dengan lokasi ini.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <LocationsTab demoMode={demoMode} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="channels">
                    <Card>
                        <CardHeader>
                            <CardTitle>Channel Notifikasi</CardTitle>
                            <CardDescription>
                                Kelola channel notifikasi untuk mengirim peringatan cuaca. Mendukung Telegram, Discord, Slack, Email, dan Webhook.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ChannelsTab demoMode={demoMode} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="config">
                    <Card>
                        <CardHeader>
                            <CardTitle>Konfigurasi Aplikasi</CardTitle>
                            <CardDescription>
                                Atur interval polling, threshold severity, jam tenang, dan export/import konfigurasi.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ConfigTab demoMode={demoMode} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="system">
                    <Card>
                        <CardHeader>
                            <CardTitle>Informasi Sistem</CardTitle>
                            <CardDescription>
                                Status dan statistik sistem BMKG Alert.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <SystemTab />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};
