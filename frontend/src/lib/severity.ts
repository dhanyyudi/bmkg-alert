// One source for how a CAP severity level is named and coloured across the app.
// Badge pairs are checked for WCAG AA: every text/background pair is >= 4.5:1.

type SeverityStyle = {
  label: string;
  badge: string;
  // Polygon fill on the map; mirrors the badge hue
  mapColor: string;
};

const SEVERITY: Record<string, SeverityStyle> = {
  extreme:  { label: 'Ekstrem', badge: 'bg-red-900 text-white',      mapColor: '#7f1d1d' },
  severe:   { label: 'Berat',   badge: 'bg-red-600 text-white',      mapColor: '#dc2626' },
  moderate: { label: 'Sedang',  badge: 'bg-amber-400 text-amber-950', mapColor: '#f59e0b' },
  minor:    { label: 'Ringan',  badge: 'bg-blue-600 text-white',     mapColor: '#2563eb' },
};

const UNKNOWN: SeverityStyle = { label: 'Tidak diketahui', badge: 'bg-slate-600 text-white', mapColor: '#475569' };

export const SEVERITY_ORDER = ['extreme', 'severe', 'moderate', 'minor'] as const;

export function severityStyle(severity: string | null | undefined): SeverityStyle {
  return SEVERITY[(severity ?? '').toLowerCase()] ?? UNKNOWN;
}
