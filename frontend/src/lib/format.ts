// Shared display formatting. BMKG timestamps carry their own UTC offset;
// everything is shown in WIB so the dashboard reads the same for every visitor.

const WIB = 'Asia/Jakarta';

// SQLite timestamps arrive with a space separator, and in UTC when they carry no offset
const normalizeUtc = (iso: string) => {
  const t = iso.replace(' ', 'T');
  return /Z$|[+-]\d{2}:\d{2}$/.test(t) ? t : t + 'Z';
};

const parse = (iso: string | null | undefined): Date | null => {
  if (!iso) return null;
  const d = new Date(normalizeUtc(iso));
  return Number.isNaN(d.getTime()) ? null : d;
};

export function fmtTime(iso: string | null | undefined): string {
  const d = parse(iso);
  if (!d) return '-';
  return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', timeZone: WIB }) + ' WIB';
}

export function fmtDateTime(iso: string | null | undefined, style: 'short' | 'long' = 'short'): string {
  const d = parse(iso);
  if (!d) return '-';
  return d.toLocaleString('id-ID', {
    dateStyle: style === 'long' ? 'long' : 'medium',
    timeStyle: 'short',
    timeZone: WIB,
  }) + ' WIB';
}

export function fmtRelative(iso: string | null | undefined, now: number = Date.now()): string {
  const d = parse(iso);
  if (!d) return '-';
  const diff = Math.max(0, Math.floor((now - d.getTime()) / 1000));
  if (diff < 60) return 'baru saja';
  if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
  return `${Math.floor(diff / 86400)} hari lalu`;
}

const URGENCY: Record<string, string> = {
  immediate: 'Segera',
  expected: 'Diperkirakan',
  future: 'Mendatang',
  past: 'Sudah lewat',
};

const CERTAINTY: Record<string, string> = {
  observed: 'Teramati',
  likely: 'Kemungkinan besar',
  possible: 'Mungkin terjadi',
  unlikely: 'Kecil kemungkinan',
};

export const urgencyLabel = (v: string | null | undefined) => URGENCY[(v ?? '').toLowerCase()] ?? (v || '-');
export const certaintyLabel = (v: string | null | undefined) => CERTAINTY[(v ?? '').toLowerCase()] ?? (v || '-');
