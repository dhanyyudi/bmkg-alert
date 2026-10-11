import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Check, Globe, MapPin, Bell, Settings, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { LocationStep } from './setup/LocationStep';
import { ChannelStep } from './setup/ChannelStep';

// Steps definition
const STEPS = [
    { id: 'welcome', title: 'Mulai', icon: Globe },
    { id: 'location', title: 'Lokasi', icon: MapPin },
    { id: 'notifications', title: 'Notifikasi', icon: Bell },
    { id: 'preferences', title: 'Jadwal cek', icon: Settings },
    { id: 'confirm', title: 'Selesai', icon: Check },
];

export const SetupWizard: React.FC = () => {
    const [step, setStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);
    const [config, setConfig] = useState<Record<string, string>>({
        notification_language: 'id',
        poll_interval: '300',
        quiet_hours_enabled: 'false',
    });
    const [locations, setLocations] = useState<any[]>([]);
    const [channelCount, setChannelCount] = useState<number | null>(null);

    const fetchLocations = async () => {
        try {
            const locs = await api.get<{data: any[]}>('/locations');
            setLocations(locs.data);
        } catch (e) {
            console.error(e);
        }
    };

    useEffect(() => {
        // Load initial config
        const load = async () => {
            try {
                const res = await api.get<{data: any}>('/config');
                setConfig(prev => ({ ...prev, ...res.data }));
                fetchLocations();
            } catch (e) {
                console.error("Failed to load initial config", e);
            }
        };
        load();
    }, []);

    // The last step reports what was actually configured, so refresh the counts on arrival
    useEffect(() => {
        if (step !== STEPS.length - 1) return;
        fetchLocations();
        api.get<{ data: any[] }>('/channels')
            .then(res => setChannelCount((res.data ?? []).filter(c => c.enabled).length))
            .catch(() => setChannelCount(null));
    }, [step]);

    const nextStep = () => { setSaveError(null); setStep(s => Math.min(s + 1, STEPS.length - 1)); };
    const prevStep = () => { setSaveError(null); setStep(s => Math.max(s - 1, 0)); };

    const handleSave = async () => {
        setLoading(true);
        setSaveError(null);
        try {
            // Backend requires { settings: { key: value } } wrapper
            await api.put('/config', { settings: { ...config, setup_completed: 'true' } });
            toast.success('Konfigurasi tersimpan. Pemantauan dimulai.');
            window.location.href = '/';
        } catch (e: any) {
            let msg: string;
            if (e?.name === 'TypeError' || !e?.status) {
                msg = 'Server tidak bisa dihubungi. Pastikan backend sudah berjalan, lalu coba lagi.';
            } else if (e?.status === 422) {
                const detail = e?.data?.detail;
                if (Array.isArray(detail) && detail.length > 0) {
                    const d = detail[0];
                    const field = d.loc?.slice(-1)[0] ?? 'tidak diketahui';
                    msg = `Isian "${field}" tidak valid: ${d.msg}`;
                } else {
                    msg = `Data tidak valid (422): ${e.message}`;
                }
            } else if (e?.status >= 500) {
                msg = `Server mengalami galat (${e.status}). Detailnya ada di log backend.`;
            } else {
                msg = e?.message ?? 'Penyebabnya tidak diketahui. Coba lagi.';
            }
            setSaveError(msg);
            toast.error('Konfigurasi gagal disimpan', { description: msg, duration: 6000 });
            console.error('Save config error:', e);
        } finally {
            setLoading(false);
        }
    };

    const StatusIcon = STEPS[step].icon;

    const enabledLocations = locations.filter(l => l.enabled !== false).length;

    return (
        <div className="flex-1 flex items-start md:items-center justify-center">
            <Card className="w-full max-w-3xl md:min-h-[500px] flex flex-col">
                <CardHeader>
                    <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div className="flex items-center gap-3">
                            <div className="bg-primary-700 p-2 rounded-lg text-white">
                                <StatusIcon className="h-6 w-6" aria-hidden="true" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold leading-tight">Penyiapan BMKG Alert</h1>
                                <CardDescription>Langkah {step + 1} dari {STEPS.length}: {STEPS[step].title}</CardDescription>
                            </div>
                        </div>
                        <div
                            className="flex gap-1"
                            role="progressbar"
                            aria-valuemin={1}
                            aria-valuemax={STEPS.length}
                            aria-valuenow={step + 1}
                            aria-label="Kemajuan penyiapan"
                        >
                            {STEPS.map((s, i) => (
                                <div key={s.id} className={cn("h-2 w-8 rounded-full", i <= step ? "bg-primary-700 dark:bg-sky-400" : "bg-slate-300 dark:bg-slate-600")} />
                            ))}
                        </div>
                    </div>
                </CardHeader>

                <CardContent className="flex-1 overflow-y-auto">
                    {step === 0 && (
                        <div className="space-y-4">
                            <h2 className="text-lg font-medium">Tiga hal yang perlu disiapkan</h2>
                            <ol className="list-decimal pl-5 space-y-1">
                                <li>Kecamatan yang ingin dipantau.</li>
                                <li>Channel tujuan notifikasi, misalnya bot Telegram.</li>
                                <li>Seberapa sering peringatan BMKG dicek.</li>
                            </ol>
                            <p className="text-muted-foreground text-sm">
                                Alamat API BMKG diatur lewat variabel BMKG_API_URL di server, jadi tidak ditanyakan di sini.
                            </p>
                        </div>
                    )}

                    {step === 1 && (
                        <LocationStep locations={locations} onUpdate={fetchLocations} />
                    )}

                    {step === 2 && (
                        <ChannelStep />
                    )}

                    {step === 3 && (
                        <div className="space-y-4">
                            <h2 className="text-lg font-medium">Jadwal cek</h2>
                            <div className="grid gap-2 max-w-sm">
                                <label htmlFor="setup-poll-interval" className="text-sm font-medium">Cek peringatan BMKG setiap</label>
                                <select
                                    id="setup-poll-interval"
                                    className="flex h-11 md:h-10 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                    value={config.poll_interval}
                                    onChange={e => setConfig({...config, poll_interval: e.target.value})}
                                >
                                    <option value="120">2 menit</option>
                                    <option value="300">5 menit (disarankan)</option>
                                    <option value="600">10 menit</option>
                                    <option value="1800">30 menit</option>
                                </select>
                                <p className="text-xs text-muted-foreground">Jam tenang dan tingkat minimum bisa diatur nanti di Pengaturan.</p>
                            </div>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="space-y-4">
                            <h2 className="text-lg font-medium">{saveError ? 'Konfigurasi gagal disimpan' : 'Periksa sebelum mulai'}</h2>
                            <ul className="space-y-2 text-sm">
                                <li className="flex items-start gap-2">
                                    {enabledLocations > 0
                                        ? <Check className="h-4 w-4 mt-0.5 shrink-0 text-green-700 dark:text-green-400" aria-hidden="true" />
                                        : <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />}
                                    <span>
                                        {enabledLocations > 0
                                            ? `${enabledLocations} lokasi akan dipantau.`
                                            : 'Belum ada lokasi. Tanpa lokasi, tidak ada peringatan yang bisa dicocokkan. Kembali ke langkah 2 untuk menambahkannya.'}
                                    </span>
                                </li>
                                <li className="flex items-start gap-2">
                                    {channelCount
                                        ? <Check className="h-4 w-4 mt-0.5 shrink-0 text-green-700 dark:text-green-400" aria-hidden="true" />
                                        : <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />}
                                    <span>
                                        {channelCount === null
                                            ? 'Jumlah channel tidak bisa diperiksa.'
                                            : channelCount > 0
                                            ? `${channelCount} channel notifikasi aktif.`
                                            : 'Belum ada channel notifikasi. Peringatan tetap tercatat di Riwayat, tetapi tidak dikirim ke mana pun.'}
                                    </span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <Check className="h-4 w-4 mt-0.5 shrink-0 text-green-700 dark:text-green-400" aria-hidden="true" />
                                    <span>Peringatan dicek setiap {Math.round(parseInt(config.poll_interval ?? '300', 10) / 60)} menit.</span>
                                </li>
                            </ul>
                            {saveError && (
                                <div role="alert" className="rounded-lg border border-red-300 bg-red-50 dark:bg-red-950/40 dark:border-red-800 px-4 py-3">
                                    <p className="text-sm font-semibold text-red-800 dark:text-red-200 mb-1 flex items-center gap-1.5">
                                        <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                                        Penyebab
                                    </p>
                                    <p className="text-sm text-red-800 dark:text-red-200">{saveError}</p>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>

                <CardFooter className="flex justify-between border-t pt-6">
                    <Button variant="ghost" onClick={prevStep} disabled={step === 0}>
                        Kembali
                    </Button>

                    {step < STEPS.length - 1 ? (
                        <Button onClick={nextStep}>Lanjut</Button>
                    ) : (
                        <Button onClick={handleSave} className="gap-2" disabled={loading}>
                            {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                            {loading ? 'Menyimpan...' : 'Simpan dan mulai pemantauan'}
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};
