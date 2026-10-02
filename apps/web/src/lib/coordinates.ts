import type { components } from "./api/schema";

type Placement = components["schemas"]["PlacementOut"];

export function boxCenterMeters(placement: Placement, deckHeightMm: number): [number, number, number] {
  return [
    (placement.x_mm + placement.length_mm / 2) / 1000,
    (deckHeightMm + placement.z_mm + placement.height_mm / 2) / 1000,
    -(placement.y_mm + placement.width_mm / 2) / 1000,
  ];
}

export function boxSizeMeters(placement: Placement): [number, number, number] {
  return [placement.length_mm / 1000, placement.height_mm / 1000, placement.width_mm / 1000];
}
