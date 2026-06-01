const API_BASE = import.meta.env.VITE_API_URL || window.location.origin
export const TILE_URL = `${API_BASE}/tiles/{z}/{x}/{y}.pbf`
