import React, { useState } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Trash2, MapPin, Search, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { MONITOR_LEVELS, levelLabel, regionContext, searchRegions, toLocationPayload, type WilayahResult } from '@/lib/wilayah';

// ─── Types ────────────────────────────────────────────────────────────────────


interface Location {
    id: number;
    label: string | null;
    subdistrict_name: string;
    district_name: string;
    province_name: string;
}

interface Props {
    locations: Location[];
    onUpdate: () => void;
}

// ─── Helper: map WilayahResult → LocationCreate payload ──────────────────────


// ─── Component ────────────────────────────────────────────────────────────────

export const LocationStep: React.FC<Props> = ({ locations, onUpdate }) => {
    const [search, setSearch] = useState('');
    const [results, setResults] = useState<WilayahResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [adding, setAdding] = useState<string | null>(null);

    const handleSearch = async () => {
        const q = search.trim();
        if (q.length < 2) {
            toast.error('Ketik minimal 2 huruf untuk mencari');
            return;
        }
        setSearching(true);
        setResults([]);
        try {
            const data = await searchRegions(q, MONITOR_LEVELS);
            setResults(data);
            if (data.length === 0) {
                toast.info(`Tidak ada hasil untuk "${q}"`, {
                    description: 'Periksa ejaannya. Yang bisa dipantau adalah kecamatan atau kabupaten/kota.',
                });
            }
        } catch (e: any) {
            toast.error('Pencarian gagal', {
                description: e?.message ?? 'Server tidak merespons.',
            });
        } finally {
            setSearching(false);
        }
    };

    const addLocation = async (loc: WilayahResult) => {
        setAdding(loc.code);
        try {
            await api.post('/locations', toLocationPayload(loc));
            onUpdate();
            setResults([]);
            setSearch('');
            toast.success(`Lokasi "${loc.name}" ditambahkan`, {
                description: regionContext(loc),
            });
        } catch (e: any) {
            if (e?.status === 409) {
                toast.error('Lokasi sudah ada', {
                    description: `${loc.name} sudah ada di daftar pantauan.`,
                });
            } else {
                toast.error('Gagal menambahkan lokasi', {
                    description: e?.message ?? 'Server tidak merespons.',
                });
            }
        } finally {
            setAdding(null);
        }
    };

    const removeLocation = async (id: number, name: string) => {
        try {
            await api.delete(`/locations/${id}`);
            onUpdate();
            toast.success(`Lokasi "${name}" dihapus`);
        } catch (e: any) {
            toast.error('Gagal menghapus lokasi', {
                description: e?.message ?? 'Server tidak merespons.',
            });
        }
    };

    return (
        <div className="space-y-6">
            {/* Search input */}
            <label htmlFor="setup-location-search" className="text-sm font-medium block">Cari kecamatan atau kabupaten/kota yang ingin dipantau</label>
            <div className="flex gap-2">
                <Input
                    id="setup-location-search"
                    placeholder="Minimal 2 huruf, misalnya Wiradesa"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                />
                <Button onClick={handleSearch} disabled={searching} className="shrink-0">
                    {searching
                        ? <Loader2 className="h-4 w-4 animate-spin mr-2" aria-hidden="true" />
                        : <Search className="h-4 w-4 mr-2" aria-hidden="true" />
                    }
                    Cari
                </Button>
            </div>

            {/* Search results dropdown */}
            {results.length > 0 && (
                <div className="border rounded-md divide-y max-h-48 overflow-y-auto">
                    {results.map(res => (
                        <div
                            key={res.code}
                            className="p-2 flex justify-between items-center gap-2"
                        >
                            <div className="text-sm min-w-0">
                                <p className="font-medium truncate">{res.name} <span className="font-normal text-muted-foreground">({levelLabel(res.level)})</span></p>
                                <p className="text-xs text-muted-foreground truncate">{regionContext(res)}</p>
                            </div>
                            <Button
                                size="sm"
                                variant="outline"
                                disabled={adding === res.code}
                                onClick={() => addLocation(res)}
                                className="shrink-0"
                            >
                                {adding === res.code
                                    ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" aria-hidden="true" />
                                    : <Plus className="h-4 w-4 mr-1.5" aria-hidden="true" />
                                }
                                Pantau
                            </Button>
                        </div>
                    ))}
                </div>
            )}

            {/* Selected locations list */}
            <div className="space-y-2">
                <h3 className="text-sm font-semibold">Lokasi yang dipantau</h3>
                {locations.length === 0 ? (
                    <div className="text-center p-4 border border-dashed rounded text-sm text-muted-foreground">
                        Belum ada lokasi. Cari kecamatan atau kabupaten/kota di atas, lalu tekan Pantau.
                    </div>
                ) : (
                    locations.map(loc => (
                        <div
                            key={loc.id}
                            className="flex items-center justify-between p-3 border rounded-md bg-card"
                        >
                            <div className="flex items-center gap-3 min-w-0">
                                <MapPin className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                                <div className="min-w-0">
                                    <p className="font-medium text-sm truncate">
                                        {loc.label || loc.subdistrict_name}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                        {loc.district_name}, {loc.province_name}
                                    </p>
                                </div>
                            </div>
                            <Button
                                size="icon"
                                variant="ghost"
                                className="text-red-600 dark:text-red-400 shrink-0"
                                aria-label={`Hapus lokasi ${loc.label || loc.subdistrict_name}`}
                                onClick={() => removeLocation(loc.id, loc.label || loc.subdistrict_name)}
                            >
                                <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </Button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
