// maplibre throws inside its constructor when the browser has no WebGL,
// which would take the whole React tree down with it. Check once, up front.
export const webglAvailable: boolean = (() => {
  if (typeof document === 'undefined') return true;
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
})();
