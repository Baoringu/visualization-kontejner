const palette = ["#8da7a0", "#b59c80", "#90a2bd", "#b297ad", "#b4ae80", "#85a8b5", "#b48f8b", "#9ca59a"] as const;

export function skuColor(sku: string): string {
  let hash = 0;
  for (const character of sku) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return palette[hash % palette.length];
}
