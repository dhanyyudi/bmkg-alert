import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Clock, MapPin, X, CheckCircle, AlertTriangle, Bot, MessageCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { regionContext, searchRegions, toLocationPayload, type WilayahResult } from '@/lib/wilayah';

// ── Types ────────────────────────────────────────────────────────────────────


type TrialStatus = {
    active: boolean;
    id?: number;
    location_code?: string;
    location_name?: string;
    district_name?: string;
    province_name?: string;
    severity_min?: string;
    registered_at?: string;
    expires_at?: string;
};

type BotInfo = {
    available: boolean;
    username?: string;
    name?: string;
};

const SEVERITY_OPTIONS = [
    { value: 'all', label: 'Semua tingkat' },
    { value: 'minor', label: 'Ringan ke atas' },
    { value: 'moderate', label: 'Sedang ke atas' },
    { value: 'severe', label: 'Berat ke atas' },
    { value: 'extreme', label: 'Hanya ekstrem' },
];

const TRIAL_CHAT_KEY = 'bmkg_trial_chat_id';

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtCountdown(expiresAt: string): string {
    const exp = expiresAt.includes('T') || expiresAt.includes('Z')
        ? new Date(expiresAt)
        : new Date(expiresAt.replace(' ', 'T') + 'Z');
    const diff = Math.max(0, Math.floor((exp.getTime() - Date.now()) / 1000));
    if (diff <= 0) return 'Berakhir';
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    return h > 0 ? `${h} jam ${m} menit` : `${m} menit`;
}

// ── Component ────────────────────────────────────────────────────────────────

