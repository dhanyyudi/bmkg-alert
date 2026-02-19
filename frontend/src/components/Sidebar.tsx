import React, { useState, useEffect } from 'react';
import { Home, History, Settings, PlayCircle, Menu, X, CloudRain, Sun, Moon, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SidebarProps {
    pathname?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ pathname }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [isDark, setIsDark] = useState(false);

    // Sync with DOM after hydration (SSR initializes to false)
    useEffect(() => {
        setIsDark(document.documentElement.classList.contains('dark'));
    }, []);

    const toggleTheme = () => {
        // Always read the live DOM state — avoids stale React state bugs
        const currentlyDark = document.documentElement.classList.contains('dark');
        const next = !currentlyDark;
        document.documentElement.classList.toggle('dark', next);
        localStorage.setItem('bmkg-theme', next ? 'dark' : 'light');
        setIsDark(next);
    };

    const toggleSidebar = () => setIsOpen(!isOpen);

    const menuItems = [
        { label: 'Dashboard', icon: Home, href: '/' },
        { label: 'Weather', icon: CloudRain, href: '/weather' },
        { label: 'History', icon: History, href: '/history' },
        { label: 'Settings', icon: Settings, href: '/settings' },
        { label: 'Try Mode', icon: PlayCircle, href: '/try' },
        { label: 'Deploy', icon: Server, href: '/deploy' },
    ];

    // Get current path for active state highlighting (simple check)
    // Use prop if available (SSR/Astro), otherwise fallback to window
    const currentPath = pathname || (typeof window !== 'undefined' ? window.location.pathname : '/');

    return (
        <>
            {/* Mobile Toggle Button */}
            <div className="md:hidden fixed top-4 left-4 z-50">
                <Button variant="outline" size="icon" onClick={toggleSidebar}>
                    {isOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                </Button>
            </div>

            {/* Sidebar Container */}
            <aside className={`
                fixed top-0 left-0 z-40 h-screen w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-transform duration-300 ease-in-out
                ${isOpen ? 'translate-x-0' : '-translate-x-full'}
                md:translate-x-0 md:static
            `}>
                <div className="flex flex-col h-full">
                    {/* Header/Logo */}
                    <div className="h-16 flex items-center px-6 border-b border-slate-200 dark:border-slate-800">
                        <CloudRain className="h-6 w-6 text-blue-600 mr-2" />
                        <span className="font-bold text-lg text-slate-900 dark:text-white">BMKG Alert</span>
                    </div>

                    {/* Navigation Links */}
                    <nav className="flex-1 px-4 py-6 space-y-1">
                        {menuItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = currentPath === item.href || (item.href !== '/' && currentPath.startsWith(item.href));
                            
                            return (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    className={`
                                        flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors
                                        ${isActive 
                                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-200' 
                                            : 'text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/50'
                                        }
                                    `}
                                >
                                    <Icon className={`mr-3 h-5 w-5 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`} />
                                    {item.label}
                                </a>
                            );
                        })}
                    </nav>

                    {/* Footer / Version + Theme Toggle */}
                    <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                        <p className="text-xs text-slate-500">v0.1.0 Beta</p>
                        <button
                            onClick={toggleTheme}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            aria-label="Toggle dark mode"
                        >
                            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                        </button>
                    </div>
                </div>
            </aside>
            
            {/* Overlay for mobile */}
            {isOpen && (
                <div 
                    className="fixed inset-0 bg-black/50 z-30 md:hidden"
                    onClick={toggleSidebar}
                />
            )}
        </>
    );
};
