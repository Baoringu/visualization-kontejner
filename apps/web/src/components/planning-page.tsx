"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import type { components } from "../lib/api/schema";
import { skuColor } from "../lib/sku-colors";

type PalletCreate = components["schemas"]["PalletTypeCreate"];
type PackagingVerification = components["schemas"]["PackagingVerification"];
type Layout = components["schemas"]["LayoutOut"];
const PalletScene = dynamic(() => import("./pallet-scene"), { ssr: false });
const blockerMessages = {
  ONE_PACKAGING_LINE_REQUIRED: "oneLineRequired",
  PACKAGING_UNIT_NOT_FOUND: "packagingMissing",
  PACKAGING_NOT_VERIFIED: "packagingUnverified",
  INCOMPLETE_CARTON_QUANTITY: "incompleteCartons",
  INSTANCE_LIMIT_EXCEEDED: "instanceLimit",
  PALLET_SUPPORT_NOT_VERIFIED: "palletUnverified",
} as const;

function failIfError<T>(result: { data?: T; error?: unknown }): T {
  if (result.error || !result.data) throw new Error("REQUEST_FAILED");
  return result.data;
}

export function PlanningPage() {
  const t = useTranslations("planning");
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => failIfError(await api.GET("/api/v1/me")), retry: false });
  const organizationId = me.data?.organization.id;
  const shipments = useQuery({ queryKey: [organizationId, "shipments"], enabled: !!organizationId, queryFn: async () => failIfError(await api.GET("/api/v1/shipments")) });
  const pallets = useQuery({ queryKey: [organizationId, "pallet-types"], enabled: !!organizationId, queryFn: async () => failIfError(await api.GET("/api/v1/pallet-types")) });
  const units = useQuery({ queryKey: [organizationId, "packaging-units"], enabled: !!organizationId, queryFn: async () => failIfError(await api.GET("/api/v1/packaging-units")) });
  const [shipmentId, setShipmentId] = useState("");
  const [palletId, setPalletId] = useState("");
  const [runId, setRunId] = useState("");
  const runs = useQuery({ queryKey: [organizationId, "shipment-runs", shipmentId], enabled: !!shipmentId, queryFn: async () => failIfError(await api.GET("/api/v1/shipments/{shipment_id}/runs", { params: { path: { shipment_id: shipmentId } } })) });
  const displayedRunId = runId || runs.data?.[0]?.id || "";
  const [palletForm, setPalletForm] = useState<PalletCreate>({ code: "", length_mm: 1200, width_mm: 800, deck_height_mm: 144, max_total_height_mm: 1000, max_cargo_mass_g: 100000, tare_mass_g: 25000, available_count: 1, support_model: "solid_deck", evidence_ref: "" });
  const [verification, setVerification] = useState({ unitId: "", evidence_ref: "", top_load_limit_g: "", allow_upright_90: false });
  const preflight = useMutation({ mutationFn: async () => failIfError(await api.POST("/api/v1/shipments/{shipment_id}/preflight", { params: { path: { shipment_id: shipmentId } }, body: { pallet_type_id: palletId } })) });
  const run = useMutation({ mutationFn: async () => {
    const shipment = shipments.data?.find((item) => item.id === shipmentId);
    if (!shipment) throw new Error("SHIPMENT_NOT_SELECTED");
    return failIfError(await api.POST("/api/v1/shipments/{shipment_id}/runs", { params: { path: { shipment_id: shipmentId }, header: { "idempotency-key": crypto.randomUUID() } }, body: { pallet_type_id: palletId, expected_shipment_revision: shipment.revision, strategy: "quick", evaluation_budget: 250000 } }));
  }, onSuccess: (data) => { setRunId(data.id); void queryClient.invalidateQueries({ queryKey: [organizationId, "shipment-runs", shipmentId] }); } });
  const runStatus = useQuery({ queryKey: [organizationId, "run", displayedRunId], enabled: !!displayedRunId, queryFn: async () => failIfError(await api.GET("/api/v1/runs/{run_id}", { params: { path: { run_id: displayedRunId } } })), refetchInterval: (query) => ["succeeded", "failed", "cancelled"].includes(query.state.data?.status ?? "") ? false : 1000 });
  const planId = runStatus.data?.plan_id;
  const plan = useQuery({ queryKey: [organizationId, "plan", planId], enabled: !!planId, queryFn: async () => failIfError(await api.GET("/api/v1/plans/{plan_id}", { params: { path: { plan_id: planId! } } })) });
  const createPallet = useMutation({ mutationFn: async () => failIfError(await api.POST("/api/v1/pallet-types", { body: palletForm })), onSuccess: (data) => { setPalletId(data.id); void queryClient.invalidateQueries({ queryKey: [organizationId, "pallet-types"] }); } });
  const verifyUnit = useMutation({ mutationFn: async () => {
    const unit = units.data?.find((item) => item.id === verification.unitId);
    if (!unit) throw new Error("UNIT_NOT_SELECTED");
    const body: PackagingVerification = { expected_revision: unit.revision, evidence_ref: verification.evidence_ref, top_load_limit_g: verification.top_load_limit_g === "" ? null : Number(verification.top_load_limit_g), allow_upright_90: verification.allow_upright_90 };
    return failIfError(await api.POST("/api/v1/packaging-units/{unit_id}/verify", { params: { path: { unit_id: unit.id } }, body }));
  }, onSuccess: () => void queryClient.invalidateQueries({ queryKey: [organizationId, "packaging-units"] }) });
  const inputClass = "w-full rounded-md border border-neutral-300 bg-background px-3 py-2 text-sm dark:border-neutral-700";
  const statusLabel = (value: string) => value === "queued" ? t("queued") : value === "running" ? t("running") : value === "succeeded" ? t("succeeded") : value === "failed" ? t("failed") : value === "cancelled" ? t("cancelled") : t("unknownStatus");
  const blockerLabel = (code: string) => code in blockerMessages ? t(blockerMessages[code as keyof typeof blockerMessages]) : t("blocked");
  if (me.isLoading) return <main className="p-6">{t("checking")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  return <main className="mx-auto max-w-6xl p-6 text-foreground"><Link href="/en/workspace" className="text-sm underline">{t("back")}</Link><h1 className="mt-4 text-2xl font-semibold">{t("title")}</h1><p className="mt-2 text-muted">{t("description")}</p>
    <section className="mt-8 rounded-lg border p-5"><div className="grid gap-4 sm:grid-cols-2"><label className="grid gap-2 text-sm">{t("selectShipment")}<select className={inputClass} value={shipmentId} onChange={(event) => { setShipmentId(event.target.value); setRunId(""); preflight.reset(); }}><option value="">{t("choose")}</option>{shipments.data?.map((item) => <option key={item.id} value={item.id}>{item.shipment_ref}</option>)}</select></label><label className="grid gap-2 text-sm">{t("selectPallet")}<select className={inputClass} value={palletId} onChange={(event) => { setPalletId(event.target.value); preflight.reset(); }}><option value="">{t("choose")}</option>{pallets.data?.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></label></div>{shipments.data?.length === 0 && <p className="mt-4 text-sm text-muted">{t("noShipments")}</p>}{pallets.data?.length === 0 && <p className="mt-4 text-sm text-muted">{t("noPallets")}</p>}{(shipments.isError || pallets.isError || units.isError || runs.isError) && <p className="mt-4 text-sm text-red-700">{t("loadError")}</p>}{runs.data && runs.data.length > 0 && <label className="mt-4 grid gap-2 text-sm">{t("priorRuns")}<select className={inputClass} value={displayedRunId} onChange={(event) => setRunId(event.target.value)}>{runs.data.map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} — {statusLabel(item.status)}</option>)}</select></label>}<div className="mt-4 flex gap-3"><button className="rounded-md border px-4 py-2 text-sm disabled:opacity-50" disabled={!shipmentId || !palletId || preflight.isPending} onClick={() => preflight.mutate()}>{t("preflight")}</button><button className="rounded-md bg-neutral-950 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-50 dark:text-neutral-950" disabled={!preflight.data?.ready || run.isPending} onClick={() => run.mutate()}>{t("run")}</button></div>{preflight.data && <div className="mt-4 text-sm"><p>{preflight.data.ready ? t("ready") : t("blocked")}</p>{preflight.data.blockers.map((code) => <p className="mt-1 text-amber-700" key={code}>{blockerLabel(code)}</p>)}</div>}{(preflight.isError || run.isError || runStatus.isError || plan.isError) && <p className="mt-4 text-sm text-red-700">{t("error")}</p>}{runStatus.data && <p className="mt-4 text-sm">{statusLabel(runStatus.data.status)}</p>}</section>
    {me.data?.role === "admin" ? <div className="mt-6 grid gap-6 lg:grid-cols-2"><section className="rounded-lg border p-5"><h2 className="text-lg font-semibold">{t("palletSetup")}</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{([ ["code", "code"], ["length_mm", "length"], ["width_mm", "width"], ["deck_height_mm", "deckHeight"], ["max_total_height_mm", "totalHeight"], ["max_cargo_mass_g", "cargoMass"], ["tare_mass_g", "tareMass"], ["available_count", "available"], ["evidence_ref", "evidence"] ] as const).map(([field, label]) => <label className="grid gap-1 text-sm" key={field}>{t(label)}<input className={inputClass} type={field === "code" || field === "evidence_ref" ? "text" : "number"} value={palletForm[field]} onChange={(event) => setPalletForm((prior) => ({ ...prior, [field]: field === "code" || field === "evidence_ref" ? event.target.value : Number(event.target.value) }))} /></label>)}</div><button className="mt-4 rounded-md bg-neutral-950 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-50 dark:text-neutral-950" disabled={createPallet.isPending} onClick={() => createPallet.mutate()}>{t("createPallet")}</button>{createPallet.isError && <p className="mt-2 text-sm text-red-700">{t("error")}</p>}</section><section className="rounded-lg border p-5"><h2 className="text-lg font-semibold">{t("verify")}</h2><div className="mt-4 grid gap-3"><label className="grid gap-1 text-sm">{t("packagingUnit")}<select className={inputClass} value={verification.unitId} onChange={(event) => setVerification((prior) => ({ ...prior, unitId: event.target.value }))}><option value="">{t("choose")}</option>{units.data?.map((item) => <option key={item.id} value={item.id}>{item.code}</option>)}</select></label><label className="grid gap-1 text-sm">{t("evidence")}<input className={inputClass} value={verification.evidence_ref} onChange={(event) => setVerification((prior) => ({ ...prior, evidence_ref: event.target.value }))} /></label><label className="grid gap-1 text-sm">{t("topLoad")}<input className={inputClass} type="number" min="0" value={verification.top_load_limit_g} onChange={(event) => setVerification((prior) => ({ ...prior, top_load_limit_g: event.target.value }))} /></label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={verification.allow_upright_90} onChange={(event) => setVerification((prior) => ({ ...prior, allow_upright_90: event.target.checked }))} />{t("rotate")}</label></div><button className="mt-4 rounded-md bg-neutral-950 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-50 dark:text-neutral-950" disabled={!verification.unitId || !verification.evidence_ref || verifyUnit.isPending} onClick={() => verifyUnit.mutate()}>{t("verifyAction")}</button>{verifyUnit.isError && <p className="mt-2 text-sm text-red-700">{t("error")}</p>}</section></div> : <p className="mt-6 text-sm text-muted">{t("permission")}</p>}
    <section className="mt-8"><h2 className="text-lg font-semibold">{t("result")}</h2>{plan.data ? <><p className="mt-2 text-sm text-muted">{t("modelOnly")}</p><div className="mt-4 grid gap-3 sm:grid-cols-4"><Metric label={t("placed")} value={String(plan.data.layout.placed_instances)} /><Metric label={t("unplaced")} value={String(plan.data.layout.unplaced_instances)} /><Metric label={t("loadedHeight")} value={`${plan.data.layout.loaded_height_mm} mm`} /><Metric label={t("loadedMass")} value={`${(plan.data.layout.loaded_mass_g / 1000).toFixed(3)} kg`} /></div><PlanDrawing layout={plan.data.layout} /></> : <p className="mt-4 text-sm text-muted">{t("empty")}</p>}</section>
  </main>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border p-4"><span className="text-xs text-muted">{label}</span><p className="mt-1 font-medium tabular-nums">{value}</p></div>; }

