import { useTranslations } from "next-intl";

const examples = [
  { name: "EPAL 1", dimensions: "800 × 1200 mm" },
  { name: "EPAL 2", dimensions: "1200 × 1000 mm" },
  { name: "EPAL 3", dimensions: "1000 × 1200 mm" },
  { name: "EPAL 6", dimensions: "800 × 600 mm" },
];

export function PalletReference() {
  const t = useTranslations("palletReference");
  return <section className="mx-auto max-w-6xl px-5 pb-10 lg:px-8"><h2 className="text-lg font-semibold">{t("title")}</h2><p className="mt-2 max-w-3xl text-sm text-muted">{t("caution")}</p><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{examples.map((item) => <div key={item.name} className="rounded-lg border p-4"><p className="font-medium">{item.name}</p><p className="mt-1 text-sm text-muted">{item.dimensions}</p></div>)}</div><a className="mt-4 inline-block text-sm underline" href="https://www.epal-pallets.org/eu-en/media-centre/product-sheets" target="_blank" rel="noreferrer">{t("source")}</a></section>;
}
