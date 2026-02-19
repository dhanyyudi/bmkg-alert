import React, { useEffect, useState, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { toast } from 'sonner';
import { engineStatus, activeAlerts, isAdmin, adminLogin, adminLogout, fetchEngineStatus, fetchActiveAlerts } from '@/stores/appStore';
import type { Alert } from '@/stores/appStore';
import { Activity, Radio, AlertTriangle, CloudRain, Zap, Clock, X, MapPin, Calendar, Info, Lock, LogOut } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { WarningMap } from '@/components/WarningMap';
import { api } from '@/lib/api';

type EarthquakeEvent = {
    datetime: string;
    magnitude: number;
    depth_km: number;
    region: string;
    tsunami_potential: string | null;
    felt_report: string | null;
};

// Formats a UTC ISO string as WIB time (Asia/Jakarta, UTC+7)
const fmtTime = (iso: string | null) => {
    if (!iso) return '-';
    try {
        return new Date(iso).toLocaleTimeString('id-ID', {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            timeZone: 'Asia/Jakarta',
        }) + ' WIB';
    }
    catch { return iso; }
};

const normalizeUtc = (iso: string) =>
    /Z$|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso.replace(' ', 'T') + 'Z';

const fmtRelative = (iso: string | null) => {
    if (!iso) return '-';
    try {
        const diff = Math.floor((Date.now() - new Date(normalizeUtc(iso)).getTime()) / 1000);
        if (diff < 60) return `${diff}d lalu`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m lalu`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}j lalu`;
        return `${Math.floor(diff / 86400)}h lalu`;
    } catch { return '-'; }
};

export const Dashboard: React.FC = () => {
    const status = useStore(engineStatus);
    const alerts = useStore(activeAlerts);
    const admin = useStore(isAdmin);
    const [eqFeed, setEqFeed] = useState<EarthquakeEvent[]>([]);
    const [checkingNow, setCheckingNow] = useState(false);
    const [showAdminLogin, setShowAdminLogin] = useState(false);
    const [adminPw, setAdminPw] = useState('');
    const [locationCount, setLocationCount] = useState<number>(0);
    const [alertStats, setAlertStats] = useState<{ total_alerts: number; alerts_this_month: number } | null>(null);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
    const [now, setNow] = useState(Date.now());

    const fetchEventFeed = useCallback(async () => {
        try {
            const [recentRes, feltRes] = await Promise.allSettled([
                api.get<{ data: EarthquakeEvent[] }>('/earthquake/recent'),
                api.get<{ data: EarthquakeEvent[] }>('/earthquake/felt'),
            ]);

            const recent: EarthquakeEvent[] = recentRes.status === 'fulfilled' ? (recentRes.value.data ?? []) : [];
            const felt: EarthquakeEvent[] = feltRes.status === 'fulfilled' ? (feltRes.value.data ?? []) : [];

            // Merge both lists, deduplicate by datetime+region, sort newest first
            const seen = new Set<string>();
            const merged = [...recent, ...felt]
                .filter(eq => {
                    const key = `${eq.datetime}|${eq.region}`;
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                })
                .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime())
                .slice(0, 6);

            setEqFeed(merged);
        } catch { /* silent */ }
    }, []);

    const fetchStats = useCallback(async () => {
        try {
            const [locRes, statsRes] = await Promise.all([
                api.get<{ data: { id: number }[] }>('/locations'),
                api.get<{ total_alerts: number; alerts_this_month: number }>('/alerts/stats'),
            ]);
            setLocationCount((locRes.data ?? []).filter((l: any) => l.enabled).length);
            setAlertStats(statsRes);
        } catch { /* silent */ }
    }, []);

    useEffect(() => {
        fetchEngineStatus();
        fetchActiveAlerts();
        fetchEventFeed();
        fetchStats();
        const interval = setInterval(() => {
            fetchEngineStatus();
            fetchActiveAlerts();
            fetchEventFeed();
            fetchStats();
        }, 30000);
        return () => clearInterval(interval);
    }, [fetchEventFeed, fetchStats]);

    // Tick every second for real-time countdown
    useEffect(() => {
        const ticker = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(ticker);
    }, []);

    const demoMode = status.demo_mode && !admin;
    const demoTooltip = 'Demo mode — deploy instance sendiri untuk mengkonfigurasi';

    const handleAdminLogin = async () => {
        const ok = await adminLogin(adminPw);
        if (ok) {
            toast.success('Admin login berhasil');
            setShowAdminLogin(false);
            setAdminPw('');
        } else {
            toast.error('Password salah');
        }
    };

    const handleAdminLogout = () => {
        adminLogout();
        toast.info('Admin logout');
    };

    const toggleEngine = async () => {
        if (demoMode) { toast.error(demoTooltip); return; }
        try {
            if (status.running) {
                await api.post('/engine/stop', {});
                toast.info('Engine berhenti...');
            } else {
                await api.post('/engine/start', {});
                toast.success('Engine dimulai');
            }
            setTimeout(fetchEngineStatus, 600);
        } catch (e) {
            console.error(e);
            toast.error('Gagal mengubah status engine');
        }
    };

    const checkNow = async () => {
        if (demoMode) { toast.error(demoTooltip); return; }
        setCheckingNow(true);
        try {
            await api.post('/engine/check-now', {});
            toast.success('Poll manual selesai');
            setTimeout(() => {
                fetchEngineStatus();
                fetchActiveAlerts();
                fetchEventFeed();
            }, 500);
        } catch (e) {
            console.error(e);
            toast.error('Gagal menjalankan poll manual');
        } finally {
            setCheckingNow(false);
        }
    };

    // Real-time countdown — recalculates every second via `now` state
    const nextPollIn = (() => {
        if (!status.last_poll || !status.running) return null;
        const elapsed = Math.floor((now - new Date(status.last_poll).getTime()) / 1000);
        const remaining = 300 - elapsed;
        if (remaining <= 0) return 'Sekarang';
        const m = Math.floor(remaining / 60);
        const s = remaining % 60;
        return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`;
    })();

    // Map BMKG event name to a weather emoji icon
    const getWeatherIcon = (event: string) => {
        const e = (event ?? '').toLowerCase();
        if (e.includes('petir') || e.includes('thunder')) return '⛈️';
        if (e.includes('angin') || e.includes('puting beliung')) return '💨';
        if (e.includes('gelombang') || e.includes('banjir')) return '🌊';
        return '🌧️';
    };

    // Highlight province/region name after the last " di " in a headline string
    const highlightRegion = (text: string) => {
        const idx = text.lastIndexOf(' di ');
        if (idx === -1) return <>{text}</>;
        return (
            <>
                {text.slice(0, idx + 4)}
                <span className="font-semibold text-amber-600 dark:text-amber-400">{text.slice(idx + 4)}</span>
            </>
        );
    };

    return (
        <>
        <div className="flex flex-col flex-1 min-h-0 gap-6">
            {/* Demo Mode Banner */}
            {status.demo_mode && (
                <div className="flex items-center justify-between gap-2 px-4 py-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-700 text-amber-800 dark:text-amber-200 text-sm">
                    <div className="flex items-center gap-2">
                        <Info className="w-4 h-4 shrink-0" />
                        <span>
                            {admin ? (
                                <><strong>Demo Mode (Admin)</strong> — Anda login sebagai admin, semua fitur aktif.</>
                            ) : (
                                <><strong>Demo Mode</strong> — Anda melihat live demo. Fitur konfigurasi dinonaktifkan.</>
                            )}
                        </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                        {admin ? (
                            <Button variant="outline" size="sm" onClick={handleAdminLogout} className="text-xs h-7">
                                <LogOut className="w-3 h-3 mr-1" /> Logout
                            </Button>
                        ) : showAdminLogin ? (
                            <div className="flex items-center gap-1">
                                <Input
                                    type="password"
                                    placeholder="Admin password"
                                    value={adminPw}
                                    onChange={e => setAdminPw(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleAdminLogin()}
                                    className="h-7 w-40 text-xs"
                                />
                                <Button size="sm" onClick={handleAdminLogin} className="text-xs h-7">Login</Button>
                                <Button variant="ghost" size="sm" onClick={() => { setShowAdminLogin(false); setAdminPw(''); }} className="text-xs h-7">
                                    <X className="w-3 h-3" />
                                </Button>
                            </div>
                        ) : (
                            <Button variant="outline" size="sm" onClick={() => setShowAdminLogin(true)} className="text-xs h-7">
                                <Lock className="w-3 h-3 mr-1" /> Admin
                            </Button>
                        )}
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
                    <p className="text-muted-foreground text-slate-500">Monitoring peringatan cuaca dini BMKG real-time.</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    {/* Engine indicator */}
                    <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 rounded-lg border shadow-sm">
                        <div className={`w-3 h-3 rounded-full ${status.running ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                        <span className="font-medium text-sm">
                            {status.running ? 'Engine Berjalan' : 'Engine Berhenti'}
                        </span>
                    </div>
                    {/* Next poll */}
                    {nextPollIn && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground px-3 py-2 border rounded-lg bg-white dark:bg-slate-800">
                            <Clock className="w-3 h-3" />
                            <span>Poll berikutnya: {nextPollIn}</span>
                        </div>
                    )}
                    {/* Check Now */}
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={checkNow}
                        disabled={demoMode || checkingNow || !status.running}
                        title={demoMode ? demoTooltip : 'Jalankan poll sekarang'}
                    >
                        <Zap className={`w-4 h-4 mr-1 ${checkingNow ? 'animate-bounce' : ''}`} />
                        {checkingNow ? 'Polling...' : 'Check Now'}
                    </Button>
                    {/* Start/Stop */}
                    <Button
                        variant={status.running ? 'destructive' : 'default'}
                        onClick={toggleEngine}
                        disabled={demoMode}
                        title={demoMode ? demoTooltip : undefined}
                    >
                        {status.running ? 'Stop Engine' : 'Start Engine'}
                    </Button>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Peringatan Aktif</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-orange-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-2xl font-bold">{alerts.length}</span>
                            <span className="text-sm text-muted-foreground font-medium">warnings</span>
                        </div>
                        <p className="text-xs text-muted-foreground">Dari BMKG Nowcast</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Poll Terakhir</CardTitle>
                        <Activity className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-lg font-bold truncate" title={status.last_poll || '-'}>
                            {status.last_poll ? fmtTime(status.last_poll) : '-'}
                        </div>
                        <p className="text-xs text-muted-foreground truncate" title={status.last_poll_result || ''}>
                            {status.last_poll_result || 'Belum ada data'}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Lokasi Dipantau</CardTitle>
                        <Radio className="h-4 w-4 text-purple-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-2xl font-bold">{locationCount}</span>
                            <span className="text-sm text-muted-foreground font-medium">area</span>
                        </div>
                        <p className="text-xs text-muted-foreground">Kecamatan aktif</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Alert Bulan Ini</CardTitle>
                        <CloudRain className="h-4 w-4 text-sky-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-2xl font-bold">{alertStats?.alerts_this_month ?? '-'}</span>
                            <span className="text-sm text-muted-foreground font-medium">alert</span>
                        </div>
                        <p className="text-xs text-muted-foreground">Total: {alertStats?.total_alerts ?? '-'}</p>
                    </CardContent>
                </Card>
            </div>

            {/* Map + Alert List + Activity Feed */}
            <div className="flex-1 min-h-0 grid gap-4 md:grid-cols-[5fr_3fr]">
                {/* Map (5/8) */}
                <div className="flex flex-col min-h-0">
                    <Card className="flex-1 flex flex-col">
                        <CardHeader>
                            <CardTitle>Warning Map</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 min-h-0">
                            <WarningMap alerts={alerts} className="h-full w-full min-h-[300px]" />
                        </CardContent>
                    </Card>
                </div>

                {/* Right column (3/8): Active Alerts + Activity Feed */}
                <div className="flex flex-col gap-4 min-h-0">
                    {/* Active Alerts */}
                    <Card className="flex-1 flex flex-col min-h-0">
                        <CardHeader>
                            <CardTitle>Peringatan Aktif</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 min-h-0 overflow-hidden">
                            <div className="space-y-3 h-full overflow-y-auto pr-1">
                                {alerts.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center h-[200px] text-slate-400">
                                        <CloudRain className="h-10 w-10 mb-2 opacity-20" />
                                        <p className="text-sm">Tidak ada peringatan aktif</p>
                                    </div>
                                ) : (
                                    alerts.map(alert => {
                                        const severityColor: Record<string, string> = {
                                            extreme: 'bg-red-900 text-white',
                                            severe:  'bg-red-500 text-white',
                                            moderate:'bg-amber-500 text-white',
                                            minor:   'bg-blue-500 text-white',
                                        };
                                        const badgeClass = severityColor[alert.severity?.toLowerCase() ?? ''] ?? 'bg-slate-400 text-white';
                                        const expiresDate = alert.expires
                                            ? new Date(alert.expires).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Jakarta' })
                                            : '-';
                                        return (
                                            <div
                                                key={alert.identifier}
                                                className="flex items-start gap-2.5 text-xs cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg p-2 -mx-2 transition-colors"
                                                onClick={() => setSelectedAlert(alert)}
                                            >
                                                <span className="shrink-0 mt-0.5 text-base leading-none">
                                                    {getWeatherIcon(alert.event)}
                                                </span>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-1 flex-wrap mb-0.5">
                                                        <span className="font-semibold text-slate-700 dark:text-slate-200 truncate">
                                                            {alert.event || 'Alert'}
                                                        </span>
                                                        <span className={`shrink-0 px-1 py-0.5 rounded text-[10px] font-bold ${badgeClass}`}>
                                                            {alert.severity}
                                                        </span>
                                                    </div>
                                                    <p className="text-slate-500 line-clamp-2">{highlightRegion(alert.headline || alert.description)}</p>
                                                    <span className="text-slate-400 mt-0.5 block">Berakhir: {expiresDate}</span>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Gempa Terkini */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm">Gempa Terkini</CardTitle>
                            <button onClick={fetchEventFeed} className="text-xs text-muted-foreground hover:text-foreground">
                                ↻ Refresh
                            </button>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2.5">
                                {eqFeed.length === 0 ? (
                                    <p className="text-xs text-muted-foreground text-center py-4">Belum ada data gempa</p>
                                ) : (
                                    eqFeed.map((eq, i) => (
                                        <div key={i} className="flex items-start gap-2 text-xs">
                                            <span className="shrink-0 mt-0.5 text-base leading-none">🌍</span>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-1">
                                                    <span className="font-semibold text-slate-700 dark:text-slate-200">
                                                        M{eq.magnitude.toFixed(1)}
                                                    </span>
                                                    {eq.tsunami_potential?.toLowerCase().includes('berpotensi') && (
                                                        <span className="px-1 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white">Potensi Tsunami</span>
                                                    )}
                                                </div>
                                                <p className="text-slate-500 truncate mt-0.5">{eq.region}</p>
                                                {eq.felt_report && (
                                                    <p className="text-slate-400 truncate">Dirasakan: {eq.felt_report}</p>
                                                )}
                                                <span className="text-slate-400 mt-0.5 block">{fmtRelative(eq.datetime)}</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>

        {/* ── Alert Detail Modal ─────────────────────────────────────────── */}
        {selectedAlert && <AlertModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />}
        </>
    );
};

// ─── Alert Detail Modal ────────────────────────────────────────────────────────

const SEVERITY_LABEL: Record<string, { label: string; cls: string }> = {
    extreme:  { label: 'Ekstrem',  cls: 'bg-red-900 text-white' },
    severe:   { label: 'Berat',    cls: 'bg-red-500 text-white' },
    moderate: { label: 'Sedang',   cls: 'bg-amber-500 text-white' },
    minor:    { label: 'Ringan',   cls: 'bg-blue-500 text-white' },
};

const fmtDateLong = (iso: string | null) => {
    if (!iso) return '-';
    try { return new Date(iso).toLocaleString('id-ID', { dateStyle: 'long', timeStyle: 'short' }); }
    catch { return iso; }
};

const AlertModal: React.FC<{ alert: Alert; onClose: () => void }> = ({ alert, onClose }) => {
    const sev = SEVERITY_LABEL[alert.severity?.toLowerCase() ?? ''] ?? { label: alert.severity, cls: 'bg-slate-400 text-white' };
    const [imgError, setImgError] = useState(false);

    // Close on backdrop click or Escape key
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={e => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">

                {/* Header */}
                <div className="flex items-start justify-between gap-3 p-5 border-b dark:border-slate-700">
                    <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${sev.cls}`}>
                                {sev.label}
                            </span>
                            <span className="text-xs text-slate-500 border rounded-full px-2.5 py-1">
                                {alert.urgency}
                            </span>
                            <span className="text-xs text-slate-500 border rounded-full px-2.5 py-1">
                                {alert.certainty}
                            </span>
                        </div>
                        <h2 className="text-lg font-bold leading-tight">{alert.event || 'Peringatan Cuaca'}</h2>
                        <p className="text-sm text-slate-500 mt-0.5">{alert.headline}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="shrink-0 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 p-1.5 rounded-lg transition-colors"
                        aria-label="Tutup"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="overflow-y-auto flex-1 p-5 space-y-5">

                    {/* Time info */}
                    <div className="grid grid-cols-2 gap-3 text-sm">
                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 space-y-0.5">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-1">
                                <Calendar className="h-3.5 w-3.5" /> Berlaku mulai
                            </div>
                            <p className="font-semibold">{fmtDateLong(alert.effective)}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3 space-y-0.5">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-1">
                                <Clock className="h-3.5 w-3.5" /> Berakhir
                            </div>
                            <p className="font-semibold">{fmtDateLong(alert.expires)}</p>
                        </div>
                    </div>

                    {/* Description */}
                    <div>
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Deskripsi</h3>
                        <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line bg-slate-50 dark:bg-slate-800 rounded-lg p-3">
                            {alert.description || '-'}
                        </p>
                    </div>

                    {/* Affected areas */}
                    {alert.areas && alert.areas.length > 0 && (
                        <div>
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                                <MapPin className="h-3.5 w-3.5" /> Wilayah Terdampak
                            </h3>
                            <div className="flex flex-wrap gap-1.5">
                                {alert.areas.map((area, i) => (
                                    <span key={i} className="text-xs bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-full px-2.5 py-1">
                                        {area.name}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Infographic */}
                    {alert.infographic_url && (
                        <div>
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Infografis BMKG</h3>
                            {!imgError ? (
                                <a href={alert.infographic_url} target="_blank" rel="noopener noreferrer">
                                    <img
                                        src={alert.infographic_url}
                                        alt="Infografis BMKG"
                                        className="rounded-xl w-full border border-slate-200 dark:border-slate-700 hover:opacity-90 transition-opacity"
                                        onError={() => setImgError(true)}
                                    />
                                    <p className="text-xs text-center text-blue-500 mt-1.5 hover:underline">
                                        Klik untuk buka di tab baru ↗
                                    </p>
                                </a>
                            ) : (
                                <a
                                    href={alert.infographic_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-2 p-3 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950 text-sm text-blue-600 hover:underline"
                                >
                                    📊 Buka Infografis BMKG ↗
                                </a>
                            )}
                        </div>
                    )}

                    {/* Sender */}
                    <p className="text-xs text-slate-400 text-right">Sumber: {alert.sender}</p>
                </div>
            </div>
        </div>
    );
};
