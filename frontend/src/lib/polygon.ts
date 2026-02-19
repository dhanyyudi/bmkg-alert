
/**
 * Calculates distance between two points in kilometers using Haversine formula.
 * @param lat1 Latitude of point 1
 * @param lon1 Longitude of point 1
 * @param lat2 Latitude of point 2
 * @param lon2 Longitude of point 2
 * @returns Distance in kilometers
 */
function haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // Radius of the earth in km
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function deg2rad(deg: number): number {
  return deg * (Math.PI / 180);
}

/**
 * Splits a flat array of coordinates into multiple rings (polygons).
 * Matches BMKG reference implementation.
 * 
 * @param coords Flattened array of [lat, lon] coordinates
 * @returns Array of rings, where each ring is an array of [lon, lat] coordinates
 */
// Thresholds per BMKG API reference implementation:
// - Split ring when consecutive point gap > 10 km
// - Reject ring if any single edge > 20 km (eliminates thin-strip artifacts)
const RING_SPLIT_GAP_KM = 10;
const ARTIFACT_MAX_EDGE_KM = 20;

function maxEdgeKm(ring: number[][]): number {
    let max = 0;
    for (let j = 0; j < ring.length - 1; j++) {
        const d = haversineDistance(ring[j][1], ring[j][0], ring[j + 1][1], ring[j + 1][0]);
        if (d > max) max = d;
    }
    return max;
}


export function splitRings(coords: number[][]): number[][][] {
    if (!coords || coords.length === 0) return [];

    const rings: number[][][] = [];
    const eps = 0.0001;
    let start = coords[0];
    let ring: number[][] = [[start[1], start[0]]]; // Swap lat,lon to lon,lat

    // Helper to get last point of current ring
    const getLast = (r: number[][]) => r[r.length - 1];

    for (let i = 1; i < coords.length; i++) {
        const c = coords[i];
        const pt = [c[1], c[0]]; // lon, lat

        // 1. Split on large gap (indicates jump to a new separate polygon)
        if (ring.length >= 4) {
             const prev = getLast(ring);
             // dist calc uses lon,lat because prev/pt are swapped
             const dist = haversineDistance(prev[1], prev[0], pt[1], pt[0]);

             if (dist > RING_SPLIT_GAP_KM) {
                 // Close current ring
                 const first = ring[0];
                 const last = getLast(ring);
                 if (first[0] !== last[0] || first[1] !== last[1]) {
                     ring.push(first);
                 }

                 rings.push(ring);
                 start = c;
                 ring = [pt];
                 continue;
             }
        }

        ring.push(pt);

        // 2. Split on coordinate match (ring closed back to start point)
        if (Math.abs(c[0] - start[0]) < eps &&
            Math.abs(c[1] - start[1]) < eps &&
            ring.length >= 4) {

            rings.push(ring);
            ring = [];

            // Start next ring if more points exist
            if (i + 1 < coords.length) {
                start = coords[i+1];
                ring = [[start[1], start[0]]];
                i++;
            }
        }
    }

    // Handle remaining open ring
    if (ring.length >= 4) {
        const first = ring[0];
        const last = getLast(ring);
        if (first[0] !== last[0] || first[1] !== last[1]) {
            ring.push(first);
        }
        rings.push(ring);
    }

    // Per BMKG API docs: reject rings with fewer than 4 points OR any edge > 20 km.
    // The 20 km edge filter eliminates thin-strip artifacts caused by the flat-array
    // format while preserving real district/subdistrict boundaries.
    return rings.filter(r => r.length >= 4 && maxEdgeKm(r) <= ARTIFACT_MAX_EDGE_KM);
}
