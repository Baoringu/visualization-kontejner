"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import { PlanDrawing } from "./planning-page";
import { PlanComparison } from "./plan-comparison";
import { skuColor } from "../lib/sku-colors";
import { legendSkus } from "../lib/legend-skus";

function required<T>(result: { data?: T; error?: unknown }): T { if (!result.data || result.error) throw new Error("REQUEST_FAILED"); return result.data; }
const input = "w-full rounded-md border bg-background px-3 py-2 text-sm";

export function PlanningWorkspace() {
  const t = useTranslations("planning");
  const demo = useTranslations("demo");
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => required(await api.GET("/api/v1/me")), retry: false });
  const scope = me.data?.organization.id;
  const shipments = useQuery({ queryKey: [scope, "shipments"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/shipments")) });
  const pallets = useQuery({ queryKey: [scope, "pallet-types"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/pallet-types")) });
  const [shipmentId, setShipmentId] = useState("");
  const [palletId, setPalletId] = useState("");
  const [strategy, setStrategy] = useState<"quick" | "best_fit">("quick");
  const [runId, setRunId] = useState("");
  const [comparisonRunId, setComparisonRunId] = useState("");
  const runs = useQuery({ queryKey: [scope, "shipment-runs", shipmentId], enabled: !!shipmentId, queryFn: async () => required(await api.GET("/api/v1/shipments/{shipment_id}/runs", { params: { path: { shipment_id: shipmentId } } })) });
  const displayedRunId = runId || runs.data?.[0]?.id || "";
  const runStatus = useQuery({ queryKey: [scope, "run", displayedRunId], enabled: !!displayedRunId, queryFn: async () => required(await api.GET("/api/v1/runs/{run_id}", { params: { path: { run_id: displayedRunId } } })), refetchInterval: (query) => ["succeeded", "failed", "cancelled"].includes(query.state.data?.status ?? "") ? false : 1000 });
  const planId = runStatus.data?.plan_id;
  const plan = useQuery({ queryKey: [scope, "plan", planId], enabled: !!planId, queryFn: async () => required(await api.GET("/api/v1/plans/{plan_id}", { params: { path: { plan_id: planId! } } })) });
  const comparisonPlanId = runs.data?.find((item) => item.id === comparisonRunId)?.plan_id;
  const comparisonPlan = useQuery({ queryKey: [scope, "plan", comparisonPlanId], enabled: !!comparisonPlanId, queryFn: async () => required(await api.GET("/api/v1/plans/{plan_id}", { params: { path: { plan_id: comparisonPlanId! } } })) });
  const preflight = useMutation({ mutationFn: async () => required(await api.POST("/api/v1/shipments/{shipment_id}/preflight", { params: { path: { shipment_id: shipmentId } }, body: { pallet_type_id: palletId } })) });
  const run = useMutation({ mutationFn: async () => {
    const shipment = shipments.data?.find((item) => item.id === shipmentId);
    if (!shipment) throw new Error("SHIPMENT_NOT_FOUND");
    return required(await api.POST("/api/v1/shipments/{shipment_id}/runs", { params: { path: { shipment_id: shipmentId }, header: { "idempotency-key": crypto.randomUUID() } }, body: { pallet_type_id: palletId, expected_shipment_revision: shipment.revision, strategy, evaluation_budget: 250000 } }));
  }, onSuccess: (item) => { setRunId(item.id); void client.invalidateQueries({ queryKey: [scope, "shipment-runs", shipmentId] }); } });
  if (me.isLoading) return <main className="p-6">{t("checking")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  const operator = me.data?.role === "warehouse" || me.data?.role === "admin";
  const status = runStatus.data?.status;
  const statusText = status === "queued" ? t("queued") : status === "running" ? t("running") : status === "succeeded" ? t("succeeded") : status === "failed" ? t("failed") : status === "cancelled" ? t("cancelled") : "";
  const layout = plan.data?.layout;
  const legend = legendSkus(layout ? (layout.cartons?.length ? layout.cartons : layout.carton ? [layout.carton] : []) : []);
  const demoPallet = pallets.data?.find((item) => item.id === palletId)?.evidence_ref.startsWith("SYNTHETIC_DEMO");
  return <main className="mx-auto max-w-[1450px] px-5 py-7 lg:px-8"><p className="text-xs font-medium uppercase tracking-wide text-muted">{t("reviewEyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 max-w-3xl text-sm text-muted">{t("reviewDescription")}</p>
    {demoPallet && <p role="status" className="mt-5 rounded-md border border-amber-400 bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950/20 dark:text-amber-200">{demo("warning")}</p>}
    <section className="mt-7 rounded-lg border p-5"><div className="grid gap-4 md:grid-cols-2"><label className="grid gap-1 text-sm">{t("selectShipment")}<select className={input} value={shipmentId} onChange={(event) => { setShipmentId(event.target.value); setRunId(""); setComparisonRunId(""); preflight.reset(); }}><option value="">{t("choose")}</option>{shipments.data?.map((shipment) => <option key={shipment.id} value={shipment.id}>{shipment.shipment_ref}</option>)}</select></label>{operator && <label className="grid gap-1 text-sm">{t("selectPallet")}<select className={input} value={palletId} onChange={(event) => { setPalletId(event.target.value); preflight.reset(); }}><option value="">{t("choose")}</option>{pallets.data?.map((pallet) => <option key={pallet.id} value={pallet.id}>{pallet.code} · {pallet.length_mm}×{pallet.width_mm} mm</option>)}</select></label>}</div>
      {shipments.data?.length === 0 && <p className="mt-3 text-sm text-muted">{t("noShipments")}</p>}{operator && pallets.data?.length === 0 && <p className="mt-3 text-sm text-muted">{t("noPallets")}</p>}{(shipments.isError || pallets.isError || runs.isError) && <p role="alert" className="mt-3 text-sm text-red-700">{t("loadError")}</p>}
      {operator ? <div className="mt-4 flex flex-wrap items-end gap-3"><label className="grid gap-1 text-sm">{t("strategy")}<select className={input} value={strategy} onChange={(event) => setStrategy(event.target.value as "quick" | "best_fit")}><option value="quick">{t("quick")}</option><option value="best_fit">{t("bestFit")}</option></select></label><button className="rounded-md border px-4 py-2.5 text-sm disabled:opacity-40" disabled={!shipmentId || !palletId || preflight.isPending} onClick={() => preflight.mutate()}>{preflight.isPending ? t("checking") : t("preflight")}</button><button className="rounded-md bg-neutral-900 px-4 py-2.5 text-sm text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900" disabled={!preflight.data?.ready || run.isPending} onClick={() => run.mutate()}>{run.isPending ? t("queued") : t("run")}</button></div> : <p className="mt-4 text-sm text-muted">{t("salesReadOnly")}</p>}
      {preflight.data && <div className={`mt-4 rounded-md border p-3 text-sm ${preflight.data.ready ? "" : "border-amber-400"}`}><p className="font-medium">{preflight.data.ready ? t("ready") : t("blocked")}</p><p className="mt-1 text-muted">{preflight.data.requested_cartons ?? 0} {t("cartons")}</p>{preflight.data.blockers.map((code) => <p className="mt-1 text-amber-700" key={code}>{code}</p>)}</div>}{(preflight.isError || run.isError || runStatus.isError || plan.isError) && <p role="alert" className="mt-3 text-sm text-red-700">{t("error")}</p>}
    </section>
    <section className="mt-7"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold">{t("result")}</h2><p className="mt-1 text-sm text-muted">{t("modelOnly")}</p></div>{plan.data && <Link href={`/en/warehouse?plan=${plan.data.id}`} className="rounded-md border px-3 py-2 text-sm">{t("warehousePreview")}</Link>}</div>{runs.data && runs.data.length > 0 && <label className="mt-4 block max-w-md text-sm">{t("priorRuns")}<select className={`${input} mt-1`} value={displayedRunId} onChange={(event) => { setRunId(event.target.value); setComparisonRunId(""); }}>{runs.data.map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.status}</option>)}</select></label>}{plan.data && runs.data && runs.data.filter((item) => item.plan_id && item.id !== displayedRunId).length > 0 && <label className="mt-4 block max-w-md text-sm">{t("compareWith")}<select className={`${input} mt-1`} value={comparisonRunId} onChange={(event) => setComparisonRunId(event.target.value)}><option value="">{t("choose")}</option>{runs.data.filter((item) => item.plan_id && item.id !== displayedRunId).map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.status}</option>)}</select></label>}{comparisonPlan.data && plan.data && <PlanComparison primary={plan.data} other={comparisonPlan.data} />}{comparisonPlan.isError && <p role="alert" className="mt-2 text-sm text-red-700">{t("loadError")}</p>}{statusText && <p role="status" className="mt-4 text-sm">{statusText}</p>}{layout && <p className="mt-2 text-sm text-muted">{t("searchSummary", { strategy: layout.search.strategy === "best_fit" ? t("bestFit") : t("quick"), candidates: layout.search.candidates_completed ?? 1, evaluations: layout.search.evaluations_completed })} · {layout.search.termination_reason === "evaluation_budget_exhausted" ? t("budgetExhausted") : t("searchCompleted")}</p>}
      {layout ? <><div className="mt-5 flex flex-wrap gap-x-7 gap-y-2 border-y py-4 text-sm"><Stat label={t("placed")} value={String(layout.placed_instances)} /><Stat label={t("unplaced")} value={String(layout.unplaced_instances)} /><Stat label={t("palletsUsed")} value={String(layout.pallet_count)} /><Stat label={t("loadedHeight")} value={`${layout.loaded_height_mm} mm`} /><Stat label={t("loadedMass")} value={`${(layout.loaded_mass_g / 1000).toFixed(3)} kg`} /></div><div className="mt-5 flex flex-wrap gap-3 text-xs">{legend.map((sku) => <span key={sku} className="flex items-center gap-2"><span className="h-3 w-3 rounded-sm border" style={{ backgroundColor: skuColor(sku) }} />{sku}</span>)}</div><PlanDrawing layout={layout} />{layout.unplaced.length > 0 && <div className="mt-6 rounded-lg border border-amber-400 p-4"><h3 className="font-medium">{t("unplacedTitle")}</h3><p className="mt-1 text-sm text-muted">{t("unplacedWarning")}</p>{layout.unplaced.map((item) => <p key={item.instance_id} className="mt-2 text-sm">{item.sku ?? "—"} · {item.instance_id.slice(0, 8)} · {item.reason}</p>)}</div>}</> : <p className="mt-5 rounded-lg border p-6 text-sm text-muted">{t("empty")}</p>}
    </section>
  </main>;
}

function Stat({ label, value }: { label: string; value: string }) { return <div><span className="text-muted">{label}</span><strong className="ml-2 tabular-nums">{value}</strong></div>; }
