import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
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

export const LocationSearch: React.FC<Props> = ({ onSelect, className }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [debouncedQuery, setDebouncedQuery] = useState('');

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedQuery(query);
        }, 500);
        return () => clearTimeout(timer);
    }, [query]);

    useEffect(() => {
        const search = async () => {
            if (debouncedQuery.length < 3) {
                setResults([]);
                return;
            }

            setLoading(true);
            try {
                const res = await api.get<{ data: SearchResult[] }>(`/wilayah/search?q=${encodeURIComponent(debouncedQuery)}&limit=10`);
                setResults(res.data);
            } catch (error) {
                console.error("Search failed:", error);
            } finally {
                setLoading(false);
            }
        };

        search();
    }, [debouncedQuery]);

    return (
        <div className={`relative ${className}`}>
             <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                    type="search"
                    placeholder="Search location (e.g. Tebet)..."
                    className="pl-9"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
                {loading && (
                    <div className="absolute right-3 top-2.5">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                )}
            </div>

            {results.length > 0 && (
                <Card className="absolute z-50 mt-1 w-full max-h-[300px] overflow-y-auto p-1 shadow-lg">
                    {results.map((result) => (
                        <Button
                            key={result.code}
                            variant="ghost"
                            className="w-full justify-start text-left h-auto py-2 px-3"
                            onClick={() => {
                                onSelect(result);
                                setQuery('');
                                setResults([]);
                            }}
                        >
                            <MapPin className="mr-2 h-4 w-4 flex-shrink-0 text-muted-foreground" />
                            <div className="flex flex-col overflow-hidden">
                                <span className="truncate font-medium">{result.name}</span>
                                <span className="truncate text-xs text-muted-foreground">
                                    {result.full_path}
                                </span>
                            </div>
                        </Button>
                    ))}
                </Card>
            )}
        </div>
    );
};
