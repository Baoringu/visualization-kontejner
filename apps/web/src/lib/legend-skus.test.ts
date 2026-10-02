import { describe, expect, it } from "vitest";
import { legendSkus } from "./legend-skus";

describe("legendSkus", () => {
  it("shows one legend color per SKU even when several packaging groups use it", () => {
    expect(legendSkus([{ sku: "SKU-P2-001" }, { sku: "DEMO-BOOK" }, { sku: "SKU-P2-001" }])).toEqual(["SKU-P2-001", "DEMO-BOOK"]);
  });

  it("handles an empty plan", () => {
    expect(legendSkus([])).toEqual([]);
  });
});
