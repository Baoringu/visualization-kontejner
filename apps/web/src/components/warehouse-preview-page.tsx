"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import { PlanDrawing } from "./planning-page";

function required<T>(result: { data?: T; error?: unknown }): T { if (!result.data || result.error) throw new Error("REQUEST_FAILED"); return result.data; }

export function WarehousePreviewPage({ initialPlanId }: { initialPlanId?: string }) {
  const t = useTranslations("warehouse");
  const demo = useTranslations("demo");
  const me = useQuery({ queryKey: ["me"], queryFn: async () => required(await api.GET("/api/v1/me")), retry: false });
  const scope = me.data?.organization.id;
  const [planId, setPlanId] = useState(initialPlanId ?? "");
  const [shipmentId, setShipmentId] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const shipments = useQuery({ queryKey: [scope, "shipments"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/shipments")) });
  const runs = useQuery({ queryKey: [scope, "shipment-runs", shipmentId], enabled: !!scope && !!shipmentId, queryFn: async () => required(await api.GET("/api/v1/shipments/{shipment_id}/runs", { params: { path: { shipment_id: shipmentId } } })) });
  const plan = useQuery({ queryKey: [scope, "plan", planId], enabled: !!scope && !!planId, queryFn: async () => required(await api.GET("/api/v1/plans/{plan_id}", { params: { path: { plan_id: planId } } })) });
  const steps = plan.data?.layout.instructions ?? [];
  const step = steps[stepIndex];
  const placement = plan.data?.layout.placed.find((item) => item.instance_id === step?.instance_id);
  const carton = plan.data?.layout.cartons?.find((item) => item.sku === placement?.sku) ?? plan.data?.layout.carton;
  const displaySku = placement?.sku || carton?.sku;
  const displayMass = placement?.mass_g ?? carton?.mass_g;
  const isDemo = plan.data?.layout.cartons?.some((item) => item.sku.startsWith("DEMO-"));
  useEffect(() => { setStepIndex(0); }, [planId]);
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "warehouse" && me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  return <main className="mx-auto max-w-[1450px] px-5 py-7 lg:px-8">
    <p className="text-xs font-medium uppercase tracking-wide text-muted">{t("eyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 max-w-3xl text-sm text-muted">{t("description")}</p>
    <div className="mt-6 rounded-lg border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-200"><strong>{t("notReleased")}</strong><p className="mt-1">{t("notReleasedDetail")}</p></div>
    {isDemo && <p className="mt-3 rounded-md border border-amber-400 p-3 text-sm">{demo("warning")}</p>}
    <section className="mt-6 rounded-lg border p-5"><div className="grid gap-4 md:grid-cols-2"><label className="grid gap-1 text-sm">{t("shipment")}<select className="rounded-md border bg-background px-3 py-2" value={shipmentId} onChange={(event) => { setShipmentId(event.target.value); setPlanId(""); }}><option value="">{t("choose")}</option>{shipments.data?.map((item) => <option key={item.id} value={item.id}>{item.shipment_ref}</option>)}</select></label><label className="grid gap-1 text-sm">{t("plan")}<select className="rounded-md border bg-background px-3 py-2" value={planId} onChange={(event) => setPlanId(event.target.value)}><option value="">{t("choose")}</option>{runs.data?.filter((item) => item.plan_id).map((item) => <option key={item.plan_id} value={item.plan_id!}>{item.plan_id?.slice(0, 8)} · {item.status}</option>)}{initialPlanId && !runs.data?.some((item) => item.plan_id === initialPlanId) && <option value={initialPlanId}>{initialPlanId.slice(0, 8)}</option>}</select></label></div>{(shipments.isError || runs.isError || plan.isError) && <p role="alert" className="mt-3 text-sm text-red-700">{t("loadError")}</p>}{(shipments.isLoading || runs.isLoading || plan.isLoading) && <p role="status" className="mt-3 text-sm text-muted">{t("loading")}</p>}</section>
    {plan.data ? <><div className="mt-6 flex flex-wrap gap-x-7 gap-y-2 border-y py-4 text-sm"><span>{t("placed")}: <strong>{plan.data.layout.placed_instances}</strong></span><span>{t("unplaced")}: <strong>{plan.data.layout.unplaced_instances}</strong></span><span>{t("pallets")}: <strong>{plan.data.layout.pallet_count}</strong></span><span>{t("validation")}: <strong>{plan.data.validation_status}</strong></span></div>
      {steps.length > 0 && <section className="mt-6 rounded-lg border p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm text-muted">{t("stepOf", { current: stepIndex + 1, total: steps.length })}</p><h2 className="mt-1 text-xl font-semibold">{carton?.name ?? displaySku ?? t("carton")}</h2><p className="text-sm text-muted">{displaySku} · {placement?.instance_id.slice(0, 8)}</p></div><div className="flex gap-2"><button className="min-h-11 rounded-md border px-4 text-sm disabled:opacity-40" disabled={stepIndex === 0} onClick={() => setStepIndex((value) => value - 1)}>{t("previous")}</button><button className="min-h-11 rounded-md border px-4 text-sm disabled:opacity-40" disabled={stepIndex >= steps.length - 1} onClick={() => setStepIndex((value) => value + 1)}>{t("next")}</button></div></div><div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4"><p>{t("pallet")}: <strong>{(step?.pallet_index ?? 0) + 1}</strong></p><p>{t("position")}: <strong>{placement?.x_mm}, {placement?.y_mm}, {placement?.z_mm} mm</strong></p><p>{t("dimensions")}: <strong>{placement?.length_mm} × {placement?.width_mm} × {placement?.height_mm} mm</strong></p><p>{t("mass")}: <strong>{displayMass == null ? "—" : (displayMass / 1000).toFixed(3)} kg</strong></p></div></section>}
      <PlanDrawing layout={plan.data.layout} focusInstanceId={step?.instance_id} visibleInstanceIds={steps.slice(0, stepIndex + 1).map((item) => item.instance_id)} onSelect={(id) => { const index = steps.findIndex((item) => item.instance_id === id); if (index >= 0) setStepIndex(index); }} />
      {plan.data.layout.unplaced.length > 0 && <div className="mt-6 rounded-lg border border-amber-400 p-4"><h2 className="font-medium">{t("unplacedTitle")}</h2><p className="mt-1 text-sm text-muted">{t("unplacedDetail")}</p>{plan.data.layout.unplaced.map((item) => <p className="mt-2 text-sm" key={item.instance_id}>{item.sku ?? "—"} · {item.instance_id.slice(0, 8)} · {item.reason}</p>)}</div>}
    </> : <p className="mt-6 rounded-lg border p-6 text-sm text-muted">{t("empty")}</p>}
  </main>;
}
