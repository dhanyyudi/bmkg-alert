import { api } from '@/lib/api';

// One entry of GET /api/v1/wilayah/search
export type WilayahResult = {
  code: string;
  name: string;
  level: string;          // 'province' | 'district' | 'subdistrict' | 'village'
  full_path: string;      // "Jawa Tengah > Kabupaten Pekalongan > Wiradesa"
  parent_code?: string;
};

const LEVEL_LABEL: Record<string, string> = {
  district: 'Kabupaten/kota',
  subdistrict: 'Kecamatan',
  village: 'Kelurahan/desa',
};

export const levelLabel = (level: string) => LEVEL_LABEL[level] ?? level;

/** "Kabupaten Pekalongan, Jawa Tengah" for a result named Wiradesa. */
export const regionContext = (result: WilayahResult) =>
  result.full_path.split(' > ').slice(0, -1).reverse().join(', ');

/** Search regions by name, keeping only the levels the caller can use. */
export async function searchRegions(query: string, levels: string[]): Promise<WilayahResult[]> {
  const res = await api.get<{ data: WilayahResult[] }>(`/wilayah/search?q=${encodeURIComponent(query)}&limit=50`);
  return (res.data ?? []).filter(r => levels.includes(r.level));
}

/**
 * Body for POST /locations. BMKG warnings name kecamatan, so a location is
 * either one kecamatan or a whole kabupaten/kota (matched through its kecamatan).
 */
export function toLocationPayload(result: WilayahResult) {
  const parts = result.full_path.split(' > ');
  const codes = result.code.split('.');
  const districtCode = codes.slice(0, 2).join('.');
  const isDistrict = result.level === 'district';
  return {
    label: null,
    province_code: codes[0] ?? '',
    province_name: parts[0] ?? '',
    district_code: districtCode,
    district_name: parts[1] ?? '',
    subdistrict_code: isDistrict ? districtCode : codes.slice(0, 3).join('.'),
    subdistrict_name: isDistrict ? (parts[1] ?? result.name) : (parts[2] ?? result.name),
  };
}

export const MONITOR_LEVELS = ['district', 'subdistrict'];
