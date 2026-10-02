"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import type { components } from "../lib/api/schema";

const CartonPreview = dynamic(() => import("./carton-preview"), { ssr: false });
type UnitCreate = components["schemas"]["PackagingUnitCreate"];
type Verification = components["schemas"]["PackagingVerification"];
const input = "w-full rounded-md border bg-background px-3 py-2 text-sm";
const button = "rounded-md bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900";

export function ProductDetailPage({ productId }: { productId: string }) {
  const t = useTranslations("catalog");
  const list = useTranslations("productList");
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => { const result = await api.GET("/api/v1/me"); if (!result.data) throw new Error("AUTH_REQUIRED"); return result.data; }, retry: false });
  const scope = me.data?.organization.id;
  const products = useQuery({ queryKey: [scope, "products"], enabled: !!scope, queryFn: async () => { const result = await api.GET("/api/v1/products"); if (!result.data) throw new Error("REQUEST_FAILED"); return result.data; } });
  const units = useQuery({ queryKey: [scope, "packaging-units"], enabled: !!scope, queryFn: async () => { const result = await api.GET("/api/v1/packaging-units"); if (!result.data) throw new Error("REQUEST_FAILED"); return result.data; } });
  const product = products.data?.find((item) => item.id === productId);
  const productUnits = units.data?.filter((item) => item.product_id === productId) ?? [];
  const [selectedId, setSelectedId] = useState("");
  const [unit, setUnit] = useState({ code: "", units_per_package: 1, length_mm: 400, width_mm: 300, height_mm: 200, mass_kg: "5.000" });
  const [evidence, setEvidence] = useState("");
  const [topLoadKg, setTopLoadKg] = useState("");
  const [allowRotate, setAllowRotate] = useState(false);
  const selected = productUnits.find((item) => item.id === selectedId) ?? productUnits[0];
  useEffect(() => {
    if (!selected) return;
    setEvidence(selected.evidence_ref ?? "");
    setTopLoadKg(selected.top_load_limit_g === null ? "" : (selected.top_load_limit_g / 1000).toFixed(3));
    setAllowRotate(selected.allow_upright_90);
  }, [selected?.id, selected?.revision]);
  function selectUnit(item: typeof selected) {
    if (!item) return;
    setSelectedId(item.id);
    setEvidence(item.evidence_ref ?? "");
    setTopLoadKg(item.top_load_limit_g === null ? "" : (item.top_load_limit_g / 1000).toFixed(3));
    setAllowRotate(item.allow_upright_90);
  }
  const createUnit = useMutation({ mutationFn: async () => {
    const body: UnitCreate = { product_id: productId, code: unit.code.trim(), units_per_package: unit.units_per_package, length_mm: unit.length_mm, width_mm: unit.width_mm, height_mm: unit.height_mm, mass_g: Math.round(Number(unit.mass_kg) * 1000) };
    const result = await api.POST("/api/v1/packaging-units", { body }); if (!result.data) throw new Error("REQUEST_FAILED"); return result.data;
  }, onSuccess: (item) => { setUnit((prior) => ({ ...prior, code: "" })); setSelectedId(item.id); void client.invalidateQueries({ queryKey: [scope, "packaging-units"] }); } });
  const verify = useMutation({ mutationFn: async () => {
    if (!selected) throw new Error("UNIT_NOT_SELECTED");
    const body: Verification = { expected_revision: selected.revision, evidence_ref: evidence.trim(), top_load_limit_g: topLoadKg === "" ? null : Math.round(Number(topLoadKg) * 1000), allow_upright_90: allowRotate };
    const result = await api.POST("/api/v1/packaging-units/{unit_id}/verify", { params: { path: { unit_id: selected.id } }, body }); if (!result.data) throw new Error("REQUEST_FAILED"); return result.data;
  }, onSuccess: () => { void client.invalidateQueries({ queryKey: [scope, "packaging-units"] }); } });
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  return <main className="mx-auto max-w-[1450px] px-5 py-7 lg:px-8"><Link href="/en/catalog/products" className="text-sm underline">{list("back")}</Link>
    {products.isLoading || units.isLoading ? <p className="mt-5 text-sm text-muted">{t("loading")}</p> : products.isError || units.isError ? <p role="alert" className="mt-5 text-sm text-red-700">{t("loadError")}</p> : !product ? <p className="mt-5 text-sm">{list("notFound")}</p> : <>
      <p className="mt-5 text-xs font-medium uppercase tracking-wide text-muted">{product.sku}</p><h1 className="mt-1 text-3xl font-semibold">{product.name}</h1><p className="mt-2 text-sm text-muted">{list("demoShape")}</p>
      <div className="mt-7 grid items-start gap-6 xl:grid-cols-[minmax(260px,360px)_minmax(0,1fr)]">
        <section><h2 className="text-lg font-semibold">{t("newPackaging")}</h2><div className="mt-3 divide-y rounded-lg border">{productUnits.length ? productUnits.map((item) => <button key={item.id} className={`block w-full px-4 py-3 text-left hover:bg-muted ${selected?.id === item.id ? "bg-muted" : ""}`} onClick={() => selectUnit(item)}><span className="font-medium">{item.code}</span><span className={`ml-2 text-xs ${item.is_verified && !item.evidence_ref?.startsWith("SYNTHETIC_DEMO") ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>{item.evidence_ref?.startsWith("SYNTHETIC_DEMO") ? list("demoFixture") : item.is_verified ? t("verified") : t("unverified")}</span><span className="mt-1 block text-xs text-muted">{item.length_mm} × {item.width_mm} × {item.height_mm} mm · {(item.mass_g / 1000).toFixed(3)} kg</span></button>) : <p className="p-4 text-sm text-muted">{t("noPackaging")}</p>}</div>
          <form className="mt-6 grid gap-3 rounded-lg border p-5" onSubmit={(event) => { event.preventDefault(); createUnit.mutate(); }}><h3 className="font-semibold">{list("createCarton")}</h3><label className="grid gap-1 text-sm">{t("packagingCode")}<input className={input} required value={unit.code} onChange={(event) => setUnit({ ...unit, code: event.target.value })} /></label><div className="grid grid-cols-2 gap-3">{([["units_per_package", "unitsPerCarton"], ["length_mm", "length"], ["width_mm", "width"], ["height_mm", "height"]] as const).map(([field, label]) => <label className="grid gap-1 text-sm" key={field}>{t(label)}<input className={input} required type="number" min="1" value={unit[field]} onChange={(event) => setUnit({ ...unit, [field]: Number(event.target.value) })} /></label>)}</div><label className="grid gap-1 text-sm">{t("grossMassKg")}<input className={input} required inputMode="decimal" value={unit.mass_kg} onChange={(event) => setUnit({ ...unit, mass_kg: event.target.value })} /></label><button className={button} disabled={createUnit.isPending || !unit.code.trim()}>{t("createPackaging")}</button>{createUnit.isError && <p role="alert" className="text-sm text-red-700">{t("saveError")}</p>}</form>
        </section>
        <section><h2 className="text-lg font-semibold">{list("cartonPreview")}</h2>{selected ? <><div className="mt-3"><CartonPreview lengthMm={selected.length_mm} widthMm={selected.width_mm} heightMm={selected.height_mm} label={t("previewLabel", { code: selected.code })} rotateLabel={t("rotatePreview")} zoomInLabel={list("zoomIn")} zoomOutLabel={list("zoomOut")} interactionHint={list("orbitHint")} /></div><div className="mt-5 rounded-lg border p-5"><h3 className="font-semibold">{list("handlingRules")}</h3><p className="mt-1 text-sm text-muted">{t("topFaceFixed")}</p><div className="mt-5 grid gap-4 sm:grid-cols-2"><label className="grid gap-1 text-sm">{t("evidence")}<input className={input} value={evidence} onChange={(event) => setEvidence(event.target.value)} /></label><label className="grid gap-1 text-sm">{t("topLoadKg")}<input className={input} inputMode="decimal" value={topLoadKg} onChange={(event) => setTopLoadKg(event.target.value)} placeholder={t("unknown")} /></label><label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" checked={allowRotate} onChange={(event) => setAllowRotate(event.target.checked)} />{t("allowUpright90")}</label><div className="sm:col-span-2"><button className={button} disabled={verify.isPending || evidence.trim().length < 3} onClick={() => verify.mutate()}>{t("verify")}</button>{verify.isError && <p role="alert" className="mt-2 text-sm text-red-700">{t("saveError")}</p>}{verify.isSuccess && <p role="status" className="mt-2 text-sm">{t("saved")}</p>}</div></div></div></> : <p className="mt-3 rounded-lg border p-6 text-sm text-muted">{list("choosePackaging")}</p>}</section>
      </div>
    </>}
  </main>;
}
