import { useEffect } from 'react';
import { api } from '@/lib/api';

/**
 * Invisible component that checks if setup has been completed.
 * If `setup_completed` is not "true" in the backend config, redirects to /setup.
 */
export const SetupCheck: React.FC = () => {
    useEffect(() => {
        api.get<{ data: Record<string, string> }>('/config')
            .then(res => {
                const cfg = res.data;
                // In demo mode the admin already completed setup — skip redirect for all visitors
                const isDemoMode = cfg?.demo_mode === 'true';
                if (!isDemoMode && cfg?.setup_completed !== 'true') {
                    window.location.href = '/setup';
                }
            })
            .catch(() => {
                // If config not available, don't redirect — backend may be starting up
            });
    }, []);

    return null;
};
