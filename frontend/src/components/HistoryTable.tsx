import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';

type AlertRecord = {
    id: number;
    bmkg_alert_code: string;
    event: string | null;
    severity: string | null;
    headline: string | null;
    effective: string | null;
    expires: string | null;
    status: string;
    created_at: string | null;
    matched_text: string | null;
    match_type: string | null;
};

const SEVERITY_CLASS: Record<string, string> = {
    extreme:  'bg-red-900 text-white',
    severe:   'bg-red-500 text-white',
    moderate: 'bg-amber-500 text-white',
    minor:    'bg-blue-500 text-white',
};

const fmtDate = (iso: string | null) => {
    if (!iso) return '-';
    try {
        return new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
    } catch { return iso; }
};

export const HistoryTable: React.FC = () => {
    const [alerts, setAlerts] = useState<AlertRecord[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);

    const fetchAlerts = async (p: number) => {
        setLoading(true);
        try {
            const res = await api.get<{ data: AlertRecord[]; total: number }>(`/alerts?page=${p}&page_size=20`);
            setAlerts(res.data ?? []);
            setTotal(res.total ?? 0);
        } catch (err) {
            console.error('Failed to fetch alert history:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAlerts(page); }, [page]);

    return (
        <Card className="w-full">
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Alert History</CardTitle>
                <span className="text-sm text-muted-foreground">{total} total tersimpan</span>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="py-8 text-center text-muted-foreground">Loading history...</div>
                ) : alerts.length === 0 ? (
                    <div className="py-8 text-center text-muted-foreground">
                        Belum ada riwayat alert. Engine akan merekam alert yang cocok dengan lokasi yang dipantau.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {alerts.map(alert => {
                            const severityKey = alert.severity?.toLowerCase() ?? '';
                            const badgeClass = SEVERITY_CLASS[severityKey] ?? 'bg-slate-400 text-white';
                            return (
                                <div key={alert.id} className="flex items-start gap-4 p-4 border rounded-lg bg-card shadow-sm hover:shadow-md transition-shadow">
                                    <div className="flex-1 space-y-1">
                                        <div className="flex items-center justify-between gap-2 flex-wrap">
                                            <a href={`/alert/${alert.id}`} className="font-semibold text-sm hover:text-blue-600 hover:underline">
                                                {alert.event ?? 'Alert'}
                                            </a>
                                            <div className="flex items-center gap-2">
                                                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badgeClass}`}>
                                                    {alert.severity ?? 'Unknown'}
                                                </span>
                                                <span className={`text-xs px-2 py-0.5 rounded-full border ${
                                                    alert.status === 'active'
                                                        ? 'border-green-500 text-green-600'
                                                        : 'border-slate-400 text-slate-500'
                                                }`}>
                                                    {alert.status}
                                                </span>
                                                <a href={`/alert/${alert.id}`} className="text-xs text-blue-500 hover:underline">
                                                    Detail →
                                                </a>
                                            </div>
                                        </div>
                                        <p className="text-xs text-muted-foreground line-clamp-2">{alert.headline ?? '-'}</p>
                                        <div className="text-xs text-slate-400 space-y-0.5 pt-1">
                                            {alert.matched_text && (
                                                <div>
                                                    Matched: <span className="font-medium text-slate-500">{alert.matched_text}</span>{' '}
                                                    <span className="text-slate-400">({alert.match_type})</span>
                                                </div>
                                            )}
                                            <div>Berlaku: {fmtDate(alert.effective)} — Berakhir: {fmtDate(alert.expires)}</div>
                                            <div>Terdeteksi: {fmtDate(alert.created_at)}</div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}

                        {total > 20 && (
                            <div className="flex justify-center items-center gap-3 pt-4">
                                <button
                                    className="px-3 py-1 text-sm border rounded disabled:opacity-50 hover:bg-slate-100"
                                    disabled={page === 1}
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                >
                                    Sebelumnya
                                </button>
                                <span className="text-sm text-muted-foreground">
                                    {page} / {Math.ceil(total / 20)}
                                </span>
                                <button
                                    className="px-3 py-1 text-sm border rounded disabled:opacity-50 hover:bg-slate-100"
                                    disabled={page >= Math.ceil(total / 20)}
                                    onClick={() => setPage(p => p + 1)}
                                >
                                    Berikutnya
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
