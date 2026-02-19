import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Cloud, CloudRain, Sun, Calendar, Droplets, Wind } from 'lucide-react';
import { format } from 'date-fns';
import { id } from 'date-fns/locale';

interface ForecastEntry {
    local_datetime: string;
    utc_datetime: string;
    temperature_c: number;
    humidity_pct: number;
    weather: string;
    weather_en: string;
    weather_code: number;
    wind_speed_kmh: number;
    wind_direction: string;
    wind_direction_deg: number;
    cloud_cover_pct: number;
    visibility_m: number;
    visibility_text: string;
    icon_url: string;
}

interface ForecastDay {
    date: string;
    entries: ForecastEntry[];
}

interface WeatherForecast {
    location: {
        code: string;
        province: string;
        district: string;
        subdistrict: string;
        village: string;
        lat: number;
        lon: number;
        timezone: string;
    };
    forecast: ForecastDay[];
}

interface Props {
    locationCode: string | null;
}

export const WeatherDisplay: React.FC<Props> = ({ locationCode }) => {
    const [forecast, setForecast] = useState<WeatherForecast | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!locationCode) return;

        const fetchWeather = async () => {
            setLoading(true);
            setError(null);
            try {
                // Backend route: GET /v1/weather/{adm4_code} (path parameter)
                const res = await api.get<{ data: WeatherForecast }>(`/weather/${locationCode}`);
                setForecast(res.data);
            } catch (err: any) {
                console.error("Failed to fetch weather:", err);
                setError(err.response?.data?.message || err.message || "Failed to load weather data");
            } finally {
                setLoading(false);
            }
        };

        fetchWeather();
    }, [locationCode]);

    if (!locationCode) {
        return (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Cloud className="h-16 w-16 mb-4 opacity-20" />
                <p>Search and select a location to view weather forecast</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-8 w-3/4" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-40" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
             <div className="p-4 border border-red-200 bg-red-50 text-red-600 rounded-md">
                Error: {error}. Please try selecting a Kelurahan/Desa level location.
            </div>
        );
    }

    if (!forecast) return null;

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold">{forecast.location.village}</h2>
                <p className="text-muted-foreground">
                    {forecast.location.subdistrict}, {forecast.location.district}, {forecast.location.province}
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {forecast.forecast.map((day) => {
                    const items = day.entries;
                    const mainForecast = items.find(i => i.local_datetime.includes("12:00:00")) || items[0];

                    return (
                        <Card key={day.date} className="overflow-hidden">
                            <CardHeader className="bg-muted/50 pb-3">
                                <CardTitle className="flex items-center gap-2 text-base">
                                    <Calendar className="h-4 w-4" />
                                    {format(new Date(day.date), 'EEEE, d MMMM yyyy', { locale: id })}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-4 space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        {mainForecast.weather_code >= 60 ? (
                                            <CloudRain className="h-10 w-10 text-blue-500" />
                                        ) : mainForecast.weather_code >= 3 ? (
                                            <Cloud className="h-10 w-10 text-slate-500" />
                                        ) : (
                                            <Sun className="h-10 w-10 text-orange-500" />
                                        )}
                                        <div>
                                            <p className="font-semibold text-lg">{mainForecast.weather}</p>
                                            <p className="text-xs text-muted-foreground">{mainForecast.weather_en}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <span className="text-3xl font-bold">{mainForecast.temperature_c}°C</span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    <div className="flex items-center gap-2 text-muted-foreground">
                                        <Droplets className="h-4 w-4" />
                                        <span>Humidity: {mainForecast.humidity_pct}%</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-muted-foreground">
                                        <Wind className="h-4 w-4" />
                                        <span>{mainForecast.wind_speed_kmh} km/h {mainForecast.wind_direction}</span>
                                    </div>
                                </div>

                                <div className="pt-2 border-t">
                                     <div className="flex justify-between text-xs text-center">
                                         {items.filter((_, idx) => idx % 2 === 0).slice(0, 4).map((entry) => (
                                             <div key={entry.local_datetime}>
                                                 <p className="mb-1 text-muted-foreground">
                                                     {format(new Date(entry.local_datetime.replace(' ', 'T')), 'HH:mm')}
                                                 </p>
                                                 <p className="font-medium">{entry.temperature_c}°</p>
                                             </div>
                                         ))}
                                     </div>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
};
