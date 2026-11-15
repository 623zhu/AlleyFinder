"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { HOT_CITIES, normalizeCityName } from "@/lib/cities";
import { cityPath } from "@/lib/api";
import { Seal } from "./Seal";

export function HomeScreen() {
  const router = useRouter();
  const [city, setCity] = useState("武汉");
  const [error, setError] = useState("");

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const name = normalizeCityName(city);
    if (!name) {
      setError("先写一座城市");
      return;
    }
    setError("");
    router.push(cityPath(name));
  }

  return (
    <main className="shell home">
      <header className="hero">
        <Seal />
        <p className="kicker">街坊口碑 · 小店指南</p>
        <h1 className="serif title">巷探</h1>
        <p className="tagline">找藏在巷子里的好味道</p>
      </header>

      <form className="form" onSubmit={submit}>
        <label className="label" htmlFor="city">
          从哪座城市开始？
        </label>
        <div className="city-field">
          <span className="pin" aria-hidden>
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path
                fill="currentColor"
                d="M12 2.5c-3.7 0-6.7 3-6.7 6.7 0 4.6 6.7 12.3 6.7 12.3s6.7-7.7 6.7-12.3c0-3.7-3-6.7-6.7-6.7zm0 9.1a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8z"
              />
            </svg>
          </span>
          <input
            id="city"
            value={city}
            onChange={(event) => {
              setCity(event.target.value);
              setError("");
            }}
            placeholder="输入城市"
            autoComplete="off"
          />
        </div>
        {error ? <p className="error">{error}</p> : null}

        <button className="cta" type="submit">
          开始找馆子 <span aria-hidden>→</span>
        </button>

        <p className="hot-label">热门巷子</p>
        <div className="pills">
          {HOT_CITIES.map((name) => (
            <button
              key={name}
              type="button"
              className={name === city.trim() ? "pill on" : "pill"}
              onClick={() => {
                setCity(name);
                setError("");
              }}
            >
              {name}
            </button>
          ))}
        </div>
      </form>

      <p className="footer">第一次探一座城大约要几分钟，可以先离开再回来</p>
    </main>
  );
}
