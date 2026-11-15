"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, cityPath, fetchShop, type ShopCard } from "@/lib/api";
import { Seal } from "./Seal";

function mapUrl(shop: ShopCard) {
  if (!shop.lng || !shop.lat) return "";
  const query = new URLSearchParams({
    position: `${shop.lng},${shop.lat}`,
    name: shop.name || shop.name_raw,
  });
  return `https://uri.amap.com/marker?${query.toString()}`;
}

export function ShopScreen() {
  const params = useParams<{ city: string; poiId: string }>();
  const city = decodeURIComponent(params.city ?? "");
  const poiId = decodeURIComponent(params.poiId ?? "");
  const [shop, setShop] = useState<ShopCard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchShop(city, poiId)
      .then((payload) => {
        if (!cancelled) setShop(payload);
      })
      .catch((exc: unknown) => {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : "巷子里暂时没回音");
      });
    return () => {
      cancelled = true;
    };
  }, [city, poiId]);

  if (error) {
    return (
      <main className="shell empty">
        <Seal />
        <p className="serif title" style={{ fontSize: 32 }}>
          巷探
        </p>
        <p className="tagline">{error}</p>
        <Link href={cityPath(city)}>回榜单</Link>
      </main>
    );
  }

  if (!shop) {
    return (
      <main className="shell empty">
        <p className="tagline">巷子探着…</p>
      </main>
    );
  }

  const map = mapUrl(shop);

  return (
    <main className="shell shop">
      <Link href={cityPath(city)} className="back">
        ← {city}榜单
      </Link>
      <p className="shop-rank">
        第 {shop.rank} 名
        {shop.score != null ? ` · ${shop.score.toFixed(1)}` : ""}
      </p>
      <h1 className="serif shop-title">{shop.name}</h1>
      <p className="shop-address">{[shop.district, shop.address].filter(Boolean).join(" · ")}</p>
      {map ? (
        <a className="map-link" href={map} target="_blank" rel="noreferrer">
          在地图上看位置
        </a>
      ) : null}

      {shop.reason ? <p className="shop-reason">{shop.reason}</p> : null}

      {shop.dishes.length ? (
        <section className="shop-block">
          <h2>可点</h2>
          <p>{shop.dishes.join("、")}</p>
        </section>
      ) : null}

      {shop.keywords.length ? (
        <section className="shop-block">
          <h2>街坊怎么说</h2>
          <div className="pills shop-pills">
            {shop.keywords.map((word) => (
              <span key={word} className="pill">
                {word}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {shop.evidence.length ? (
        <section className="shop-block">
          <h2>出处</h2>
          <ul className="evidence">
            {shop.evidence.map((item) => (
              <li key={`${item.url}-${item.quote}`}>
                <blockquote>{item.quote}</blockquote>
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    原文
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