export const TryMode: React.FC = () => {
    // Form state
    const [chatId, setChatId] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<WilayahResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [selectedLocation, setSelectedLocation] = useState<WilayahResult | null>(null);
    const [severity, setSeverity] = useState('all');
    const [registering, setRegistering] = useState(false);

    // Trial status
    const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
    const [loadingStatus, setLoadingStatus] = useState(true);
    const [cancelling, setCancelling] = useState(false);
    const [confirmCancel, setConfirmCancel] = useState(false);
    const [sendingTest, setSendingTest] = useState(false);
    // Re-render once a minute so the remaining time stays current
    const [, setNow] = useState(Date.now());

    // Bot info
    const [botInfo, setBotInfo] = useState<BotInfo | null>(null);

    // Check for existing trial on mount + fetch bot info
    useEffect(() => {
        api.get<BotInfo>('/trial/bot-info')
            .then(info => setBotInfo(info))
            .catch(() => setBotInfo({ available: false }));

        const savedChatId = localStorage.getItem(TRIAL_CHAT_KEY);
        if (savedChatId) {
            setChatId(savedChatId);
            checkTrialStatus(savedChatId);
        } else {
            setLoadingStatus(false);
        }
    }, []);

    // Tick for countdown
    useEffect(() => {
        if (!trialStatus?.active) return;
        const t = setInterval(() => setNow(Date.now()), 60000);
        return () => clearInterval(t);
    }, [trialStatus?.active]);

    const checkTrialStatus = async (id: string) => {
        try {
            const res = await api.get<TrialStatus>(`/trial/status/${encodeURIComponent(id)}`);
            setTrialStatus(res);
        } catch {
            setTrialStatus({ active: false });
        } finally {
            setLoadingStatus(false);
        }
    };

    // Location search
    const searchWilayah = useCallback(async (q: string) => {
        if (q.length < 2) { setSearchResults([]); return; }
        setSearching(true);
        try {
            setSearchResults(await searchRegions(q, ['subdistrict']));
        } catch { setSearchResults([]); }
        finally { setSearching(false); }
    }, []);

    useEffect(() => {
        const t = setTimeout(() => searchWilayah(searchQuery), 400);
        return () => clearTimeout(t);
    }, [searchQuery, searchWilayah]);

    // Register trial
    const handleRegister = async () => {
        if (!chatId.trim()) { toast.error('Masukkan Chat ID Telegram'); return; }
        if (!selectedLocation) { toast.error('Pilih lokasi terlebih dahulu'); return; }

        setRegistering(true);
        try {
            const res = await api.post<{ success: boolean; id: number; expires_at: string }>('/trial/register', {
                chat_id: chatId.trim(),
                location_code: selectedLocation.code,
                location_name: selectedLocation.name,
                district_name: toLocationPayload(selectedLocation).district_name,
                province_name: toLocationPayload(selectedLocation).province_name,
                severity_min: severity,
            });

            if (res.success) {
                localStorage.setItem(TRIAL_CHAT_KEY, chatId.trim());
                toast.success('Trial berhasil diaktifkan! Cek Telegram Anda.');
                await checkTrialStatus(chatId.trim());
            }
        } catch (e: any) {
            toast.error(e?.message ?? 'Gagal mendaftar trial');
        } finally {
            setRegistering(false);
        }
    };

    // Cancel trial
    const handleCancel = async () => {
        if (!trialStatus?.id) return;
        setCancelling(true);
        try {
            await api.delete(`/trial/${trialStatus.id}?chat_id=${encodeURIComponent(chatId)}`);
            toast.info('Trial dihentikan');
            localStorage.removeItem(TRIAL_CHAT_KEY);
            setTrialStatus({ active: false });
            setSelectedLocation(null);
            setConfirmCancel(false);
        } catch (e: any) {
            toast.error(e?.message ?? 'Gagal menghentikan trial');
        } finally {
            setCancelling(false);
        }
    };

    // Send test message
    const handleTestMessage = async () => {
        if (!trialStatus?.id) return;
        setSendingTest(true);
        try {
            await api.post(`/trial/${trialStatus.id}/test-message?chat_id=${encodeURIComponent(chatId)}`, {});
            toast.success('Pesan tes berhasil dikirim! Cek Telegram Anda.');
        } catch (e: any) {
            toast.error(e?.message ?? 'Gagal mengirim pesan tes. Pastikan sudah kirim /start ke bot.');
        } finally {
            setSendingTest(false);
        }
    };

    if (loadingStatus) {
        return (
            <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
                Memuat status trial...
            </div>
        );
    }

    // ── Active Trial Panel ───────────────────────────────────────────────────
    if (trialStatus?.active) {
        const locLabel = [trialStatus.location_name, trialStatus.district_name, trialStatus.province_name]
            .filter(Boolean).join(', ');

        return (
            <div className="space-y-6">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Coba BMKG Alert</h1>
                    <p className="text-muted-foreground">Trial notifikasi Telegram selama 24 jam.</p>
                </div>

                <Card className="border-green-200 dark:border-green-800">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-green-700 dark:text-green-400" />
                            <CardTitle className="text-lg">Trial aktif</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3">
                                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                    <MapPin className="w-3 h-3" /> Lokasi
                                </div>
                                <p className="font-medium">{locLabel || '-'}</p>
                            </div>
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3">
                                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" /> Tingkat minimum
                                </div>
                                <p className="font-medium">{SEVERITY_OPTIONS.find(o => o.value === trialStatus.severity_min)?.label ?? 'Semua tingkat'}</p>
                            </div>
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3">
                                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                    <Clock className="w-3 h-3" /> Waktu Tersisa
                                </div>
                                <p className="font-medium">{trialStatus.expires_at ? fmtCountdown(trialStatus.expires_at) : '-'}</p>
                            </div>
                            <div className="rounded-lg bg-slate-50 dark:bg-slate-800 p-3">
                                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                                    <Send className="w-3 h-3" /> Chat ID
                                </div>
                                <p className="font-medium font-mono text-xs">{chatId}</p>
                            </div>
                        </div>

                        <p className="text-xs text-muted-foreground">
                            Jika ada peringatan cuaca BMKG yang cocok dengan lokasi Anda, notifikasi akan dikirim ke Telegram.
                        </p>

                        {/* Test message button */}
                        <Button
                            variant="outline"
                            onClick={handleTestMessage}
                            disabled={sendingTest}
                            className="w-full"
                        >
                            <MessageCircle className="w-4 h-4 mr-2" />
                            {sendingTest ? 'Mengirim...' : 'Kirim Pesan Tes ke Telegram'}
                        </Button>

                        {confirmCancel ? (
                            <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 p-4 space-y-3">
                                <p className="text-sm font-medium text-red-700 dark:text-red-400">
                                    Yakin ingin menghentikan trial?
                                </p>
                                <p className="text-xs text-red-700 dark:text-red-400">
                                    Notifikasi akan langsung berhenti dan trial tidak bisa diaktifkan kembali tanpa mendaftar ulang.
                                </p>
                                <div className="flex gap-2">
                                    <Button
                                        variant="destructive"
                                        size="sm"
                                        onClick={handleCancel}
                                        disabled={cancelling}
                                        className="flex-1"
                                    >
                                        <X className="w-3.5 h-3.5 mr-1.5" />
                                        {cancelling ? 'Menghentikan...' : 'Ya, Hentikan'}
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setConfirmCancel(false)}
                                        disabled={cancelling}
                                        className="flex-1"
                                    >
                                        Batal
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <Button
                                variant="outline"
                                onClick={() => setConfirmCancel(true)}
                                className="w-full text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40"
                            >
                                <X className="w-4 h-4 mr-2" />
                                Hentikan Trial
                            </Button>
                        )}
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ── Registration Form ────────────────────────────────────────────────────
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Coba BMKG Alert</h1>
                <p className="text-muted-foreground">Terima peringatan cuaca BMKG lewat Telegram selama 24 jam. Gratis, tanpa perlu memasang server.</p>
            </div>

            {/* Prerequisite: start the bot first */}
            <Card className="border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/30">
                <CardHeader className="pb-3">
                    <div className="flex items-center gap-2">
                        <Bot className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        <CardTitle className="text-base">Sebelum mulai</CardTitle>
                    </div>
                    <CardDescription>
                        Lakukan 2 langkah ini di Telegram terlebih dahulu agar bot dapat menghubungi Anda.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                    {/* Step 1 */}
                    <div className="flex gap-3 items-start">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-700 text-white text-xs flex items-center justify-center font-bold mt-0.5">1</span>
                        <div className="flex-1 space-y-2">
                            <p className="font-medium">Dapatkan Chat ID Anda</p>
                            <p className="text-xs text-muted-foreground">
                                Kirim <code>/start</code> ke <strong>@userinfobot</strong>, lalu salin angka <strong>Id</strong> yang muncul.
                            </p>
                            <a
                                href="https://t.me/userinfobot"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg min-h-11 bg-primary-700 hover:bg-primary-800 text-white text-sm font-semibold transition-colors"
                            >
                                <Send className="w-3.5 h-3.5" />
                                Buka @userinfobot di Telegram
                            </a>
                        </div>
                    </div>

                    <div className="border-t border-blue-100 dark:border-blue-900" />

                    {/* Step 2 */}
                    <div className="flex gap-3 items-start">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-700 text-white text-xs flex items-center justify-center font-bold mt-0.5">2</span>
                        <div className="flex-1 space-y-2">
                            <p className="font-medium">Mulai percakapan dengan bot kami</p>
                            <p className="text-xs text-muted-foreground">
                                Kirim <code>/start</code> ke bot BMKG Alert.{' '}
                                <span className="text-amber-700 dark:text-amber-400 font-medium">
                                    Langkah ini wajib: bot tidak bisa mengirim pesan jika belum pernah Anda hubungi.
                                </span>
                            </p>
                            {botInfo?.available && botInfo.username ? (
                                <a
                                    href={`https://t.me/${botInfo.username}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg min-h-11 bg-primary-700 hover:bg-primary-800 text-white text-sm font-semibold transition-colors"
                                >
                                    <Bot className="w-3.5 h-3.5" />
                                    Buka @{botInfo.username} di Telegram
                                </a>
                            ) : (
                                <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg min-h-11 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm font-semibold cursor-not-allowed">
                                    <Bot className="w-3.5 h-3.5" />
                                    Bot belum dikonfigurasi di server ini
                                </span>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Daftar trial 24 jam</CardTitle>
                    <CardDescription>
                        Masukkan Chat ID Telegram, pilih lokasi, dan mulai menerima peringatan cuaca BMKG.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Step 1: Chat ID */}
                    <div className="space-y-2">
                        <label htmlFor="trial-chat-id" className="text-sm font-medium">Chat ID Telegram</label>
                        <Input
                            id="trial-chat-id"
                            placeholder="Contoh: 391047285"
                            value={chatId}
                            onChange={e => setChatId(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            Dapatkan dari{' '}
                            <a href="https://t.me/userinfobot" target="_blank" rel="noopener noreferrer"
                               className="text-blue-600 dark:text-blue-400 underline underline-offset-2 font-medium">
                                @userinfobot
                            </a>{' '}
                            (langkah 1 di atas).
                        </p>
                    </div>

                    {/* Step 2: Location */}
                    <div className="space-y-2">
                        <label htmlFor="trial-location" className="text-sm font-medium block">Lokasi (kecamatan)</label>
                        {selectedLocation ? (
                            <div className="flex items-center justify-between p-3 border rounded-lg bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
                                <div>
                                    <div className="font-medium text-sm">{selectedLocation.name}</div>
                                    <div className="text-xs text-muted-foreground">
                                        {regionContext(selectedLocation)}
                                    </div>
                                </div>
                                <Button variant="ghost" size="icon" aria-label="Ganti lokasi" onClick={() => setSelectedLocation(null)}>
                                    <X className="w-4 h-4" aria-hidden="true" />
                                </Button>
                            </div>
                        ) : (
                            <div className="relative">
                                <Input
                                    id="trial-location"
                                    placeholder="Ketik nama kecamatan, minimal 2 huruf"
                                    value={searchQuery}
                                    onChange={e => setSearchQuery(e.target.value)}
                                />
                                {(searching || searchResults.length > 0) && (
                                    <div className="absolute z-20 top-full mt-1 w-full bg-card border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                        {searching && <div className="p-3 text-sm text-muted-foreground">Mencari...</div>}
                                        {!searching && searchResults.map(r => (
                                            <button
                                                key={r.code}
                                                type="button"
                                                className="w-full min-h-11 text-left px-3 py-2 text-sm hover:bg-accent focus-visible:outline-none focus-visible:bg-accent"
                                                onClick={() => {
                                                    setSelectedLocation(r);
                                                    setSearchQuery('');
                                                    setSearchResults([]);
                                                }}
                                            >
                                                <div className="font-medium">{r.name}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    {regionContext(r)}
                                                </div>
                                            </button>
                                        ))}
                                        {!searching && searchResults.length === 0 && searchQuery.length >= 2 && (
                                            <div className="p-3 text-sm text-muted-foreground">Tidak ada kecamatan dengan nama itu. Periksa ejaannya.</div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Step 3: Severity */}
                    <div className="space-y-2">
                        <p id="trial-severity-label" className="text-sm font-medium">Tingkat peringatan minimum</p>
                        <div className="flex flex-wrap gap-2" role="group" aria-labelledby="trial-severity-label">
                            {SEVERITY_OPTIONS.map(opt => (
                                <button
                                    key={opt.value}
                                    type="button"
                                    aria-pressed={severity === opt.value}
                                    onClick={() => setSeverity(opt.value)}
                                    className={`min-h-11 md:min-h-9 text-sm px-4 rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${
                                        severity === opt.value
                                            ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white'
                                            : 'border-input hover:bg-accent'
                                    }`}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Anda hanya menerima peringatan pada tingkat yang dipilih atau lebih tinggi.
                        </p>
                    </div>

                    {/* Submit */}
                    <Button
                        onClick={handleRegister}
                        disabled={registering || !chatId.trim() || !selectedLocation}
                        className="w-full"
                        size="lg"
                    >
                        <Send className="w-4 h-4 mr-2" />
                        {registering ? 'Mendaftar...' : 'Mulai Trial 24 Jam'}
                    </Button>

                    <p className="text-xs text-muted-foreground text-center">
                        Selesaikan langkah 1 dan 2 di atas sebelum mendaftar.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
};
