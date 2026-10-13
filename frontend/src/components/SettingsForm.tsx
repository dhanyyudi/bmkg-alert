import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trash2, Plus, Save, Send, Download, Upload, Info } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { fmtDateTime } from '@/lib/format';
import { MONITOR_LEVELS, levelLabel, regionContext, searchRegions, toLocationPayload, type WilayahResult } from '@/lib/wilayah';
import { engineStatus, isAdmin, fetchEngineStatus, lockReason } from '@/stores/appStore';
import { AdminLogin } from '@/components/AdminLogin';


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


type Channel = {
    id: number;
    channel_type: string;
    enabled: boolean;
    config: Record<string, string>;
    last_success_at: string | null;
};

type AppConfig = Record<string, string>;

// ─── Locations Tab ────────────────────────────────────────────────────────────

const LocationsTab: React.FC<{ locked: boolean }> = ({ locked }) => {
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
            setSearchResults(await searchRegions(q, MONITOR_LEVELS));
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
            await api.post('/locations', toLocationPayload(result));
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
        if (!window.confirm(`Hapus lokasi "${name}"? Peringatan untuk lokasi ini tidak akan dikirim lagi.`)) return;
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
                    aria-label="Cari kecamatan atau kabupaten/kota untuk dipantau"
                    placeholder={locked ? 'Pencarian dimatikan: pengaturan terkunci' : 'Ketik nama kecamatan atau kabupaten/kota, minimal 2 huruf'}
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    disabled={locked}
                />
                {(searching || searchResults.length > 0) && (
                    <div className="absolute z-20 top-full mt-1 w-full bg-card border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                        {searching && <div className="p-3 text-sm text-muted-foreground">Mencari...</div>}
                        {!searching && searchResults.map(r => (
                            <button
                                key={r.code}
                                type="button"
                                className="w-full min-h-11 text-left px-3 py-2 text-sm hover:bg-accent focus-visible:outline-none focus-visible:bg-accent flex justify-between items-center gap-2"
                                onClick={() => addLocation(r)}
                                disabled={adding}
                            >
                                <div>
                                    <div className="font-medium">{r.name} <span className="font-normal text-muted-foreground">({levelLabel(r.level)})</span></div>
                                    <div className="text-xs text-muted-foreground">{regionContext(r)}</div>
                                </div>
                                <Plus className="w-4 h-4 shrink-0 text-green-700 dark:text-green-400" />
                            </button>
                        ))}
                        {!searching && searchResults.length === 0 && searchQuery.length >= 2 && (
                            <div className="p-3 text-sm text-muted-foreground">Tidak ada kecamatan atau kabupaten/kota dengan nama itu. Periksa ejaannya.</div>
                        )}
                    </div>
                )}
            </div>

            {/* Location list */}
            {loading ? (
                <div className="py-6 text-center text-muted-foreground text-sm">Memuat lokasi...</div>
            ) : locations.length === 0 ? (
                <div className="py-6 text-center text-muted-foreground text-sm">
                    Belum ada lokasi yang dipantau. Cari kecamatan atau kabupaten/kota di kolom atas untuk menambahkannya.
                </div>
            ) : (
                <div className="space-y-2">
                    {locations.map(loc => (
                        <div
                            key={loc.id}
                            className={`flex justify-between items-center p-3 border rounded-lg ${
                                loc.enabled ? 'bg-card' : 'bg-muted'
                            }`}
                        >
                            <div>
                                <div className="font-medium text-sm">{loc.label ?? loc.subdistrict_name}</div>
                                <div className="text-xs text-muted-foreground">
                                    {[loc.district_name, loc.province_name].filter(Boolean).join(', ')}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    role="switch"
                                    aria-checked={loc.enabled}
                                    aria-label={`Pantau ${loc.label ?? loc.subdistrict_name}`}
                                    onClick={() => toggleLocation(loc.id, loc.enabled)}
                                    disabled={locked}
                                    title={locked ? lockReason() : undefined}
                                >
                                    {loc.enabled ? 'Aktif' : 'Nonaktif'}
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    aria-label={`Hapus lokasi ${loc.label ?? loc.subdistrict_name}`}
                                    onClick={() => deleteLocation(loc.id, loc.label ?? loc.subdistrict_name)}
                                    disabled={locked}
                                    title={locked ? lockReason() : undefined}
                                >
                                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" aria-hidden="true" />
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
        { key: 'webhook_url', label: 'Webhook URL', placeholder: 'https://server-anda.example/webhook' },
        { key: 'secret', label: 'Header Authorization (opsional)', type: 'password', placeholder: 'Bearer token-anda' },
    ],
};

const ChannelsTab: React.FC<{ locked: boolean }> = ({ locked }) => {
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
        if (!window.confirm('Hapus channel ini? Notifikasi tidak akan dikirim lewat channel ini lagi.')) return;
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
            toast.success('Notifikasi tes terkirim');
        } catch { toast.error('Notifikasi tes gagal terkirim. Periksa token atau URL channel.'); }
        finally { setTesting(null); }
    };

    const fields = CHANNEL_FIELDS[addType] ?? [];

    return (
        <div className="space-y-6">
            {/* Existing channels */}
            {loading ? (
                <div className="py-4 text-center text-sm text-muted-foreground">Memuat channel...</div>
            ) : channels.length === 0 ? (
                <div className="py-4 text-center text-sm text-muted-foreground">
                    Belum ada channel notifikasi. Tambahkan satu di bawah supaya peringatan bisa dikirim.
                </div>
            ) : (
                <div className="space-y-2">
                    {channels.map(ch => (
                        <div key={ch.id} className={`flex items-center justify-between p-3 border rounded-lg ${
                            ch.enabled ? 'bg-card' : 'bg-muted'
                        }`}>
                            <div>
                                <div className="font-medium text-sm capitalize">{ch.channel_type}</div>
                                <div className="text-xs text-muted-foreground">
                                    {ch.last_success_at ? `Terakhir mengirim: ${fmtDateTime(ch.last_success_at)}` : 'Belum pernah mengirim'}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    role="switch"
                                    aria-checked={ch.enabled}
                                    aria-label={`Channel ${ch.channel_type}`}
                                    onClick={() => toggleChannel(ch.id, ch.enabled)}
                                    disabled={locked}
                                    title={locked ? lockReason() : undefined}
                                >
                                    {ch.enabled ? 'Aktif' : 'Nonaktif'}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => testChannel(ch.id)}
                                    disabled={locked || testing === ch.id}
                                    title={locked ? lockReason() : undefined}
                                >
                                    <Send className="w-4 h-4 mr-1.5" aria-hidden="true" />
                                    {testing === ch.id ? 'Mengirim...' : 'Kirim tes'}
                                </Button>
                                <Button variant="ghost" size="icon" aria-label={`Hapus channel ${ch.channel_type}`} onClick={() => deleteChannel(ch.id)} disabled={locked} title={locked ? lockReason() : undefined}>
                                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" aria-hidden="true" />
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Add new channel */}
            <div className="border rounded-lg p-4 space-y-3 bg-muted/50">
                <h3 id="add-channel-label" className="font-medium text-sm">Tambah channel baru</h3>
                <div className="flex gap-2 flex-wrap" role="group" aria-labelledby="add-channel-label">
                    {Object.keys(CHANNEL_FIELDS).map(type => (
                        <button
                            key={type}
                            type="button"
                            aria-pressed={addType === type}
                            onClick={() => { setAddType(type); setAddConfig({}); }}
                            className={`min-h-11 md:min-h-9 text-sm px-4 rounded-md border capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${
                                addType === type
                                    ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white'
                                    : 'bg-card border-input hover:bg-accent'
                            }`}
                        >
                            {type}
                        </button>
                    ))}
                </div>
                <div className="space-y-2">
                    {fields.map(f => (
                        <div key={f.key}>
                            <label htmlFor={`channel-${f.key}`} className="text-sm font-medium">{f.label}</label>
                            <Input
                                id={`channel-${f.key}`}
                                type={f.type ?? 'text'}
                                placeholder={f.placeholder}
                                value={addConfig[f.key] ?? ''}
                                onChange={e => setAddConfig(c => ({ ...c, [f.key]: e.target.value }))}
                            />
                        </div>
                    ))}
                </div>
                <Button onClick={addChannel} disabled={locked || saving} className="w-full" title={locked ? lockReason() : undefined}>
                    <Plus className="w-4 h-4 mr-2" />
                    {saving ? 'Menyimpan...' : `Tambah channel ${addType}`}
                </Button>
            </div>
        </div>
    );
};

// ─── Config Tab ───────────────────────────────────────────────────────────────

type ConfigField = {
    key: string;
    label: string;
    hint?: string;
    type?: string;
    placeholder?: string;
    readOnly?: boolean;
    options?: { value: string; label: string }[];
};

const YES_NO = [{ value: 'true', label: 'Ya' }, { value: 'false', label: 'Tidak' }];

const CONFIG_FIELDS: ConfigField[] = [
    { key: 'poll_interval', label: 'Jeda pengecekan (detik)', type: 'number', placeholder: '300', hint: 'Seberapa sering peringatan BMKG dicek. 300 berarti tiap 5 menit.' },
    { key: 'severity_threshold', label: 'Tingkat peringatan minimum', hint: 'Peringatan di bawah tingkat ini tidak dicatat dan tidak dikirim.', options: [
        { value: 'all', label: 'Semua tingkat' },
        { value: 'minor', label: 'Ringan ke atas' },
        { value: 'moderate', label: 'Sedang ke atas' },
        { value: 'severe', label: 'Berat ke atas' },
        { value: 'extreme', label: 'Hanya ekstrem' },
    ] },
    { key: 'quiet_hours_enabled', label: 'Aktifkan jam tenang', hint: 'Selama jam tenang notifikasi tidak dikirim.', options: YES_NO },
    { key: 'quiet_hours_start', label: 'Jam tenang mulai', type: 'time', hint: 'Mengikuti zona waktu server (variabel TZ).' },
    { key: 'quiet_hours_end', label: 'Jam tenang selesai', type: 'time' },
    { key: 'quiet_hours_override_severe', label: 'Tetap kirim peringatan berat dan ekstrem saat jam tenang', options: YES_NO },
    { key: 'bmkg_api_url', label: 'URL API BMKG', placeholder: 'https://bmkg-api.dhanypedia.com', readOnly: true, hint: 'Diatur lewat variabel BMKG_API_URL di server.' },
];

const ConfigTab: React.FC<{ locked: boolean }> = ({ locked }) => {
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
                toast.success('Konfigurasi diimpor');
                window.location.reload();
            } catch { toast.error('Gagal mengimpor. Pastikan berkasnya hasil Ekspor JSON dari aplikasi ini.'); }
        };
        input.click();
    };

    if (loading) return <div className="py-4 text-center text-sm text-muted-foreground">Memuat konfigurasi...</div>;

    return (
        <div className="space-y-4">
            {CONFIG_FIELDS.map(f => (
                <div key={f.key} className="space-y-1">
                    <label htmlFor={`config-${f.key}`} className="text-sm font-medium block">{f.label}</label>
                    {f.readOnly ? (
                        <output id={`config-${f.key}`} className="block px-3 py-2 rounded-md border bg-muted text-sm font-mono break-all select-all">
                            {config[f.key] ?? f.placeholder}
                        </output>
                    ) : f.options ? (
                        <select
                            id={`config-${f.key}`}
                            value={config[f.key] ?? f.options[0].value}
                            onChange={e => setConfig(c => ({ ...c, [f.key]: e.target.value }))}
                            disabled={locked}
                            className="flex h-11 md:h-10 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                    ) : (
                        <Input
                            id={`config-${f.key}`}
                            type={f.type ?? 'text'}
                            min={f.key === 'poll_interval' ? 60 : undefined}
                            placeholder={f.placeholder}
                            value={config[f.key] ?? ''}
                            onChange={e => setConfig(c => ({ ...c, [f.key]: e.target.value }))}
                            disabled={locked}
                        />
                    )}
                    {f.hint && <p className="text-xs text-muted-foreground">{f.hint}</p>}
                </div>
            ))}
            <Button onClick={save} disabled={locked || saving} className="w-full mt-2" title={locked ? lockReason() : undefined}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Menyimpan...' : 'Simpan konfigurasi'}
            </Button>
            <div className="flex gap-2 pt-4 border-t">
                <Button variant="outline" onClick={exportConfig} className="flex-1" disabled={locked} title={locked ? lockReason() : undefined}>
                    <Download className="w-4 h-4 mr-2" aria-hidden="true" /> Ekspor JSON
                </Button>
                <Button variant="outline" onClick={importConfig} className="flex-1" disabled={locked} title={locked ? lockReason() : undefined}>
                    <Upload className="w-4 h-4 mr-2" aria-hidden="true" /> Impor JSON
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
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        Promise.all([
            api.get<any>('/engine/status'),
            api.get<any>('/alerts/stats'),
            api.get<{ data: Record<string, string> }>('/config'),
        ]).then(([eng, stats, cfg]) => {
            setEngStatus(eng);
            setAlertStats(stats);
            setVersion(cfg.data?.app_version ?? '1.0.0');
        }).catch(() => setFailed(true))
          .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="py-4 text-center text-sm text-muted-foreground">Memuat info sistem...</div>;
    if (failed) return <div className="py-4 text-center text-sm text-muted-foreground">Info sistem tidak bisa dimuat. Server tidak merespons, coba muat ulang halaman.</div>;

    const rows = [
        { label: 'Versi aplikasi', value: version },
        { label: 'Mode', value: engStatus?.demo_mode ? 'Demo' : 'Produksi' },
        { label: 'Pemantauan', value: engStatus?.running ? 'Aktif' : 'Berhenti' },
        { label: 'Cek terakhir', value: fmtDateTime(engStatus?.last_poll) },
        { label: 'Hasil cek terakhir', value: engStatus?.last_poll_result ?? '-' },
        { label: 'Total peringatan tercatat', value: alertStats?.total_alerts ?? '-' },
        { label: 'Peringatan bulan ini', value: alertStats?.alerts_this_month ?? '-' },
        { label: 'Lokasi dipantau', value: alertStats?.monitored_locations ?? '-' },
        { label: 'Channel aktif', value: alertStats?.active_channels ?? '-' },
    ];

    return (
        <div className="space-y-2">
            {rows.map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-2 border-b last:border-0 text-sm gap-4">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-medium text-right break-words min-w-0">{String(value)}</span>
                </div>
            ))}
        </div>
    );
};

// ─── Main SettingsForm ────────────────────────────────────────────────────────

export const SettingsForm: React.FC = () => {
    const status = useStore(engineStatus);
    const admin = useStore(isAdmin);
    const locked = status.write_locked && !admin;

    useEffect(() => { fetchEngineStatus(); }, []);

    return (
        <div className="w-full max-w-4xl mx-auto pb-10 space-y-6">
            <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Pengaturan</h1>
                <p className="text-muted-foreground">Lokasi yang dipantau, channel notifikasi, dan jadwal pengecekan.</p>
            </div>
            {status.write_locked && (locked || !status.demo_mode) && (
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-700 text-amber-800 dark:text-amber-200 text-sm">
                    <div className="flex items-center gap-2">
                        <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
                        <span>
                            {status.demo_mode && <><strong>Mode demo.</strong> Pengaturan tidak bisa diubah di sini. Pasang instance sendiri untuk memakai semua fitur.</>}
                            {!status.demo_mode && !admin && <><strong>Pengaturan terkunci.</strong> Masuk sebagai admin untuk mengubahnya.</>}
                            {!status.demo_mode && admin && <>Anda masuk sebagai admin.</>}
                        </span>
                    </div>
                    {!status.demo_mode && <AdminLogin expanded idPrefix="settings-admin" />}
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
                            <CardTitle className="text-lg">Lokasi yang dipantau</CardTitle>
                            <CardDescription>
                                Tambahkan kecamatan atau kabupaten/kota yang ingin dipantau. Setiap peringatan BMKG dicocokkan dengan daftar ini.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <LocationsTab locked={locked} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="channels">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Channel notifikasi</CardTitle>
                            <CardDescription>
                                Tujuan pengiriman peringatan: Telegram, Discord, Slack, email, atau webhook.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ChannelsTab locked={locked} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="config">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Konfigurasi</CardTitle>
                            <CardDescription>
                                Jeda pengecekan, tingkat minimum, jam tenang, serta ekspor dan impor konfigurasi.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ConfigTab locked={locked} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="system">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">Informasi sistem</CardTitle>
                            <CardDescription>
                                Status pemantauan dan jumlah peringatan yang tercatat.
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
