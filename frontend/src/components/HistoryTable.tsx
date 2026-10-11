import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { severityStyle } from '@/lib/severity';
import { fmtDateTime } from '@/lib/format';

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

const PAGE_SIZE = 20;

export const HistoryTable: React.FC = () => {
    const [alerts, setAlerts] = useState<AlertRecord[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [failed, setFailed] = useState(false);

    const fetchAlerts = async (p: number) => {
        setLoading(true);
        setFailed(false);
        try {
            const res = await api.get<{ data: AlertRecord[]; total: number }>(`/alerts?page=${p}&page_size=${PAGE_SIZE}`);
            setAlerts(res.data ?? []);
            setTotal(res.total ?? 0);
        } catch (err) {
            console.error('Failed to fetch alert history:', err);
            setFailed(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAlerts(page); }, [page]);

    const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

    return (
        <div className="w-full space-y-6">
            <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Riwayat peringatan</h1>
                <p className="text-muted-foreground">Peringatan BMKG yang pernah cocok dengan lokasi yang Anda pantau.</p>
            </div>

            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base">{loading || failed ? 'Riwayat' : `${total} peringatan tercatat`}</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="py-8 text-center text-sm text-muted-foreground">Memuat riwayat peringatan...</div>
                    ) : failed ? (
                        <div className="py-8 text-center text-sm text-muted-foreground">
                            <p className="mb-3">Riwayat tidak bisa dimuat. Server tidak merespons.</p>
                            <Button variant="outline" size="sm" onClick={() => fetchAlerts(page)}>Coba lagi</Button>
                        </div>
                    ) : alerts.length === 0 ? (
                        <div className="py-8 text-center text-sm text-muted-foreground">
                            Belum ada peringatan yang cocok dengan lokasi Anda. Peringatan baru tercatat di sini begitu BMKG mengeluarkannya.
                        </div>
                    ) : (
                        <>
                            <ul className="divide-y">
                                {alerts.map(alert => {
                                    const sev = severityStyle(alert.severity);
                                    const active = alert.status === 'active';
                                    return (
                                        <li key={alert.id} className="py-4 first:pt-0 last:pb-0 space-y-1">
                                            <div className="flex items-center justify-between gap-2 flex-wrap">
                                                <a
                                                    href={`/alert/${alert.id}`}
                                                    className="font-semibold text-sm underline-offset-2 hover:underline rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                                >
                                                    {alert.event ?? 'Peringatan cuaca'}
                                                </a>
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${sev.badge}`}>{sev.label}</span>
                                                    <span className={`text-xs px-2 py-0.5 rounded border ${active ? 'border-green-700 text-green-700 dark:border-green-400 dark:text-green-400' : 'text-muted-foreground'}`}>
                                                        {active ? 'Masih berlaku' : 'Sudah berakhir'}
                                                    </span>
                                                </div>
                                            </div>
                                            <p className="text-sm text-muted-foreground line-clamp-2">{alert.headline ?? '-'}</p>
                                            <div className="text-xs text-muted-foreground space-y-0.5 pt-1">
                                                {alert.matched_text && (
                                                    <div>Cocok dengan {alert.match_type === 'kabupaten' ? 'kabupaten' : 'kecamatan'} <span className="font-medium text-foreground">{alert.matched_text}</span></div>
                                                )}
                                                <div>Berlaku {fmtDateTime(alert.effective)} sampai {fmtDateTime(alert.expires)}</div>
                                                <div>Terdeteksi {fmtDateTime(alert.created_at)}</div>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ul>

                            {total > PAGE_SIZE && (
                                <nav className="flex justify-center items-center gap-3 pt-6" aria-label="Halaman riwayat">
                                    <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))}>
                                        Sebelumnya
                                    </Button>
                                    <span className="text-sm text-muted-foreground">Halaman {page} dari {pageCount}</span>
                                    <Button variant="outline" size="sm" disabled={page >= pageCount} onClick={() => setPage(p => p + 1)}>
                                        Berikutnya
                                    </Button>
                                </nav>
                            )}
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};
