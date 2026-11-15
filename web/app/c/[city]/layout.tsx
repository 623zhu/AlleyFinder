import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "巷子",
};

export default function CityLayout({ children }: LayoutProps<"/c/[city]">) {
  return children;
}