export function PlanDrawing({ layout, focusInstanceId, onSelect, visibleInstanceIds }: { layout: Layout; focusInstanceId?: string; onSelect?: (id: string) => void; visibleInstanceIds?: string[] }) {
  const t = useTranslations("planning");
  const scene = useTranslations("scene");
  const [palletIndex, setPalletIndex] = useState(0);
  const [layer, setLayer] = useState(0);
  const [internalSelectedId, setInternalSelectedId] = useState("");
  const [show3d, setShow3d] = useState(false);
  const [throughLayer, setThroughLayer] = useState(false);
  const [webgl, setWebgl] = useState(false);
  useEffect(() => {
    const canvas = document.createElement("canvas");
    setWebgl(Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl")));
  }, []);
  const selectedId = focusInstanceId ?? internalSelectedId;
  const select = onSelect ?? setInternalSelectedId;
  const chosen = layout.placed.find((item) => item.instance_id === selectedId);
  const activePallet = chosen?.pallet_index ?? palletIndex;
  const levels = [...new Set(layout.placed.filter((item) => item.pallet_index === activePallet).map((item) => item.z_mm))].sort((a, b) => a - b);
  const activeLayer = chosen ? levels.indexOf(chosen.z_mm) : layer;
  const z = levels[activeLayer] ?? levels[0] ?? 0;
  const visible = layout.placed.filter((item) => item.pallet_index === activePallet && item.z_mm === z && (!visibleInstanceIds || visibleInstanceIds.includes(item.instance_id)));
  return <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]"><div>
    <div className="mb-3 flex flex-wrap gap-3"><label className="text-sm">{t("pallet")} <select className="ml-2 rounded border bg-background px-2 py-1" value={activePallet} onChange={(event) => { select(""); setPalletIndex(Number(event.target.value)); setLayer(0); }}>{Array.from({ length: layout.pallet_count }, (_, i) => <option key={i} value={i}>{i + 1}</option>)}</select></label><label className="text-sm">{t("level")} <select className="ml-2 rounded border bg-background px-2 py-1" value={activeLayer} onChange={(event) => { select(""); setLayer(Number(event.target.value)); }}>{levels.map((level, i) => <option key={level} value={i}>{i + 1} (z={level} mm)</option>)}</select></label><button className="rounded border px-3 py-1 text-sm disabled:opacity-50" disabled={!webgl} onClick={() => setShow3d((value) => !value)}>{show3d ? t("show2d") : t("show3d")}</button>{show3d && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={throughLayer} onChange={(event) => setThroughLayer(event.target.checked)} />{scene("throughLayer")}</label>}</div>
    {show3d && webgl ? <PalletScene layout={layout} palletIndex={activePallet} selectedId={selectedId} onSelect={select} visibleInstanceIds={visibleInstanceIds} maxZ={throughLayer ? z : undefined} /> : <svg className="w-full max-w-2xl rounded border bg-neutral-50 dark:bg-neutral-900" viewBox={`0 0 ${layout.pallet.length_mm} ${layout.pallet.width_mm}`} role="img" aria-label={`${t("pallet")} ${activePallet + 1}, ${t("level")} ${activeLayer + 1}`}><rect x="0" y="0" width={layout.pallet.length_mm} height={layout.pallet.width_mm} fill="transparent" stroke="currentColor" strokeWidth="4" />{visible.map((item, i) => <g key={item.instance_id} onClick={() => select(item.instance_id)} tabIndex={0} role="button" onKeyDown={(event) => { if (event.key === "Enter") select(item.instance_id); }} aria-label={`${item.sku ?? layout.carton?.sku ?? ""} ${i + 1}`}><rect x={item.x_mm} y={item.y_mm} width={item.length_mm} height={item.width_mm} fill={selectedId === item.instance_id ? "#525252" : skuColor(item.sku ?? layout.carton?.sku ?? "")} stroke="#404040" strokeWidth="3" /><text x={item.x_mm + item.length_mm / 2} y={item.y_mm + item.width_mm / 2} textAnchor="middle" dominantBaseline="middle" fontSize="42" fill="#171717">{i + 1}</text></g>)}</svg>}
    {!webgl && <p className="mt-2 text-sm text-muted">{t("noWebgl")}</p>}
  </div><div className="rounded-lg border p-4"><h3 className="font-medium">{t("selected")}</h3>{chosen ? <dl className="mt-3 grid gap-2 text-sm"><div>SKU: {chosen.sku ?? layout.carton?.sku}</div><div>ID: {chosen.instance_id}</div><div>x/y/z: {chosen.x_mm}/{chosen.y_mm}/{chosen.z_mm} mm</div><div>{chosen.orientation_code}</div><div>{t("sequence")}: {layout.instructions.find((step) => step.instance_id === chosen.instance_id)?.sequence_no}</div></dl> : <p className="mt-3 text-sm text-muted">{t("choose")}</p>}</div></div>;
}
