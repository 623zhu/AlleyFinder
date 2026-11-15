"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, fetchRanking, shopPath, type RankingResponse } from "@/lib/api";
import { Seal } from "./Seal";

export function RankingScreen() {
  const params = useParams<{ city: string }>();
  const city = decodeURIComponent(params.city ?? "");
  const [data, setData] = useState<RankingResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchRanking(city)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((exc: unknown) => {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : "巷子里暂时没回音");
      });
    return () => {
      cancelled = true;
    };
  }, [city]);

  if (error) {
    return (
      <main className="shell empty">
        <Seal />
        <p className="serif title" style={{ fontSize: 32 }}>
          巷探
        </p>
        <p className="tagline">{error}</p>
        <Link href="/">回起点</Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="shell empty">
        <p className="tagline">巷子探着…</p>
      </main>
    );
  }

  return (
    <main className="shell ranking">
      <header className="rank-head">
        <Link href="/" className="back">
          ← 换城市
        </Link>
        <p className="kicker">{data.city} · {data.count} 家</p>
        <h1 className="serif rank-title">{data.city}巷子</h1>
        <p className="tagline">不看装修和热度，只找街坊愿意再吃的小馆子</p>
      </header>
      <ol className="rank-list">
        {data.shops.map((shop) => (
          <li key={shop.poi_id}>
            <Link className="rank-card" href={shopPath(data.city, shop.poi_id)}>
              <div className="rank-card-top">
                <span className="rank-num">{shop.rank}</span>
                <strong className="rank-name">{shop.name}</strong>
                {shop.score != null ? <span className="rank-score">{shop.score.toFixed(1)}</span> : null}
              </div>
              <p className="rank-meta">
                {[shop.district, shop.address].filter(Boolean).join(" · ")}
              </p>
              {shop.dishes.length ? (
                <p className="rank-dishes">{shop.dishes.join(" / ")}</p>
              ) : null}
              {shop.reason ? <p className="rank-reason">{shop.reason}</p> : null}
            </Link>
          </li>
        ))}
      </ol>
    </main>
  );
}
