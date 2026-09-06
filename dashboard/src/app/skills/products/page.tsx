import { ErrorPanel, PageHeader } from "@/components/panel";
import { ProductCompareBrowser } from "@/components/product-compare-browser";
import { getSkillEntries } from "@/lib/api";
import type { ProductListing } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Product Comparisons — LOOM",
};

export default async function ProductsPage() {
  const entries = await getSkillEntries<ProductListing>("products", {
    limit: 200,
    sort: "recent",
  });

  return (
    <div className="flex flex-col gap-lg">
      <PageHeader
        title="Product Comparisons"
        description="Listings captured from shopping pages, with prices normalised for ranking and specs lined up on one grid. Export opens as a spreadsheet."
      />

      {!entries.ok ? (
        <ErrorPanel title="Could not load products" error={entries.error} />
      ) : (
        <ProductCompareBrowser initialEntries={entries.data} />
      )}
    </div>
  );
}
