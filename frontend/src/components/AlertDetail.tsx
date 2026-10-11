import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { splitRings } from '@/lib/polygon';
import { severityStyle } from '@/lib/severity';
import { certaintyLabel, fmtDateTime, urgencyLabel } from '@/lib/format';
import { webglAvailable } from '@/lib/webgl';
import { EventIcon } from '@/components/EventIcon';
import { Button } from '@/components/ui/button';

// ─── Types ────────────────────────────────────────────────────────────────────

type AreaPolygon = { name: string; polygon: number[][] | null };

type AlertRecord = {
    id: number;
    bmkg_alert_code: string;
    event: string | null;
    severity: string | null;
    urgency: string | null;
    certainty: string | null;
    headline: string | null;
    description: string | null;
    effective: string | null;
    expires: string | null;
    infographic_url: string | null;
    polygon_data: AreaPolygon[] | string | null;
    matched_location_id: number | null;
    match_type: string | null;
    matched_text: string | null;
    status: string;
    created_at: string | null;
};

type Delivery = {
    id: number;
    channel_id: number;
    status: string;
    error_message: string | null;
    sent_at: string | null;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Highlight area names in description text with amber styling. */
function highlightAreas(text: string, areaNames: string[]): React.ReactNode[] {
    const names = areaNames.filter(Boolean);
    if (!text || names.length === 0) return [text];
    const escaped = names
        .sort((a, b) => b.length - a.length)
        .map(n => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const regex = new RegExp(`(${escaped.join('|')})`, 'gi');
    return text.split(regex).map((part, i) =>
        names.some(n => n.toLowerCase() === part.toLowerCase())
            ? <mark key={i} className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 rounded px-0.5 font-medium not-italic">{part}</mark>
            : part
    );
}

/** Map known backend error patterns to user-friendly Indonesian descriptions. */
function explainDeliveryError(msg: string): React.ReactNode {
    if (msg.includes("argument of type 'datetime.datetime' is not a container or iterable")) {
        return (
            <span>
                Waktu pada pesan notifikasi gagal diformat{' '}
                <span className="text-muted-foreground text-xs">(internal: datetime type error)</span>
            </span>
        );
    }
    if (msg.length > 150) {
        return <span title={msg}>{msg.slice(0, 147)}…</span>;
    }
    return msg;
}

const DELIVERY_STATUS: Record<string, string> = {
    sent: 'Terkirim',
    failed: 'Gagal',
    skipped_quiet_hours: 'Ditahan (jam tenang)',
};

const parsePolygonData = (raw: AreaPolygon[] | string | null): AreaPolygon[] => {
    if (!raw) return [];
    if (typeof raw === 'string') {
        try { return JSON.parse(raw); } catch { return []; }
    }
    return raw;
};

// ─── Mini Map ─────────────────────────────────────────────────────────────────

interface MiniMapProps {
    areas: AreaPolygon[];
    color: string;
    className?: string;
}

const MiniMap: React.FC<MiniMapProps> = ({ areas, color, className = 'h-56' }) => {
    // Build one GeoJSON Feature per ring (same as WarningMap)
    const features: GeoJSON.Feature[] = [];
    for (const a of areas) {
        if (!a.polygon || a.polygon.length === 0) continue;
        const rings = splitRings(a.polygon);
        for (const ring of rings) {
            features.push({
                type: 'Feature' as const,
                geometry: { type: 'Polygon' as const, coordinates: [ring] },
                properties: { name: a.name, color },
            });
        }
    }

    if (features.length === 0 || !webglAvailable) {
        return (
            <div className={`flex items-center justify-center p-4 text-center bg-muted rounded-lg text-sm text-muted-foreground ${className}`}>
                {features.length === 0
                    ? 'BMKG tidak menyertakan data poligon untuk peringatan ini.'
                    : 'Peta tidak bisa ditampilkan karena browser ini tidak mendukung WebGL.'}
            </div>
        );
    }

    // Auto-fit: compute bounding box from all ring coordinates
    const allCoords = features.flatMap(f => (f.geometry as GeoJSON.Polygon).coordinates[0]);
    let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
    for (const [lon, lat] of allCoords) {
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
    }
    const span = Math.max(maxLon - minLon, maxLat - minLat);
    const zoom = span < 0.3 ? 10 : span < 0.7 ? 9 : span < 1.5 ? 8 : span < 3 ? 7 : span < 6 ? 6 : span < 12 ? 5 : 4;

    const geoJson: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features };

    return (
        <div className={`rounded-lg overflow-hidden border ${className}`}>
            <Map
                initialViewState={{
                    longitude: (minLon + maxLon) / 2,
                    latitude: (minLat + maxLat) / 2,
                    zoom,
                }}
                style={{ width: '100%', height: '100%' }}
                mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
            >
                <Source type="geojson" data={geoJson}>
                    <Layer
                        id="alert-fill"
                        type="fill"
                        paint={{ 'fill-color': ['get', 'color'], 'fill-opacity': 0.5 }}
                    />
                    <Layer
                        id="alert-outline"
                        type="line"
                        paint={{ 'line-color': ['get', 'color'], 'line-width': 2 }}
                    />
                </Source>
            </Map>
        </div>
    );
};

// ─── Main Component ───────────────────────────────────────────────────────────

interface AlertDetailProps {
    alertId: number;
}

export const AlertDetail: React.FC<AlertDetailProps> = ({ alertId }) => {
    const [alert, setAlert] = useState<AlertRecord | null>(null);
    const [deliveries, setDeliveries] = useState<Delivery[]>([]);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        api.get<{ data: AlertRecord; deliveries: Delivery[] }>(`/alerts/${alertId}`)
            .then(res => {
                setAlert(res.data);
                setDeliveries(res.deliveries ?? []);
            })
            .catch(err => {
                if (err?.status === 404) setNotFound(true);
                else { console.error('Failed to load alert:', err); setFailed(true); }
            })
            .finally(() => setLoading(false));
    }, [alertId]);

    const backLink = (
        <a href="/history" className="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Kembali ke Riwayat
        </a>
    );

    if (loading) return <div className="py-16 text-center text-muted-foreground">Memuat detail peringatan...</div>;

    if (failed) {
        return (
            <div className="py-16 text-center space-y-3">
                <p className="text-xl font-bold">Detail peringatan tidak bisa dimuat</p>
                <p className="text-muted-foreground">Server tidak merespons. Periksa koneksi, lalu coba lagi.</p>
                <Button variant="outline" onClick={() => window.location.reload()}>Coba lagi</Button>
            </div>
        );
    }

    if (notFound || !alert) {
        return (
            <div className="py-16 text-center space-y-3">
                <p className="text-xl font-bold">Peringatan tidak ditemukan</p>
                <p className="text-muted-foreground">Tidak ada peringatan dengan nomor #{alertId} di riwayat.</p>
                {backLink}
            </div>
        );
    }

    const areas = parsePolygonData(alert.polygon_data);
    const sev = severityStyle(alert.severity);
    const mapColor = sev.mapColor;
    const active = alert.status === 'active';

    const fields = [
        { label: 'Kode peringatan BMKG', value: alert.bmkg_alert_code },
        { label: 'Jenis', value: alert.event ?? '-' },
        { label: 'Urgensi', value: urgencyLabel(alert.urgency) },
        { label: 'Kepastian', value: certaintyLabel(alert.certainty) },
        { label: 'Status', value: active ? 'Masih berlaku' : 'Sudah berakhir' },
        { label: 'Berlaku', value: fmtDateTime(alert.effective) },
        { label: 'Berakhir', value: fmtDateTime(alert.expires) },
        { label: 'Terdeteksi', value: fmtDateTime(alert.created_at) },
        { label: 'Lokasi yang cocok', value: alert.matched_text ? `${alert.matched_text} (${alert.match_type})` : '-' },
    ];

    return (
        <div className="space-y-6 w-full max-w-4xl mx-auto">
            <div>{backLink}</div>

            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <EventIcon event={alert.event} className="h-6 w-6 shrink-0 text-muted-foreground" />
                        {alert.event ?? 'Peringatan cuaca'}
                    </h1>
                    <p className="text-muted-foreground mt-1">{alert.headline ?? '-'}</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-semibold px-3 py-1 rounded ${sev.badge}`}>{sev.label}</span>
                    <span className={`text-sm px-3 py-1 rounded border ${active ? 'border-green-700 text-green-700 dark:border-green-400 dark:text-green-400' : 'text-muted-foreground'}`}>
                        {active ? 'Masih berlaku' : 'Sudah berakhir'}
                    </span>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2 items-stretch">
                {/* Detail fields */}
                <Card className="flex flex-col">
                    <CardHeader><CardTitle className="text-base">Rincian peringatan</CardTitle></CardHeader>
                    <CardContent className="space-y-2">
                        {fields.map(({ label, value }) => (
                            <div key={label} className="flex justify-between text-sm border-b last:border-0 py-1.5 gap-4">
                                <span className="text-muted-foreground shrink-0">{label}</span>
                                <span className="font-medium text-right">{value}</span>
                            </div>
                        ))}
                        {alert.infographic_url && (
                            <a
                                href={alert.infographic_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 text-sm text-blue-600 dark:text-blue-400 hover:underline pt-2 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <ExternalLink className="h-4 w-4" aria-hidden="true" /> Lihat infografis BMKG
                            </a>
                        )}
                    </CardContent>
                </Card>

                {/* Map */}
                <Card className="flex flex-col">
                    <CardHeader><CardTitle className="text-base">Peta wilayah terdampak</CardTitle></CardHeader>
                    <CardContent className="flex-1 flex flex-col min-h-0 pb-4">
                        <MiniMap areas={areas} color={mapColor} className="flex-1 min-h-[14rem]" />
                        {areas.length > 0 && (
                            <div className="mt-3 pt-3 border-t space-y-1.5">
                                <p className="text-xs font-semibold mb-2">Wilayah terdampak</p>
                                {areas.map((a, i) => (
                                    <div key={i} className="text-xs flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-sm shrink-0 opacity-70" style={{ backgroundColor: mapColor }} />
                                        <span className="font-medium">{a.name}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Description */}
            {alert.description && (
                <Card>
                    <CardHeader><CardTitle className="text-base">Deskripsi</CardTitle></CardHeader>
                    <CardContent>
                        <p className="text-sm whitespace-pre-line leading-relaxed">
                            {highlightAreas(alert.description, areas.map(a => a.name))}
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Delivery log */}
            <Card>
                <CardHeader><CardTitle className="text-base">Riwayat pengiriman notifikasi</CardTitle></CardHeader>
                <CardContent>
                    {deliveries.length === 0 ? (
                        <p className="text-sm text-muted-foreground">Belum ada notifikasi yang dikirim untuk peringatan ini. Periksa apakah ada channel yang aktif di Pengaturan.</p>
                    ) : (
                        <div className="space-y-2">
                            {deliveries.map(d => (
                                <div key={d.id} className="flex items-center justify-between gap-3 flex-wrap text-sm border-b last:border-0 py-2">
                                    <div>
                                        <span className="font-medium">Channel #{d.channel_id}</span>
                                        {d.error_message && (
                                            <p className="text-xs text-red-600 dark:text-red-400 mt-0.5">{explainDeliveryError(d.error_message)}</p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-3 text-right">
                                        <span className={`text-xs px-2 py-0.5 rounded ${
                                            d.status === 'sent'
                                                ? 'bg-green-100 text-green-800'
                                                : d.status === 'failed'
                                                ? 'bg-red-100 text-red-800'
                                                : 'bg-slate-200 text-slate-700'
                                        }`}>
                                            {DELIVERY_STATUS[d.status] ?? d.status}
                                        </span>
                                        <span className="text-xs text-muted-foreground">{fmtDateTime(d.sent_at)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};
