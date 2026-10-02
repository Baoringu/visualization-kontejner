"use client";

import { useTranslations } from "next-intl";
import type { components } from "../lib/api/schema";

type Plan = components["schemas"]["PlanOut"];

export function PlanComparison({ primary, other }: { primary: Plan; other: Plan }) {
  const t = useTranslations("planning");
  const rows = [
    [t("placed"), primary.layout.placed_instances, other.layout.placed_instances],
    [t("unplaced"), primary.layout.unplaced_instances, other.layout.unplaced_instances],
    [t("palletsUsed"), primary.layout.pallet_count, other.layout.pallet_count],
    [t("loadedHeight"), `${primary.layout.loaded_height_mm} mm`, `${other.layout.loaded_height_mm} mm`],
    [t("loadedMass"), `${(primary.layout.loaded_mass_g / 1000).toFixed(3)} kg`, `${(other.layout.loaded_mass_g / 1000).toFixed(3)} kg`],
  ] as const;
  return <section className="mt-5 rounded-lg border p-4"><h3 className="font-medium">{t("compareTitle")}</h3><p className="mt-1 text-sm text-muted">{t("compareCaution")}</p><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[440px] text-left text-sm"><thead><tr className="border-b"><th className="py-2 font-medium">{t("metric")}</th><th className="py-2 font-medium">{t("currentPlan")}</th><th className="py-2 font-medium">{t("comparisonPlan")}</th></tr></thead><tbody><tr className="border-b"><th className="py-2 font-normal text-muted">{t("strategy")}</th><td>{primary.layout.search.strategy === "best_fit" ? t("bestFit") : t("quick")}</td><td>{other.layout.search.strategy === "best_fit" ? t("bestFit") : t("quick")}</td></tr>{rows.map(([label, current, comparison]) => <tr className="border-b last:border-0" key={label}><th className="py-2 font-normal text-muted">{label}</th><td className="tabular-nums">{current}</td><td className="tabular-nums">{comparison}</td></tr>)}</tbody></table></div></section>;
}
