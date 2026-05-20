export const MOCK_FEED_URL: string =
  process.env.MOCK_FEED_URL || "http://localhost:3001";

export const LE_URL: string =
  process.env.LE_URL || "http://localhost:8000";

export const DATABASE_URL: string =
  process.env.DATABASE_URL ||
  "postgres://livingmap:livingmap@localhost:5432/livingmap_test";

export async function ensureServices(): Promise<void> {
  const services = [
    { name: "mock-feed", url: `${MOCK_FEED_URL}/feed?count=1` },
    { name: "location-extraction", url: `${LE_URL}/health` },
  ];

  const results = await Promise.allSettled(
    services.map((s) =>
      fetch(s.url).then((r) => {
        if (!r.ok) throw new Error(`${s.name} returned ${r.status}`);
      })
    )
  );

  const failures = results
    .map((r, i) => (r.status === "rejected" ? services[i].name : null))
    .filter(Boolean);

  if (failures.length > 0) {
    throw new Error(
      `Required services not healthy: ${failures.join(", ")}`,
    );
  }
}
