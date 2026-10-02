import "../globals.css";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { Providers } from "../../components/providers";
import { AppShell } from "../../components/app-shell";

export default async function LocaleLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><NextIntlClientProvider messages={await getMessages()}><Providers><AppShell>{children}</AppShell></Providers></NextIntlClientProvider></body></html>;
}
