"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../lib/api/client";

const schema = z.object({ email: z.string().email(), password: z.string().min(8) });
type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const submit = form.handleSubmit(async (values) => {
    const result = await api.POST("/api/v1/auth/login", { body: values });
    if (result.error) { form.setError("root", { message: t("invalid") }); return; }
    router.push("/en/status");
  });
  return <main className="flex min-h-screen items-center justify-center bg-background px-6"><form onSubmit={submit} className="w-full max-w-sm rounded-lg border p-6"><h1 className="text-xl font-semibold">{t("title")}</h1><div className="mt-6 grid gap-4"><label className="grid gap-2 text-sm"><span>{t("email")}</span><input className="rounded-md border bg-transparent px-3 py-2" type="email" {...form.register("email")} /></label><label className="grid gap-2 text-sm"><span>{t("password")}</span><input className="rounded-md border bg-transparent px-3 py-2" type="password" {...form.register("password")} /></label>{form.formState.errors.root && <p className="text-sm text-red-700">{form.formState.errors.root.message}</p>}<button className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50" disabled={form.formState.isSubmitting}>{t("submit")}</button></div></form></main>;
}
