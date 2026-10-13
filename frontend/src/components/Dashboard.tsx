import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { toast } from 'sonner';
import {
    engineStatus, engineState, activeAlerts, alertsState, isAdmin,
    fetchEngineStatus, fetchActiveAlerts, lockReason,
} from '@/stores/appStore';
import type { Alert } from '@/stores/appStore';
import { AlertTriangle, CalendarDays, Clock, ExternalLink, Info, MapPin, RefreshCw, X } from 'lucide-react';
import { AdminLogin } from '@/components/AdminLogin';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { WarningMap } from '@/components/WarningMap';
import { EventIcon } from '@/components/EventIcon';
import { api } from '@/lib/api';
import { severityStyle } from '@/lib/severity';
import { certaintyLabel, fmtDateTime, fmtRelative, fmtTime, urgencyLabel } from '@/lib/format';

type EarthquakeEvent = {
    datetime: string;
    magnitude: number;
    depth_km: number;
    region: string;
    tsunami_potential: string | null;
    felt_report: string | null;
};

type FeedState = 'loading' | 'ready' | 'error';

const DEFAULT_POLL_INTERVAL_SEC = 300;

// BMKG writes "Tidak berpotensi tsunami" for the common case, so "berpotensi" alone is not enough
const hasTsunamiPotential = (text: string | null) => {
    const t = (text ?? '').toLowerCase();
    return t.includes('berpotensi') && !t.includes('tidak');
};

/** Ticks on its own so the rest of the dashboard (and the map) does not re-render every second. */
const NextPollCountdown: React.FC<{ lastPoll: string; intervalSec: number }> = ({ lastPoll, intervalSec }) => {
    const [now, setNow] = useState(Date.now());

    useEffect(() => {
        const ticker = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(ticker);
    }, []);

    const remaining = intervalSec - Math.floor((now - new Date(lastPoll).getTime()) / 1000);
    const text =
        remaining <= 0 ? 'sebentar lagi'
        : remaining >= 60 ? `${Math.floor(remaining / 60)} mnt ${String(remaining % 60).padStart(2, '0')} dtk`
        : `${remaining} dtk`;

    return (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-3 py-2 border rounded-lg bg-card">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Cek berikutnya: {text}</span>
        </div>
    );
};

