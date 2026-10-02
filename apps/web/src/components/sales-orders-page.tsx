"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import type { components } from "../lib/api/schema";

type CartLine = components["schemas"]["CartLineWrite"];
type Unit = components["schemas"]["PackagingUnitOut"];

const input = "w-full rounded-md border bg-background px-3 py-2 text-sm";
const primary = "rounded-md bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900";
function required<T>(result: { data?: T; error?: unknown }): T { if (!result.data || result.error) throw new Error("REQUEST_FAILED"); return result.data; }

export function SalesOrdersPage() {
  const t = useTranslations("sales");
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => required(await api.GET("/api/v1/me")), retry: false });
  const scope = me.data?.organization.id;
  const customers = useQuery({ queryKey: [scope, "customers"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/customers")) });
  const products = useQuery({ queryKey: [scope, "products"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/products")) });
  const units = useQuery({ queryKey: [scope, "packaging-units"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/packaging-units")) });
  const orders = useQuery({ queryKey: [scope, "orders"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/orders")) });
  const shipments = useQuery({ queryKey: [scope, "shipments"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/shipments")) });
  const [orderId, setOrderId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [orderRef, setOrderRef] = useState("");
  const [shipmentRef, setShipmentRef] = useState("");
  const [search, setSearch] = useState("");
  const [basket, setBasket] = useState<CartLine[]>([]);
  const [dirty, setDirty] = useState(false);
  const hydratedRevision = useRef("");
  const [lastShipment, setLastShipment] = useState("");
  const detail = useQuery({ queryKey: [scope, "order", orderId], enabled: !!orderId, queryFn: async () => required(await api.GET("/api/v1/orders/{order_id}", { params: { path: { order_id: orderId } } })) });
  useEffect(() => {
    if (!detail.data || !units.data) return;
    const key = `${detail.data.id}:${detail.data.revision}`;
    if (hydratedRevision.current === key) return;
    hydratedRevision.current = key;
    setBasket(detail.data.lines.map((line) => {
      const unit = units.data?.find((item) => item.id === line.packaging_unit_id);
      return { packaging_unit_id: line.packaging_unit_id, quantity_cartons: unit ? line.quantity_units / unit.units_per_package : line.quantity_units };
    }));
    setDirty(false);
  }, [detail.data, units.data]);
  const createOrder = useMutation({ mutationFn: async () => required(await api.POST("/api/v1/orders", { body: { customer_id: customerId, order_ref: orderRef.trim() } })), onSuccess: (order) => { setOrderId(order.id); setOrderRef(""); void client.invalidateQueries({ queryKey: [scope, "orders"] }); } });
  const save = useMutation({ mutationFn: async () => {
    if (!detail.data) throw new Error("ORDER_NOT_LOADED");
    return required(await api.PUT("/api/v1/orders/{order_id}/cart", { params: { path: { order_id: detail.data.id } }, body: { expected_revision: detail.data.revision, lines: basket } }));
  }, onSuccess: (order) => { client.setQueryData([scope, "order", order.id], order); setDirty(false); void client.invalidateQueries({ queryKey: [scope, "orders"] }); } });
  const ship = useMutation({ mutationFn: async () => {
    if (!detail.data || dirty || !shipmentRef.trim()) throw new Error("UNSAVED_ORDER");
    const lines = detail.data.lines.filter((line) => line.quantity_units > line.allocated_units).map((line) => ({ packaging_unit_id: line.packaging_unit_id, line_no: line.line_no, quantity_units: line.quantity_units - line.allocated_units }));
    if (!lines.length) throw new Error("NO_REMAINING_ITEMS");
    return required(await api.POST("/api/v1/orders/{order_id}/shipments", { params: { path: { order_id: detail.data.id } }, body: { shipment_ref: shipmentRef.trim(), lines } }));
  }, onSuccess: (shipment) => { setLastShipment(shipment.shipment_ref); setShipmentRef(""); void client.invalidateQueries({ queryKey: [scope, "shipments"] }); void client.invalidateQueries({ queryKey: [scope, "order", orderId] }); } });
  function changeQuantity(unitId: string, quantity: number) {
    setBasket((current) => current.filter((line) => line.packaging_unit_id !== unitId).concat(quantity > 0 ? [{ packaging_unit_id: unitId, quantity_cartons: quantity }] : []));
    setDirty(true);
    save.reset();
  }
  function add(unitId: string) { changeQuantity(unitId, (basket.find((line) => line.packaging_unit_id === unitId)?.quantity_cartons ?? 0) + 1); }
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "sales" && me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  const filtered = (units.data ?? []).filter((unit) => {
    const product = products.data?.find((item) => item.id === unit.product_id);
    return `${product?.sku ?? ""} ${product?.name ?? ""} ${unit.code}`.toLowerCase().includes(search.toLowerCase());
  });
  const cartonCount = basket.reduce((sum, line) => sum + line.quantity_cartons, 0);
  const knownMass = basket.reduce((sum, line) => sum + line.quantity_cartons * (units.data?.find((unit) => unit.id === line.packaging_unit_id)?.mass_g ?? 0), 0);
  const unresolved = basket.filter((line) => !units.data?.find((unit) => unit.id === line.packaging_unit_id)?.is_verified).length;
  const selectedShipments = shipments.data?.filter((shipment) => shipment.order_id === orderId) ?? [];
  const locked = Boolean(detail.data?.lines.some((line) => line.allocated_units > 0));
  const selectedCustomer = customers.data?.find((item) => item.id === (detail.data?.customer_id ?? customerId));
  const customerText = selectedCustomer ? [selectedCustomer.ship_to_name, selectedCustomer.ship_to_address_line1, selectedCustomer.ship_to_address_line2, selectedCustomer.ship_to_postal_code, selectedCustomer.ship_to_city, selectedCustomer.ship_to_country_code].filter(Boolean).join(", ") : "";
  return <main className="mx-auto max-w-[1500px] px-5 py-7 lg:px-8">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-medium uppercase tracking-wide text-muted">{t("eyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 text-sm text-muted">{t("description")}</p></div><span className="rounded-md border px-3 py-1.5 text-sm text-muted">{me.data.organization.name}</span></div>
    <section className="mt-7 rounded-lg border bg-background p-5" aria-label={t("orderHeader")}><div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"><label className="grid gap-1 text-sm">{t("customer")}<select className={input} value={customerId} onChange={(event) => setCustomerId(event.target.value)}><option value="">{t("chooseCustomer")}</option>{customers.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="grid gap-1 text-sm">{t("orderRef")}<input className={input} value={orderRef} onChange={(event) => setOrderRef(event.target.value)} placeholder={t("orderRefPlaceholder")} /></label><button className={`${primary} self-end`} disabled={!customerId || !orderRef.trim() || createOrder.isPending} onClick={() => createOrder.mutate()}>{createOrder.isPending ? t("creating") : t("createOrder")}</button></div>
      {selectedCustomer && <div className="mt-4 border-t pt-4 text-sm"><p className="font-medium">{selectedCustomer.name}</p><p className="mt-1 text-muted">{customerText || "—"}</p>{selectedCustomer.contact_name && <p className="mt-1 text-muted">{selectedCustomer.contact_name}{selectedCustomer.contact_phone ? ` · ${selectedCustomer.contact_phone}` : ""}</p>}</div>}
      <div className="mt-5 grid gap-3 border-t pt-4 md:grid-cols-[minmax(0,1fr)_auto]"><label className="grid gap-1 text-sm">{t("openOrder")}<select className={input} value={orderId} onChange={(event) => { setOrderId(event.target.value); setBasket([]); setDirty(false); setLastShipment(""); }}><option value="">{t("chooseOrder")}</option>{orders.data?.map((item) => <option key={item.id} value={item.id}>{item.order_ref}</option>)}</select></label><span className="self-end text-sm text-muted">{detail.data ? `${t("revision")} ${detail.data.revision}` : t("selectOrderHint")}</span></div>
      {(customers.isError || products.isError || units.isError || orders.isError || detail.isError) && <p role="alert" className="mt-3 text-sm text-red-700">{t("loadError")}</p>}{createOrder.isError && <p role="alert" className="mt-3 text-sm text-red-700">{t("createError")}</p>}
    </section>
    <div className="mt-6 grid items-start gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(340px,2fr)]"><section className="min-w-0"><div className="flex flex-wrap items-end justify-between gap-4"><div><h2 className="text-xl font-semibold">{t("catalog")}</h2><p className="mt-1 text-sm text-muted">{t("catalogHint")}</p></div><label className="w-full max-w-xs text-sm">{t("search")}<input className={`${input} mt-1`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("searchPlaceholder")} /></label></div>
      {units.isLoading || products.isLoading ? <p className="mt-5 text-muted">{t("loading")}</p> : filtered.length === 0 ? <p className="mt-5 rounded-lg border p-6 text-sm text-muted">{t("noProducts")}</p> : <div className="mt-4 grid gap-3 sm:grid-cols-2">{filtered.map((unit) => { const product = products.data?.find((item) => item.id === unit.product_id); return <article key={unit.id} className="flex min-h-44 flex-col rounded-lg border bg-background p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-medium text-muted">{product?.sku ?? unit.code} · {unit.code}</p><h3 className="mt-1 font-semibold">{product?.name ?? unit.code}</h3></div><span className={`rounded border px-2 py-0.5 text-xs ${unit.is_verified ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>{unit.is_verified ? t("verified") : t("unverified")}</span></div><div className="mt-4 text-sm text-muted"><p>{unit.length_mm} × {unit.width_mm} × {unit.height_mm} mm</p><p>{(unit.mass_g / 1000).toFixed(3)} kg / {t("carton")}</p><p>{unit.units_per_package} {t("unitsPerCarton")}</p></div><button className="mt-auto self-start rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-40" disabled={!orderId || locked || save.isPending} onClick={() => add(unit.id)}>{t("addToOrder")}</button></article>; })}</div>}
    </section><aside className="rounded-lg border bg-background p-5 xl:sticky xl:top-6" aria-label={t("basket")}><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">{t("basket")}</h2><span className="text-sm text-muted">{cartonCount} {t("cartons")}</span></div>{!orderId ? <p className="mt-5 text-sm text-muted">{t("createFirst")}</p> : detail.isLoading ? <p className="mt-5 text-sm text-muted">{t("loading")}</p> : basket.length === 0 ? <p className="mt-5 rounded-md border border-dashed p-6 text-sm text-muted">{t("emptyBasket")}</p> : <div className="mt-4 divide-y">{basket.map((line) => { const unit = units.data?.find((item) => item.id === line.packaging_unit_id); const product = products.data?.find((item) => item.id === unit?.product_id); return <div key={line.packaging_unit_id} className="flex items-center justify-between gap-3 py-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{product?.name ?? unit?.code}</p><p className="text-xs text-muted">{product?.sku} · {unit?.code} · {unit ? (unit.mass_g / 1000).toFixed(3) : "—"} kg</p></div><div className="flex items-center gap-1"><button aria-label={t("decrease", { name: product?.name ?? unit?.code ?? "" })} className="h-9 w-9 rounded border text-lg disabled:opacity-40" disabled={locked || save.isPending} onClick={() => changeQuantity(line.packaging_unit_id, line.quantity_cartons - 1)}>−</button><input aria-label={t("quantity", { name: product?.name ?? unit?.code ?? "" })} className="h-9 w-14 rounded border bg-background text-center text-sm" type="number" min="0" value={line.quantity_cartons} disabled={locked || save.isPending} onChange={(event) => changeQuantity(line.packaging_unit_id, Math.max(0, Number(event.target.value) || 0))} /><button aria-label={t("increase", { name: product?.name ?? unit?.code ?? "" })} className="h-9 w-9 rounded border text-lg disabled:opacity-40" disabled={locked || save.isPending} onClick={() => changeQuantity(line.packaging_unit_id, line.quantity_cartons + 1)}>+</button></div></div>; })}</div>}
      <div className="mt-4 space-y-2 border-t pt-4 text-sm"><div className="flex justify-between"><span className="text-muted">{t("cartons")}</span><strong>{cartonCount}</strong></div><div className="flex justify-between"><span className="text-muted">{t("knownMass")}</span><strong>{(knownMass / 1000).toFixed(3)} kg</strong></div>{unresolved > 0 && <p className="text-amber-700 dark:text-amber-400">{t("missingVerification", { count: unresolved })}</p>}<p className="text-muted">{t("palletEstimateLater")}</p></div>
      <button className={`${primary} mt-5 w-full`} disabled={!orderId || !dirty || save.isPending || locked} onClick={() => save.mutate()}>{save.isPending ? t("saving") : t("saveOrder")}</button><p role="status" className="mt-2 min-h-5 text-sm text-muted">{locked ? t("allocatedLocked") : save.isError ? t("saveConflict") : dirty ? t("unsaved") : detail.data ? t("saved") : ""}</p>{save.isError && <button className="text-sm underline" onClick={() => { void detail.refetch(); save.reset(); }}>{t("reloadServer")}</button>}
      <div className="mt-5 border-t pt-5"><h3 className="font-medium">{t("shipment")}</h3><p className="mt-1 text-sm text-muted">{t("shipmentHint")}</p><label className="mt-3 grid gap-1 text-sm">{t("shipmentRef")}<input className={input} value={shipmentRef} onChange={(event) => setShipmentRef(event.target.value)} /></label><button className={`${primary} mt-3 w-full`} disabled={!orderId || dirty || !detail.data?.lines.length || !shipmentRef.trim() || ship.isPending} onClick={() => ship.mutate()}>{ship.isPending ? t("creating") : t("createShipment")}</button>{ship.isError && <p role="alert" className="mt-2 text-sm text-red-700">{t("shipmentError")}</p>}{lastShipment && <p role="status" className="mt-2 text-sm">{t("shipmentCreated", { reference: lastShipment })}</p>}{selectedShipments.length > 0 && <div className="mt-4 border-t pt-3"><p className="text-xs font-medium uppercase text-muted">{t("shipments")}</p>{selectedShipments.map((shipment) => <p key={shipment.id} className="mt-2 text-sm">{shipment.shipment_ref} · {shipment.lines.length} {t("lines")} <Link href="/en/planning" className="ml-2 underline">{t("viewPlans")}</Link></p>)}</div>}</div>
    </aside></div>
  </main>;
}
