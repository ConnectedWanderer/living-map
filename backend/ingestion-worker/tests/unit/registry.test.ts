import { describe, it } from "node:test";
import assert from "node:assert";
import { registerAdapter, getAdapter } from "../../src/sources/registry.ts";
import type { NormalizedArticle } from "../../src/normalizer.ts";

describe("registry", () => {
  it("returns the registered fetch function for a known type", () => {
    const fn = getAdapter("mock-feed");
    assert.strictEqual(typeof fn, "function");
  });

  it("throws for an unknown type", () => {
    assert.throws(
      () => getAdapter("nonexistent-source"),
      { message: "Unknown source type: nonexistent-source" },
    );
  });

  it("getAdapter returns the registered function after registerAdapter", () => {
    const fakeFn = async (): Promise<NormalizedArticle[]> => [];
    registerAdapter("test-adapter", fakeFn);
    assert.strictEqual(getAdapter("test-adapter"), fakeFn);
  });
});
