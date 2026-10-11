import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Search, MapPin, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface SearchResult {
    code: string;
    name: string;
    level: string;
    full_path: string;
    parent_code: string;
}

interface Props {
    onSelect: (location: SearchResult) => void;
    className?: string;
}

const MIN_QUERY = 3;
const LEVEL_LABEL: Record<string, string> = { subdistrict: 'Kecamatan', village: 'Kelurahan/desa' };

export const LocationSearch: React.FC<Props> = ({ onSelect, className }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [state, setState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
    const [debouncedQuery, setDebouncedQuery] = useState('');

    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(query.trim()), 400);
        return () => clearTimeout(timer);
    }, [query]);

    useEffect(() => {
        if (debouncedQuery.length < MIN_QUERY) {
            setResults([]);
            setState('idle');
            return;
        }
        let cancelled = false;
        setState('loading');
        api.get<{ data: SearchResult[] }>(`/wilayah/search?q=${encodeURIComponent(debouncedQuery)}&limit=20`)
            .then(res => {
                if (cancelled) return;
                // Forecasts only exist below kecamatan level, so provinces and kabupaten are left out
                setResults((res.data ?? []).filter(r => r.level in LEVEL_LABEL));
                setState('ready');
            })
            .catch(error => {
                if (cancelled) return;
                console.error('Search failed:', error);
                setResults([]);
                setState('error');
            });
        return () => { cancelled = true; };
    }, [debouncedQuery]);

    const showPanel = state === 'ready' || state === 'error';

    return (
        <div className={`relative ${className ?? ''}`}>
            <label htmlFor="weather-search" className="sr-only">Cari kecamatan atau desa</label>
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <Input
                    id="weather-search"
                    type="search"
                    placeholder="Cari kecamatan atau desa, misalnya Tebet"
                    className="pl-9"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
                {state === 'loading' && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" aria-label="Mencari" />
                )}
            </div>

            {showPanel && (
                <Card className="absolute z-50 mt-1 w-full max-h-[300px] overflow-y-auto p-1 shadow-lg">
                    {state === 'error' && (
                        <p className="p-3 text-sm text-muted-foreground">Pencarian gagal. Server tidak merespons, coba lagi sebentar.</p>
                    )}
                    {state === 'ready' && results.length === 0 && (
                        <p className="p-3 text-sm text-muted-foreground">Tidak ada kecamatan atau desa dengan nama itu.</p>
                    )}
                    {results.map((result) => (
                        <button
                            key={result.code}
                            type="button"
                            className="w-full min-h-11 flex items-center text-left rounded-md py-2 px-3 hover:bg-accent focus-visible:outline-none focus-visible:bg-accent"
                            onClick={() => {
                                onSelect(result);
                                setQuery('');
                                setResults([]);
                                setState('idle');
                            }}
                        >
                            <MapPin className="mr-2 h-4 w-4 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
                            <span className="flex flex-col overflow-hidden">
                                <span className="truncate text-sm font-medium">{result.name} <span className="font-normal text-muted-foreground">({LEVEL_LABEL[result.level]})</span></span>
                                <span className="truncate text-xs text-muted-foreground">{result.full_path}</span>
                            </span>
                        </button>
                    ))}
                </Card>
            )}
        </div>
    );
};
