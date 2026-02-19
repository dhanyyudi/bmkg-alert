import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

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

const SEVERITY_CLASS: Record<string, string> = {
    extreme:  'bg-red-900 text-white',
    severe:   'bg-red-500 text-white',
    moderate: 'bg-amber-500 text-white',
    minor:    'bg-blue-500 text-white',
};

const SEVERITY_HEX: Record<string, string> = {
    extreme:  '#7f1d1d',
    severe:   '#ef4444',
    moderate: '#f59e0b',
    minor:    '#3b82f6',
};

const fmtDate = (iso: string | null) => {
    if (!iso) return '-';
    try { return new Date(iso).toLocaleString('id-ID', { dateStyle: 'long', timeStyle: 'short' }); }
    catch { return iso; }
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
}

const MiniMap: React.FC<MiniMapProps> = ({ areas, color }) => {
    const features = areas
        .filter(a => a.polygon && a.polygon.length > 0)
        .map(a => ({
            type: 'Feature' as const,
            geometry: {
                type: 'Polygon' as const,
                coordinates: [a.polygon!.map(([lat, lon]) => [lon, lat])],
            },
            properties: { name: a.name, color },
        }));

    if (features.length === 0) {
        return (
            <div className="h-48 flex items-center justify-center bg-slate-100 dark:bg-slate-800 rounded-lg text-sm text-muted-foreground">
                Tidak ada data polygon tersedia
            </div>
        );
    }

    const geoJson: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features };

    return (
        <div className="h-56 rounded-lg overflow-hidden border">
            <Map
                initialViewState={{ longitude: 118, latitude: -2.5, zoom: 4 }}
                style={{ width: '100%', height: '100%' }}
                mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
                attributionControl={false}
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

    useEffect(() => {
        api.get<{ data: AlertRecord; deliveries: Delivery[] }>(`/alerts/${alertId}`)
            .then(res => {
                setAlert(res.data);
                setDeliveries(res.deliveries ?? []);
            })
            .catch(err => {
                if (err?.status === 404) setNotFound(true);
                else console.error('Failed to load alert:', err);
            })
            .finally(() => setLoading(false));
    }, [alertId]);

    if (loading) return <div className="py-16 text-center text-muted-foreground">Memuat detail alert...</div>;
    if (notFound || !alert) {
        return (
            <div className="py-16 text-center">
                <p className="text-2xl font-bold mb-2">Alert tidak ditemukan</p>
                <p className="text-muted-foreground">ID #{alertId} tidak ada dalam database.</p>
                <a href="/history" className="mt-4 inline-block text-blue-500 hover:underline text-sm">
                    ← Kembali ke History
                </a>
            </div>
        );
    }

    const areas = parsePolygonData(alert.polygon_data);
    const severityKey = alert.severity?.toLowerCase() ?? '';
    const badgeClass = SEVERITY_CLASS[severityKey] ?? 'bg-slate-400 text-white';
    const mapColor = SEVERITY_HEX[severityKey] ?? '#10b981';

    const fields = [
        { label: 'BMKG Alert Code', value: alert.bmkg_alert_code },
        { label: 'Event', value: alert.event ?? '-' },
        { label: 'Urgency', value: alert.urgency ?? '-' },
        { label: 'Certainty', value: alert.certainty ?? '-' },
        { label: 'Status', value: alert.status },
        { label: 'Berlaku', value: fmtDate(alert.effective) },
        { label: 'Berakhir', value: fmtDate(alert.expires) },
        { label: 'Terdeteksi', value: fmtDate(alert.created_at) },
        { label: 'Matched', value: alert.matched_text ? `${alert.matched_text} (${alert.match_type})` : '-' },
    ];

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            {/* Back */}
            <div>
                <a href="/history" className="text-sm text-muted-foreground hover:text-foreground">
                    ← Kembali ke History
                </a>
            </div>

            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-2xl font-bold">{alert.event ?? 'Alert'}</h1>
                    <p className="text-muted-foreground mt-1">{alert.headline ?? '-'}</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold px-3 py-1 rounded-full ${badgeClass}`}>
                        {alert.severity ?? 'Unknown'}
                    </span>
                    <span className={`text-sm px-3 py-1 rounded-full border ${
                        alert.status === 'active'
                            ? 'border-green-500 text-green-600'
                            : 'border-slate-400 text-slate-500'
                    }`}>
                        {alert.status}
                    </span>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Detail fields */}
                <Card>
                    <CardHeader><CardTitle className="text-base">Informasi Alert</CardTitle></CardHeader>
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
                                className="block text-sm text-blue-500 hover:underline pt-2"
                            >
                                📊 Lihat Infografis BMKG
                            </a>
                        )}
                    </CardContent>
                </Card>

                {/* Map */}
                <Card>
                    <CardHeader><CardTitle className="text-base">Peta Wilayah Terdampak</CardTitle></CardHeader>
                    <CardContent>
                        <MiniMap areas={areas} color={mapColor} />
                        {areas.length > 0 && (
                            <div className="mt-3 space-y-1">
                                {areas.map((a, i) => (
                                    <div key={i} className="text-xs text-muted-foreground flex items-center gap-1.5">
                                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: mapColor }} />
                                        {a.name}
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
                        <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
                            {alert.description}
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Delivery log */}
            <Card>
                <CardHeader><CardTitle className="text-base">Log Pengiriman Notifikasi</CardTitle></CardHeader>
                <CardContent>
                    {deliveries.length === 0 ? (
                        <p className="text-sm text-muted-foreground italic">Belum ada pengiriman notifikasi untuk alert ini.</p>
                    ) : (
                        <div className="space-y-2">
                            {deliveries.map(d => (
                                <div key={d.id} className="flex items-center justify-between text-sm border-b last:border-0 py-2">
                                    <div>
                                        <span className="font-medium">Channel #{d.channel_id}</span>
                                        {d.error_message && (
                                            <p className="text-xs text-red-500 mt-0.5">{d.error_message}</p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-3 text-right">
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                                            d.status === 'sent'
                                                ? 'bg-green-100 text-green-700'
                                                : d.status === 'failed'
                                                ? 'bg-red-100 text-red-700'
                                                : 'bg-slate-100 text-slate-600'
                                        }`}>
                                            {d.status}
                                        </span>
                                        <span className="text-xs text-muted-foreground">{fmtDate(d.sent_at)}</span>
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
