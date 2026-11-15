import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "馆子",
};

export default function ShopLayout({
  children,
}: LayoutProps<"/c/[city]/[poiId]">) {
  return children;
}
