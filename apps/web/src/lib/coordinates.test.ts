import { describe, expect, it } from "vitest";
import { boxCenterMeters, boxSizeMeters } from "./coordinates";

describe("deck frame to Three Y-up adapter", () => {
  it("uses already oriented dimensions and deck offset", () => {
    const placement = { instance_id: "a", pallet_index: 0, x_mm: 900, y_mm: 400, z_mm: 200, orientation_code: "upright_90", length_mm: 300, width_mm: 400, height_mm: 200 };
    expect(boxSizeMeters(placement)).toEqual([0.3, 0.2, 0.4]);
    expect(boxCenterMeters(placement, 144)).toEqual([1.05, 0.444, -0.6]);
  });
});
