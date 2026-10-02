export function legendSkus(groups: readonly { sku: string }[]): string[] {
  return [...new Set(groups.map((group) => group.sku))];
}
