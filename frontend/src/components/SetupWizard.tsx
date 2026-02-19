import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Check, ChevronRight, Globe, MapPin, Bell, Settings, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { LocationStep } from './setup/LocationStep';
import { ChannelStep } from './setup/ChannelStep';

// Steps definition
const STEPS = [
    { id: 'welcome', title: 'Welcome', icon: Globe },
    { id: 'location', title: 'Location', icon: MapPin },
    { id: 'notifications', title: 'Notifications', icon: Bell },
    { id: 'preferences', title: 'Preferences', icon: Settings },
    { id: 'confirm', title: 'Confirm', icon: Check },
];

export const SetupWizard: React.FC = () => {
    const [step, setStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [saveError, setSaveError] = useState<string | null>(null);
    const [config, setConfig] = useState<any>({
        bmkg_api_url: 'https://bmkg-restapi.vercel.app',
        notification_language: 'id',
        poll_interval: '300',
        quiet_hours_enabled: 'false',
    });
    const [locations, setLocations] = useState<any[]>([]);

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

    const nextStep = () => { setSaveError(null); setStep(s => Math.min(s + 1, STEPS.length - 1)); };
    const prevStep = () => { setSaveError(null); setStep(s => Math.max(s - 1, 0)); };

    const handleSave = async () => {
        setLoading(true);
        setSaveError(null);
        try {
            // Backend requires { settings: { key: value } } wrapper
            await api.put('/config', { settings: { ...config, setup_completed: 'true' } });
            toast.success('Konfigurasi berhasil disimpan. Memulai monitoring...');
            window.location.href = '/';
        } catch (e: any) {
            let msg: string;
            if (e?.name === 'TypeError' || !e?.status) {
                msg = 'Tidak dapat terhubung ke backend. Pastikan server sudah berjalan (uvicorn app.main:app --port 8000).';
            } else if (e?.status === 422) {
                const detail = e?.data?.detail;
                if (Array.isArray(detail) && detail.length > 0) {
                    const d = detail[0];
                    const field = d.loc?.slice(-1)[0] ?? 'field tidak diketahui';
                    msg = `Validasi gagal pada field "${field}": ${d.msg}`;
                } else {
                    msg = `Data tidak valid (422): ${e.message}`;
                }
            } else if (e?.status >= 500) {
                msg = `Server error (${e.status}). Cek log backend di terminal untuk detail.`;
            } else {
                msg = e?.message ?? 'Terjadi kesalahan tidak diketahui.';
            }
            setSaveError(msg);
            toast.error('Gagal menyimpan konfigurasi', { description: msg, duration: 6000 });
            console.error('Save config error:', e);
        } finally {
            setLoading(false);
        }
    };

    const StatusIcon = STEPS[step].icon;

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4">
            <Card className="w-full max-w-3xl min-h-[500px] flex flex-col shadow-xl">
                <CardHeader>
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                             <div className="bg-primary-600 p-2 rounded-lg text-white">
                                <StatusIcon className="h-6 w-6" />
                             </div>
                             <div>
                                <CardTitle>BMKG Alert Setup</CardTitle>
                                <CardDescription>Step {step + 1} of {STEPS.length}: {STEPS[step].title}</CardDescription>
                             </div>
                        </div>
                        <div className="flex gap-1">
                            {STEPS.map((s, i) => (
                                <div key={s.id} className={cn("h-2 w-8 rounded-full transition-colors", i <= step ? "bg-primary-600" : "bg-slate-200 dark:bg-slate-800")} />
                            ))}
                        </div>
                    </div>
                </CardHeader>
                
                <CardContent className="flex-1 overflow-y-auto">
                    {step === 0 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-medium">Welcome to BMKG Alert</h3>
                            <p className="text-slate-600 dark:text-slate-400">
                                This wizard will help you configure your weather monitoring system. 
                                Only a few steps are required to get started.
                            </p>
                            
                            <div className="grid gap-2">
                                <label className="text-sm font-medium">BMKG API URL</label>
                                <Input 
                                    value={config.bmkg_api_url} 
                                    onChange={e => setConfig({...config, bmkg_api_url: e.target.value})} 
                                />
                                <p className="text-xs text-muted-foreground">Default: https://bmkg-restapi.vercel.app</p>
                            </div>
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
                            <h3 className="text-lg font-medium">Preferences</h3>
                            <div className="grid gap-4">
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium">Polling Interval (seconds)</label>
                                    <div className="relative">
                                        <select 
                                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 appearance-none"
                                            value={config.poll_interval}
                                            onChange={e => setConfig({...config, poll_interval: e.target.value})}
                                        >
                                            <option value="120">2 minutes</option>
                                            <option value="300">300 (5 minutes - Recommended)</option>
                                            <option value="600">10 minutes</option>
                                            <option value="1800">30 minutes</option>
                                        </select>
                                    </div>
                                </div>
                                {/* Future: Quiet Hours */}
                            </div>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="space-y-4 text-center py-10">
                            <div className={cn(
                                "mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4",
                                saveError ? "bg-red-100" : "bg-green-100"
                            )}>
                                {saveError
                                    ? <AlertCircle className="h-8 w-8 text-red-600" />
                                    : <Check className="h-8 w-8 text-green-600" />
                                }
                            </div>
                            <h3 className="text-xl font-bold">
                                {saveError ? 'Gagal Menyimpan' : 'Ready to Launch!'}
                            </h3>
                            <p className="text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                                {saveError
                                    ? 'Terjadi kesalahan saat menyimpan konfigurasi. Lihat detail di bawah.'
                                    : 'Sistem BMKG Alert sudah dikonfigurasi. Engine akan mulai memantau lokasi Anda segera setelah selesai.'}
                            </p>
                            {saveError && (
                                <div className="mt-2 mx-auto max-w-md rounded-lg border border-red-300 bg-red-50 dark:bg-red-950 dark:border-red-700 px-4 py-3 text-left">
                                    <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-1 flex items-center gap-1.5">
                                        <AlertCircle className="h-4 w-4 shrink-0" />
                                        Detail Error
                                    </p>
                                    <p className="text-sm text-red-600 dark:text-red-400">{saveError}</p>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>

                <CardFooter className="flex justify-between border-t pt-6">
                    <Button variant="ghost" onClick={prevStep} disabled={step === 0}>
                        Back
                    </Button>
                    
                    {step < STEPS.length - 1 ? (
                        <Button onClick={nextStep} className="gap-2">
                            Next <ChevronRight className="h-4 w-4" />
                        </Button>
                    ) : (
                        <Button onClick={handleSave} className="gap-2 bg-green-600 hover:bg-green-700 text-white" disabled={loading}>
                            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                            Start Monitoring
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};
