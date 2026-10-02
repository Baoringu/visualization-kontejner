"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api/client";

export function ProductCreatePage() {
  const t = useTranslations("catalog");
  const list = useTranslations("productList");
  const router = useRouter();
  const client = useQueryClient();
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const me = useQuery({ queryKey: ["me"], queryFn: async () => { const response = await api.GET("/api/v1/me"); if (!response.data) throw new Error("AUTH_REQUIRED"); return response.data; }, retry: false });
  const scope = me.data?.organization.id;
  const create = useMutation({ mutationFn: async () => { const response = await api.POST("/api/v1/products", { body: { sku: sku.trim(), name: name.trim() } }); if (!response.data) throw new Error("REQUEST_FAILED"); return response.data; }, onSuccess: (item) => { void client.invalidateQueries({ queryKey: [scope, "products"] }); router.push(`/en/catalog/products/${item.id}`); } });
  if (me.isLoading) return <main className="p-6">{t("loading")}</main>;
  if (me.isError) return <main className="p-6"><Link href="/en/login" className="underline">{t("signIn")}</Link></main>;
  if (me.data?.role !== "admin") return <main className="p-6">{t("permission")}</main>;
  return <main className="mx-auto max-w-3xl px-5 py-7 lg:px-8"><Link href="/en/catalog/products" className="text-sm underline">{list("back")}</Link><h1 className="mt-5 text-3xl font-semibold">{list("create")}</h1><p className="mt-2 text-sm text-muted">{list("createHint")}</p><form className="mt-7 grid gap-5 rounded-lg border p-6" onSubmit={(event) => { event.preventDefault(); create.mutate(); }}><label className="grid gap-1 text-sm">{t("sku")}<input className="rounded-md border bg-background px-3 py-2" required maxLength={100} value={sku} onChange={(event) => setSku(event.target.value)} /></label><label className="grid gap-1 text-sm">{t("name")}<input className="rounded-md border bg-background px-3 py-2" required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} /></label><button className="w-fit rounded-md bg-neutral-900 px-4 py-2.5 text-sm text-white disabled:opacity-40 dark:bg-neutral-100 dark:text-neutral-900" disabled={create.isPending || !sku.trim() || !name.trim()}>{create.isPending ? t("saving") : t("createProduct")}</button>{create.isError && <p role="alert" className="text-sm text-red-700">{t("saveError")}</p>}</form></main>;
}
