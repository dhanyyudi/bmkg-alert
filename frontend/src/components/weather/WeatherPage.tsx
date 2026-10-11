import React, { useState, useEffect, useCallback } from 'react';
import { LocationSearch } from './LocationSearch';
import { WeatherDisplay } from './WeatherDisplay';
import { api } from '@/lib/api';
import { MapPin } from 'lucide-react';

type MonitoredLocation = {
    id: number;
    label: string | null;
    subdistrict_name: string;
    district_name: string;
    subdistrict_code: string;
    enabled: boolean;
};

type Village = { code: string; name: string };

// BMKG forecasts exist per kelurahan/desa (4-part code); monitored locations are kecamatan (3-part)
const isVillageCode = (code: string) => code.split('.').length === 4;

export const WeatherPage: React.FC = () => {
    const [areaCode, setAreaCode] = useState<string | null>(null);
    const [villages, setVillages] = useState<Village[]>([]);
    const [villageCode, setVillageCode] = useState<string | null>(null);
    const [villageError, setVillageError] = useState(false);
    const [monitored, setMonitored] = useState<MonitoredLocation[]>([]);

    const selectArea = useCallback(async (code: string) => {
        setAreaCode(code);
        setVillageError(false);
        if (isVillageCode(code)) {
            setVillages([]);
            setVillageCode(code);
            return;
        }
        setVillageCode(null);
        try {
            const res = await api.get<{ data: Village[] }>(`/wilayah/villages?subdistrict=${encodeURIComponent(code)}`);
            const list = res.data ?? [];
            setVillages(list);
            setVillageCode(list[0]?.code ?? null);
            if (list.length === 0) setVillageError(true);
        } catch (e) {
            console.error('Failed to load villages', e);
            setVillages([]);
            setVillageError(true);
        }
    }, []);

    useEffect(() => {
        api.get<{ data: MonitoredLocation[] }>('/locations')
            .then(res => {
                const enabled = (res.data ?? []).filter(l => l.enabled);
                setMonitored(enabled);
                if (enabled.length > 0) selectArea(enabled[0].subdistrict_code);
            })
            .catch(e => console.error('Failed to load monitored locations', e));
    }, [selectArea]);

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Prakiraan cuaca</h1>
                    <p className="text-muted-foreground">Prakiraan BMKG tiga hari ke depan, per kelurahan atau desa.</p>
                </div>
                <div className="w-full md:w-[320px]">
                    <LocationSearch onSelect={(loc) => selectArea(loc.code)} />
                </div>
            </div>

            {monitored.length > 0 && (
                <div className="flex flex-wrap gap-2" role="group" aria-label="Lokasi yang dipantau">
                    {monitored.map(loc => {
                        const isActive = areaCode === loc.subdistrict_code;
                        return (
                            <button
                                key={loc.id}
                                type="button"
                                aria-pressed={isActive}
                                onClick={() => selectArea(loc.subdistrict_code)}
                                className={`inline-flex items-center gap-1.5 min-h-11 md:min-h-9 px-4 rounded-md text-sm font-medium border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${
                                    isActive
                                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white'
                                        : 'bg-card border-input hover:bg-accent'
                                }`}
                            >
                                <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
                                {loc.label || loc.subdistrict_name}
                            </button>
                        );
                    })}
                </div>
            )}

            {villages.length > 0 && (
                <div className="space-y-1 max-w-sm">
                    <label htmlFor="weather-village" className="text-sm font-medium block">Kelurahan/desa</label>
                    <select
                        id="weather-village"
                        value={villageCode ?? ''}
                        onChange={e => setVillageCode(e.target.value)}
                        className="flex h-11 md:h-10 w-full rounded-md border border-input bg-background px-3 text-base md:text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
                    >
                        {villages.map(v => <option key={v.code} value={v.code}>{v.name}</option>)}
                    </select>
                </div>
            )}

            {villageError ? (
                <p className="text-sm text-muted-foreground">
                    Daftar kelurahan/desa untuk kecamatan ini tidak bisa dimuat. Cari nama desanya langsung lewat kolom pencarian.
                </p>
            ) : (
                <WeatherDisplay locationCode={villageCode} />
            )}
        </div>
    );
};
