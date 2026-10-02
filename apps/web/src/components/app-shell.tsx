"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../lib/api/client";

const links = [
  { href: "/en/orders", key: "orders", roles: ["sales", "admin"] },
  { href: "/en/catalog/products", key: "products", roles: ["admin"] },
  { href: "/en/catalog/customers", key: "customers", roles: ["admin"] },
  { href: "/en/catalog/pallets", key: "pallets", roles: ["admin"] },
  { href: "/en/planning", key: "planning", roles: ["sales", "warehouse", "admin"] },
  { href: "/en/warehouse", key: "warehouse", roles: ["warehouse", "admin"] },
  { href: "/en/status", key: "status", roles: ["sales", "warehouse", "admin"] },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const client = useQueryClient();
  const t = useTranslations("nav");
  const common = useTranslations("common");
  const login = path.endsWith("/login");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => { setCollapsed(localStorage.getItem("pallet-building-sidebar-collapsed") === "true"); }, []);
  useEffect(() => { setMobileOpen(false); }, [path]);
  const me = useQuery({ queryKey: ["me"], queryFn: async () => {
    const result = await api.GET("/api/v1/me");
    if (!result.data) throw new Error("AUTH_REQUIRED");
    return result.data;
  }, enabled: !login, retry: false });
  if (login) return children;
  const role = me.data?.role ?? "";
  const visibleLinks = links.filter((link) => link.roles.some((allowed) => allowed === role));
  function toggleSidebar() {
    setCollapsed((current) => {
      localStorage.setItem("pallet-building-sidebar-collapsed", String(!current));
      return !current;
    });
  }
  async function signOut() {
    await api.POST("/api/v1/auth/logout");
    client.clear();
    router.push("/en/login");
  }
  const navigation = <nav aria-label={t("menu")} className="grid gap-1">
    {visibleLinks.map((link) => <Link key={link.href} href={link.href} aria-current={path === link.href || path.startsWith(`${link.href}/`) ? "page" : undefined} className={`rounded-md px-3 py-2.5 text-sm transition-colors ${path === link.href || path.startsWith(`${link.href}/`) ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900" : "text-muted hover:bg-muted hover:text-foreground"}`}>{t(link.key)}</Link>)}
  </nav>;
  return <div className="min-h-screen bg-background text-foreground md:flex">
    {mobileOpen && <button aria-label={t("closeMenu")} className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={() => setMobileOpen(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r bg-background px-4 py-6 transition-transform md:sticky md:top-0 md:z-auto md:h-screen md:shrink-0 md:transition-[width,padding] ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"} ${collapsed ? "md:w-0 md:overflow-hidden md:border-0 md:px-0" : "md:w-60"}`} aria-hidden={collapsed && !mobileOpen}>
      <div className="mb-7 flex items-center justify-between gap-2"><Link href="/en/status" className="px-3 text-lg font-semibold tracking-tight">{common("appName")}</Link><button className="rounded-md border px-2 py-1 text-sm md:hidden" onClick={() => setMobileOpen(false)} aria-label={t("closeMenu")}>×</button></div>
      {me.isLoading ? <p className="px-3 text-sm text-muted">{common("loading")}</p> : navigation}
      <div className="mt-auto border-t px-3 pt-4 text-sm"><p className="truncate font-medium">{me.data?.organization.name}</p><p className="mt-1 text-muted">{role}</p><button className="mt-4 rounded-md border px-3 py-2 text-sm hover:bg-muted" onClick={signOut}>{common("signOut")}</button></div>
    </aside>
    <div className="min-w-0 flex-1"><header className="flex items-center gap-3 border-b px-5 py-3"><button className="rounded-md border px-3 py-2 text-sm hover:bg-muted md:hidden" onClick={() => setMobileOpen(true)} aria-label={t("openMenu")} aria-expanded={mobileOpen}>☰</button><button className="hidden rounded-md border px-3 py-2 text-sm hover:bg-muted md:inline-flex" onClick={toggleSidebar} aria-label={collapsed ? t("showMenu") : t("hideMenu")} aria-expanded={!collapsed}>{collapsed ? "☰" : "‹"}</button><Link href="/en/status" className="font-semibold">{common("appName")}</Link></header>{children}</div>
  </div>;
}
