"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ApiError,
  createJob,
  fetchJob,
  fetchRanking,
  shopPath,
  type RankingResponse,
} from "@/lib/api";
import { Seal } from "./Seal";

export function RankingScreen() {
  const params = useParams<{ city: string }>();
  const city = decodeURIComponent(params.city ?? "");
  const [data, setData] = useState<RankingResponse | null>(null);
  const [progress, setProgress] = useState("巷子探着…");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;

    function later(fn: () => void) {
      timer = window.setTimeout(fn, 2000);
    }

    async function showRanking() {
      const payload = await fetchRanking(city);
      if (cancelled) return;
      setData(payload);
      setError("");
      setProgress("");
    }

    async function pollJob() {
      try {
        const job = await fetchJob(city);
        if (cancelled) return;
        if (job.status === "done") {
          try {
            await showRanking();
          } catch {
            if (!cancelled) setError("这座城市没探到合适的馆子");
          }
          return;
        }
        if (job.status === "error") {
          setError(job.error || job.message || "探巷失败");
          return;
        }
        setProgress(job.message || "巷子探着…");
        later(() => {
          void pollJob();
        });
      } catch (exc: unknown) {
        if (cancelled) return;
        setError(exc instanceof ApiError ? exc.message : "巷子里暂时没回音");
      }
    }

    setData(null);
    setError("");
    setProgress("巷子探着…");

    void (async () => {
      try {
        await showRanking();
      } catch (exc: unknown) {
        if (cancelled) return;
        if (!(exc instanceof ApiError) || exc.status !== 404) {
          setError(exc instanceof ApiError ? exc.message : "巷子里暂时没回音");
          return;
        }
        try {
          await createJob(city);
          if (cancelled) return;
          await pollJob();
        } catch (start: unknown) {
          if (cancelled) return;
          setError(start instanceof ApiError ? start.message : "巷子里暂时没回音");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [city, retry]);

  if (error) {
    return (
      <main className="shell empty">
        <Seal />
        <p className="serif title" style={{ fontSize: 32 }}>
          巷探
        </p>
        <p className="tagline">{error}</p>
        <button type="button" className="pill" onClick={() => setRetry((n) => n + 1)}>
          再探一次
        </button>
        <Link href="/">回起点</Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="shell empty">
        <p className="tagline">巷子探着…</p>
        {progress ? <p className="note">{progress}</p> : null}
        <p className="note">可以先离开，过一会儿再来</p>
        <Link href="/">回起点</Link>
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
