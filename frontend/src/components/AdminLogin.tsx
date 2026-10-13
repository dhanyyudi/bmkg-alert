import React, { useState } from 'react';
import { useStore } from '@nanostores/react';
import { toast } from 'sonner';
import { Lock, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { adminLogin, adminLogout, engineStatus, isAdmin } from '@/stores/appStore';

/**
 * Admin sign-in for a locked instance. `expanded` shows the password field
 * straight away, for places where signing in is the next step.
 */
export const AdminLogin: React.FC<{ expanded?: boolean; idPrefix?: string }> = ({ expanded = false, idPrefix = 'admin' }) => {
    const status = useStore(engineStatus);
    const admin = useStore(isAdmin);
    const [open, setOpen] = useState(expanded);
    const [password, setPassword] = useState('');
    const [busy, setBusy] = useState(false);

    if (admin) {
        return (
            <Button
                variant="outline"
                size="sm"
                onClick={() => { adminLogout(); toast.info('Anda keluar dari mode admin'); }}
            >
                <LogOut className="w-4 h-4 mr-1.5" aria-hidden="true" /> Keluar
            </Button>
        );
    }

    if (!status.admin_login_available) {
        return (
            <p className="text-sm">
                Login admin belum aktif: ganti <code className="font-mono">ADMIN_PASSWORD</code> di server dari nilai bawaannya.
            </p>
        );
    }

    if (!open) {
        return (
            <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
                <Lock className="w-4 h-4 mr-1.5" aria-hidden="true" /> Masuk admin
            </Button>
        );
    }

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setBusy(true);
        const ok = await adminLogin(password);
        setBusy(false);
        if (ok) {
            toast.success('Berhasil masuk sebagai admin');
            setPassword('');
            setOpen(expanded);
        } else {
            toast.error('Kata sandi salah, atau terlalu banyak percobaan. Coba lagi sebentar.');
        }
    };

    return (
        <form onSubmit={submit} className="flex items-center gap-2 flex-wrap">
            <label htmlFor={`${idPrefix}-password`} className="sr-only">Kata sandi admin</label>
            <Input
                id={`${idPrefix}-password`}
                type="password"
                autoComplete="current-password"
                placeholder="Kata sandi admin"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-48 text-foreground"
                autoFocus={!expanded}
            />
            <Button type="submit" size="sm" disabled={busy || !password}>
                {busy ? 'Memeriksa...' : 'Masuk'}
            </Button>
            {!expanded && (
                <Button type="button" variant="ghost" size="sm" onClick={() => { setOpen(false); setPassword(''); }}>
                    Batal
                </Button>
            )}
        </form>
    );
};
