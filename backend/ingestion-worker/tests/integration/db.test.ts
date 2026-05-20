import { describe, it, before, after } from "node:test";
import assert from "node:assert";
import { insertEvents, updateLocation } from "../../src/db.ts";
import { createTestPool, runMigrations, cleanTables, closePool } from "../helpers.ts";
import type pg from "pg";

describe("db integration", () => {
  let pool: pg.Pool;

  before(async () => {
    pool = await createTestPool();
    await runMigrations(pool);
  });

  after(async () => {
    await cleanTables(pool);
    await closePool(pool);
  });

  it("inserts events and returns inserted count", async () => {
    const articles = [
      {
        source_id: "int-test-1",
        title: "Integration Test Article",
        description: "Testing DB insert",
        url: "http://example.com/int-test",
        published_at: "2026-05-20T00:00:00.000Z",
        source: "integration-test",
      },
    ];

    const result = await insertEvents(pool, articles);

    assert.strictEqual(result.inserted, 1);
    assert.strictEqual(result.skipped, 0);
  });

  it("skips duplicates on conflict", async () => {
    const articles = [
      {
        source_id: "int-test-dup",
        title: "Duplicate Article",
        description: "Already inserted",
        url: "http://example.com/dup",
        published_at: "2026-05-20T00:00:00.000Z",
        source: "integration-test",
      },
    ];

    const first = await insertEvents(pool, articles);
    assert.strictEqual(first.inserted, 1);

    const second = await insertEvents(pool, articles);
    assert.strictEqual(second.inserted, 0);
    assert.strictEqual(second.skipped, 1);
  });

  it("updates location on existing event", async () => {
    const articles = [
      {
        source_id: "int-test-location",
        title: "Location Update Test",
        description: "Testing location update",
        url: "http://example.com/loc",
        published_at: "2026-05-20T00:00:00.000Z",
        source: "integration-test",
      },
    ];

    await insertEvents(pool, articles);

    const geoJson = {
      type: "FeatureCollection" as const,
      features: [
        {
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [2.35, 48.86] },
          properties: {},
        },
      ],
    };

    await updateLocation(pool, "integration-test", "int-test-location", geoJson);

    const result = await pool.query(
      "SELECT location FROM events WHERE source = $1 AND source_id = $2",
      ["integration-test", "int-test-location"],
    );

    const loc = result.rows[0].location;
    assert.ok(loc);
    assert.strictEqual(loc.type, "Point");
    assert.deepStrictEqual(loc.coordinates, [2.35, 48.86]);
  });
});
