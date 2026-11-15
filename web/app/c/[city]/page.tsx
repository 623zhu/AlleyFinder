import { Suspense } from "react";
import { RankingScreen } from "@/components/RankingScreen";
import { HOT_CITIES } from "@/lib/cities";

export function generateStaticParams() {
  return HOT_CITIES.map((city) => ({ city }));
}

export default function Page() {
  return (
    <Suspense
      fallback={
        <main className="shell empty">
          <p className="tagline">巷子探着…</p>
        </main>
      }
    >
      <RankingScreen />
    </Suspense>
  );
}
