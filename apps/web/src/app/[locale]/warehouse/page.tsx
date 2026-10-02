import { WarehousePreviewPage } from "../../../components/warehouse-preview-page";

export default async function Page({ searchParams }: { searchParams: Promise<{ plan?: string }> }) {
  const { plan } = await searchParams;
  return <WarehousePreviewPage initialPlanId={plan} />;
}
