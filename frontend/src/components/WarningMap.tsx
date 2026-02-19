import React, { useRef, useMemo, useState, useCallback } from 'react';
import Map, { Source, Layer, NavigationControl, FullscreenControl, Popup } from 'react-map-gl/maplibre';
import type { MapRef, LayerProps, MapLayerMouseEvent } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { splitRings } from '@/lib/polygon';
import type { Alert } from '@/stores/appStore';

interface WarningMapProps {
  alerts: Alert[];
  className?: string;
}

interface PopupState {
  longitude: number;
  latitude: number;
  event: string;
  headline: string;
  area: string;
  severity: string;
  effective: string;
  expires: string;
  infographic_url: string | null;
}

const SEVERITY_COLOR: Record<string, string> = {
  extreme:  '#7f1d1d',
  severe:   '#ef4444',
  moderate: '#f59e0b',
  minor:    '#3b82f6',
};

const LEGEND_ITEMS = [
  { label: 'Extreme', color: '#7f1d1d' },
  { label: 'Severe',  color: '#ef4444' },
  { label: 'Moderate', color: '#f59e0b' },
  { label: 'Minor',   color: '#3b82f6' },
];

const getSeverityColor = (severity: string): string => {
  const key = severity?.toLowerCase() ?? '';
  return SEVERITY_COLOR[key] ?? '#10b981';
};

const SOURCE_ID = 'alerts-polygon-source';
const FILL_LAYER_ID = 'alerts-fill';
const OUTLINE_LAYER_ID = 'alerts-outline';

export const WarningMap: React.FC<WarningMapProps> = ({ alerts, className }) => {
  const mapRef = useRef<MapRef>(null);
  const [popupInfo, setPopupInfo] = useState<PopupState | null>(null);

  // Derived flag: how many alerts actually have polygon data
  const polygonCount = useMemo(
    () => alerts.reduce((n, a) => n + (a.areas ?? []).filter(ar => ar.polygon && ar.polygon.length > 0).length, 0),
    [alerts],
  );

  // Build GeoJSON FeatureCollection from all alert areas
  const geoJsonData = useMemo(() => {
    const features: any[] = [];

    for (const alert of alerts) {
      for (const area of alert.areas ?? []) {
        if (!area.polygon || area.polygon.length === 0) continue;
        try {
          const rings = splitRings(area.polygon);
          for (const ring of rings) {
            features.push({
              type: 'Feature',
              geometry: { type: 'Polygon', coordinates: [ring] },
              properties: {
                event:          alert.event ?? '',
                headline:       alert.headline ?? '',
                severity:       alert.severity ?? '',
                area:           area.name ?? '',
                effective:      alert.effective ?? '',
                expires:        alert.expires ?? '',
                infographic_url: alert.infographic_url ?? null,
                color:          getSeverityColor(alert.severity),
              },
            });
          }
        } catch (e) {
          console.error('Polygon processing error for', alert.identifier, area.name, e);
        }
      }
    }

    return { type: 'FeatureCollection', features } as GeoJSON.FeatureCollection;
  }, [alerts]);

  const fillLayerStyle: LayerProps = {
    id: FILL_LAYER_ID,
    type: 'fill',
    paint: {
      'fill-color': ['get', 'color'],
      'fill-opacity': 0.45,
    },
  };

  const outlineLayerStyle: LayerProps = {
    id: OUTLINE_LAYER_ID,
    type: 'line',
    paint: {
      'line-color': ['get', 'color'],
      'line-width': 2,
    },
  };

  const handleMapClick = useCallback((e: MapLayerMouseEvent) => {
    const features = e.features;
    if (!features || features.length === 0) {
      setPopupInfo(null);
      return;
    }
    const f = features[0];
    const props = f.properties ?? {};
    setPopupInfo({
      longitude: e.lngLat.lng,
      latitude:  e.lngLat.lat,
      event:          props.event ?? '',
      headline:       props.headline ?? '',
      area:           props.area ?? '',
      severity:       props.severity ?? '',
      effective:      props.effective ?? '',
      expires:        props.expires ?? '',
      infographic_url: props.infographic_url ?? null,
    });
  }, []);

  const fmtDate = (iso: string) => {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
    } catch { return iso; }
  };

  return (
    <div className={`relative ${className ?? 'h-full w-full rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800'}`}>
      {/* Fallback badge when no polygon data is available */}
      {alerts.length > 0 && polygonCount === 0 && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 bg-amber-100 border border-amber-400 text-amber-800 text-xs font-medium px-3 py-1.5 rounded-full shadow">
          ⚠️ Data polygon tidak tersedia dari BMKG untuk peringatan aktif
        </div>
      )}

      {/* Severity legend */}
      <div className="absolute bottom-3 left-3 z-10 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 shadow-md text-xs pointer-events-none">
        <p className="font-semibold text-slate-600 dark:text-slate-300 mb-1.5 tracking-wide uppercase text-[10px]">Severity</p>
        {LEGEND_ITEMS.map(({ label, color }) => (
          <div key={label} className="flex items-center gap-2 mb-1 last:mb-0">
            <span
              className="w-3 h-3 rounded-sm flex-shrink-0 border border-black/10"
              style={{ backgroundColor: color }}
            />
            <span className="text-slate-700 dark:text-slate-300">{label}</span>
          </div>
        ))}
      </div>

      <Map
        ref={mapRef}
        initialViewState={{ longitude: 118, latitude: -2.5, zoom: 4.5 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
        attributionControl={false}
        interactiveLayerIds={[FILL_LAYER_ID]}
        onClick={handleMapClick}
        cursor="pointer"
      >
        <NavigationControl position="top-right" />
        <FullscreenControl position="top-right" />

        <Source id={SOURCE_ID} type="geojson" data={geoJsonData}>
          <Layer {...fillLayerStyle} />
          <Layer {...outlineLayerStyle} />
        </Source>

        {popupInfo && (
          <Popup
            longitude={popupInfo.longitude}
            latitude={popupInfo.latitude}
            anchor="bottom"
            onClose={() => setPopupInfo(null)}
            closeButton={false}
            maxWidth="300px"
          >
            <div className="p-2 space-y-2 min-w-[220px]">
              {/* Severity dot + event + area */}
              <div className="flex items-start gap-2">
                <span
                  className="shrink-0 mt-1 w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: getSeverityColor(popupInfo.severity) }}
                />
                <div className="min-w-0">
                  <p className="font-bold text-sm text-gray-900 leading-tight">{popupInfo.event}</p>
                  <p className="text-xs font-medium text-gray-700 mt-0.5">{popupInfo.area}</p>
                </div>
              </div>

              {/* Headline */}
              <p className="text-xs text-gray-600 leading-snug">{popupInfo.headline}</p>

              {/* Dates */}
              <div className="text-xs space-y-0.5 pt-1.5 border-t border-gray-200">
                <div className="flex justify-between gap-3">
                  <span className="text-gray-400">Berlaku</span>
                  <span className="font-medium text-gray-800">{fmtDate(popupInfo.effective)}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-gray-400">Berakhir</span>
                  <span className="font-medium text-gray-800">{fmtDate(popupInfo.expires)}</span>
                </div>
              </div>

              {/* Infographic link */}
              {popupInfo.infographic_url && (
                <a
                  href={popupInfo.infographic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
                >
                  📊 Lihat Infografis BMKG ↗
                </a>
              )}
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
};
