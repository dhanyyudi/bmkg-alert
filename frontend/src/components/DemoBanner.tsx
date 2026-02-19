import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

/**
 * Shows a banner when the backend is running in demo mode.
 * Demo mode = read-only, no real notifications sent.
 */
export const DemoBanner: React.FC = () => {
    const [isDemoMode, setIsDemoMode] = useState(false);

    useEffect(() => {
        api.get<{ data: Record<string, string> }>('/config')
            .then(res => {
                setIsDemoMode(res.data?.demo_mode === 'true');
            })
            .catch(() => {});
    }, []);

    if (!isDemoMode) return null;

    return (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-800 text-sm dark:bg-amber-950 dark:border-amber-700 dark:text-amber-200">
            <span className="font-bold">Demo Mode</span>
            <span>—</span>
            <span>
                Sistem berjalan dalam mode demo. Notifikasi tidak akan dikirim ke channel nyata.
                Data hanya untuk keperluan demonstrasi.
            </span>
        </div>
    );
};
