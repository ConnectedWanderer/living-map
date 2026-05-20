export interface GeoJsonFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: string; coordinates: unknown };
    properties: Record<string, unknown>;
  }>;
}

const RETRY_DELAYS = [1000, 4000, 16000];

export async function extractLocation(
  text: string,
  config: { url: string },
): Promise<GeoJsonFeatureCollection | null> {
  for (let attempt = 0; attempt <= RETRY_DELAYS.length; attempt++) {
    try {
      const response = await fetch(`${config.url}/api/extract-location`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAYS[attempt]));
    }
  }

  return null;
}
