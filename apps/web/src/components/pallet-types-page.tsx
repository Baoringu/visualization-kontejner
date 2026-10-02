"use client";

import Link from "next/link";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import type { components } from "../lib/api/schema";

type PalletCreate = components["schemas"]["PalletTypeCreate"];
const input = "w-full rounded-md border bg-background px-3 py-2 text-sm";

export function PalletTypesPage() {
  const t = useTranslations("palletTypes");
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => { const result = await api.GET("/api/v1/me"); if (!result.data) throw new Error("AUTH_REQUIRED"); return result.data; }, retry: false });
  const scope = me.data?.organization.id;
  const pallets = useQuery({ queryKey: [scope, "pallet-types"], enabled: !!scope, queryFn: async () => { const result = await api.GET("/api/v1/pallet-types"); if (!result.data) throw new Error("REQUEST_FAILED"); return result.data; } });
  const [form, setForm] = useState({ code: "", length_mm: 1200, width_mm: 800, deck_height_mm: 144, max_total_height_mm: 1000, cargo_kg: "100.000", tare_kg: "25.000", available_count: 1, evidence_ref: "" });
  const create = useMutation({ mutationFn: async () => {
    const body: PalletCreate = { code: form.code.trim(), length_mm: form.length_mm, width_mm: form.width_mm, deck_height_mm: form.deck_height_mm, max_total_height_mm: form.max_total_height_mm, max_cargo_mass_g: Math.round(Number(form.cargo_kg) * 1000), tare_mass_g: Math.round(Number(form.tare_kg) * 1000), available_count: form.available_count, support_model: "solid_deck", evidence_ref: form.evidence_ref.trim() };
    const result = await api.POST("/api/v1/pallet-types", { body });
    if (!result.data) throw new Error("REQUEST_FAILED");
    return result.data;
  }, onSuccess: () => { setForm((prior) => ({ ...prior, code: "", evidence_ref: "" })); void client.invalidateQueries({ queryKey: [scope, "pallet-types"] }); } });
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  return <main className="mx-auto max-w-6xl px-5 py-7 lg:px-8"><p className="text-xs font-medium uppercase tracking-wide text-muted">{t("eyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 max-w-3xl text-sm text-muted">{t("description")}</p><div className="mt-7 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]"><section><h2 className="text-lg font-semibold">{t("availableTypes")}</h2>{pallets.isLoading ? <p className="mt-4 text-sm text-muted">{t("loading")}</p> : pallets.isError ? <p role="alert" className="mt-4 text-sm text-red-700">{t("loadError")}</p> : pallets.data?.length === 0 ? <p className="mt-4 rounded-lg border p-6 text-sm text-muted">{t("empty")}</p> : <div className="mt-4 grid gap-3">{pallets.data?.map((pallet) => <article key={pallet.id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><h3 className="font-semibold">{pallet.code}</h3><span className="text-xs text-muted">{t("count", { count: pallet.available_count })}</span></div><p className="mt-2 text-sm text-muted">{pallet.length_mm} × {pallet.width_mm} mm · {t("deck")} {pallet.deck_height_mm} mm · {t("maxHeight")} {pallet.max_total_height_mm} mm</p><p className="mt-1 text-sm text-muted">{t("cargo")} {(pallet.max_cargo_mass_g / 1000).toFixed(3)} kg · {t("tare")} {(pallet.tare_mass_g / 1000).toFixed(3)} kg</p><p className="mt-2 text-xs text-muted">{t("evidence")}: {pallet.evidence_ref}</p></article>)}</div>}</section><section className="rounded-lg border p-5"><h2 className="text-lg font-semibold">{t("create")}</h2><p className="mt-2 text-sm text-muted">{t("solidDeckNote")}</p><form className="mt-4 grid gap-3" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}><label className="grid gap-1 text-sm">{t("code")}<input className={input} required maxLength={100} value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} /></label><div className="grid grid-cols-2 gap-3">{([ ["length_mm", "length"], ["width_mm", "width"], ["deck_height_mm", "deckHeight"], ["max_total_height_mm", "maxHeight"], ["available_count", "available"] ] as const).map(([field, label]) => <label key={field} className="grid gap-1 text-sm">{t(label)}<input className={input} type="number" min="1" required value={form[field]} onChange={(event) => setForm({ ...form, [field]: Number(event.target.value) })} /></label>)}</div><div className="grid grid-cols-2 gap-3"><label className="grid gap-1 text-sm">{t("cargoKg")}<input className={input} inputMode="decimal" required value={form.cargo_kg} onChange={(event) => setForm({ ...form, cargo_kg: event.target.value })} /></label><label className="grid gap-1 text-sm">{t("tareKg")}<input className={input} inputMode="decimal" required value={form.tare_kg} onChange={(event) => setForm({ ...form, tare_kg: event.target.value })} /></label></div><label className="grid gap-1 text-sm">{t("evidence")}<input className={input} required minLength={3} value={form.evidence_ref} onChange={(event) => setForm({ ...form, evidence_ref: event.target.value })} /></label><button className="rounded-md bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900" disabled={create.isPending || !form.code.trim() || !form.evidence_ref.trim()}>{create.isPending ? t("saving") : t("save")}</button><p role="status" className="text-sm text-muted">{create.isError ? t("saveError") : create.isSuccess ? t("saved") : ""}</p></form></section></div></main>;
}
