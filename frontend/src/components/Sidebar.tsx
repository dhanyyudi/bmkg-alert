import React, { useState, useEffect } from 'react';
import { Home, History, Settings, Send, Menu, X, CloudRain, CloudSun, Sun, Moon, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SidebarProps {
    pathname?: string;
}

const MENU_ITEMS = [
    { label: 'Dasbor', icon: Home, href: '/' },
    { label: 'Prakiraan cuaca', icon: CloudSun, href: '/weather' },
    { label: 'Riwayat', icon: History, href: '/history' },
    { label: 'Pengaturan', icon: Settings, href: '/settings' },
    { label: 'Coba via Telegram', icon: Send, href: '/try' },
    { label: 'Pasang sendiri', icon: Server, href: '/deploy' },
];

export const Sidebar: React.FC<SidebarProps> = ({ pathname }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [isDark, setIsDark] = useState(false);

    // Sync with DOM after hydration (SSR initializes to false)
    useEffect(() => {
        setIsDark(document.documentElement.classList.contains('dark'));
    }, []);

    useEffect(() => {
        if (!isOpen) return;
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setIsOpen(false); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [isOpen]);

    const toggleTheme = () => {
        // Read the live DOM state: the inline script in Layout may have set it before React did
        const next = !document.documentElement.classList.contains('dark');
        document.documentElement.classList.toggle('dark', next);
        localStorage.setItem('bmkg-theme', next ? 'dark' : 'light');
        setIsDark(next);
    };

    const currentPath = pathname || (typeof window !== 'undefined' ? window.location.pathname : '/');

    return (
        <>
            {/* Phone/tablet top bar: reserves its own height in Layout so it never covers content */}
            <header className="md:hidden fixed top-0 inset-x-0 z-30 h-14 flex items-center gap-2 px-2 bg-card border-b">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsOpen(true)}
                    aria-expanded={isOpen}
                    aria-controls="app-sidebar"
                >
                    <Menu className="h-5 w-5 mr-2" aria-hidden="true" /> Menu
                </Button>
                <span className="font-bold">BMKG Alert</span>
            </header>

            <aside
                id="app-sidebar"
                className={`
                    fixed top-0 left-0 z-50 h-dvh w-64 bg-card border-r transition-transform duration-200
                    ${isOpen ? 'translate-x-0' : '-translate-x-full max-md:invisible'}
                    md:translate-x-0 md:static md:h-screen md:shrink-0
                `}
            >
                <div className="flex flex-col h-full">
                    <div className="h-14 md:h-16 flex items-center justify-between px-4 md:px-6 border-b">
                        <a href="/" className="flex items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                            <CloudRain className="h-6 w-6 text-blue-600 dark:text-blue-400 mr-2" aria-hidden="true" />
                            <span className="font-bold text-lg">BMKG Alert</span>
                        </a>
                        <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsOpen(false)} aria-label="Tutup menu">
                            <X className="h-5 w-5" aria-hidden="true" />
                        </Button>
                    </div>

                    <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Navigasi utama">
                        {MENU_ITEMS.map((item) => {
                            const Icon = item.icon;
                            const isActive = currentPath === item.href || (item.href !== '/' && currentPath.startsWith(item.href));

                            return (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    aria-current={isActive ? 'page' : undefined}
                                    className={`
                                        flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors
                                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
                                        ${isActive
                                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200'
                                            : 'text-slate-700 hover:bg-accent dark:text-slate-300'
                                        }
                                    `}
                                >
                                    <Icon className="mr-3 h-5 w-5" aria-hidden="true" />
                                    {item.label}
                                </a>
                            );
                        })}
                    </nav>

                    <div className="p-3 border-t">
                        <Button variant="ghost" size="sm" onClick={toggleTheme} className="w-full justify-start">
                            {isDark
                                ? <><Sun className="h-4 w-4 mr-3" aria-hidden="true" /> Tema terang</>
                                : <><Moon className="h-4 w-4 mr-3" aria-hidden="true" /> Tema gelap</>}
                        </Button>
                    </div>
                </div>
            </aside>

            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 md:hidden"
                    onClick={() => setIsOpen(false)}
                    aria-hidden="true"
                />
            )}
        </>
    );
};
