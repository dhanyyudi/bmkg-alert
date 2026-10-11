import React from 'react';
import { CloudLightning, CloudRain, Waves, Wind } from 'lucide-react';

/** Picks the weather glyph that matches a BMKG event name ("Hujan Lebat dan Petir", "Angin Kencang", ...). */
export const EventIcon: React.FC<{ event: string | null | undefined; className?: string }> = ({ event, className }) => {
    const e = (event ?? '').toLowerCase();
    const Icon =
        e.includes('petir') ? CloudLightning
        : e.includes('angin') || e.includes('puting beliung') ? Wind
        : e.includes('gelombang') || e.includes('banjir') ? Waves
        : CloudRain;
    return <Icon className={className} aria-hidden="true" />;
};
