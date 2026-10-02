"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";
import type { components } from "../lib/api/schema";

type Customer = components["schemas"]["CustomerOut"];
type CustomerCreate = components["schemas"]["CustomerCreate"];
type Form = Record<"external_ref" | "name" | "contact_name" | "contact_email" | "contact_phone" | "ship_to_name" | "ship_to_address_line1" | "ship_to_address_line2" | "ship_to_city" | "ship_to_postal_code" | "ship_to_country_code" | "delivery_instructions", string>;
const blank: Form = { external_ref: "", name: "", contact_name: "", contact_email: "", contact_phone: "", ship_to_name: "", ship_to_address_line1: "", ship_to_address_line2: "", ship_to_city: "", ship_to_postal_code: "", ship_to_country_code: "", delivery_instructions: "" };
const fields: { key: keyof Form; label: string; wide?: boolean }[] = [
  { key: "external_ref", label: "reference" }, { key: "name", label: "name" },
  { key: "contact_name", label: "contactName" }, { key: "contact_email", label: "contactEmail" }, { key: "contact_phone", label: "contactPhone" },
  { key: "ship_to_name", label: "shipToName" }, { key: "ship_to_address_line1", label: "addressLine1", wide: true }, { key: "ship_to_address_line2", label: "addressLine2", wide: true },
  { key: "ship_to_city", label: "city" }, { key: "ship_to_postal_code", label: "postalCode" }, { key: "ship_to_country_code", label: "countryCode" },
  { key: "delivery_instructions", label: "deliveryInstructions", wide: true },
];

function required<T>(result: { data?: T; error?: unknown }): T { if (!result.data || result.error) throw new Error("REQUEST_FAILED"); return result.data; }
function toForm(customer: Customer): Form { return Object.fromEntries(Object.keys(blank).map((key) => [key, customer[key as keyof Form] ?? ""])) as Form; }
function payload(form: Form): CustomerCreate {
  return {
    external_ref: form.external_ref.trim(), name: form.name.trim(),
    contact_name: form.contact_name.trim() || null, contact_email: form.contact_email.trim() || null,
    contact_phone: form.contact_phone.trim() || null, ship_to_name: form.ship_to_name.trim() || null,
    ship_to_address_line1: form.ship_to_address_line1.trim() || null, ship_to_address_line2: form.ship_to_address_line2.trim() || null,
    ship_to_city: form.ship_to_city.trim() || null, ship_to_postal_code: form.ship_to_postal_code.trim() || null,
    ship_to_country_code: form.ship_to_country_code.trim().toUpperCase() || null,
    delivery_instructions: form.delivery_instructions.trim() || null,
  };
}

export function CustomersPage() {
  const t = useTranslations("customers");
  const client = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: async () => required(await api.GET("/api/v1/me")), retry: false });
  const scope = me.data?.organization.id;
  const customers = useQuery({ queryKey: [scope, "customers"], enabled: !!scope, queryFn: async () => required(await api.GET("/api/v1/customers")) });
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState<Form>(blank);
  const selected = customers.data?.find((item) => item.id === selectedId);
  const save = useMutation({ mutationFn: async () => {
    const body = payload(form);
    if (selected) return required(await api.PUT("/api/v1/customers/{customer_id}", { params: { path: { customer_id: selected.id } }, body: { ...body, expected_revision: selected.revision } }));
    return required(await api.POST("/api/v1/customers", { body }));
  }, onSuccess: (item) => { setSelectedId(item.id); setForm(toForm(item)); void client.invalidateQueries({ queryKey: [scope, "customers"] }); } });
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  return <main className="mx-auto max-w-[1450px] px-5 py-7 lg:px-8">
    <p className="text-xs font-medium uppercase tracking-wide text-muted">{t("eyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 text-sm text-muted">{t("description")}</p>
    <div className="mt-7 grid items-start gap-6 lg:grid-cols-[minmax(260px,380px)_minmax(0,1fr)]">
      <section><div className="flex items-center justify-between"><h2 className="text-lg font-semibold">{t("records")}</h2><button className="rounded-md border px-3 py-2 text-sm" onClick={() => { setSelectedId(""); setForm(blank); save.reset(); }}>{t("new")}</button></div>
        {customers.isLoading ? <p className="mt-4 text-sm text-muted">{t("loading")}</p> : customers.isError ? <p role="alert" className="mt-4 text-sm text-red-700">{t("loadError")}</p> : customers.data?.length ? <div className="mt-4 divide-y rounded-lg border">{customers.data.map((item) => <button key={item.id} className={`block w-full px-4 py-3 text-left hover:bg-muted ${selectedId === item.id ? "bg-muted" : ""}`} onClick={() => { setSelectedId(item.id); setForm(toForm(item)); save.reset(); }}><span className="block font-medium">{item.name}</span><span className="text-sm text-muted">{item.external_ref}{item.ship_to_city ? ` · ${item.ship_to_city}` : ""}</span></button>)}</div> : <p className="mt-4 rounded-lg border p-5 text-sm text-muted">{t("empty")}</p>}
      </section>
      <section className="rounded-lg border p-5"><h2 className="text-lg font-semibold">{selected ? t("edit") : t("new")}</h2><p className="mt-1 text-sm text-muted">{t("shippingHint")}</p>
        <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>{fields.map(({ key, label, wide }) => <label key={key} className={`grid gap-1 text-sm ${wide ? "sm:col-span-2" : ""}`}>{t(label)}{key === "delivery_instructions" ? <textarea className="min-h-24 rounded-md border bg-background px-3 py-2" maxLength={1000} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /> : <input className="rounded-md border bg-background px-3 py-2" required={key === "external_ref" || key === "name"} maxLength={key === "ship_to_country_code" ? 2 : undefined} type={key === "contact_email" ? "email" : "text"} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />}</label>)}
          <div className="sm:col-span-2"><button className="rounded-md bg-neutral-900 px-4 py-2.5 text-sm text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900" disabled={!form.name.trim() || !form.external_ref.trim() || save.isPending}>{save.isPending ? t("saving") : selected ? t("update") : t("save")}</button>{save.isError && <p role="alert" className="mt-2 text-sm text-red-700">{t("saveError")}</p>}{save.isSuccess && <p role="status" className="mt-2 text-sm">{t("saved")}</p>}</div>
        </form>
      </section>
    </div>
  </main>;
}
