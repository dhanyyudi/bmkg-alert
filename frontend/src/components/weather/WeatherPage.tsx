import React, { useState, useEffect } from 'react';
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

export const WeatherPage: React.FC = () => {
    const [locationCode, setLocationCode] = useState<string | null>(null);
    const [activeCode, setActiveCode] = useState<string | null>(null);
    const [monitored, setMonitored] = useState<MonitoredLocation[]>([]);

    useEffect(() => {
        api.get<{ data: MonitoredLocation[] }>('/locations')
            .then(res => {
                const enabled = (res.data ?? []).filter(l => l.enabled);
                setMonitored(enabled);
                if (enabled.length > 0) {
                    setLocationCode(enabled[0].subdistrict_code);
                    setActiveCode(enabled[0].subdistrict_code);
                }
            })
            .catch(() => { /* silent */ });
    }, []);

    const selectMonitored = (loc: MonitoredLocation) => {
        setLocationCode(loc.subdistrict_code);
        setActiveCode(loc.subdistrict_code);
    };

    const selectSearch = (code: string) => {
        setLocationCode(code);
        setActiveCode(null); // deselect monitored pills when using search
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Weather Forecast</h1>
                    <p className="text-muted-foreground">
                        Get detailed weather forecasts for any location in Indonesia.
                    </p>
                </div>
                <div className="w-full md:w-[300px]">
                    <LocationSearch onSelect={(loc) => selectSearch(loc.code)} />
                </div>
            </div>

            {/* Monitored locations quick-select pills */}
            {monitored.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {monitored.map(loc => {
                        const isActive = activeCode === loc.subdistrict_code;
                        return (
                            <button
                                key={loc.id}
                                onClick={() => selectMonitored(loc)}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                                    isActive
                                        ? 'bg-blue-600 text-white border-blue-600'
                                        : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400'
                                }`}
                            >
                                <MapPin className="h-3.5 w-3.5 shrink-0" />
                                {loc.label || loc.subdistrict_name}
                            </button>
                        );
                    })}
                </div>
            )}

            <WeatherDisplay locationCode={locationCode} />
        </div>
    );
};
