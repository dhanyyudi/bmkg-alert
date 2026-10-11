import React, { useRef, useMemo, useState, useCallback } from 'react';
import { ExternalLink } from 'lucide-react';
import Map, { Source, Layer, NavigationControl, FullscreenControl, Popup } from 'react-map-gl/maplibre';
import type { MapRef, LayerProps, MapLayerMouseEvent } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { splitRings } from '@/lib/polygon';
import type { Alert } from '@/stores/appStore';
import { SEVERITY_ORDER, severityStyle } from '@/lib/severity';
import { fmtDateTime } from '@/lib/format';
import { webglAvailable } from '@/lib/webgl';

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
                color:          severityStyle(alert.severity).mapColor,
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

  if (!webglAvailable) {
    return (
      <div className={`flex items-center justify-center p-6 text-center text-sm text-muted-foreground ${className ?? ''}`}>
        <p>
          Peta tidak bisa ditampilkan karena browser ini tidak mendukung WebGL.
          Daftar peringatan aktif tetap lengkap di panel sebelahnya.
        </p>
      </div>
    );
  }

  return (
    <div className={`relative ${className ?? 'h-full w-full rounded-lg overflow-hidden border border-border'}`}>
      {alerts.length > 0 && polygonCount === 0 && (
        <p className="absolute top-3 left-3 right-14 z-10 bg-amber-50 border border-amber-300 text-amber-800 text-xs px-3 py-2 rounded-md">
          BMKG tidak menyertakan data poligon untuk peringatan yang aktif, jadi wilayahnya tidak bisa digambar.
        </p>
      )}

      <div className="absolute bottom-8 left-3 z-10 bg-card text-card-foreground rounded-md border px-3 py-2 text-xs shadow-sm">
        <p className="font-semibold mb-1.5">Tingkat peringatan</p>
        {SEVERITY_ORDER.map(key => {
          const { label, mapColor } = severityStyle(key);
          return (
            <div key={key} className="flex items-center gap-2 mb-1 last:mb-0">
              <span className="w-3 h-3 rounded-sm flex-shrink-0 border border-black/20" style={{ backgroundColor: mapColor }} />
              <span>{label}</span>
            </div>
          );
        })}
      </div>

      <Map
        ref={mapRef}
        initialViewState={{ longitude: 118, latitude: -2.5, zoom: 4.5 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
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
                  style={{ backgroundColor: severityStyle(popupInfo.severity).mapColor }}
                />
                <div className="min-w-0">
                  <p className="font-bold text-sm text-gray-900 leading-tight">{popupInfo.event} ({severityStyle(popupInfo.severity).label})</p>
                  <p className="text-xs font-medium text-gray-700 mt-0.5">{popupInfo.area}</p>
                </div>
              </div>

              {/* Headline */}
              <p className="text-xs text-gray-600 leading-snug">{popupInfo.headline}</p>

              {/* Dates */}
              <div className="text-xs space-y-0.5 pt-1.5 border-t border-gray-200">
                <div className="flex justify-between gap-3">
                  <span className="text-gray-600">Berlaku</span>
                  <span className="font-medium text-gray-800">{fmtDateTime(popupInfo.effective)}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span className="text-gray-600">Berakhir</span>
                  <span className="font-medium text-gray-800">{fmtDateTime(popupInfo.expires)}</span>
                </div>
              </div>

              {/* Infographic link */}
              {popupInfo.infographic_url && (
                <a
                  href={popupInfo.infographic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-700 hover:underline font-medium"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /> Lihat infografis BMKG
                </a>
              )}
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
};
