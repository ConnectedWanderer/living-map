import { describe, it, before } from "node:test";
import assert from "node:assert";
import { extractLocation } from "../../src/enrich.ts";
import { LE_URL, ensureServices } from "./helpers.ts";

describe("enrich integration", () => {
  before(async () => {
    await ensureServices();
  });

  it("extracts location from text via real LE service", async () => {
    const result = await extractLocation("Flood in Paris", {
      url: LE_URL,
    });

    assert.ok(result);
    assert.strictEqual(result.type, "FeatureCollection");
    assert.ok(Array.isArray(result.features));
  });
});
