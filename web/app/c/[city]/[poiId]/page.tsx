import { Suspense } from "react";
import { ShopScreen } from "@/components/ShopScreen";

export default function Page() {
  return (
    <Suspense
      fallback={
        <main className="shell empty">
          <p className="tagline">巷子探着…</p>
        </main>
      }
    >
      <ShopScreen />
    </Suspense>
  );
}
