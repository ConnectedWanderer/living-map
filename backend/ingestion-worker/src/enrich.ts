/** A GeoJSON FeatureCollection returned by the location extraction service. */
export interface GeoJsonFeatureCollection {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    geometry: { type: string; coordinates: unknown };
    properties: Record<string, unknown>;
  }>;
}

const RETRY_DELAYS = [1000, 4000, 16000];

/** POST text to the location extraction service with exponential retry. */
export async function extractLocation(
  text: string,
  config: { url: string; fetch?: typeof global.fetch; wait?: (ms: number) => Promise<void> },
): Promise<GeoJsonFeatureCollection | null> {
  const doFetch = config.fetch ?? global.fetch;
  const doWait = config.wait ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));

  for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
    try {
      const response = await doFetch(`${config.url}/api/extract-location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        return null;
      }

      return response.json() as Promise<GeoJsonFeatureCollection>;
    } catch {
      if (attempt === RETRY_DELAYS.length) {
        return null;
      }
      await doWait(RETRY_DELAYS[attempt]);
    }
  }

  return null;
}
