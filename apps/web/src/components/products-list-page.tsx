"use client";

import Link from "next/link";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api/client";

export function ProductsListPage() {
  const t = useTranslations("catalog");
  const list = useTranslations("productList");
  const [search, setSearch] = useState("");
  const me = useQuery({ queryKey: ["me"], queryFn: async () => { const response = await api.GET("/api/v1/me"); if (!response.data) throw new Error("AUTH_REQUIRED"); return response.data; }, retry: false });
  const scope = me.data?.organization.id;
  const products = useQuery({ queryKey: [scope, "products"], enabled: !!scope, queryFn: async () => { const response = await api.GET("/api/v1/products"); if (!response.data) throw new Error("REQUEST_FAILED"); return response.data; } });
  const units = useQuery({ queryKey: [scope, "packaging-units"], enabled: !!scope, queryFn: async () => { const response = await api.GET("/api/v1/packaging-units"); if (!response.data) throw new Error("REQUEST_FAILED"); return response.data; } });
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  const filtered = products.data?.filter((item) => `${item.sku} ${item.name}`.toLowerCase().includes(search.toLowerCase())) ?? [];
  return <main className="mx-auto max-w-[1450px] px-5 py-7 lg:px-8">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-medium uppercase tracking-wide text-muted">{t("eyebrow")}</p><h1 className="mt-1 text-3xl font-semibold tracking-tight">{t("title")}</h1><p className="mt-2 max-w-3xl text-sm text-muted">{t("description")}</p></div><Link href="/en/catalog/products/new" className="rounded-md bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white dark:bg-neutral-100 dark:text-neutral-900">{list("create")}</Link></div>
    <label className="mt-7 block max-w-lg text-sm">{list("search")}<input className="mt-1 w-full rounded-md border bg-background px-3 py-2" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    {products.isLoading || units.isLoading ? <p className="mt-5 text-sm text-muted">{t("loading")}</p> : products.isError || units.isError ? <p role="alert" className="mt-5 text-sm text-red-700">{t("loadError")}</p> : filtered.length === 0 ? <p className="mt-5 rounded-lg border p-6 text-sm text-muted">{t("empty")}</p> : <div className="mt-5 divide-y rounded-lg border">{filtered.map((item) => { const count = units.data?.filter((unit) => unit.product_id === item.id).length ?? 0; return <Link href={`/en/catalog/products/${item.id}`} key={item.id} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-muted"><span><span className="block text-xs font-medium text-muted">{item.sku}</span><span className="mt-1 block font-medium">{item.name}</span><span className="mt-1 block text-sm text-muted">{list("packagingCount", { count })}</span></span><span className="shrink-0 text-sm underline">{list("open")}</span></Link>; })}</div>}
  </main>;
}