export const Dashboard: React.FC = () => {
    const status = useStore(engineStatus);
    const statusState = useStore(engineState);
    const alerts = useStore(activeAlerts);
    const alertsLoad = useStore(alertsState);
    const admin = useStore(isAdmin);
    const [eqFeed, setEqFeed] = useState<EarthquakeEvent[]>([]);
    const [eqState, setEqState] = useState<FeedState>('loading');
    const [checkingNow, setCheckingNow] = useState(false);
    const [locationCount, setLocationCount] = useState<number | null>(null);
    const [alertStats, setAlertStats] = useState<{ total_alerts: number; alerts_this_month: number } | null>(null);
    const [pollIntervalSec, setPollIntervalSec] = useState(DEFAULT_POLL_INTERVAL_SEC);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

    const fetchEventFeed = useCallback(async () => {
        const [recentRes, feltRes] = await Promise.allSettled([
            api.get<{ data: EarthquakeEvent[] }>('/earthquake/recent'),
            api.get<{ data: EarthquakeEvent[] }>('/earthquake/felt'),
        ]);

        if (recentRes.status === 'rejected' && feltRes.status === 'rejected') {
            setEqState('error');
            return;
        }

        const recent = recentRes.status === 'fulfilled' ? (recentRes.value.data ?? []) : [];
        const felt = feltRes.status === 'fulfilled' ? (feltRes.value.data ?? []) : [];

        // Merge both lists, deduplicate by datetime+region, newest first
        const seen = new Set<string>();
        const merged = [...recent, ...felt]
            .filter(eq => {
                const key = `${eq.datetime}|${eq.region}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            })
            .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime())
            .slice(0, 5);

        setEqFeed(merged);
        setEqState('ready');
    }, []);

    const fetchStats = useCallback(async () => {
        try {
            const [locRes, statsRes] = await Promise.all([
                api.get<{ data: { id: number; enabled: boolean }[] }>('/locations'),
                api.get<{ total_alerts: number; alerts_this_month: number }>('/alerts/stats'),
            ]);
            setLocationCount((locRes.data ?? []).filter(l => l.enabled).length);
            setAlertStats(statsRes);
        } catch (e) {
            console.error('Failed to fetch dashboard stats', e);
        }
    }, []);

    useEffect(() => {
        const refresh = () => {
            fetchEngineStatus();
            fetchActiveAlerts();
            fetchEventFeed();
            fetchStats();
        };
        refresh();
        const interval = setInterval(refresh, 30000);
        return () => clearInterval(interval);
    }, [fetchEventFeed, fetchStats]);

    // The countdown has to follow the interval the engine really uses
    useEffect(() => {
        api.get<{ data: Record<string, string> }>('/config')
            .then(res => {
                const seconds = parseInt(res.data?.poll_interval ?? '', 10);
                if (seconds > 0) setPollIntervalSec(seconds);
            })
            .catch(() => { /* keep the default interval */ });
    }, []);

    const closeModal = useCallback(() => setSelectedAlert(null), []);

    const locked = status.write_locked && !admin;

    const toggleEngine = async () => {
        try {
            if (status.running) {
                await api.post('/engine/stop', {});
                toast.info('Pemantauan dihentikan');
            } else {
                await api.post('/engine/start', {});
                toast.success('Pemantauan dimulai');
            }
            setTimeout(fetchEngineStatus, 600);
        } catch (e) {
            console.error(e);
            toast.error('Status pemantauan gagal diubah');
        }
    };

    const checkNow = async () => {
        setCheckingNow(true);
        try {
            await api.post('/engine/check-now', {});
            toast.success('Pengecekan selesai');
            fetchEngineStatus();
            fetchActiveAlerts();
            fetchStats();
        } catch (e) {
            console.error(e);
            toast.error('Pengecekan gagal dijalankan');
        } finally {
            setCheckingNow(false);
        }
    };

    // The province after the last " di " is what tells near-identical headlines apart
    const highlightRegion = (text: string) => {
        const idx = text.lastIndexOf(' di ');
        if (idx === -1) return <>{text}</>;
        return (
            <>
                {text.slice(0, idx + 4)}
                <span className="font-semibold text-amber-700 dark:text-amber-400">{text.slice(idx + 4)}</span>
            </>
        );
    };

    const engineLabel =
        statusState === 'loading' ? 'Memeriksa status...'
        : statusState === 'error' ? 'Server tidak merespons'
        : status.running ? 'Pemantauan aktif' : 'Pemantauan berhenti';
    const engineDot =
        statusState !== 'ready' ? 'bg-slate-400'
        : status.running ? 'bg-green-600' : 'bg-red-600';

    return (
        <>
        <div className="flex flex-col flex-1 gap-6">
            {status.write_locked && (
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950 dark:border-amber-700 text-amber-800 dark:text-amber-200 text-sm">
                    <div className="flex items-center gap-2">
                        <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
                        <span>
                            {status.demo_mode && admin && <><strong>Mode demo (admin).</strong> Anda masuk sebagai admin, semua fitur aktif.</>}
                            {status.demo_mode && !admin && <><strong>Mode demo.</strong> Anda melihat demo langsung, pengaturan tidak bisa diubah.</>}
                            {!status.demo_mode && admin && <>Anda masuk sebagai admin.</>}
                            {!status.demo_mode && !admin && <><strong>Pengaturan terkunci.</strong> Masuk sebagai admin untuk mengubah pengaturan atau menjalankan pengecekan.</>}
                        </span>
                    </div>
                    <AdminLogin idPrefix="dashboard-admin" />
                </div>
            )}

            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Dasbor</h1>
                    <p className="text-muted-foreground">
                        Peringatan dini cuaca BMKG, dicek tiap {Math.round(pollIntervalSec / 60)} menit.
                    </p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-2 px-4 py-2 bg-card rounded-lg border" role="status">
                        <span className={`w-3 h-3 rounded-full ${engineDot}`} aria-hidden="true" />
                        <span className="font-medium text-sm">{engineLabel}</span>
                    </div>
                    {status.running && status.last_poll && (
                        <NextPollCountdown lastPoll={status.last_poll} intervalSec={pollIntervalSec} />
                    )}
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={checkNow}
                        disabled={locked || checkingNow || !status.running}
                        title={locked ? lockReason() : 'Cek peringatan BMKG tanpa menunggu jadwal'}
                    >
                        <RefreshCw className={`w-4 h-4 mr-1.5 ${checkingNow ? 'animate-spin' : ''}`} aria-hidden="true" />
                        {checkingNow ? 'Mengecek...' : 'Cek sekarang'}
                    </Button>
                    <Button
                        variant={status.running ? 'destructive' : 'default'}
                        onClick={toggleEngine}
                        disabled={locked || statusState !== 'ready'}
                        title={locked ? lockReason() : undefined}
                    >
                        {status.running ? 'Hentikan pemantauan' : 'Mulai pemantauan'}
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Peringatan aktif</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{alertsLoad === 'loading' ? '-' : alerts.length}</div>
                        <p className="text-xs text-muted-foreground">Seluruh Indonesia, dari BMKG Nowcast</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Cek terakhir</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{fmtTime(status.last_poll)}</div>
                        <p className="text-xs text-muted-foreground truncate" title={status.last_poll_result || undefined}>
                            {status.last_poll_result || 'Belum ada pengecekan'}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Lokasi dipantau</CardTitle>
                        <MapPin className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{locationCount ?? '-'}</div>
                        <p className="text-xs text-muted-foreground">
                            {locationCount === 0
                                ? <a href="/settings" className="underline underline-offset-2 text-blue-600 dark:text-blue-400">Tambah lokasi di Pengaturan</a>
                                : 'Kecamatan atau kabupaten/kota aktif'}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Peringatan bulan ini</CardTitle>
                        <CalendarDays className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{alertStats?.alerts_this_month ?? '-'}</div>
                        <p className="text-xs text-muted-foreground">
                            Untuk lokasi Anda. Total tercatat: {alertStats?.total_alerts ?? '-'}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,3fr)] lg:min-h-[36rem] flex-1">
                <Card className="flex flex-col overflow-hidden min-w-0">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">Peta peringatan</CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 p-0 min-h-[20rem]">
                        <WarningMap alerts={alerts} className="h-full w-full min-h-[20rem]" />
                    </CardContent>
                </Card>

                <div className="flex flex-col gap-4 min-h-0 min-w-0">
                    <Card className="flex-1 flex flex-col min-h-[18rem] lg:min-h-0">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base">Peringatan aktif</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 min-h-0 overflow-y-auto">
                            {alertsLoad === 'error' && alerts.length > 0 && (
                                <p className="mb-3 text-xs text-amber-800 dark:text-amber-200" role="status">
                                    Gagal memperbarui. Daftar di bawah adalah data terakhir yang berhasil dimuat.
                                </p>
                            )}
                            {alerts.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full min-h-[10rem] text-center text-sm text-muted-foreground">
                                    {alertsLoad === 'loading' && <p>Memuat peringatan dari BMKG...</p>}
                                    {alertsLoad === 'error' && (
                                        <>
                                            <p className="mb-3">Peringatan tidak bisa dimuat. Server tidak merespons.</p>
                                            <Button variant="outline" size="sm" onClick={fetchActiveAlerts}>Coba lagi</Button>
                                        </>
                                    )}
                                    {alertsLoad === 'ready' && <p>BMKG tidak mengeluarkan peringatan dini saat ini.</p>}
                                </div>
                            ) : (
                                <ul className="space-y-1">
                                    {alerts.map(alert => {
                                        const sev = severityStyle(alert.severity);
                                        return (
                                            <li key={alert.identifier}>
                                                <button
                                                    type="button"
                                                    onClick={() => setSelectedAlert(alert)}
                                                    className="w-full flex items-start gap-3 text-left rounded-lg p-2 -mx-2 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                                >
                                                    <EventIcon event={alert.event} className="h-5 w-5 shrink-0 mt-0.5 text-muted-foreground" />
                                                    <span className="flex-1 min-w-0">
                                                        <span className="flex items-center gap-2 flex-wrap">
                                                            <span className="font-semibold text-sm">{alert.event || 'Peringatan cuaca'}</span>
                                                            <span className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-semibold ${sev.badge}`}>
                                                                {sev.label}
                                                            </span>
                                                        </span>
                                                        <span className="block text-xs text-muted-foreground line-clamp-2 mt-0.5">
                                                            {highlightRegion(alert.headline || alert.description)}
                                                        </span>
                                                        <span className="block text-xs text-muted-foreground mt-0.5">
                                                            Berakhir {fmtDateTime(alert.expires)}
                                                        </span>
                                                    </span>
                                                </button>
                                            </li>
                                        );
                                    })}
                                </ul>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-base">Gempa terkini</CardTitle>
                            <Button variant="ghost" size="sm" onClick={fetchEventFeed}>
                                <RefreshCw className="w-4 h-4 mr-1.5" aria-hidden="true" /> Muat ulang
                            </Button>
                        </CardHeader>
                        <CardContent>
                            {eqFeed.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">
                                    {eqState === 'loading' && 'Memuat data gempa BMKG...'}
                                    {eqState === 'error' && 'Data gempa tidak bisa dimuat. Tekan Muat ulang untuk mencoba lagi.'}
                                    {eqState === 'ready' && 'BMKG belum mencatat gempa baru.'}
                                </p>
                            ) : (
                                <ul className="space-y-3">
                                    {eqFeed.map(eq => (
                                        <li key={`${eq.datetime}|${eq.region}`} className="flex items-start gap-3">
                                            <span className="shrink-0 w-11 text-sm font-bold tabular-nums">
                                                M {eq.magnitude.toFixed(1)}
                                            </span>
                                            <div className="flex-1 min-w-0 text-xs">
                                                <p className="text-sm truncate" title={eq.region}>{eq.region}</p>
                                                {eq.felt_report && (
                                                    <p className="text-muted-foreground truncate" title={eq.felt_report}>Dirasakan: {eq.felt_report}</p>
                                                )}
                                                <p className="text-muted-foreground flex items-center gap-2 flex-wrap mt-0.5">
                                                    <span>{fmtRelative(eq.datetime)}</span>
                                                    {hasTsunamiPotential(eq.tsunami_potential) && (
                                                        <span className="px-1.5 py-0.5 rounded font-semibold bg-red-600 text-white">Berpotensi tsunami</span>
                                                    )}
                                                </p>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>

        {selectedAlert && <AlertModal alert={selectedAlert} onClose={closeModal} />}
        </>
    );
};

const AlertModal: React.FC<{ alert: Alert; onClose: () => void }> = ({ alert, onClose }) => {
    const sev = severityStyle(alert.severity);
    const [imgError, setImgError] = useState(false);
    const dialogRef = useRef<HTMLDivElement>(null);
    const closeRef = useRef<HTMLButtonElement>(null);

    // Move focus into the dialog, keep Tab inside it, and hand focus back on close
    useEffect(() => {
        const previouslyFocused = document.activeElement as HTMLElement | null;
        closeRef.current?.focus();

        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') { onClose(); return; }
            if (e.key !== 'Tab' || !dialogRef.current) return;
            const focusable = dialogRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
            if (focusable.length === 0) return;
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
            else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
        };
        document.addEventListener('keydown', handler);
        return () => {
            document.removeEventListener('keydown', handler);
            previouslyFocused?.focus();
        };
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
            onClick={e => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="alert-modal-title"
                className="bg-card text-card-foreground rounded-lg shadow-xl w-full max-w-2xl max-h-[90dvh] flex flex-col overflow-hidden"
            >
                <div className="flex items-start justify-between gap-3 p-5 border-b">
                    <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-2">
                            <span className={`text-xs font-semibold px-2 py-1 rounded ${sev.badge}`}>{sev.label}</span>
                            <span className="text-xs text-muted-foreground border rounded px-2 py-1">{urgencyLabel(alert.urgency)}</span>
                            <span className="text-xs text-muted-foreground border rounded px-2 py-1">{certaintyLabel(alert.certainty)}</span>
                        </div>
                        <h2 id="alert-modal-title" className="text-lg font-bold leading-tight">{alert.event || 'Peringatan cuaca'}</h2>
                        <p className="text-sm text-muted-foreground mt-0.5">{alert.headline}</p>
                    </div>
                    <Button ref={closeRef} variant="ghost" size="icon" onClick={onClose} aria-label="Tutup" className="shrink-0">
                        <X className="h-5 w-5" aria-hidden="true" />
                    </Button>
                </div>

                <div className="overflow-y-auto flex-1 p-5 space-y-5">
                    <dl className="grid sm:grid-cols-2 gap-3 text-sm">
                        <div className="rounded-lg bg-muted p-3">
                            <dt className="text-xs font-medium text-muted-foreground mb-1">Berlaku mulai</dt>
                            <dd className="font-semibold">{fmtDateTime(alert.effective, 'long')}</dd>
                        </div>
                        <div className="rounded-lg bg-muted p-3">
                            <dt className="text-xs font-medium text-muted-foreground mb-1">Berakhir</dt>
                            <dd className="font-semibold">{fmtDateTime(alert.expires, 'long')}</dd>
                        </div>
                    </dl>

                    <div>
                        <h3 className="text-sm font-semibold mb-2">Deskripsi</h3>
                        <p className="text-sm leading-relaxed whitespace-pre-line">{alert.description || '-'}</p>
                    </div>

                    {alert.areas && alert.areas.length > 0 && (
                        <div>
                            <h3 className="text-sm font-semibold mb-2">Wilayah terdampak</h3>
                            <ul className="flex flex-wrap gap-1.5">
                                {alert.areas.map((area, i) => (
                                    <li key={`${area.name}-${i}`} className="text-xs border rounded px-2 py-1">{area.name}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {alert.infographic_url && (
                        <div>
                            <h3 className="text-sm font-semibold mb-2">Infografis BMKG</h3>
                            <a
                                href={alert.infographic_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block rounded-lg text-sm text-blue-600 dark:text-blue-400 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                {!imgError && (
                                    <img
                                        src={alert.infographic_url}
                                        alt={`Infografis BMKG: ${alert.headline}`}
                                        className="rounded-lg w-full border mb-2"
                                        onError={() => setImgError(true)}
                                    />
                                )}
                                <span className="inline-flex items-center gap-1.5">
                                    <ExternalLink className="h-4 w-4" aria-hidden="true" />
                                    {imgError ? 'Gambar gagal dimuat. Buka infografis di situs BMKG' : 'Buka infografis di tab baru'}
                                </span>
                            </a>
                        </div>
                    )}

                    <p className="text-xs text-muted-foreground">Sumber: {alert.sender}</p>
                </div>
            </div>
        </div>
    );
};
