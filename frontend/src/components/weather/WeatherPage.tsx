import React, { useState } from 'react';
import { LocationSearch } from './LocationSearch';
import { WeatherDisplay } from './WeatherDisplay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const WeatherPage: React.FC = () => {
    const [locationCode, setLocationCode] = useState<string | null>(null);

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
                     <LocationSearch 
                        onSelect={(loc) => setLocationCode(loc.code)} 
                    />
                </div>
            </div>

            <WeatherDisplay locationCode={locationCode} />
        </div>
    );
};
