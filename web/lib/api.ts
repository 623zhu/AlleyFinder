import { normalizeCityName } from "./cities";

export type Evidence = {
  quote: string;
  url: string;
};

export type ShopCard = {
  rank: number;
  name: string;
  name_raw: string;
  poi_id: string;
  address: string;
  district: string;
  cityname: string;
  type: string;
  lng: string;
  lat: string;
  score: number | null;
  reason: string;
  dishes: string[];
  keywords: string[];
  evidence: Evidence[];
  taste: string | null;
  environment: string | null;
  price: string | null;
  price_hint: string | null;
  is_old_shop: boolean | null;
};

export type RankingResponse = {
  city: string;
  count: number;
  shops: ShopCard[];
};

export type JobStatus = {
  city: string;
  status: "idle" | "queued" | "running" | "done" | "error" | string;
  stage: string;
  message: string;
  error: string | null;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function readError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) return payload.detail;
  } catch {
    /* ignore */
  }
  return "巷子里暂时没回音";
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as T;
}

export function cityPath(city: string) {
  return `/c/${encodeURIComponent(normalizeCityName(city))}`;
}

export function shopPath(city: string, poiId: string) {
  return `${cityPath(city)}/${encodeURIComponent(poiId)}`;
}

export function fetchRanking(city: string) {
  return getJson<RankingResponse>(
    `/api/cities/${encodeURIComponent(normalizeCityName(city))}/ranking`,
  );
}

export function fetchShop(city: string, poiId: string) {
  return getJson<ShopCard>(
    `/api/cities/${encodeURIComponent(normalizeCityName(city))}/shops/${encodeURIComponent(poiId)}`,
  );
}

function jobPath(city: string) {
  return `/api/cities/${encodeURIComponent(normalizeCityName(city))}/jobs`;
}

export function fetchJob(city: string) {
  return getJson<JobStatus>(jobPath(city));
}

export function createJob(city: string) {
  return getJson<JobStatus>(jobPath(city), { method: "POST" });
}
