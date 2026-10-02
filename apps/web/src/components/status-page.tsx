"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api/client";

export function StatusPage() {
  const t = useTranslations();
  const query = useQuery({ queryKey: ["me"], queryFn: async () => { const result = await api.GET("/api/v1/me"); if (result.error) throw new Error("unauthorized"); return result.data; }, retry: false });
  return <main className="min-h-screen bg-background text-foreground"><header className="border-b"><div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"><span className="font-semibold">{t("common.appName")}</span><span className="text-sm text-muted">{t("shell.phase")}</span></div></header><div className="mx-auto grid max-w-6xl gap-8 px-6 py-10 md:grid-cols-[220px_1fr]"><aside className="border-r pr-6"><p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted">{t("shell.workspace")}</p><Link href="/en/status" className="block rounded-md bg-muted px-3 py-2 text-sm">{t("shell.foundation")}</Link><Link href="/en/workspace" className="mt-2 block rounded-md px-3 py-2 text-sm hover:bg-muted">{t("workspace.title")}</Link><Link href="/en/planning" className="mt-2 block rounded-md px-3 py-2 text-sm hover:bg-muted">{t("planning.title")}</Link></aside><section><h1 className="text-2xl font-semibold">{t("status.title")}</h1><p className="mt-2 max-w-2xl text-muted">{t("status.description")}</p>{query.isLoading && <div className="mt-8 rounded-lg border p-5">{t("status.loading")}</div>}{query.isError && <div className="mt-8 rounded-lg border border-amber-300 bg-amber-50 p-5 text-amber-950">{t("status.unauthorized")} <Link className="ml-2 underline" href="/en/login">{t("status.signIn")}</Link></div>}{query.data && <div className="mt-8 grid gap-4 sm:grid-cols-3"><Info label={t("status.organization")} value={query.data.organization.name} /><Info label={t("status.role")} value={query.data.role} /><Info label={t("status.session")} value={t("status.connected")} /></div>}<div className="mt-8 rounded-lg border p-5"><p className="font-medium">{t("status.adminOnly")}</p><p className="mt-1 text-sm text-muted">{t("status.unavailable")}</p></div></section></div></main>;
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border p-4"><p className="text-xs uppercase tracking-wide text-muted">{label}</p><p className="mt-2 font-medium">{value}</p></div>; }
